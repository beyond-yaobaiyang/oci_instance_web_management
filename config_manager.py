import os
import sys
import yaml
import logging

# 打印 Python 路径
print("Python Path:", sys.path)
print("Current File:", os.path.abspath(__file__))

logger = logging.getLogger(__name__)

def parse_tenants_config(config):
    """
    解析租户配置，支持字典和列表两种格式
    
    字典格式示例：
    tenants:
      tenant1:
        name: tenant1
        display_name: 租户1
        regions: [...]
    
    列表格式示例：
    tenants:
      - name: tenant1
        display_name: 租户1
        regions: [...]
    """
    tenants = {}
    
    # 处理字典格式
    if isinstance(config, dict) and 'tenants' in config:
        if isinstance(config['tenants'], dict):
            return config['tenants']
        
        # 处理列表格式
        for tenant in config['tenants']:
            name = tenant.get('name') or tenant.get('display_name')
            if name:
                tenants[name] = tenant
    
    return tenants

def load_tenants_config(config_path=None):
    """
    加载租户配置文件
    
    :param config_path: 配置文件路径，默认为 'config/tenants.yaml'
    :return: 租户配置字典
    """
    if not config_path:
        config_path = os.path.join('config', 'tenants.yaml')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return parse_tenants_config(config)
    except FileNotFoundError:
        logger.error(f"租户配置文件未找到: {config_path}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"解析租户配置文件失败: {e}")
        return {}

def get_tenant_config(tenant_name):
    """
    获取特定租户的配置信息
    
    :param tenant_name: 租户名称
    :return: 租户配置字典
    """
    tenants_config = load_tenants_config()
    
    if tenant_name not in tenants_config:
        # 尝试查找大小写不敏感的匹配
        tenant_name_lower = tenant_name.lower()
        for key, value in tenants_config.items():
            if key.lower() == tenant_name_lower:
                return value
        
        logger.error(f"未找到租户配置: {tenant_name}")
        raise ValueError(f"未找到租户配置: {tenant_name}")
    
    return tenants_config[tenant_name]

def get_compartment_id(tenant_name):
    """
    获取租户的 Compartment ID
    
    :param tenant_name: 租户名称
    :return: Compartment ID
    """
    tenant_config = get_tenant_config(tenant_name)
    
    if 'compartment_ocid' not in tenant_config:
        logger.error(f"租户 {tenant_name} 未配置 compartment_ocid")
        raise ValueError(f"租户 {tenant_name} 未配置 compartment_ocid")
    
    return tenant_config['compartment_ocid']

def get_tenant_regions(tenant_name):
    """
    获取租户的可用区域
    
    :param tenant_name: 租户名称
    :return: 区域列表
    """
    tenant_config = get_tenant_config(tenant_name)
    
    if 'regions' not in tenant_config:
        logger.warning(f"租户 {tenant_name} 未配置区域")
        return []
    
    return tenant_config['regions']

def validate_tenant_config(tenant_name):
    """
    验证租户配置的完整性
    
    :param tenant_name: 租户名称
    :return: 是否验证通过
    """
    try:
        tenant_config = get_tenant_config(tenant_name)
        required_keys = [
            'user_ocid', 
            'private_key', 
            'fingerprint', 
            'tenancy_ocid', 
            'compartment_ocid'
        ]
        
        for key in required_keys:
            if key not in tenant_config or not tenant_config[key]:
                logger.error(f"租户 {tenant_name} 缺少必要配置: {key}")
                return False
        
        return True
    except Exception as e:
        logger.error(f"租户 {tenant_name} 配置验证失败: {e}")
        return False
