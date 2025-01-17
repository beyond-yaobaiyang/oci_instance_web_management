"""订阅服务模块"""
import oci
from typing import List, Dict, Any
from app.services.tenant_service import TenantService

class SubscriptionService:
    """订阅服务类"""
    
    def __init__(self):
        self.tenant_service = TenantService()
    
    def get_subscribed_services(self, tenant_name: str) -> List[Dict[str, Any]]:
        """
        获取指定租户的订阅服务列表
        
        Args:
            tenant_name: 租户名称
            
        Returns:
            List[Dict[str, Any]]: 订阅服务列表
        """
        try:
            # 获取租户配置
            tenant_config = self.tenant_service.get_tenant_config(tenant_name)
            if not tenant_config:
                raise ValueError(f"未找到租户配置: {tenant_name}")
            
            # 创建 OCI 客户端
            config = {
                "user": tenant_config["user_ocid"],
                "key_file": tenant_config["key_file"],
                "fingerprint": tenant_config["fingerprint"],
                "tenancy": tenant_config["tenancy"],
                "region": tenant_config["region"]
            }
            
            # 初始化订阅客户端
            subscription_client = oci.tenant_manager_control_plane.SubscriptionClient(config)
            
            # 获取订阅列表
            response = subscription_client.list_subscriptions(
                compartment_id=tenant_config["tenancy"]
            ).data
            
            # 处理订阅信息
            subscribed_services = []
            for subscription in response.items:
                # 格式化日期
                start_date = subscription.start_date.strftime('%Y-%m-%d') if subscription.start_date else '未知'
                end_date = subscription.end_date.strftime('%Y-%m-%d') if subscription.end_date else '永久'
                
                # 获取付费模式
                payment_model = subscription.payment_model if subscription.payment_model else (
                    '传统订阅' if subscription.is_classic_subscription else '未知'
                )
                
                subscribed_services.append({
                    'name': subscription.service_name,
                    'description': f'Oracle Cloud Infrastructure {subscription.service_name} 服务',
                    'contract_value': payment_model,
                    'start_date': start_date,
                    'end_date': end_date,
                    'status': subscription.lifecycle_state
                })
            
            return subscribed_services
            
        except Exception as e:
            print(f"获取订阅服务列表时出错: {str(e)}")
            raise
    
    def get_subscription_summary(self, tenant_name: str) -> Dict[str, Any]:
        """
        获取订阅服务的汇总信息
        
        Args:
            tenant_name: 租户名称
            
        Returns:
            Dict[str, Any]: 订阅汇总信息
        """
        try:
            services = self.get_subscribed_services(tenant_name)
            
            # 统计信息
            active_services = [s for s in services if s['status'] == 'ACTIVE']
            summary = {
                'total_services': len(services),
                'active_services': len(active_services),
                'services': {
                    'total': len(services),
                    'active': len(active_services)
                }
            }
            
            return summary
            
        except Exception as e:
            print(f"获取订阅汇总信息时出错: {str(e)}")
            raise
