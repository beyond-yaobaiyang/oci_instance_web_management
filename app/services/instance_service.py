import oci
import logging
import random
import string
import base64
import time
from typing import Dict, Any, List, Optional, Tuple
from app.services.tenant_service import TenantService

class InstanceService:
    def __init__(self):
        self.tenant_service = TenantService()
    
    def _get_clients(self, tenant_id: str) -> Tuple[Optional[oci.core.ComputeClient], Optional[oci.core.VirtualNetworkClient]]:
        """获取OCI客户端"""
        try:
            compute_client = self.tenant_service.get_oci_client(tenant_id, service="compute")
            network_client = self.tenant_service.get_oci_client(tenant_id, service="network")
            return compute_client, network_client
        except Exception as e:
            logging.error(f"创建OCI客户端失败: {str(e)}")
            return None, None

    def _get_compute_client(self, tenant_id):
        """获取计算客户端"""
        tenant = self.tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ValueError("租户不存在")
        
        config = {
            "user": tenant.user_ocid,
            "key_file": tenant.key_file,
            "fingerprint": tenant.fingerprint,
            "tenancy": tenant.tenancy,
            "region": tenant.region
        }
        
        return oci.core.ComputeClient(config)

    def _get_network_client(self, tenant_id):
        """获取网络客户端"""
        tenant = self.tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ValueError("租户不存在")
        
        config = {
            "user": tenant.user_ocid,
            "key_file": tenant.key_file,
            "fingerprint": tenant.fingerprint,
            "tenancy": tenant.tenancy,
            "region": tenant.region
        }
        
        return oci.core.VirtualNetworkClient(config)

    def _generate_random_password(self, length=12):
        """生成随机密码"""
        characters = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(random.choice(characters) for _ in range(length))
        return password

    def get_instance_vnic_attachments(self, compute_client, network_client, compartment_id: str, instance_id: str) -> Tuple[Optional[str], Optional[str]]:
        """获取实例的网络接口信息"""
        try:
            vnic_attachments = compute_client.list_vnic_attachments(
                compartment_id=compartment_id,
                instance_id=instance_id
            ).data
            
            if not vnic_attachments:
                logging.warning(f"实例 {instance_id} 没有找到网络接口")
                return None, None
            
            try:
                # 获取主VNIC的信息
                primary_vnic = network_client.get_vnic(vnic_attachments[0].vnic_id).data
                return primary_vnic.private_ip, primary_vnic.public_ip
            except Exception as e:
                logging.error(f"获取VNIC信息失败: {str(e)}")
                return None, None
        except Exception as e:
            logging.error(f"获取网络接口信息失败: {str(e)}")
            return None, None
    
    def list_instances(self, tenant_id: str) -> List[Dict[str, Any]]:
        """获取租户下的所有实例列表"""
        try:
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant:
                raise Exception(f"找不到租户: {tenant_id}")

            compute_client, network_client = self._get_clients(tenant_id)
            if not compute_client or not network_client:
                raise Exception(f"无法创建OCI客户端")

            # 获取实例列表
            instances = compute_client.list_instances(
                compartment_id=tenant['compartment_id'] or tenant['tenancy']
            ).data

            result = []
            for instance in instances:
                instance_data = {
                    'id': instance.id,
                    'display_name': instance.display_name,
                    'lifecycle_state': instance.lifecycle_state,
                    'availability_domain': instance.availability_domain,
                    'shape': instance.shape,
                    'time_created': instance.time_created.strftime('%Y-%m-%d %H:%M:%S'),
                }

                # 获取实例的网络信息
                try:
                    private_ip, public_ip = self.get_instance_vnic_attachments(
                        compute_client, network_client,
                        tenant['compartment_id'] or tenant['tenancy'],
                        instance.id
                    )
                    instance_data['private_ip'] = private_ip
                    instance_data['public_ip'] = public_ip
                except Exception as e:
                    logging.error(f"获取实例网络信息失败: {str(e)}")
                    instance_data['private_ip'] = None
                    instance_data['public_ip'] = None

                result.append(instance_data)

            return result

        except Exception as e:
            logging.error(f"获取实例列表失败: {str(e)}")
            raise

    def instance_action(self, tenant_id: str, instance_id: str, action: str) -> bool:
        """执行实例操作"""
        try:
            compute_client, _ = self._get_clients(tenant_id)
            if not compute_client:
                raise Exception("无法创建OCI客户端")
            
            action_map = {
                'start': compute_client.instance_action,
                'stop': compute_client.instance_action,
                'reset': compute_client.instance_action,
                'softreset': compute_client.instance_action,
                'terminate': compute_client.terminate_instance
            }
            
            if action not in action_map:
                raise Exception(f"不支持的操作类型: {action}")

            try:
                if action == 'terminate':
                    action_map[action](instance_id, preserve_boot_volume=False)
                else:
                    action_map[action](instance_id, action=action.upper())
                
                # 等待操作开始执行
                time.sleep(2)
                
                # 检查操作是否成功启动
                instance = compute_client.get_instance(instance_id).data
                expected_states = {
                    'start': ['STARTING', 'RUNNING'],
                    'stop': ['STOPPING', 'STOPPED'],
                    'reset': ['STOPPING', 'STOPPED', 'STARTING', 'RUNNING'],
                    'terminate': ['TERMINATING', 'TERMINATED']
                }
                
                if instance.lifecycle_state not in expected_states.get(action, []):
                    raise Exception(f"操作未能成功执行，当前状态: {instance.lifecycle_state}")
                
                return True
            except Exception as e:
                logging.error(f"执行{action}操作失败: {str(e)}")
                raise Exception(f"执行{action}操作失败: {str(e)}")
        except Exception as e:
            logging.error(f"执行实例操作失败: {str(e)}")
            raise
    
    def start_instance(self, tenant_id: str, instance_id: str) -> bool:
        """启动实例"""
        return self.instance_action(tenant_id, instance_id, 'start')
    
    def stop_instance(self, tenant_id: str, instance_id: str) -> bool:
        """停止实例"""
        return self.instance_action(tenant_id, instance_id, 'stop')
    
    def restart_instance(self, tenant_id: str, instance_id: str) -> bool:
        """重启实例"""
        return self.instance_action(tenant_id, instance_id, 'reset')
    
    def get_instance(self, tenant_id: str, instance_id: str) -> Optional[Dict[str, Any]]:
        """获取实例信息"""
        try:
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant:
                raise Exception(f"找不到租户: {tenant_id}")
            
            compute_client, network_client = self._get_clients(tenant_id)
            if not compute_client or not network_client:
                raise Exception("无法创建OCI客户端")
            
            instance = compute_client.get_instance(instance_id).data
            
            # 如果实例已终止，则不获取额外信息
            if instance.lifecycle_state == 'TERMINATED':
                return {
                    'id': instance.id,
                    'display_name': instance.display_name,
                    'shape': instance.shape,
                    'lifecycle_state': instance.lifecycle_state,
                    'availability_domain': instance.availability_domain,
                    'time_created': instance.time_created.strftime('%Y-%m-%d %H:%M:%S') if instance.time_created else None,
                    'fault_domain': instance.fault_domain,
                    'private_ip': None,
                    'public_ip': None,
                    'shape_config': None
                }
            
            # 获取网络信息
            private_ip, public_ip = self.get_instance_vnic_attachments(
                compute_client, network_client, 
                tenant['compartment_id'] or tenant['tenancy'], 
                instance_id
            )

            # 获取实例配置信息
            shape_config = None
            try:
                if hasattr(instance, 'shape_config'):
                    shape_config = {
                        'ocpus': instance.shape_config.ocpus,
                        'memory_in_gbs': instance.shape_config.memory_in_gbs
                    }
            except Exception as e:
                logging.warning(f"获取实例规格信息失败: {str(e)}")
                shape_config = None
            
            return {
                'id': instance.id,
                'display_name': instance.display_name,
                'shape': instance.shape,
                'lifecycle_state': instance.lifecycle_state,
                'availability_domain': instance.availability_domain,
                'time_created': instance.time_created.strftime('%Y-%m-%d %H:%M:%S') if instance.time_created else None,
                'fault_domain': instance.fault_domain,
                'private_ip': private_ip,
                'public_ip': public_ip,
                'shape_config': shape_config
            }
        except Exception as e:
            logging.error(f"获取实例详情失败: {str(e)}")
            raise

    def change_public_ip(self, tenant_id: str, instance_id: str) -> Optional[Dict[str, Any]]:
        """更换实例的公共IP地址"""
        try:
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant:
                raise Exception(f"找不到租户: {tenant_id}")
            
            compute_client, network_client = self._get_clients(tenant_id)
            if not compute_client or not network_client:
                raise Exception("无法创建OCI客户端")

            # 获取实例的VNIC附件
            vnic_attachments = compute_client.list_vnic_attachments(
                instance_id=instance_id,
                compartment_id=tenant['compartment_id'] or tenant['tenancy']
            ).data

            if not vnic_attachments:
                raise Exception(f"找不到实例的网络接口: {instance_id}")

            # 获取主VNIC
            primary_vnic = network_client.get_vnic(vnic_attachments[0].vnic_id).data

            # 如果已有公共IP，先释放它
            if primary_vnic.public_ip:
                try:
                    # 获取公共IP对象
                    public_ip = network_client.get_public_ip_by_ip_address(
                        get_public_ip_by_ip_address_details=oci.core.models.GetPublicIpByIpAddressDetails(
                            ip_address=primary_vnic.public_ip
                        )
                    ).data

                    # 释放公共IP
                    if public_ip.lifecycle_state != 'TERMINATED':
                        network_client.delete_public_ip(public_ip.id)
                        
                        # 等待旧IP完全释放
                        try:
                            oci.wait_until(
                                network_client,
                                network_client.get_public_ip(public_ip.id),
                                'lifecycle_state',
                                'TERMINATED',
                                max_wait_seconds=300,
                                succeed_on_not_found=True
                            )
                        except oci.exceptions.ServiceError as e:
                            if e.status != 404:  # 404是预期的，表示IP已被释放
                                raise
                except Exception as e:
                    logging.error(f"释放旧公共IP时出错: {str(e)}")
                    raise Exception(f"释放旧公共IP失败: {str(e)}")

            # 获取私有IP对象
            private_ips = network_client.list_private_ips(vnic_id=primary_vnic.id).data
            if not private_ips:
                raise Exception(f"找不到实例的私有IP: {instance_id}")
            
            private_ip = private_ips[0]  # 使用主私有IP

            # 等待一段时间确保旧IP完全释放
            time.sleep(10)

            # 创建新的临时公共IP
            public_ip_details = oci.core.models.CreatePublicIpDetails(
                compartment_id=tenant['compartment_id'] or tenant['tenancy'],
                lifetime='EPHEMERAL',
                private_ip_id=private_ip.id
            )
            
            # 分配新的公共IP
            try:
                new_public_ip = network_client.create_public_ip(
                    create_public_ip_details=public_ip_details
                ).data

                # 等待公共IP变为可用状态
                oci.wait_until(
                    network_client,
                    network_client.get_public_ip(new_public_ip.id),
                    'lifecycle_state',
                    'AVAILABLE',
                    max_wait_seconds=300
                )
                
                # 获取更新后的实例信息
                instance = self.get_instance(tenant_id, instance_id)
                return instance
            except Exception as e:
                logging.error(f"分配新公共IP时出错: {str(e)}")
                raise Exception(f"分配新公共IP失败: {str(e)}")

        except Exception as e:
            logging.error(f"更换公共IP失败: {str(e)}")
            raise

    def get_resources(self, tenant_id):
        """获取可用域、镜像和子网等资源"""
        try:
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            logging.debug(f"获取租户配置: {tenant}")
            
            if not tenant:
                raise ValueError("租户不存在")

            # 创建OCI配置
            config = {
                "user": tenant['user_ocid'],  # 使用user_ocid作为键名
                "key_file": tenant['key_file'],
                "fingerprint": tenant['fingerprint'],
                "tenancy": tenant['tenancy'],
                "region": tenant['region']
            }
            logging.debug(f"创建OCI客户端配置: {config}")

            # 创建不同的客户端
            identity_client = oci.identity.IdentityClient(config)
            compute_client = oci.core.ComputeClient(config)
            network_client = oci.core.VirtualNetworkClient(config)
            logging.debug("成功创建OCI客户端")

            # 获取可用域（在租户级别）
            availability_domains = identity_client.list_availability_domains(
                compartment_id=tenant['tenancy']
            ).data
            logging.debug(f"获取到可用域: {[ad.name for ad in availability_domains]}")

            # 获取系统镜像（Oracle Linux、CentOS、Ubuntu）
            images = []
            for os_name in ["Oracle Linux", "CentOS", "Canonical Ubuntu"]:
                os_images = compute_client.list_images(
                    compartment_id=tenant['compartment_id'],
                    operating_system=os_name,
                    sort_by="TIMECREATED",
                    sort_order="DESC"
                ).data
                images.extend(os_images)
            logging.debug(f"获取到系统镜像: {[image.display_name for image in images]}")

            # 获取子网
            subnets = network_client.list_subnets(
                compartment_id=tenant['compartment_id']
            ).data
            logging.debug(f"获取到子网: {[subnet.display_name for subnet in subnets]}")

            # 获取实例规格
            shapes = compute_client.list_shapes(
                compartment_id=tenant['compartment_id']
            ).data
            logging.debug(f"获取到实例规格: {[shape.shape for shape in shapes]}")

            result = {
                'availability_domains': [
                    {
                        'name': ad.name,
                        'id': ad.name
                    } for ad in availability_domains
                ],
                'images': [
                    {
                        'id': image.id,
                        'name': f"{image.operating_system} {image.operating_system_version} - {image.display_name}",
                        'size': image.size_in_mbs // 1024  # 转换为GB
                    } for image in sorted(images, key=lambda x: (x.operating_system, x.operating_system_version))
                ],
                'subnets': [
                    {
                        'id': subnet.id,
                        'name': subnet.display_name,
                        'cidr_block': subnet.cidr_block
                    } for subnet in subnets
                ],
                'shapes': [
                    {
                        'name': shape.shape,
                        'ocpus': shape.ocpus,
                        'memory_in_gbs': shape.memory_in_gbs,
                        'networking_bandwidth_in_gbps': shape.networking_bandwidth_in_gbps,
                        'processor_description': shape.processor_description,
                        'is_flex': shape.shape.endswith('.Flex')
                    } for shape in shapes
                ]
            }
            logging.debug(f"返回资源数据: {result}")
            return result

        except Exception as e:
            logging.error(f"获取资源列表失败: {str(e)}", exc_info=True)
            raise

    def _generate_random_password(self, length=12):
        """生成随机密码"""
        # 确保密码包含所有类型的字符
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = '!@#$%^&*'
        
        # 确保至少包含每种类型的字符
        password = [
            random.choice(lowercase),
            random.choice(uppercase),
            random.choice(digits),
            random.choice(special)
        ]
        
        # 填充剩余长度
        all_chars = lowercase + uppercase + digits + special
        for _ in range(length - 4):
            password.append(random.choice(all_chars))
        
        # 打乱密码字符顺序
        random.shuffle(password)
        return ''.join(password)

    def _generate_cloud_init_script(self, password: str) -> str:
        """
        生成cloud-init脚本
        :param password: 要设置的密码
        :return: base64编码的cloud-init脚本
        """
        script = f"""#cloud-config
users:
  - name: root
    lock_passwd: false
    shell: /bin/bash
  - name: opc
    lock_passwd: false
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash

# 设置密码
chpasswd:
  list: |
    root:{password}
    opc:{password}
  expire: false

# 启用密码认证
ssh_pwauth: true

# 配置SSH
ssh:
  pwauth: yes
  
write_files:
  - path: /etc/ssh/sshd_config
    content: |
      Port 22
      Protocol 2
      HostKey /etc/ssh/ssh_host_rsa_key
      HostKey /etc/ssh/ssh_host_ecdsa_key
      HostKey /etc/ssh/ssh_host_ed25519_key
      SyslogFacility AUTHPRIV
      PermitRootLogin yes
      PasswordAuthentication yes
      ChallengeResponseAuthentication no
      GSSAPIAuthentication yes
      GSSAPICleanupCredentials no
      UsePAM yes
      X11Forwarding yes
      PrintMotd no
      AcceptEnv LANG LC_*
      Subsystem sftp /usr/lib/openssh/sftp-server
    permissions: '0600'

runcmd:
  - sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
  - sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
  - systemctl restart sshd
"""
        return base64.b64encode(script.encode()).decode()

    def get_compute_client(self, config):
        """
        获取OCI计算客户端
        :param config: OCI配置信息
        :return: ComputeClient对象
        """
        try:
            # 创建OCI配置对象
            oci_config = {
                "user": config["user"],
                "key_file": config["key_file"],
                "fingerprint": config["fingerprint"],
                "tenancy": config["tenancy"],
                "region": config["region"]
            }
            
            # 创建并返回计算客户端
            return oci.core.ComputeClient(oci_config)
        except Exception as e:
            logging.error(f"创建计算客户端失败: {str(e)}", exc_info=True)
            raise Exception(f"创建计算客户端失败: {str(e)}")

    def create_instance(self, data):
        """
        创建实例
        :param data: 包含实例配置的字典
        :return: dict 包含创建结果的字典
        """
        try:
            tenant_id = data['tenant_id']
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError("租户不存在")
            
            # 创建OCI配置
            config = {
                "user": tenant['user_ocid'],
                "key_file": tenant['key_file'],
                "fingerprint": tenant['fingerprint'],
                "tenancy": tenant['tenancy'],
                "region": tenant['region']
            }
            
            compute_client = self.get_compute_client(config)
            network_client = oci.core.VirtualNetworkClient(config)
            
            # 准备用户数据和SSH密钥
            metadata = {}
            if data['login_method'] == 'password':
                # 生成随机密码
                password = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=16))
                metadata['user_data'] = self._generate_cloud_init_script(password)
            elif data['login_method'] == 'ssh' and data.get('ssh_key'):
                metadata['ssh_authorized_keys'] = data['ssh_key']
            
            # 准备实例详情
            instance_details = oci.core.models.LaunchInstanceDetails(
                availability_domain=data['availability_domain'],
                compartment_id=tenant['compartment_id'],
                display_name=data['display_name'],
                shape=data['shape'],
                metadata=metadata,
                source_details=oci.core.models.InstanceSourceViaImageDetails(
                    image_id=data['image_id'],
                    boot_volume_size_in_gbs=data['boot_volume_size_in_gbs']
                ),
                create_vnic_details=oci.core.models.CreateVnicDetails(
                    subnet_id=data['subnet_id'],
                    assign_public_ip=True  # 分配公网IP
                )
            )

            # 如果是弹性配置，添加shape配置详情
            if data['shape'].endswith('.Flex'):
                instance_details.shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(
                    ocpus=float(data['ocpus']),
                    memory_in_gbs=float(data['memory_in_gbs'])
                )

            # 创建实例
            launch_instance_response = compute_client.launch_instance(
                launch_instance_details=instance_details
            )
            
            instance = launch_instance_response.data
            
            # 等待实例变为RUNNING状态
            get_instance_response = oci.wait_until(
                compute_client,
                compute_client.get_instance(instance.id),
                'lifecycle_state',
                'RUNNING',
                max_wait_seconds=1000
            )
            
            instance = get_instance_response.data
            
            # 获取实例的VNIC信息以获取公网IP
            private_ip, public_ip = self.get_instance_vnic_attachments(
                compute_client,
                network_client,
                tenant['compartment_id'],
                instance.id
            )
            
            # 构建返回结果
            result = {
                'success': True,
                'instance': {
                    'id': instance.id,
                    'display_name': instance.display_name,
                    'lifecycle_state': instance.lifecycle_state,
                    'time_created': instance.time_created.strftime('%Y-%m-%d %H:%M:%S'),
                    'public_ip': public_ip,
                    'private_ip': private_ip
                }
            }
            
            # 如果是密码登录，返回生成的密码
            if data['login_method'] == 'password':
                result['password'] = password
        
            return result
        
        except Exception as e:
            logging.error(f"创建实例失败: {str(e)}", exc_info=True)
            raise Exception(f"创建实例失败: {str(e)}")

    def delete_instance(self, tenant_id: str, instance_id: str) -> bool:
        """
        删除实例
        :param tenant_id: 租户ID
        :param instance_id: 实例ID
        :return: 是否成功
        """
        try:
            # 获取租户信息
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError("租户不存在")
            
            # 创建OCI配置
            config = {
                "user": tenant['user_ocid'],
                "key_file": tenant['key_file'],
                "fingerprint": tenant['fingerprint'],
                "tenancy": tenant['tenancy'],
                "region": tenant['region']
            }
            
            # 获取计算客户端
            compute_client = self.get_compute_client(config)
            
            # 终止实例
            compute_client.terminate_instance(instance_id)
            
            # 等待实例被删除
            try:
                oci.wait_until(
                    compute_client,
                    compute_client.get_instance(instance_id),
                    'lifecycle_state',
                    'TERMINATED',
                    max_wait_seconds=1000
                )
            except oci.exceptions.ServiceError as e:
                if e.status == 404:  # 实例已经被删除
                    return True
                raise
                
            return True
            
        except Exception as e:
            logging.error(f"删除实例失败: {str(e)}", exc_info=True)
            return False
