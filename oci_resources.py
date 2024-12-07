import yaml
import logging
from flask import jsonify, request
from flask_login import login_required
import oci

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
    tenants = config.get('tenants', [])
    
    # 如果是字典格式，转换为列表
    if isinstance(tenants, dict):
        tenants = [
            {**tenant_info, 'name': tenant_name}
            for tenant_name, tenant_info in tenants.items()
        ]
    
    return tenants

def get_tenant_config(tenant_name=None):
    """
    获取指定租户的配置信息
    
    :param tenant_name: 租户名称，如果为 None 则使用第一个租户
    :return: 租户配置字典
    """
    try:
        # 读取租户配置
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # 解析租户配置
        tenants = parse_tenants_config(config)
        
        # 如果没有指定租户，使用第一个租户
        if not tenant_name:
            tenant_name = tenants[0]['name']
        
        # 查找指定租户的配置
        tenant_config = next((t for t in tenants if t['name'] == tenant_name), None)
        
        if not tenant_config:
            raise ValueError(f"未找到租户 {tenant_name} 的配置")
        
        return tenant_config
    except Exception as e:
        logger.error(f"获取租户配置时发生错误: {e}")
        raise

def create_oci_client_config(tenant_config, region=None):
    """
    根据租户配置创建 OCI 客户端配置
    
    :param tenant_config: 租户配置字典
    :param region: 区域（可选）
    :return: OCI 客户端配置字典
    """
    # 如果没有指定区域，使用租户的第一个区域
    if not region and tenant_config.get('regions'):
        region = tenant_config['regions'][0]
    
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
    
    return config_dict

def get_vcns(tenant_name=None, region=None):
    """
    获取指定租户和区域的虚拟云网络(VCN)列表
    
    :param tenant_name: 租户名称
    :param region: 区域
    :return: VCN列表
    """
    try:
        # 获取租户配置
        tenant_config = get_tenant_config(tenant_name)
        if not tenant_config:
            return []
        
        # 创建 OCI 网络客户端配置
        config_dict = create_oci_client_config(tenant_config, region)
        
        virtual_network_client = oci.core.VirtualNetworkClient(config_dict)
        
        # 获取 VCN 列表
        vcns = virtual_network_client.list_vcns(
            compartment_id=tenant_config.get('tenancy')
        ).data
        
        # 格式化 VCN 信息
        vcns_list = [
            {
                'id': vcn.id,
                'display_name': vcn.display_name,
                'cidr_block': vcn.cidr_block,
                'state': vcn.lifecycle_state
            }
            for vcn in vcns
        ]
        
        return vcns_list
    
    except Exception as e:
        logger.error(f"获取 VCN 列表失败: {e}", exc_info=True)
        return []

def get_subnets(tenant_name=None, region=None, vcn_id=None):
    """
    获取指定 VCN 下的子网列表
    
    :param tenant_name: 租户名称
    :param region: 区域
    :param vcn_id: 虚拟云网络 ID
    :return: 子网列表
    """
    try:
        # 获取租户配置
        tenant_config = get_tenant_config(tenant_name)
        if not tenant_config:
            return []
        
        # 如果没有指定区域，使用租户配置中的第一个区域
        if not region and tenant_config.get('regions'):
            region = tenant_config['regions'][0]
        
        # 创建 OCI 网络客户端配置
        config_dict = create_oci_client_config(tenant_config, region)
        
        virtual_network_client = oci.core.VirtualNetworkClient(config_dict)
        
        # 获取子网列表
        subnets = virtual_network_client.list_subnets(
            compartment_id=tenant_config.get('tenancy'),
            vcn_id=vcn_id if vcn_id else None
        ).data
        
        # 格式化子网信息
        subnets_list = [
            {
                'id': subnet.id,
                'display_name': subnet.display_name,
                'cidr_block': subnet.cidr_block,
                'availability_domain': subnet.availability_domain,
                'state': subnet.lifecycle_state
            }
            for subnet in subnets
        ]
        
        return subnets_list
    
    except Exception as e:
        logger.error(f"获取子网列表失败: {e}", exc_info=True)
        return []

def get_network_security_groups(tenant_name=None, region=None, vcn_id=None):
    """
    获取网络安全组列表
    
    :param tenant_name: 租户名称
    :param region: 区域
    :param vcn_id: 虚拟云网络 ID（可选）
    :return: 网络安全组列表
    """
    try:
        # 获取租户配置
        tenant_config = get_tenant_config(tenant_name)
        if not tenant_config:
            return []
        
        # 创建 OCI 网络客户端配置
        config_dict = create_oci_client_config(tenant_config, region)
        
        virtual_network_client = oci.core.VirtualNetworkClient(config_dict)
        
        # 获取网络安全组列表
        nsgs = virtual_network_client.list_network_security_groups(
            compartment_id=tenant_config.get('tenancy'),
            vcn_id=vcn_id if vcn_id else None
        ).data
        
        # 格式化网络安全组信息
        nsgs_list = [
            {
                'id': nsg.id,
                'display_name': nsg.display_name,
                'state': nsg.lifecycle_state
            }
            for nsg in nsgs
        ]
        
        return nsgs_list
    
    except Exception as e:
        logger.error(f"获取网络安全组列表失败: {e}", exc_info=True)
        return []

def get_shapes(tenant_name=None, region=None, availability_domain=None):
    """
    获取指定租户、区域和可用域的实例形状列表
    
    :param tenant_name: 租户名称
    :param region: 区域
    :param availability_domain: 可用域
    :return: 实例形状列表
    """
    try:
        # 获取租户配置
        tenant_config = get_tenant_config(tenant_name)
        if not tenant_config:
            return []
        
        # 创建 OCI 计算客户端配置
        config_dict = create_oci_client_config(tenant_config, region)
        
        compute_client = oci.core.ComputeClient(config_dict)
        
        # 获取实例形状列表
        shapes = compute_client.list_shapes(
            compartment_id=tenant_config.get('tenancy')
        ).data
        
        # 过滤形状
        filtered_shapes = []
        for shape in shapes:
            # 如果指定了可用域，检查形状是否在该可用域可用
            if availability_domain and not any(
                ad == availability_domain for ad in shape.availability_domains
            ):
                continue
            
            filtered_shapes.append({
                'name': shape.shape,
                'ocpus': shape.ocpus,
                'memory_in_gbs': shape.memory_in_gbs,
                'availability_domains': shape.availability_domains
            })
        
        # 按 OCPUs 和内存排序
        filtered_shapes.sort(key=lambda x: (x['ocpus'], x['memory_in_gbs']))
        
        return filtered_shapes
    
    except Exception as e:
        logger.error(f"获取实例形状列表失败: {e}", exc_info=True)
        return []
