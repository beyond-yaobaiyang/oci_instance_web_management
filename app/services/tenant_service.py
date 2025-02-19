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
        
        # 为每个租户验证配置
        validated_tenants = []
        for i, tenant in enumerate(tenants):
            is_valid = self.validate_tenant_config(tenant)
            tenant_info = {
                'id': str(i + 1),  # 使用从1开始的索引
                'name': tenant.get('name', f'tenant{i+1}'),
                'user_ocid': tenant.get('user_ocid'),
                'fingerprint': tenant.get('fingerprint'),
                'key_file': tenant.get('key_file'),
                'tenancy': tenant.get('tenancy'),
                'region': tenant.get('region'),
                'description': tenant.get('description', ''),
                'compartment_id': tenant.get('compartment_id', tenant.get('tenancy')),
                'status': '有效' if is_valid else '无效'
            }
            validated_tenants.append(tenant_info)
        
        return validated_tenants

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
                    'tenancy': tenant.get('tenancy'),
                    'region': tenant.get('region'),
                    'key_file': tenant.get('key_file'),
                    'compartment_id': tenant.get('compartment_id', tenant.get('tenancy')),  
                    'iscopy': tenant.get('iscopy', False)
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
                    'tenancy': tenant_data['tenancy'],
                    'region': tenant_data['region'],
                    'key_file': tenant_data['key_file'],
                    'compartment_id': tenant_data.get('compartment_id')
                })
                
                # 写入文件
                return self._write_tenants(config_data)
                
        except Exception as e:
            logging.error(f"更新租户失败: {str(e)}")
        return False

    def delete_tenant(self, tenant_id: str) -> bool:
        """
        删除租户
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 获取租户信息以获取密钥文件路径
            tenant = self.get_tenant_by_id(tenant_id)
            if not tenant:
                return False
            print(tenant)
            # 删除密钥文件
            if  tenant.get('iscopy') != True:
                key_file = tenant.get('key_file')
                if key_file and os.path.exists(key_file):
                    try:
                        os.remove(key_file)
                        logging.info(f"已删除密钥文件: {key_file}")
                    except Exception as e:
                        logging.error(f"删除密钥文件失败: {str(e)}")
                        # 继续执行，不因为删除文件失败而中断整个删除操作
            
            # 从配置文件中删除租户
            config_data = self._read_tenants()
            tenants = config_data.get('tenants', [])
            tenant_idx = int(tenant_id) - 1
            
            if 0 <= tenant_idx < len(tenants):
                del tenants[tenant_idx]
                success = self._write_tenants(config_data)
                if success:
                    logging.info(f"已删除租户: {tenant_id}")
                return success
                
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

    def validate_tenant_config(self, tenant: Dict[str, Any]) -> bool:
        """验证租户配置是否有效"""
        try:
            # 首先检查必要字段是否存在
            required_fields = ['user_ocid', 'fingerprint', 'tenancy', 'region', 'key_file']
            if not all(tenant.get(field) for field in required_fields):
                return False

            # 读取私钥文件
            try:
                with open(tenant['key_file'], 'r') as f:
                    private_key = f.read()
            except Exception as e:
                logging.error(f"读取私钥文件失败: 私钥不存在", exc_info=True)
                return False

            # 创建OCI配置
            config = {
                "user": tenant['user_ocid'],
                "key_content": private_key,
                "fingerprint": tenant['fingerprint'],
                "tenancy": tenant['tenancy'],
                "region": tenant['region']
            }

            # 尝试创建身份客户端并调用API
            try:
                identity_client = oci.identity.IdentityClient(config)
                # 尝试获取用户信息，这将验证配置是否正确
                identity_client.get_user(tenant['user_ocid']).data
                return True
            except Exception as e:
                logging.error(f"验证租户配置失败: 配置无效或账户已被封号", exc_info=True)
                return False

        except Exception as e:
            logging.error(f"验证租户配置时发生错误: 配置无效或账户已被封号", exc_info=True)
            return False

    def get_tenant_statistics(self) -> Dict[str, Any]:
        """获取租户配置统计信息"""
        tenants = self._read_tenants().get('tenants', [])
        total_count = len(tenants)
        
        # 遍历所有租户并验证配置
        valid_tenants = []
        for tenant in tenants:
            if self.validate_tenant_config(tenant):
                valid_tenants.append(tenant)
        
        valid_count = len(valid_tenants)
        invalid_count = total_count - valid_count

        return {
            'total_count': total_count,
            'valid_count': valid_count,
            'invalid_count': invalid_count
        }
