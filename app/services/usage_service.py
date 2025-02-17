import oci
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from app.services.tenant_service import TenantService
from oci.usage_api.models import RequestSummarizedUsagesDetails, Filter, Dimension

class UsageService:
    """使用量查询服务"""

    def __init__(self):
        self.tenant_service = TenantService()

    def get_usage(self, tenant_id: str, start_time: str = None, end_time: str = None) -> List[Dict]:
        """
        获取资源使用量数据
        
        Args:
            tenant_id: 租户ID
            start_time: 开始时间，ISO格式
            end_time: 结束时间，ISO格式
            
        Returns:
            List[Dict]: 使用量数据列表
        """
        try:
            # 获取租户信息
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError(f"找不到租户: {tenant_id}")
                
            tenant_ocid = tenant.get('tenancy')
            if not tenant_ocid:
                raise ValueError(f"租户配置中缺少tenancy: {tenant_id}")

            # 创建OCI配置
            config = {
                "user": tenant.get("user_ocid"),
                "key_file": tenant.get("key_file"),
                "fingerprint": tenant.get("fingerprint"),
                "tenancy": tenant.get("tenancy"),
                "region": tenant.get("region")
            }

            # 创建Usage API客户端
            usage_client = oci.usage_api.UsageapiClient(config)

            # 将时间字符串转换为UTC datetime对象
            start_dt = datetime.strptime(start_time[:10], "%Y-%m-%d")
            start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
            
            end_dt = datetime.strptime(end_time[:10], "%Y-%m-%d")
            end_dt = end_dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"

            all_items = []
            next_page = None

            while True:
                # 构建查询请求
                request = oci.usage_api.models.RequestSummarizedUsagesDetails(
                    tenant_id=tenant_ocid,
                    time_usage_started=start_dt,
                    time_usage_ended=end_dt,
                    granularity="DAILY",
                    query_type="COST",
                    group_by=["service", "skuName", "unit"],  # 最多4个字段，我们只需要这3个
                    is_aggregate_by_time=True,
                    compartment_depth=1
                )

                # 发送请求
                response = usage_client.request_summarized_usages(
                    request_summarized_usages_details=request,
                    page=next_page,
                    limit=50
                )

                if response.data.items:
                    all_items.extend(response.data.items)

                next_page = response.next_page
                if not next_page:
                    break

            # 格式化数据
            return self._format_usage_data(all_items)

        except Exception as e:
            logging.error(f"获取使用量数据失败: {str(e)}")
            raise

    def _format_usage_data(self, items):
        """格式化使用量数据"""
        formatted_data = []
        
        # 创建SKU到单位的映射
        sku_unit_map = {}
        
        for item in items:
            # 确保数值字段不为None
            computed_quantity = getattr(item, 'computed_quantity', 0)
            if computed_quantity is None:
                computed_quantity = 0
                
            # 只处理有实际使用量的数据
            if float(computed_quantity) > 0:
                service = None
                sku_name = None
                unit = None
                
                # 从维度中获取信息
                if hasattr(item, 'dimensions'):
                    for dim in item.dimensions:
                        if dim.key == 'service':
                            service = dim.value
                        elif dim.key == 'skuName':
                            sku_name = dim.value
                        elif dim.key in ['unit', 'billingUnit', 'unitOfMeasure']:
                            unit = dim.value
                            break

                # 使用备用字段
                service = service or getattr(item, 'service', 'Unknown')
                sku_name = sku_name or getattr(item, 'sku_name', 'Unknown SKU')
                
                # 如果这个SKU已经有确定的单位，就使用它
                if sku_name in sku_unit_map:
                    unit = sku_unit_map[sku_name]
                # 否则，如果找到了新的单位，就记录下来
                elif unit:
                    sku_unit_map[sku_name] = unit
                # 如果还是没有单位，根据SKU名称推断
                else:
                    sku_name_upper = (sku_name or '').upper()
                    if any(word in sku_name_upper for word in ['OCPU', 'CPU']):
                        unit = 'OCPU Hours'
                    elif 'MEMORY' in sku_name_upper:
                        unit = 'GB Hours'
                    elif any(word in sku_name_upper for word in ['STORAGE', 'VOLUME', 'BACKUP']):
                        unit = 'GB Months'
                    elif any(word in sku_name_upper for word in ['BANDWIDTH', 'DATA TRANSFER', 'OUTBOUND']):
                        unit = 'GB'
                    elif 'DATABASE' in sku_name_upper:
                        unit = 'Instance Hours'
                    else:
                        unit = 'Units'  # 默认单位
                    sku_unit_map[sku_name] = unit
                
                # 处理费用
                computed_amount = getattr(item, 'computed_amount', 0)
                if computed_amount is None:
                    computed_amount = 0
                
                formatted_item = {
                    'service': service,
                    'sku_name': sku_name,
                    'quantity': float(computed_quantity),
                    'unit': unit,
                    'cost': float(computed_amount)
                }
                formatted_data.append(formatted_item)
        
        # 按SKU名称分组汇总
        grouped_data = {}
        for item in formatted_data:
            key = (item['sku_name'], item['unit'])  # 使用SKU名称和单位作为键
            if key not in grouped_data:
                grouped_data[key] = {
                    'service': item['service'],
                    'sku_name': item['sku_name'],
                    'total_quantity': 0,
                    'total_cost': 0,
                    'unit': item['unit']
                }
            grouped_data[key]['total_quantity'] += item['quantity']
            grouped_data[key]['total_cost'] += item['cost']
        
        # 转换为列表并排序
        result = list(grouped_data.values())
        return sorted(result, key=lambda x: (-x['total_cost'], x['service'], x['sku_name']))
