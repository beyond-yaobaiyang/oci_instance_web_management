import oci
from app.utils.tenant_config import get_tenant_config

def get_tenant_quotas(tenant_id):
    """获取租户的配额信息"""
    tenant_config = get_tenant_config(tenant_id)
    if not tenant_config:
        return None
    
    # 创建OCI客户端
    config = {
        "user": tenant_config["user_ocid"],
        "key_file": tenant_config["key_file"],
        "fingerprint": tenant_config["fingerprint"],
        "tenancy": tenant_config["tenancy"],
        "region": tenant_config["region"]
    }
    
    try:
        # 创建配额客户端
        limits_client = oci.limits.LimitsClient(config)
        quotas_client = oci.limits.QuotasClient(config)
        
        # 获取服务限制
        service_limits = []
        list_limit_definitions = limits_client.list_limit_definitions(
            compartment_id=tenant_config["compartment_id"],
            sort_by="name"
        )
        
        for limit in list_limit_definitions.data:
            # 获取当前使用量
            limit_value = limits_client.get_resource_availability(
                service_name=limit.service_name,
                limit_name=limit.name,
                compartment_id=tenant_config["compartment_id"]
            ).data
            
            service_limits.append({
                "service_name": limit.service_name,
                "limit_name": limit.name,
                "description": limit.description,
                "available": limit_value.available,
                "used": limit_value.used,
                "quota": limit_value.limit
            })
        
        # 获取自定义配额
        custom_quotas = []
        list_quotas = quotas_client.list_quotas(
            compartment_id=tenant_config["compartment_id"]
        ).data
        
        for quota in list_quotas:
            custom_quotas.append({
                "name": quota.name,
                "description": quota.description,
                "statements": quota.statements
            })
        
        return {
            "service_limits": service_limits,
            "custom_quotas": custom_quotas
        }
        
    except Exception as e:
        print(f"Error getting quotas: {str(e)}")
        return None
