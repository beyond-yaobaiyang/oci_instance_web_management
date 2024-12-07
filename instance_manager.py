import oci
import base64
import logging
from typing import Dict, Optional, List

class OCIInstanceManager:
    def __init__(self, config: Dict):
        """
        Initialize OCI Instance Manager
        
        Args:
            config: OCI configuration dictionary with either key_content or key_file
        """
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        try:
            self.config = config.copy()
            
            # 如果提供了 key_file 而不是 key_content，读取密钥文件
            if 'key_file' in self.config and 'key_content' not in self.config:
                try:
                    with open(self.config['key_file'], 'r') as f:
                        self.config['key_content'] = f.read()
                except Exception as e:
                    raise ValueError(f"无法读取密钥文件: {str(e)}")
            
            # 验证必要的配置项
            required_keys = ['user', 'key_content', 'fingerprint', 'tenancy', 'region']
            missing_keys = [key for key in required_keys if key not in self.config]
            
            if missing_keys:
                raise ValueError(f"Missing required configuration keys: {', '.join(missing_keys)}")
            
            # 设置默认的 compartment_id
            if 'compartment_id' not in self.config:
                self.config['compartment_id'] = self.config['tenancy']
            
            # 初始化计算客户端
            self.compute_client = oci.core.ComputeClient(self.config)
            
            # 初始化网络客户端（用于获取 IP 信息）
            self.network_client = oci.core.VirtualNetworkClient(self.config)
            
            # 初始化身份客户端（用于获取区间信息）
            self.identity_client = oci.identity.IdentityClient(self.config)
            
            # 存储 compartment_id
            self.compartment_id = self.config['compartment_id']
            
        except Exception as e:
            self.logger.error(f"初始化失败: {str(e)}")
            raise
    
    def list_instances(self) -> List[Dict]:
        """
        获取实例列表
        
        Returns:
            List[Dict]: 实例列表
        """
        try:
            self.logger.info(f"开始获取区间 {self.compartment_id} 的实例列表")
            instances = self.compute_client.list_instances(
                compartment_id=self.compartment_id
            ).data
            self.logger.info(f"成功获取 {len(instances)} 个实例")
            return instances
        except Exception as e:
            self.logger.error(f"获取实例列表失败: {str(e)}")
            raise
            
    def get_instance(self, instance_id: str) -> Optional[Dict]:
        """
        获取实例详细信息
        
        Args:
            instance_id: 实例 ID
            
        Returns:
            Dict: 实例详细信息
        """
        try:
            self.logger.info(f"开始获取实例 {instance_id} 的详细信息")
            
            # 获取实例基本信息
            instance = self.compute_client.get_instance(instance_id).data
            
            # 获取 VNIC 附件
            vnic_attachments = self.compute_client.list_vnic_attachments(
                compartment_id=self.compartment_id,
                instance_id=instance_id
            ).data
            
            # 获取 VNIC 详细信息
            instance_details = {
                'id': instance.id,
                'display_name': instance.display_name,
                'state': instance.lifecycle_state,
                'shape': instance.shape,
                'time_created': instance.time_created.strftime('%Y-%m-%d %H:%M:%S'),
                'availability_domain': instance.availability_domain,
                'public_ip': 'N/A',
                'private_ip': 'N/A'
            }
            
            # 如果有 VNIC 附件，获取 IP 信息
            if vnic_attachments:
                for attachment in vnic_attachments:
                    if attachment.lifecycle_state == "ATTACHED":
                        vnic = self.network_client.get_vnic(attachment.vnic_id).data
                        if vnic.public_ip:
                            instance_details['public_ip'] = vnic.public_ip
                        if vnic.private_ip:
                            instance_details['private_ip'] = vnic.private_ip
            
            self.logger.info(f"成功获取实例 {instance_id} 的详细信息")
            return instance_details
            
        except oci.exceptions.ServiceError as e:
            if e.status == 404:
                self.logger.warning(f"实例 {instance_id} 不存在")
                return None
            self.logger.error(f"获取实例详细信息失败: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"获取实例详细信息时发生错误: {str(e)}")
            raise
            
    def delete_instance(self, instance_id: str) -> Dict:
        """
        删除实例
        
        Args:
            instance_id: 实例 ID
            
        Returns:
            Dict: 删除操作结果
        """
        try:
            self.logger.info(f"开始删除实例: {instance_id}")
            
            # 验证实例 ID
            if not instance_id or not isinstance(instance_id, str):
                raise ValueError("无效的实例 ID")
            
            # 发送删除请求
            response = self.compute_client.terminate_instance(
                instance_id=instance_id,
                preserve_boot_volume=False
            )
            
            self.logger.info(f"实例 {instance_id} 删除请求已发送")
            return {
                'status': 'success',
                'message': f'实例 {instance_id} 删除请求已发送',
                'instance_id': instance_id
            }
            
        except oci.exceptions.ServiceError as e:
            self.logger.error(f"删除实例时发生 OCI 服务错误: {str(e)}")
            return {
                'status': 'error',
                'message': f'删除实例失败: {str(e)}',
                'instance_id': instance_id
            }
        except Exception as e:
            self.logger.error(f"删除实例时发生未知错误: {str(e)}")
            return {
                'status': 'error',
                'message': f'删除实例失败: {str(e)}',
                'instance_id': instance_id
            }
            
    def terminate_instance(self, instance_id: str) -> bool:
        """
        终止实例
        
        Args:
            instance_id: 实例 ID
            
        Returns:
            bool: 是否成功
        """
        try:
            self.compute_client.terminate_instance(instance_id)
            return True
        except oci.exceptions.ServiceError as e:
            self.logger.error(f"终止实例失败: {str(e)}")
            return False
