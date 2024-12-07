import oci
import logging
from typing import Dict, List, Optional
import base64

class OCIInstanceCreator:
    def __init__(self, tenant_config: Dict, region: Optional[str] = None):
        """
        初始化OCI实例创建器
        
        Args:
            tenant_config (dict): 租户配置信息
            region (str, optional): 指定的区域，如果为None则使用默认区域
        """
        # 首先初始化日志记录
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        
        try:
            # 配置基本租户信息
            self.tenant_config = tenant_config
            self.compartment_id = tenant_config.get('compartment_id')
            
            # 选择区域配置
            if region:
                # 从配置中找到匹配的区域
                regions = tenant_config.get('regions', [])
                if region not in regions:
                    raise ValueError(f"未找到区域: {region}")
                self.region_config = {'key': region}
            else:
                # 使用默认区域
                regions = tenant_config.get('regions', [])
                if not regions:
                    raise ValueError("租户配置中没有可用的区域")
                self.region_config = {'key': regions[0]}
            
            # 配置OCI客户端
            self.config = {
                "user": tenant_config.get('user_ocid'),
                "key_content": tenant_config.get('private_key'),
                "fingerprint": tenant_config.get('fingerprint'),
                "tenancy": tenant_config.get('tenancy_ocid'),
                "region": self.region_config.get('key')
            }
            
            # 初始化OCI客户端
            self.compute_client = oci.core.ComputeClient(self.config)
            self.network_client = oci.core.VirtualNetworkClient(self.config)
            
            self.logger.info(f"初始化实例创建器 - 租户: {tenant_config.get('name')}, 区域: {self.region_config.get('key')}")
        
        except Exception as e:
            self.logger.error(f"实例创建器初始化失败: {e}")
            raise

    def _get_compute_client(self):
        """获取计算服务客户端"""
        return self.compute_client

    def _get_network_client(self):
        """获取网络服务客户端"""
        return self.network_client

    def list_availability_domains(self) -> List[Dict]:
        """
        列出租户的可用域
        :return: 可用域列表
        """
        try:
            identity_client = oci.identity.IdentityClient(self.config)
            domains = identity_client.list_availability_domains(self.compartment_id)
            return [
                {
                    "id": domain.id, 
                    "name": domain.name
                } for domain in domains.data
            ]
        except Exception as e:
            self.logger.error(f"获取可用域失败: {e}")
            raise

    def list_images(self, os_filter: Optional[str] = None, os_type: Optional[str] = None) -> List[Dict]:
        """
        获取可用的系统镜像列表
        
        Args:
            os_filter (str, optional): 操作系统过滤关键词
            os_type (str, optional): 操作系统类型（'linux', 'windows'）
        
        Returns:
            list: 可用镜像列表
        """
        try:
            compute_client = self._get_compute_client()
            
            # 获取所有镜像
            images = compute_client.list_images(
                compartment_id=self.compartment_id,
                operating_system_version=os_filter
            ).data
            
            # 转换为字典列表，便于前端处理
            image_list = []
            for image in images:
                image_dict = {
                    'id': image.id,
                    'display_name': image.display_name,
                    'operating_system': image.operating_system,
                    'operating_system_version': image.operating_system_version,
                    'state': image.lifecycle_state
                }
                
                # 操作系统类型过滤
                if os_type:
                    if os_type == 'linux' and 'Linux' not in image.operating_system:
                        continue
                    if os_type == 'windows' and 'Windows' not in image.operating_system:
                        continue
                
                image_list.append(image_dict)
            
            return image_list
        except Exception as e:
            self.logger.error(f"获取镜像列表失败: {e}")
            return []

    def list_shapes(self, shape_type: Optional[str] = None, purpose: Optional[str] = None) -> List[Dict]:
        """
        获取可用的实例形状列表
        
        Args:
            shape_type (str, optional): 形状类型（'standard', 'flex'）
            purpose (str, optional): 实例用途（'general', 'compute', 'memory', 'gpu'）
        
        Returns:
            list: 可用形状列表
        """
        try:
            compute_client = self._get_compute_client()
            
            # 获取所有形状
            shapes = compute_client.list_shapes(
                compartment_id=self.compartment_id
            ).data
            
            # 形状过滤和分类
            shape_list = []
            for shape in shapes:
                shape_dict = {
                    'name': shape.shape,
                    'ocpus_range': shape.ocpus_range,
                    'memory_range': shape.memory_range
                }
                
                # 形状类型过滤
                if shape_type:
                    is_flex = 'Flex' in shape.shape
                    if shape_type == 'standard' and is_flex:
                        continue
                    if shape_type == 'flex' and not is_flex:
                        continue
                
                # 用途分类
                if purpose:
                    if purpose == 'general' and 'Standard' in shape.shape:
                        shape_dict['purpose'] = 'general'
                    elif purpose == 'compute' and 'Compute' in shape.shape:
                        shape_dict['purpose'] = 'compute'
                    elif purpose == 'memory' and 'Memory' in shape.shape:
                        shape_dict['purpose'] = 'memory'
                    elif purpose == 'gpu' and 'GPU' in shape.shape:
                        shape_dict['purpose'] = 'gpu'
                    else:
                        continue
                
                shape_list.append(shape_dict)
            
            return shape_list
        except Exception as e:
            self.logger.error(f"获取形状列表失败: {e}")
            return []

    def list_vcns(self) -> List[Dict]:
        """
        列出虚拟云网络(VCN)
        :return: VCN列表
        """
        try:
            network_client = self._get_network_client()
            vcns = network_client.list_vcns(
                compartment_id=self.compartment_id
            )
            return [
                {
                    "id": vcn.id,
                    "display_name": vcn.display_name,
                    "cidr_block": vcn.cidr_block,
                    "lifecycle_state": vcn.lifecycle_state
                } for vcn in vcns.data
            ]
        except Exception as e:
            self.logger.error(f"获取VCN列表失败: {e}")
            raise

    def list_subnets(self, vcn_id: str) -> List[Dict]:
        """
        列出指定VCN的子网
        :param vcn_id: 虚拟云网络ID
        :return: 子网列表
        """
        try:
            network_client = self._get_network_client()
            subnets = network_client.list_subnets(
                compartment_id=self.compartment_id,
                vcn_id=vcn_id
            )
            return [
                {
                    "id": subnet.id,
                    "display_name": subnet.display_name,
                    "cidr_block": subnet.cidr_block,
                    "availability_domain": subnet.availability_domain,
                    "lifecycle_state": subnet.lifecycle_state
                } for subnet in subnets.data
            ]
        except Exception as e:
            self.logger.error(f"获取子网列表失败: {e}")
            raise

    def create_instance(self, 
                    display_name: str, 
                    availability_domain: str, 
                    image_id: str, 
                    shape: str, 
                    subnet_id: str, 
                    ssh_public_key: str = '', 
                    root_password: str = '', 
                    flex_shape_config: Optional[Dict] = None) -> Dict:
        """
        创建OCI实例，支持更多配置选项
        
        Args:
            display_name (str): 实例显示名称
            availability_domain (str): 可用域
            image_id (str): 系统镜像ID
            shape (str): 实例形状
            subnet_id (str): 子网ID
            ssh_public_key (str, optional): SSH公钥
            root_password (str, optional): Root用户密码
            flex_shape_config (dict, optional): Flex形状配置，仅当shape为Flex类型时使用
        
        Returns:
            dict: 创建结果
        """
        try:
            # 创建基本的实例配置
            launch_details = oci.core.models.LaunchInstanceDetails(
                compartment_id=self.compartment_id,
                availability_domain=availability_domain,
                display_name=display_name,
                shape=shape,
                source_details=oci.core.models.InstanceSourceViaImageDetails(
                    source_type="image",
                    image_id=image_id
                ),
                create_vnic_details=oci.core.models.CreateVnicDetails(
                    subnet_id=subnet_id,
                    assign_public_ip=True
                ),
                metadata={
                    'ssh_authorized_keys': ssh_public_key,
                    'root_password': root_password  # 可选的root密码
                }
            )
            
            # 如果是Flex形状且提供了配置，添加shape_config
            if 'Flex' in shape and flex_shape_config:
                self.logger.info(f"配置Flex实例: OCPUs={flex_shape_config.get('ocpus')}, Memory={flex_shape_config.get('memory_in_gbs')}GB")
                launch_details.shape_config = oci.core.models.InstanceShapeConfig(
                    ocpus=flex_shape_config.get('ocpus', 1),
                    memory_in_gbs=flex_shape_config.get('memory_in_gbs', 16)
                )
            else:
                self.logger.info(f"使用标准实例形状: {shape}")
            
            # 创建实例
            response = self.compute_client.launch_instance(launch_details)
            instance = response.data
            
            # 等待实例创建完成
            self._wait_for_instance_lifecycle_state(instance.id, 'RUNNING')
            
            self.logger.info(f"实例创建成功: {instance.id}")
            return {
                "status": "success",
                "instance_id": instance.id,
                "message": "实例创建成功"
            }
        except Exception as e:
            self.logger.error(f"创建实例失败: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def _wait_for_instance_lifecycle_state(self, instance_id: str, target_state: str):
        """
        等待实例达到指定生命周期状态
        
        Args:
            instance_id (str): 实例ID
            target_state (str): 目标生命周期状态
        """
        try:
            # 等待实例创建完成
            get_instance_response = self.compute_client.get_instance(instance_id)
            instance = get_instance_response.data
            
            # 等待实例达到指定生命周期状态
            while instance.lifecycle_state != target_state:
                self.logger.info(f"实例 {instance_id} 当前状态: {instance.lifecycle_state}")
                get_instance_response = self.compute_client.get_instance(instance_id)
                instance = get_instance_response.data
        except Exception as e:
            self.logger.error(f"等待实例生命周期状态失败: {e}")
            raise

# 可以添加一些测试代码或示例用法
if __name__ == '__main__':
    # 示例使用方法
    import yaml
    
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    creator = OCIInstanceCreator(config['tenants'][0])
    
    # 打印可用域
    print("可用域:")
    print(creator.list_availability_domains())
    
    # 打印镜像列表
    print("\n镜像列表:")
    print(creator.list_images())
    
    # 打印形状列表
    print("\n形状列表:")
    print(creator.list_shapes())
    
    # 打印VCN列表
    print("\nVCN列表:")
    print(creator.list_vcns())
    
    # 打印子网列表
    print("\n子网列表:")
    print(creator.list_subnets("your_vcn_id"))
    
    # 创建实例
    instance_details = {
        "display_name": "your_display_name",
        "availability_domain": "your_availability_domain",
        "image_id": "your_image_id",
        "shape": "your_shape",
        "subnet_id": "your_subnet_id",
        "ssh_public_key": "your_ssh_public_key",
        "root_password": "your_root_password"
    }
    print("\n创建实例结果:")
    print(creator.create_instance(**instance_details))
