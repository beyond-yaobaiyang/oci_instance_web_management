import oci
import logging
from typing import List, Dict, Optional, Any
from config.config import config
import yaml
import os

class TenantService:
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')
        self.tenants_path = os.path.join(self.config_dir, 'tenants.yml')

    def _read_tenants(self) -> Dict[str, Any]:
        """读取租户配置文件"""
        try:
            with open(self.tenants_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data if data else {'tenants': []}
        except FileNotFoundError:
            return {'tenants': []}
        except Exception as e:
            logging.error(f"读取租户配置失败: {str(e)}")
            return {'tenants': []}

    def _write_tenants(self, data: Dict[str, Any]) -> bool:
        """写入租户配置文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.tenants_path), exist_ok=True)
            
            # 写入配置
            with open(self.tenants_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
            
            # 重新加载配置
            config.reload()
            return True
        except Exception as e:
            logging.error(f"写入租户配置失败: {str(e)}")
            return False

    def get_all_tenants(self) -> List[Dict[str, Any]]:
        """获取所有租户配置"""
        config_data = self._read_tenants()
        tenants = config_data.get('tenants', [])
        return [
            {
                'id': str(i + 1),  # 使用从1开始的索引
                'name': tenant.get('name', f'tenant{i+1}'),
                'user_ocid': tenant.get('user_ocid'),
                'fingerprint': tenant.get('fingerprint'),
                'key_file': tenant.get('key_file'),
                'tenancy': tenant.get('tenancy'),
                'region': tenant.get('region'),
                'description': tenant.get('description', ''),
                'compartment_id': tenant.get('compartment_id', tenant.get('tenancy'))  # 如果没有设置，使用tenancy作为默认值
            }
            for i, tenant in enumerate(tenants)
        ]

    def get_tenant_config(self, tenant_name: str) -> Optional[Dict[str, Any]]:
        """根据租户名称获取租户配置"""
        config_data = self._read_tenants()
        for tenant in config_data.get('tenants', []):
            if tenant.get('name') == tenant_name:
                return tenant
        return None

    def get_tenant_by_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取租户配置"""
        try:
            tenant_idx = int(tenant_id) - 1
            config_data = self._read_tenants()
            tenants = config_data.get('tenants', [])
            
            if 0 <= tenant_idx < len(tenants):
                tenant = tenants[tenant_idx]
                return {
                    'id': tenant_id,
                    'name': tenant.get('name', f'tenant{tenant_id}'),
                    'user_ocid': tenant.get('user_ocid'),
                    'fingerprint': tenant.get('fingerprint'),
                    'key_file': tenant.get('key_file'),
                    'tenancy': tenant.get('tenancy'),
                    'region': tenant.get('region'),
                    'compartment_id': tenant.get('compartment_id', tenant.get('tenancy'))  # 如果没有设置，使用tenancy作为默认值
                }
        except (ValueError, IndexError) as e:
            logging.error(f"获取租户配置失败: {str(e)}")
        return None

    def create_tenant(self, tenant_data: Dict[str, Any]) -> bool:
        """创建租户配置"""
        try:
            # 读取现有配置
            config_data = self._read_tenants()
            tenants = config_data.get('tenants', [])
            
            # 设置区间ID为租户OCID
            tenant_data['compartment_id'] = tenant_data.get('tenancy')
            
            # 添加新租户
            tenants.append(tenant_data)
            config_data['tenants'] = tenants
            
            # 写入配置
            return self._write_tenants(config_data)
        except Exception as e:
            logging.error(f"创建租户失败: {str(e)}")
            return False

    def update_tenant(self, tenant_id: str, tenant_data: Dict[str, Any]) -> bool:
        """更新租户配置"""
        try:
            tenant_idx = int(tenant_id) - 1
            config_data = self._read_tenants()
            tenants = config_data.get('tenants', [])
            
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
                
                # 写入文件
                return self._write_tenants(config_data)
                
        except Exception as e:
            logging.error(f"更新租户失败: {str(e)}")
        return False

    def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户配置"""
        try:
            tenant_idx = int(tenant_id) - 1
            config_data = self._read_tenants()
            tenants = config_data.get('tenants', [])
            
            if 0 <= tenant_idx < len(tenants):
                # 删除租户配置
                del tenants[tenant_idx]
                
                # 写入文件
                return self._write_tenants(config_data)
                
        except Exception as e:
            logging.error(f"删除租户失败: {str(e)}")
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
