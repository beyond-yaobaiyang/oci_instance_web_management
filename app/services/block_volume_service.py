import oci
import logging
from typing import Dict, Any, List, Optional, Tuple
from app.services.tenant_service import TenantService
# from app import db

class BlockVolumeService:
    def __init__(self):
        self.tenant_service = TenantService()
    
    def _get_clients(self, tenant_id: str) -> Tuple[Optional[oci.core.ComputeClient], Optional[oci.core.BlockstorageClient], Optional[oci.core.BlockstorageClient]]:
        """获取OCI客户端"""
        try:
            compute_client = self.tenant_service.get_oci_client(tenant_id, service="compute")
            block_volume_client = self.tenant_service.get_oci_client(tenant_id, service="block_storage")
            boot_volume_client = self.tenant_service.get_oci_client(tenant_id, service="block_storage")
            return compute_client, block_volume_client, boot_volume_client
        except Exception as e:
            logging.error(f"创建OCI客户端失败: {str(e)}")
            return None, None, None
            
    def list_attached_volumes(self, tenant_id: str, instance_id: str) -> List[Dict[str, Any]]:
        """获取实例上已附加的块存储卷"""
        try:
            compute_client, block_volume_client, boot_volume_client = self._get_clients(tenant_id)
            if not compute_client or not block_volume_client:
                raise ValueError("无法创建OCI客户端")
            
            # 获取租户的compartment_id
            tenant_config = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant_config:
                raise ValueError("找不到租户配置")
            compartment_id = tenant_config.get('compartment_id')
            if not compartment_id:
                raise ValueError("租户配置中缺少compartment_id")
            
            # 获取实例的所有附件（包括已分离的）
            attachments = compute_client.list_volume_attachments(
                compartment_id=compartment_id,
                instance_id=instance_id
            ).data
            
            volumes = []
            for attachment in attachments:
                try:
                    if attachment.lifecycle_state != "ATTACHED":
                        # 如果附件的状态不是ATTACHED，跳过
                        logging.info(f"卷附件 {attachment.id} 状态为 {attachment.lifecycle_state}，跳过获取卷详情")
                        continue
                    volume_info = None
                    if attachment.volume_id.startswith('ocid1.bootvolume.'):
                        # 如果是引导卷
                        volume_info = boot_volume_client.get_boot_volume(boot_volume_id=attachment.volume_id).data
                    else:
                        # 如果是块存储卷
                        volume_info = block_volume_client.get_volume(volume_id=attachment.volume_id).data
                    
                    volumes.append({
                        "id": volume_info.id,
                        "display_name": volume_info.display_name,
                        "size_in_gbs": volume_info.size_in_gbs,
                        "vpus_per_gb": volume_info.vpus_per_gb,
                        "lifecycle_state": attachment.lifecycle_state,  # 使用附件的状态而不是卷的状态
                        "attachment_id": attachment.id,
                        "attachment_type": attachment.attachment_type,
                        "time_created": attachment.time_created.strftime("%Y-%m-%d %H:%M:%S")
                    })
                except Exception as e:
                    logging.error(f"获取卷详情失败: {str(e)}")
                    continue
            
            logging.info(f"找到 {len(volumes)} 个卷")
            return volumes
            
        except Exception as e:
            logging.error(f"获取卷列表失败: {str(e)}")
            raise
            
    def detach_volume(self, tenant_id: str, attachment_id: str) -> Dict[str, str]:
        """分离块存储卷"""
        try:
            compute_client, _, _ = self._get_clients(tenant_id)
            if not compute_client:
                raise ValueError("无法创建OCI客户端")
                
            compute_client.detach_volume(volume_attachment_id=attachment_id)
            return {"message": "块存储卷分离操作已启动"}
        except Exception as e:
            logging.error(f"分离块存储卷失败: {str(e)}")
            raise
            
    def attach_volume(self, tenant_id: str, instance_id: str, volume_id: str) -> Dict[str, Any]:
        """附加块存储卷到实例"""
        try:
            compute_client, block_volume_client, _ = self._get_clients(tenant_id)
            if not compute_client or not block_volume_client:
                raise ValueError("无法创建OCI客户端")
            
            # 创建卷附件
            attach_details = oci.core.models.AttachVolumeDetails(
                type="paravirtualized",  # 使用paravirtualized类型以支持在线附加
                volume_id=volume_id,
                instance_id=instance_id
            )
            
            attachment = compute_client.attach_volume(attach_details).data
            logging.info(f"已创建卷附件: {attachment.id}")
            
            return {
                "id": attachment.id,
                "lifecycle_state": attachment.lifecycle_state,
                "volume_id": attachment.volume_id,
                "instance_id": attachment.instance_id
            }
            
        except Exception as e:
            logging.error(f"附加块存储卷失败: {str(e)}")
            raise
            
    def update_volume(self, tenant_id: str, volume_id: str, vpus_per_gb: int) -> Dict[str, Any]:
        """更新块存储卷或引导卷的性能"""
        try:
            compute_client, block_volume_client, boot_volume_client = self._get_clients(tenant_id)
            if not block_volume_client or not boot_volume_client:
                raise ValueError("无法创建OCI客户端")

            # 判断是否为引导卷
            is_boot_volume = volume_id.startswith('ocid1.bootvolume.')
            logging.info(f"更新{'引导卷' if is_boot_volume else '块存储卷'} {volume_id} 的性能为 {vpus_per_gb} VPUS/GB")

            try:
                if is_boot_volume:
                    # 更新引导卷
                    details = oci.core.models.UpdateBootVolumeDetails(vpus_per_gb=vpus_per_gb)
                    result = boot_volume_client.update_boot_volume(
                        boot_volume_id=volume_id, 
                        update_boot_volume_details=details
                    )
                    volume_info = result.data
                else:
                    # 更新块存储卷
                    details = oci.core.models.UpdateVolumeDetails(vpus_per_gb=vpus_per_gb)
                    result = block_volume_client.update_volume(
                        volume_id=volume_id, 
                        update_volume_details=details
                    )
                    volume_info = result.data

                return {
                    "message": f"{'引导卷' if is_boot_volume else '块存储卷'}更新成功",
                    "volume": {
                        "id": volume_info.id,
                        "display_name": volume_info.display_name,
                        "size_in_gbs": volume_info.size_in_gbs,
                        "vpus_per_gb": volume_info.vpus_per_gb,
                        "lifecycle_state": volume_info.lifecycle_state
                    }
                }
            except oci.exceptions.ServiceError as e:
                if e.status == 409 and e.code == "IncorrectState":
                    raise ValueError(f"{'引导卷' if is_boot_volume else '块存储卷'}当前状态不允许更新，请稍后再试")
                logging.error(f"OCI服务错误: {str(e)}")
                raise ValueError(str(e))
                
        except ValueError as e:
            logging.error(f"更新卷失败: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"更新卷失败: {str(e)}")
            raise ValueError(f"更新{'引导卷' if is_boot_volume else '块存储卷'}失败: {str(e)}")
            
    def list_available_volumes(self, tenant_id: str, availability_domain: str) -> List[Dict[str, Any]]:
        """获取可用的块存储卷和已分离的引导卷列表"""
        try:
            compute_client, block_volume_client, boot_volume_client = self._get_clients(tenant_id)
            if not compute_client or not block_volume_client or not boot_volume_client:
                raise ValueError("无法创建OCI客户端")
            
            # 获取租户的compartment_id
            tenant_config = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant_config:
                raise ValueError("找不到租户配置")
            compartment_id = tenant_config.get('compartment_id')
            if not compartment_id:
                raise ValueError("租户配置中缺少compartment_id")
            
            # 获取可用的块存储卷
            block_volumes = block_volume_client.list_volumes(
                compartment_id=compartment_id,
                availability_domain=availability_domain
            ).data
            
            # 获取可用的引导卷
            boot_volumes = boot_volume_client.list_boot_volumes(
                compartment_id=compartment_id,
                availability_domain=availability_domain
            ).data
            
            # 获取所有引导卷附件
            boot_attachments = compute_client.list_boot_volume_attachments(
                compartment_id=compartment_id,
                availability_domain=availability_domain
            ).data
            
            # 创建已附加引导卷ID集合
            attached_boot_volume_ids = {attachment.boot_volume_id for attachment in boot_attachments
                                     if attachment.lifecycle_state not in ["DETACHING", "DETACHED"]}
            
            # 合并块存储卷和引导卷列表
            available_volumes = []
            
            # 添加块存储卷
            for volume in block_volumes:
                if volume.lifecycle_state == "AVAILABLE":
                    available_volumes.append({
                        "id": volume.id,
                        "display_name": volume.display_name,
                        "size_in_gbs": volume.size_in_gbs,
                        "vpus_per_gb": volume.vpus_per_gb,
                        "lifecycle_state": volume.lifecycle_state,
                        "volume_type": "block"  # 标记为块存储卷
                    })
            
            # 添加已分离的引导卷
            for volume in boot_volumes:
                # 检查引导卷是否已分离（状态为AVAILABLE且没有活动的附件）
                if (volume.lifecycle_state == "AVAILABLE" and 
                    volume.id not in attached_boot_volume_ids):
                    available_volumes.append({
                        "id": volume.id,
                        "display_name": f"[引导卷] {volume.display_name}",  # 添加标记以区分
                        "size_in_gbs": volume.size_in_gbs,
                        "vpus_per_gb": volume.vpus_per_gb,
                        "lifecycle_state": volume.lifecycle_state,
                        "volume_type": "boot"  # 标记为引导卷
                    })
            
            logging.info(f"找到 {len(available_volumes)} 个可用卷（包括块存储卷和已分离的引导卷）")
            return available_volumes
            
        except Exception as e:
            logging.error(f"获取可用卷列表失败: {str(e)}")
            raise
