import oci
import yaml
import logging
from typing import Dict, List, Optional
from oci_resources import create_oci_client_config, get_tenant_config

class OCIInstanceManager:
    def __init__(self, tenant_config: Dict):
        """
        Initialize OCI Instance Manager for a specific tenant
        
        :param tenant_config: Tenant configuration dictionary from config.yaml
        """
        # 首先初始化日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        try:
            self.tenant_config = tenant_config
            
            # 验证必要的配置项
            required_keys = ['user', 'key_file', 'fingerprint', 'tenancy', 'regions']
            for key in required_keys:
                if key not in tenant_config:
                    raise ValueError(f"Missing required configuration key: {key}")
            
            # 如果没有指定区间，尝试获取租户的根区间
            if 'compartment' not in tenant_config:
                try:
                    identity_client = oci.identity.IdentityClient({
                        "user": tenant_config['user'],
                        "key_content": self._read_key_file(tenant_config['key_file']),
                        "fingerprint": tenant_config['fingerprint'],
                        "tenancy": tenant_config['tenancy'],
                        "region": tenant_config['regions'][0]
                    })
                    
                    # 获取租户的根区间
                    root_compartment = identity_client.get_compartment(tenant_config['tenancy'])
                    tenant_config['compartment'] = root_compartment.data.id
                except Exception as e:
                    self.logger.error(f"Error retrieving root compartment: {e}")
                    raise ValueError("Unable to determine default compartment")
            
            # 存储 compartment_id 为实例属性
            self.compartment_id = tenant_config['compartment']
            
            # 初始化默认区间的客户端
            default_region = tenant_config['regions'][0]
            self.config = {
                "user": tenant_config['user'],
                "key_content": self._read_key_file(tenant_config['key_file']),
                "fingerprint": tenant_config['fingerprint'],
                "tenancy": tenant_config['tenancy'],
                "region": default_region
            }
            
            # 创建默认区间的计算客户端
            self.compute_client = oci.core.ComputeClient(self.config)
            
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            raise
    
    def _read_key_file(self, key_path: str) -> str:
        """
        Read OCI API private key file
        
        :param key_path: Path to the private key file
        :return: Key content as string
        """
        try:
            with open(key_path, 'r') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading key file {key_path}: {e}")
            raise
    
    def _create_client_for_region(self, region: str) -> oci.core.ComputeClient:
        """
        为特定区间创建计算客户端
        
        :param region: 区间名称
        :return: OCI 计算客户端
        """
        try:
            config = self.config.copy()
            config['region'] = region
            return oci.core.ComputeClient(config)
        except Exception as e:
            self.logger.error(f"创建区域客户端失败: {e}")
            raise
    
    def list_regions(self) -> List[Dict]:
        """
        获取租户配置中的区间列表
        
        :return: 区间列表
        """
        try:
            return [
                {
                    'key': region,
                    'name': region
                }
                for region in self.tenant_config.get('regions', [])
            ]
        except Exception as e:
            self.logger.error(f"Error listing regions: {e}")
            return []
            
    def get_tenant_config(self, tenant_name: str, region: str) -> Dict:
        """
        获取特定租户和区域的配置
        
        :param tenant_name: 租户名称
        :param region: 区域名称
        :return: 配置字典
        """
        try:
            # 创建区域特定的配置
            config = {
                "user": self.tenant_config['user'],
                "key_content": self._read_key_file(self.tenant_config['key_file']),
                "fingerprint": self.tenant_config['fingerprint'],
                "tenancy": self.tenant_config['tenancy'],
                "region": region
            }
            return config
        except Exception as e:
            self.logger.error(f"获取租户 {tenant_name} 在区域 {region} 的配置失败: {e}")
            raise

    def list_instances(self, tenant_name: str, region: str) -> List[Dict]:
        """获取指定租户和区域下的所有实例列表"""
        try:
            config = self.get_tenant_config(tenant_name, region)
            compute_client = oci.core.ComputeClient(config)
            network_client = oci.core.VirtualNetworkClient(config)

            # 获取所有实例
            instances = []
            try:
                instances = oci.pagination.list_call_get_all_results(
                    compute_client.list_instances,
                    compartment_id=self.compartment_id
                ).data
            except Exception as e:
                self.logger.error(f"获取区域 {region} 的实例列表失败: {str(e)}")
                return []

            # 获取每个实例的详细信息
            instance_details = []
            for instance in instances:
                try:
                    # 获取实例的vnic附件
                    vnic_attachments = compute_client.list_vnic_attachments(
                        compartment_id=instance.compartment_id,
                        instance_id=instance.id
                    ).data

                    # 获取网络信息
                    public_ip = None
                    private_ip = None
                    
                    if vnic_attachments:
                        vnic = network_client.get_vnic(vnic_attachments[0].vnic_id).data
                        private_ip = vnic.private_ip
                        
                        # 获取公网IP（如果有）
                        if vnic.public_ip:
                            public_ip = vnic.public_ip

                    # 构建实例信息
                    instance_info = {
                        'id': instance.id,
                        'display_name': instance.display_name,
                        'lifecycle_state': instance.lifecycle_state,
                        'availability_domain': instance.availability_domain,
                        'shape': instance.shape,
                        'time_created': instance.time_created.isoformat(),
                        'public_ip': public_ip,
                        'private_ip': private_ip
                    }
                    instance_details.append(instance_info)
                except Exception as e:
                    self.logger.error(f"获取实例 {instance.id} 的详细信息失败: {str(e)}")
                    continue

            self.logger.info(f"成功获取到 {len(instance_details)} 个实例")
            return instance_details
        except Exception as e:
            self.logger.error(f"获取区域 {region} 的实例列表失败: {str(e)}")
            return []

    def _validate_compartment_id(self, compartment_id: str) -> bool:
        """
        验证区间ID是否有效
        
        :param compartment_id: 要验证的区间ID
        :return: 区间ID是否有效
        """
        try:
            # 创建 Identity 客户端
            identity_client = oci.identity.IdentityClient(self.compute_client.config)
            
            # 尝试获取区间信息
            compartment = identity_client.get_compartment(compartment_id=compartment_id)
            
            # 检查区间状态是否为活跃
            return compartment.data.lifecycle_state == oci.identity.models.Compartment.LIFECYCLE_STATE_ACTIVE
        except Exception as e:
            self.logger.warning(f"Compartment ID validation failed for {compartment_id}: {e}")
            return False

    def create_instance(self, 
                    display_name: str, 
                    image_id: str, 
                    shape: str = 'VM.Standard.E4.Flex',
                    ocpus: int = 1, 
                    memory_in_gbs: int = 16,
                    availability_domain: Optional[str] = None,
                    subnet_id: Optional[str] = None,
                    ssh_authorized_keys: Optional[str] = None):
        """
        创建新的OCI实例,增加了网络配置等必要参数

        Args:
            display_name: 实例名称
            image_id: 镜像OCID
            shape: 实例规格(默认: VM.Standard.E4.Flex)
            ocpus: OCPU数量
            memory_in_gbs: 内存大小(GB)
            availability_domain: 可用域
            subnet_id: 子网OCID(必需)
            ssh_authorized_keys: SSH公钥(可选)

        Returns:
            创建的实例详情
        """
        try:
            if not subnet_id:
                raise ValueError("必须提供subnet_id(子网OCID)")

            # 配置实例形状
            shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=ocpus,
                memory_in_gbs=memory_in_gbs
            )

            # 配置实例详情
            instance_details = oci.core.models.LaunchInstanceDetails(
                compartment_id=self.compartment_id,
                display_name=display_name,
                availability_domain=availability_domain or self._get_first_availability_domain(),
                shape=shape,
                shape_config=shape_config,
                source_details=oci.core.models.InstanceSourceViaImageDetails(
                    source_type="image",
                    image_id=image_id
                ),
                create_vnic_details=oci.core.models.CreateVnicDetails(
                    subnet_id=subnet_id,
                    assign_public_ip=True
                ),
                metadata={
                    'ssh_authorized_keys': ssh_authorized_keys
                } if ssh_authorized_keys else {}
            )

            # 启动实例
            launch_instance_response = self.compute_client.launch_instance(
                launch_instance_details=instance_details
            )

            # 等待实例创建完成
            created_instance = self.wait_for_instance_state(
                launch_instance_response.data.id, 
                oci.core.models.Instance.LIFECYCLE_STATE_RUNNING
            )

            self.logger.info(f"实例创建成功: {created_instance.id}")
            return created_instance

        except Exception as e:
            self.logger.error(f"创建实例失败: {str(e)}")
            raise

    def _get_first_availability_domain(self) -> str:
        """
        Get the first availability domain for the region
        
        :return: First availability domain
        """
        try:
            identity_client = oci.identity.IdentityClient(self.compute_client.config)
            domains = identity_client.list_availability_domains(self.compartment_id)
            return domains.data[0].name
        except Exception as e:
            self.logger.error(f"Error getting availability domains: {e}")
            raise
    
    def manage_instance(self, instance_id: str, action: str, region: Optional[str] = None) -> Dict:
        """
        管理实例的生命周期操作，增加确认机制
        
        :param instance_id: 实例ID
        :param action: 操作类型（start, stop, restart, terminate）
        :param region: 可选的区间名称
        :return: 操作结果
        """
        try:
            # 如果未指定区间，使用租户配置中的第一个区间
            target_region = region or self.tenant_config['regions'][0]
            
            # 为指定区间创建计算客户端
            compute_client = self._create_client_for_region(target_region)
            
            # 获取实例详情以进行额外检查
            instance_details = compute_client.get_instance(instance_id=instance_id).data
            
            # 检查实例状态，防止对已终止实例重复操作
            if instance_details.lifecycle_state == 'TERMINATED':
                return {
                    'status': 'error',
                    'message': f'实例 {instance_id} 已经被终止，无法进行操作',
                    'current_state': instance_details.lifecycle_state
                }
            
            # 根据操作类型执行不同的实例管理操作，并增加确认逻辑
            if action == 'start':
                # 检查实例是否已在运行
                if instance_details.lifecycle_state == 'RUNNING':
                    return {
                        'status': 'error',
                        'message': f'实例 {instance_id} 已经处于运行状态',
                        'current_state': instance_details.lifecycle_state
                    }
                
                # 确认启动操作
                response = compute_client.instance_action(
                    instance_id=instance_id, 
                    action='START'
                )
                
            elif action == 'stop':
                # 检查实例是否已停止
                if instance_details.lifecycle_state in ['STOPPING', 'STOPPED']:
                    return {
                        'status': 'error',
                        'message': f'实例 {instance_id} 已经处于停止状态',
                        'current_state': instance_details.lifecycle_state
                    }
                
                # 确认停止操作
                response = compute_client.instance_action(
                    instance_id=instance_id, 
                    action='STOP'
                )
                
            elif action == 'restart':
                # 检查实例是否在运行中
                if instance_details.lifecycle_state != 'RUNNING':
                    return {
                        'status': 'error',
                        'message': f'实例 {instance_id} 不在运行状态，无法重启',
                        'current_state': instance_details.lifecycle_state
                    }
                
                # 确认重启操作
                response = compute_client.instance_action(
                    instance_id=instance_id, 
                    action='RESET'
                )
                
            elif action == 'terminate':
                # 终止实例需要额外的确认和检查
                if instance_details.lifecycle_state == 'TERMINATED':
                    return {
                        'status': 'error',
                        'message': f'实例 {instance_id} 已经被终止',
                        'current_state': instance_details.lifecycle_state
                    }
                
                # 终止实例的额外确认逻辑
                response = compute_client.terminate_instance(
                    instance_id=instance_id,
                    preserve_boot_volume=False  # 是否保留启动卷
                )
                
            else:
                raise ValueError(f"不支持的操作类型: {action}")
            
            return {
                'status': 'success',
                'message': f'成功对实例 {instance_id} 执行 {action} 操作',
                'request_id': response.headers.get('opc-request-id'),
                'previous_state': instance_details.lifecycle_state
            }
        
        except Exception as e:
            self.logger.error(f"管理实例 {instance_id} 时发生错误: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def list_images(self, operating_system: Optional[str] = None) -> List[Dict]:
        """
        List available images with optional OS filter
        
        :param operating_system: Optional OS filter (e.g., 'Oracle Linux')
        :return: List of available images
        """
        try:
            list_images_request = oci.core.models.ListImagesRequest(
                compartment_id=self.compartment_id,
                operating_system=operating_system
            )
            images = self.compute_client.list_images(list_images_request)
            return [
                {
                    'id': image.id,
                    'display_name': image.display_name,
                    'operating_system': image.operating_system,
                    'operating_system_version': image.operating_system_version
                }
                for image in images.data
            ]
        except Exception as e:
            self.logger.error(f"Error listing images: {e}")
            return []
    
    def list_compartments(self) -> List[Dict]:
        """
        通过 OCI API 获取可用的区间 OCID 列表，并处理树形层级关系
        
        :return: 区间 OCID 列表，包含 OCID、名称、描述和父区间信息
        """
        try:
            # 创建 Identity 客户端
            identity_client = oci.identity.IdentityClient(self.config)
            
            # 获取所有区间
            compartments = identity_client.list_compartments(
                compartment_id=self.tenant_config['tenancy'],
                lifecycle_state=oci.identity.models.Compartment.LIFECYCLE_STATE_ACTIVE
            )
            
            # 构建区间字典，便于建立树形关系
            compartment_dict = {}
            for compartment in compartments.data:
                compartment_dict[compartment.id] = {
                    'id': compartment.id,
                    'name': compartment.name,
                    'description': compartment.description,
                    'parent_id': compartment.compartment_id,  # 父区间的 OCID
                    'children': []
                }
            
            # 构建树形结构
            root_compartments = []
            for compartment_id, compartment in compartment_dict.items():
                parent_id = compartment['parent_id']
                
                # 如果没有父区间，或父区间不存在，则为根区间
                if not parent_id or parent_id not in compartment_dict:
                    root_compartments.append(compartment)
                else:
                    # 将当前区间添加到父区间的子区间列表中
                    compartment_dict[parent_id]['children'].append(compartment)
            
            return root_compartments
        except Exception as e:
            self.logger.error(f"Error listing compartments: {e}")
            return []
    
    def _format_compartment_tree(self, compartments: List[Dict], prefix: str = '') -> List[Dict]:
        """
        格式化区间树，为下拉菜单添加缩进
        
        :param compartments: 区间列表
        :param prefix: 缩进前缀
        :return: 格式化后的区间列表
        """
        formatted_compartments = []
        for compartment in compartments:
            formatted_compartments.append({
                'id': compartment['id'],
                'name': f"{prefix}{compartment['name']}",
                'description': compartment['description']
            })
            
            # 递归处理子区间
            if compartment.get('children'):
                formatted_compartments.extend(
                    self._format_compartment_tree(
                        compartment['children'], 
                        prefix='  ' + prefix
                    )
                )
        
        return formatted_compartments

    def get_instance_details(self, tenant_name: str, region: str, instance_id: str) -> Dict:
        """
        获取指定实例的详细信息
        
        :param tenant_name: 租户名称
        :param region: 区域
        :param instance_id: 实例ID
        :return: 实例详情字典
        """
        try:
            # 为指定区域创建计算客户端
            compute_client = self._create_client_for_region(region)
            
            # 获取实例详情
            instance = compute_client.get_instance(instance_id=instance_id).data
            
            # 获取网络信息
            public_ip, private_ip = self._get_instance_ips(instance)
            
            # 准备实例详情字典
            instance_details = {
                'id': instance.id,
                'display_name': instance.display_name,
                'availability_domain': instance.availability_domain,
                'lifecycle_state': instance.lifecycle_state,
                'time_created': instance.time_created.isoformat(),
                'region': region,
                'compartment_id': instance.compartment_id,
                'shape': instance.shape,
                
                # 网络信息
                'public_ip': public_ip,
                'private_ip': private_ip,
                
                # 故障域
                'fault_domain': instance.fault_domain or '未知',
                
                # 尝试获取OCPU和内存信息
                'ocpus': getattr(instance.shape_config, 'ocpus', '未知') if instance.shape_config else '未知',
                'memory_in_gbs': getattr(instance.shape_config, 'memory_in_gbs', '未知') if instance.shape_config else '未知',
                
                # 操作系统信息
                'image_os_version': self._get_image_os_version(instance)
            }
            
            return instance_details
        
        except Exception as e:
            self.logger.error(f"获取实例 {instance_id} 详情失败: {e}", exc_info=True)
            raise

    def _get_image_os_version(self, instance):
        """
        获取实例的操作系统版本
        
        :param instance: OCI实例对象
        :return: 操作系统版本或'未知'
        """
        try:
            # 获取镜像详情
            compute_client = self.compute_client
            image = compute_client.get_image(image_id=instance.image_id).data
            
            # 构建操作系统描述
            return f"{image.operating_system} {image.operating_system_version}" or '未知'
        
        except Exception as e:
            self.logger.error(f"获取实例 {instance.id} 的操作系统版本失败: {e}")
            return '未知'

    def get_instances(self, tenant_name: str, region: str) -> List[Dict]:
        """获取指定租户和区域下的所有实例列表"""
        try:
            config = self.get_tenant_config(tenant_name, region)
            compute_client = oci.core.ComputeClient(config)
            network_client = oci.core.VirtualNetworkClient(config)

            # 获取所有实例
            instances = []
            try:
                instances = oci.pagination.list_call_get_all_results(
                    compute_client.list_instances,
                    compartment_id=config.get('tenancy')
                ).data
            except Exception as e:
                self.logger.error(f"获取区域 {region} 的实例列表失败: {str(e)}")
                return []

            # 获取每个实例的详细信息
            instance_details = []
            for instance in instances:
                try:
                    # 获取实例的vnic附件
                    vnic_attachments = compute_client.list_vnic_attachments(
                        compartment_id=instance.compartment_id,
                        instance_id=instance.id
                    ).data

                    # 获取网络信息
                    public_ip = None
                    private_ip = None
                    
                    if vnic_attachments:
                        vnic = network_client.get_vnic(vnic_attachments[0].vnic_id).data
                        private_ip = vnic.private_ip
                        
                        # 获取公网IP（如果有）
                        if vnic.public_ip:
                            public_ip = vnic.public_ip

                    # 构建实例信息
                    instance_info = {
                        'id': instance.id,
                        'display_name': instance.display_name,
                        'lifecycle_state': instance.lifecycle_state,
                        'availability_domain': instance.availability_domain,
                        'shape': instance.shape,
                        'time_created': instance.time_created.isoformat(),
                        'public_ip': public_ip,
                        'private_ip': private_ip
                    }
                    instance_details.append(instance_info)
                except Exception as e:
                    self.logger.error(f"获取实例 {instance.id} 的详细信息失败: {str(e)}")
                    continue

            self.logger.info(f"成功获取到 {len(instance_details)} 个实例")
            return instance_details
        except Exception as e:
            self.logger.error(f"获取区域 {region} 的实例列表失败: {str(e)}")
            return []

    def get_network_interfaces(self, instance_id: str) -> List[Dict]:
        """
        获取实例的网络接口详情
        
        :param instance_id: 实例ID
        :return: 网络接口详情列表
        """
        try:
            # 为实例所在区域创建虚拟网络客户端
            vcn_client = oci.core.VirtualNetworkClient(self.config)
            
            # 获取实例的网络接口
            network_interfaces = vcn_client.list_vnic_attachments(
                compartment_id=self.config['compartment_id'],
                instance_id=instance_id
            ).data
            
            # 存储网络接口详情的列表
            interfaces_details = []
            
            for vnic_attachment in network_interfaces:
                # 获取每个网络接口的详细信息
                vnic_details = vcn_client.get_vnic(vnic_id=vnic_attachment.vnic_id).data
                
                interface_info = {
                    'id': vnic_attachment.vnic_id,
                    'private_ip': vnic_details.private_ip,
                    'public_ip': vnic_details.public_ip or None,
                    'subnet_id': vnic_details.subnet_id,
                    'mac_address': vnic_details.mac_address
                }
                
                interfaces_details.append(interface_info)
            
            return interfaces_details
        
        except Exception as e:
            self.logger.error(f"获取实例 {instance_id} 的网络接口失败: {e}")
            return []

    def _get_shape_details(self, shape: str) -> Dict:
        """
        获取实例形状的详细信息
        
        :param shape: 实例形状名称
        :return: 形状详情字典
        """
        try:
            self.logger.info(f"开始获取形状 {shape} 的详细信息")
            self.logger.info(f"使用的配置: {self.config}")
            
            # 尝试使用不同的OCI客户端获取形状信息
            compute_client = oci.core.ComputeClient(self.config)
            
            # 获取形状信息
            shapes = compute_client.list_shapes(
                compartment_id=self.config['compartment_id']
            ).data
            
            self.logger.info(f"获取到的形状数量: {len(shapes)}")
            
            # 打印所有形状名称，帮助调试
            shape_names = [s.shape for s in shapes]
            self.logger.info(f"可用形状列表: {shape_names}")
            
            # 查找匹配的形状
            matching_shape = next((s for s in shapes if s.shape == shape), None)
            
            if matching_shape:
                # 尝试获取更多形状信息
                shape_info = {
                    'ocpu_count': getattr(matching_shape, 'ocpus', '未知'),
                    'memory_in_gbs': getattr(matching_shape, 'memory_in_gbs', '未知'),
                    'processor_description': getattr(matching_shape, 'processor_description', '未知')
                }
                
                # 打印所有可用的属性
                self.logger.info(f"形状 {shape} 的所有属性: {vars(matching_shape)}")
                
                self.logger.info(f"找到形状 {shape} 的详细信息: {shape_info}")
                return shape_info
            
            self.logger.warning(f"未找到形状 {shape} 的详细信息")
            return {
                'ocpu_count': '未知',
                'memory_in_gbs': '未知',
                'processor_description': '未知'
            }
        
        except Exception as e:
            self.logger.error(f"获取形状 {shape} 详情失败: {e}", exc_info=True)
            return {
                'ocpu_count': '未知',
                'memory_in_gbs': '未知',
                'processor_description': '未知'
            }

    def _get_instance_ips(self, instance):
        """
        获取实例的公网和私有IP地址
        
        :param instance: OCI实例对象
        :return: 元组 (公网IP, 私有IP)
        """
        try:
            # 获取VNIC附件
            vnic_attachments = self.compute_client.list_vnic_attachments(
                compartment_id=instance.compartment_id,
                instance_id=instance.id
            ).data

            if vnic_attachments:
                # 获取第一个VNIC的详细信息
                first_vnic = vnic_attachments[0]
                
                # 获取VNIC详情
                vnic_client = oci.core.VirtualNetworkClient(self.config)
                vnic = vnic_client.get_vnic(vnic_id=first_vnic.vnic_id).data
                
                return (
                    vnic.public_ip or '无', 
                    vnic.private_ip or '无'
                )
            
            return ('无', '无')
        
        except Exception as e:
            self.logger.error(f"获取实例 {instance.id} 的IP失败: {e}")
            return ('无', '无')

def get_oci_manager(tenant_name: str) -> OCIInstanceManager:
    """
    Create OCIInstanceManager for a specific tenant
    
    :param tenant_name: Name of the tenant from config.yaml
    :return: OCIInstanceManager instance
    """
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    tenant_config = next((t for t in config['tenants'] if t['name'] == tenant_name), None)
    
    if not tenant_config:
        raise ValueError(f"Tenant {tenant_name} not found in configuration")
    
    return OCIInstanceManager(tenant_config)
