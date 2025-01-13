import oci
import logging
from typing import Dict, Any, Optional, List
from .tenant_service import TenantService

class QuotaService:
    def __init__(self):
        self.tenant_service = TenantService()

    def get_availability_domains(self, tenant_id: str) -> List[Dict[str, str]]:
        """获取租户的可用性域列表"""
        tenant_config = self.tenant_service.get_tenant_by_id(tenant_id)
        if not tenant_config:
            logging.error(f"未找到租户配置: {tenant_id}")
            raise ValueError(f"未找到租户配置: {tenant_id}")
        
        config = {
            "user": tenant_config["user_ocid"],
            "key_file": tenant_config["key_file"],
            "fingerprint": tenant_config["fingerprint"],
            "tenancy": tenant_config["tenancy"],
            "region": tenant_config["region"]
        }
        
        try:
            identity_client = oci.identity.IdentityClient(config)
            ad_list = identity_client.list_availability_domains(
                compartment_id=tenant_config["compartment_id"]
            ).data
            return [{"name": ad.name, "id": ad.name} for ad in ad_list]
        except Exception as e:
            logging.error(f"获取可用性域列表失败: {str(e)}")
            raise

    def get_services(self, tenant_id: str) -> List[Dict[str, str]]:
        """获取服务列表"""
        tenant_config = self.tenant_service.get_tenant_by_id(tenant_id)
        if not tenant_config:
            logging.error(f"未找到租户配置: {tenant_id}")
            raise ValueError(f"未找到租户配置: {tenant_id}")
        
        config = {
            "user": tenant_config["user_ocid"],
            "key_file": tenant_config["key_file"],
            "fingerprint": tenant_config["fingerprint"],
            "tenancy": tenant_config["tenancy"],
            "region": tenant_config["region"]
        }
        
        try:
            limits_client = oci.limits.LimitsClient(config)
            services = limits_client.list_services(
                compartment_id=tenant_config["tenancy"]
            ).data
            
            return [{"name": service.name, "description": service.description} for service in services]
        except Exception as e:
            logging.error(f"获取服务列表失败: {str(e)}")
            raise

    def get_service_quotas(self, tenant_id: str, service_name: str, availability_domain: Optional[str] = None) -> Dict[str, Any]:
        """获取特定服务的配额信息"""
        tenant_config = self.tenant_service.get_tenant_by_id(tenant_id)
        if not tenant_config:
            logging.error(f"未找到租户配置: {tenant_id}")
            raise ValueError(f"未找到租户配置: {tenant_id}")
        
        config = {
            "user": tenant_config["user_ocid"],
            "key_file": tenant_config["key_file"],
            "fingerprint": tenant_config["fingerprint"],
            "tenancy": tenant_config["tenancy"],
            "region": tenant_config["region"]
        }
        
        try:
            limits_client = oci.limits.LimitsClient(config)
            
            # 获取服务的限制值（处理分页）
            kwargs = {
                "compartment_id": tenant_config["tenancy"],
                "service_name": service_name
            }
            if availability_domain:
                kwargs["availability_domain"] = availability_domain
                
            # 使用分页获取所有限制值
            limits = []
            next_page = None
            while True:
                if next_page:
                    kwargs["page"] = next_page
                    
                response = limits_client.list_limit_values(**kwargs)
                limits.extend(response.data)
                
                # 检查是否有下一页
                if response.has_next_page:
                    next_page = response.next_page
                else:
                    break
                    
            logging.debug(f"获取到的限制值: {limits}")
            
            # 处理限制值
            service_limits = []
            for limit in limits:
                # 跳过配额为0的项目
                if not limit.value or int(limit.value) == 0:
                    logging.debug(f"跳过配额为0的项目: {limit.name}")
                    continue
                    
                limit_data = {
                    "service_name": service_name,
                    "limit_name": limit.name,
                    "scope_type": limit.scope_type,
                    "availability_domain": limit.availability_domain or "全局",
                    "quota": int(limit.value)  # 确保配额是整数
                }
                
                # 尝试获取资源使用情况
                try:
                    usage = limits_client.get_resource_availability(
                        compartment_id=tenant_config["tenancy"],
                        service_name=service_name,
                        limit_name=limit.name,
                        availability_domain=limit.availability_domain
                    ).data
                    
                    if usage:
                        used = int(usage.used) if hasattr(usage, 'used') else 0
                        available = int(usage.available) if hasattr(usage, 'available') else limit.value
                        
                        # 只有当配额为0时才跳过，不再过滤使用量为0的项目
                        if limit_data["quota"] == 0:
                            logging.debug(f"跳过配额为0的项目: {limit.name}")
                            continue
                            
                        limit_data.update({
                            "available": available,
                            "used": used,
                        })
                    else:
                        limit_data.update({
                            "available": int(limit.value),
                            "used": 0
                        })
                except Exception as e:
                    logging.debug(f"获取资源 {limit.name} 的使用情况失败（这可能是正常的）: {str(e)}")
                    limit_data.update({
                        "available": int(limit.value),
                        "used": 0
                    })
                
                # 添加使用率
                if limit_data["quota"] > 0:
                    limit_data["usage_rate"] = (limit_data["used"] / limit_data["quota"]) * 100
                else:
                    limit_data["usage_rate"] = 0
                
                service_limits.append(limit_data)
            
            # 按使用率降序排序
            service_limits.sort(key=lambda x: x["usage_rate"], reverse=True)
            
            logging.info(f"成功获取服务 {service_name} 的配额信息，共 {len(service_limits)} 条有效记录")
            return {
                "service_limits": service_limits,
                "service_name": service_name,
                "total_limits": len(service_limits)
            }
            
        except Exception as e:
            logging.error(f"获取服务配额失败: {str(e)}")
            raise

    def get_tenant_quotas(self, tenant_id: str, availability_domain: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取租户的配额信息"""
        tenant_config = self.tenant_service.get_tenant_by_id(tenant_id)
        if not tenant_config:
            logging.error(f"未找到租户配置: {tenant_id}")
            raise ValueError(f"未找到租户配置: {tenant_id}")
        
        config = {
            "user": tenant_config["user_ocid"],
            "key_file": tenant_config["key_file"],
            "fingerprint": tenant_config["fingerprint"],
            "tenancy": tenant_config["tenancy"],
            "region": tenant_config["region"]
        }
        
        try:
            # 创建Limits客户端
            limits_client = oci.limits.LimitsClient(config)
            
            # 获取服务限制定义
            service_limits = []
            try:
                limit_definitions = limits_client.list_limit_definitions(
                    compartment_id=tenant_config["tenancy"]
                ).data
                logging.info(f"成功获取到 {len(limit_definitions)} 个限制定义")
            except oci.exceptions.ServiceError as se:
                logging.error(f"获取限制定义失败 (ServiceError): {str(se)}")
                raise
            except Exception as e:
                logging.error(f"获取限制定义失败: {str(e)}")
                raise
            
            # 获取每个限制的具体值
            error_count = 0
            for limit in limit_definitions:
                try:
                    # 获取资源可用性
                    params = {
                        "service_name": limit.service_name,
                        "limit_name": limit.name,
                        "compartment_id": tenant_config["tenancy"]
                    }
                    
                    # 只有当scope_type为AD时才添加availability_domain参数
                    if limit.scope_type == "AD" and availability_domain:
                        params["availability_domain"] = availability_domain
                    
                    availability = limits_client.get_resource_availability(**params).data
                    
                    service_limits.append({
                        "service_name": limit.service_name,
                        "limit_name": limit.name,
                        "description": limit.description,
                        "scope_type": limit.scope_type,
                        "available": availability.available,
                        "used": getattr(availability, 'used', 0),
                        "quota": getattr(availability, 'fractional_availability', 0),
                        "availability_domain": availability_domain if availability_domain and limit.scope_type == "AD" else "全局"
                    })
                except oci.exceptions.ServiceError as se:
                    # 记录详细错误但继续处理其他限制
                    error_count += 1
                    logging.warning(f"获取资源 {limit.name} 的使用量失败 (ServiceError): {str(se)}")
                    continue
                except Exception as e:
                    error_count += 1
                    logging.warning(f"处理资源 {limit.name} 时发生错误: {str(e)}")
                    continue
            
            if error_count > 0:
                logging.warning(f"处理过程中有 {error_count} 个资源发生错误")
            
            if not service_limits:
                logging.warning("未能获取到任何服务限制信息")
                return {"service_limits": [], "custom_quotas": []}
            
            # 获取自定义配额
            quotas_client = oci.limits.QuotasClient(config)
            custom_quotas = []
            try:
                quotas = quotas_client.list_quotas(
                    compartment_id=tenant_config["compartment_id"]
                ).data
                
                for quota in quotas:
                    custom_quotas.append({
                        "name": quota.name,
                        "description": quota.description,
                        "statements": quota.statements
                    })
            except Exception as e:
                logging.warning(f"获取自定义配额失败: {str(e)}")
            
            return {
                "service_limits": service_limits,
                "custom_quotas": custom_quotas
            }
            
        except Exception as e:
            logging.error(f"获取配额信息失败: {str(e)}")
            raise
