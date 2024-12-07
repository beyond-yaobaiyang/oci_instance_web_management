import logging
import yaml
import oci
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_oci_images(tenant_name=None, region=None, os_type=None, tenant_config=None):
    """
    获取特定操作系统的 OCI 镜像列表
    
    :param tenant_name: 租户名称
    :param region: 区域
    :param os_type: 操作系统类型 ('oracle', 'centos', 'ubuntu')
    :param tenant_config: 直接传入的租户配置（可选）
    :return: 镜像列表
    """
    try:
        # 操作系统映射
        os_mapping = {
            'oracle': 'Oracle Linux',
            'centos': 'CentOS',
            'ubuntu': 'Canonical Ubuntu'
        }
        
        # 如果没有指定操作系统类型，返回空列表
        if not os_type or os_type not in os_mapping:
            return []

        # 如果没有传入租户配置，则从配置文件读取
        if not tenant_config:
            # 读取租户配置
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)
            
            # 如果没有指定租户，使用第一个租户
            if not tenant_name:
                tenant_name = config['tenants'][0]['name']
            
            # 找到对应的租户配置
            tenant_config = next((t for t in config['tenants'] if t['name'] == tenant_name), None)
            if not tenant_config:
                logger.error(f"未找到租户 {tenant_name}")
                return []
        
        # 如果没有指定区域，使用租户的第一个区域
        if not region and tenant_config.get('regions'):
            region = tenant_config['regions'][0]
        
        # 创建 OCI 计算客户端
        oci_config = {
            "user": tenant_config.get('user'),
            "key_file": tenant_config.get('key_file'),
            "fingerprint": tenant_config.get('fingerprint'),
            "tenancy": tenant_config.get('tenancy'),
            "region": region
        }
        
        config_dict = {
            "user": oci_config["user"],
            "key_content": open(oci_config["key_file"], "r").read(),
            "fingerprint": oci_config["fingerprint"],
            "tenancy": oci_config["tenancy"],
            "region": oci_config["region"]
        }
        
        compute_client = oci.core.ComputeClient(config_dict)
        
        # 获取镜像列表
        images = compute_client.list_images(
            compartment_id=tenant_config.get('tenancy'),
            operating_system=os_mapping[os_type],
            lifecycle_state=oci.core.models.Image.LIFECYCLE_STATE_AVAILABLE
        ).data
        
        # 处理镜像数据
        filtered_images = []
        for image in images:
            filtered_images.append({
                'id': image.id,
                'display_name': image.display_name,
                'operating_system': image.operating_system,
                'os_version': image.operating_system_version,
                'create_time': image.time_created.isoformat() if image.time_created else None
            })
        
        # 按创建时间排序，最新的在前
        filtered_images.sort(key=lambda x: x['create_time'] or '', reverse=True)
        
        return filtered_images
    
    except Exception as e:
        logger.error(f"获取镜像列表失败: {e}", exc_info=True)
        return []

def parse_tenants_config(config: Dict) -> List[Dict]:
    tenants = config.get('tenants', [])
    if isinstance(tenants, dict):
        tenants = [tenants]
    return tenants

def list_images(tenant_name: str, region: str, os_type: str) -> List[Dict]:
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        tenants = parse_tenants_config(config)
        
        tenant_config = next((tenant for tenant in tenants if tenant.get('name') == tenant_name), None)
        
        if not tenant_config:
            logger.warning(f"未找到租户: {tenant_name}")
            return []
        
        return get_oci_images(tenant_name, region, os_type, tenant_config)
    
    except Exception as e:
        logger.error(f"获取镜像列表发生未知错误: {e}", exc_info=True)
        return []

if __name__ == '__main__':
    try:
        print("开始调试镜像选择器...")
        
        with open('config.yaml', 'r') as f:
            config_content = f.read()
            print("\n配置文件内容:")
            print(config_content)
        
        test_tenants = ['zookejason']
        test_regions = ['ap-chuncheon-1']
        test_os_types = ['oracle', 'centos', 'ubuntu']
        
        for tenant_name in test_tenants:
            for region in test_regions:
                for os_type in test_os_types:
                    print(f"\n正在搜索 {tenant_name} {region} {os_type} 镜像:")
                    try:
                        images = list_images(tenant_name, region, os_type)
                        
                        print(f"找到 {len(images)} 个镜像:")
                        for image in images:
                            print(f"- ID: {image.get('id', 'N/A')}")
                            print(f"  显示名称: {image.get('display_name', 'N/A')}")
                            print(f"  操作系统: {image.get('operating_system', 'N/A')}")
                            print(f"  操作系统版本: {image.get('os_version', 'N/A')}")
                            print(f"  创建时间: {image.get('create_time', 'N/A')}")
                            print("---")
                    except Exception as search_error:
                        print(f"搜索 {tenant_name} {region} {os_type} 镜像时发生错误: {search_error}")
                        import traceback
                        traceback.print_exc()
    
    except Exception as e:
        print(f"调试失败: {e}")
        import traceback
        traceback.print_exc()
