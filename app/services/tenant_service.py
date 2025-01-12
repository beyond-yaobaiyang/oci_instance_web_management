import oci
import logging
from typing import List, Dict, Optional, Any
from config.config import config

class TenantService:
    def get_all_tenants(self) -> List[Dict[str, Any]]:
        """获取所有租户配置"""
        tenants = config.get('tenants', [])
        logging.debug(f"从配置文件获取的租户列表: {tenants}")
        return [
            {
                'id': str(i),
                'name': tenant.get('name', f'tenant{i}'),
                'user_ocid': tenant.get('user_ocid'),
                'fingerprint': tenant.get('fingerprint'),
                'key_file': tenant.get('key_file'),
                'tenancy': tenant.get('tenancy'),
                'region': tenant.get('region'),
                'compartment_id': tenant.get('compartment_id')
            }
            for i, tenant in enumerate(tenants, 1)
        ]
    
    def get_tenant_config(self, tenant_name: str) -> Optional[Dict[str, Any]]:
        """根据租户名称获取租户配置"""
        tenants = config.get('tenants', [])
        for tenant in tenants:
            if tenant.get('name') == tenant_name:
                return tenant
        return None
    
    def get_tenant_by_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取租户配置"""
        try:
            tenant_idx = int(tenant_id) - 1
            tenants = config.get('tenants', [])
            logging.debug(f"获取租户 {tenant_id} 的配置，所有租户: {tenants}")
            
            if 0 <= tenant_idx < len(tenants):
                tenant = tenants[tenant_idx]
                logging.debug(f"找到租户配置: {tenant}")
                result = {
                    'id': tenant_id,
                    'name': tenant.get('name', f'tenant{tenant_id}'),
                    'user_ocid': tenant.get('user_ocid'),
                    'fingerprint': tenant.get('fingerprint'),
                    'key_file': tenant.get('key_file'),
                    'tenancy': tenant.get('tenancy'),
                    'region': tenant.get('region'),
                    'compartment_id': tenant.get('compartment_id')
                }
                logging.debug(f"返回租户配置: {result}")
                return result
        except (ValueError, IndexError) as e:
            logging.error(f"获取租户配置失败: {str(e)}")
        return None
    
    def create_tenant(self, tenant_data: Dict[str, Any]) -> bool:
        """创建新租户"""
        try:
            tenants = config.get('tenants', [])
            
            # 创建新租户配置
            new_tenant = {
                'name': tenant_data['name'],
                'user_ocid': tenant_data['user_ocid'],
                'fingerprint': tenant_data['fingerprint'],
                'key_file': tenant_data['key_file'],
                'tenancy': tenant_data['tenancy'],
                'region': tenant_data['region'],
                'compartment_id': tenant_data.get('compartment_id')
            }
            logging.debug(f"创建新租户配置: {new_tenant}")
            
            # 添加到配置中
            tenants.append(new_tenant)
            logging.debug(f"添加新租户到配置中: {tenants}")
            return config.set('tenants', tenants)
            
        except Exception as e:
            logging.error(f"创建租户失败: {str(e)}", exc_info=True)
            return False
    
    def update_tenant(self, tenant_id: str, tenant_data: Dict[str, Any]) -> bool:
        """更新租户配置"""
        try:
            tenant_idx = int(tenant_id) - 1
            tenants = config.get('tenants', [])
            
            if 0 <= tenant_idx < len(tenants):
                # 更新租户配置
                tenants[tenant_idx].update({
                    'name': tenant_data['name'],
                    'user_ocid': tenant_data['user_ocid'],
                    'fingerprint': tenant_data['fingerprint'],
                    'key_file': tenant_data['key_file'],
                    'tenancy': tenant_data['tenancy'],
                    'region': tenant_data['region'],
                    'compartment_id': tenant_data.get('compartment_id')
                })
                logging.debug(f"更新租户配置: {tenants[tenant_idx]}")
                
                return config.set('tenants', tenants)
                
        except Exception as e:
            logging.error(f"更新租户失败: {str(e)}", exc_info=True)
            return False
        return False
    
    def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户配置"""
        try:
            tenant_idx = int(tenant_id) - 1
            tenants = config.get('tenants', [])
            
            if 0 <= tenant_idx < len(tenants):
                # 删除租户配置
                tenants.pop(tenant_idx)
                logging.debug(f"删除租户配置: {tenants}")
                return config.set('tenants', tenants)
                
        except Exception as e:
            logging.error(f"删除租户失败: {str(e)}", exc_info=True)
            return False
        return False
    
    def get_oci_client(self, tenant_id: str, service: str = "compute") -> Optional[Any]:
        """获取OCI客户端
        
        Args:
            tenant_id: 租户ID
            service: 服务类型，可选值：compute, network, identity等
        """
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            logging.error(f"获取OCI客户端失败：找不到租户 {tenant_id}")
            return None
        
        try:
            # 创建配置对象
            config = {
                "user": tenant['user_ocid'],
                "fingerprint": tenant['fingerprint'],
                "key_file": tenant['key_file'],
                "tenancy": tenant['tenancy'],
                "region": tenant['region']
            }
            logging.debug(f"创建配置对象: {config}")
            
            # 根据服务类型创建不同的客户端
            service_map = {
                "compute": oci.core.ComputeClient,
                "network": oci.core.VirtualNetworkClient,
                "identity": oci.identity.IdentityClient,
                "object_storage": oci.object_storage.ObjectStorageClient,
                "block_storage": oci.core.BlockstorageClient
            }
            
            client_class = service_map.get(service.lower())
            if not client_class:
                logging.error(f"不支持的服务类型: {service}")
                return None
            
            logging.info(f"正在使用配置创建 {service} 客户端：{config}")
            return client_class(config)
        except Exception as e:
            logging.error(f"创建OCI客户端失败: {str(e)}", exc_info=True)
            return None
