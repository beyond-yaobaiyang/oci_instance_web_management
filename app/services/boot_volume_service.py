import oci
import logging
from typing import Dict, Any, List, Optional, Tuple
from app.services.tenant_service import TenantService
# from app import db

class BootVolumeService:
    def __init__(self):
        self.tenant_service = TenantService()
    
    def _get_clients(self, tenant_id: str) -> Tuple[Optional[oci.core.ComputeClient], Optional[oci.core.BlockstorageClient]]:
        """获取OCI客户端"""
        try:
            compute_client = self.tenant_service.get_oci_client(tenant_id, service="compute")
            boot_volume_client = self.tenant_service.get_oci_client(tenant_id, service="block_storage")
            return compute_client, boot_volume_client
        except Exception as e:
            logging.error(f"创建OCI客户端失败: {str(e)}")
            return None, None
            
    def list_attached_volumes(self, tenant_id: str, instance_id: str) -> List[Dict[str, Any]]:
        """获取实例已附加的引导卷列表"""
        try:
            compute_client, boot_volume_client = self._get_clients(tenant_id)
            if not compute_client or not boot_volume_client:
                raise ValueError("无法创建OCI客户端")
            
            # 获取实例信息以获取可用性域
            instance = compute_client.get_instance(instance_id).data
            availability_domain = instance.availability_domain
            compartment_id = instance.compartment_id
            
            logging.info(f"获取实例 {instance_id} 的引导卷附件列表")
            # 获取实例的引导卷附件
            boot_attachments = compute_client.list_boot_volume_attachments(
                availability_domain=availability_domain,
                compartment_id=compartment_id,
                instance_id=instance_id
            ).data
            
            logging.info(f"找到 {len(boot_attachments)} 个引导卷附件")
            
            # 获取所有引导卷的ID
            volume_ids = set(attachment.boot_volume_id for attachment in boot_attachments)
            
            # 获取引导卷详情
            volumes = []
            for volume_id in volume_ids:
                try:
                    # 获取引导卷详情
                    volume = boot_volume_client.get_boot_volume(boot_volume_id=volume_id).data
                    
                    # 查找对应的附件
                    attachment = next(
                        (att for att in boot_attachments if att.boot_volume_id == volume_id),
                        None
                    )
                    
                    if attachment:
                        logging.info(f"引导卷 {volume_id} - 附件状态: {attachment.lifecycle_state}, 卷状态: {volume.lifecycle_state}")
                        # 如果有附件，使用附件的状态
                        volume_state = attachment.lifecycle_state
                        attachment_id = attachment.id
                        
                        # 如果附件状态是ATTACHED，但引导卷状态不是AVAILABLE，使用引导卷状态
                        if volume_state == "ATTACHED" and volume.lifecycle_state != "AVAILABLE":
                            volume_state = volume.lifecycle_state
                    else:
                        logging.info(f"引导卷 {volume_id} - 无附件, 卷状态: {volume.lifecycle_state}")
                        # 如果没有附件，使用卷的状态
                        volume_state = "DETACHED"
                        attachment_id = None
                    
                    volumes.append({
                        "id": volume.id,
                        "display_name": volume.display_name,
                        "size_in_gbs": volume.size_in_gbs,
                        "vpus_per_gb": volume.vpus_per_gb,
                        "lifecycle_state": volume_state,
                        "attachment_id": attachment_id,
                        "availability_domain": availability_domain
                    })
                except Exception as ve:
                    logging.error(f"获取引导卷 {volume_id} 详情失败: {str(ve)}")
                    continue
            
            return volumes
            
        except Exception as e:
            logging.error(f"获取已附加引导卷列表失败: {str(e)}")
            raise
            
    def detach_volume(self, tenant_id: str, attachment_id: str) -> Dict[str, str]:
        """分离引导卷"""
        try:
            compute_client, _ = self._get_clients(tenant_id)
            if not compute_client:
                raise ValueError("无法创建OCI客户端")
            
            logging.info(f"开始分离引导卷，附件ID: {attachment_id}")
            
            # 获取附件信息
            try:
                attachment = compute_client.get_boot_volume_attachment(attachment_id).data
                logging.info(f"当前附件状态: {attachment.lifecycle_state}")
                
                # 如果已经在分离中或已分离，直接返回
                if attachment.lifecycle_state == "DETACHING":
                    return {"message": "引导卷正在分离中", "state": "DETACHING"}
                elif attachment.lifecycle_state == "DETACHED":
                    return {"message": "引导卷已分离", "state": "DETACHED"}
                
                # 执行分离操作
                compute_client.detach_boot_volume(attachment_id).data
                
                # 再次获取附件状态
                attachment = compute_client.get_boot_volume_attachment(attachment_id).data
                logging.info(f"分离操作后的附件状态: {attachment.lifecycle_state}")
                
                return {
                    "message": "引导卷分离操作已启动",
                    "state": attachment.lifecycle_state
                }
            except Exception as e:
                logging.error(f"分离引导卷时发生错误: {str(e)}")
                if "NotAuthorizedOrNotFound" in str(e):
                    return {"message": "引导卷已分离", "state": "DETACHED"}
                raise
                
        except Exception as e:
            logging.error(f"分离引导卷失败: {str(e)}")
            raise
            
    def attach_volume(self, tenant_id: str, instance_id: str, volume_id: str) -> Dict[str, str]:
        """附加引导卷到实例"""
        try:
            compute_client, boot_volume_client = self._get_clients(tenant_id)
            if not compute_client or not boot_volume_client:
                raise ValueError("无法创建OCI客户端")
            
            logging.info(f"开始附加引导卷 {volume_id} 到实例 {instance_id}")
            
            # 获取实例信息
            instance = compute_client.get_instance(instance_id).data
            
            # 创建附件
            attachment_details = oci.core.models.AttachBootVolumeDetails(
                boot_volume_id=volume_id,
                instance_id=instance_id,
                display_name=f"Boot Volume for {instance.display_name}"
            )
            
            try:
                attachment = compute_client.attach_boot_volume(attachment_details).data
                logging.info(f"引导卷附件创建成功，状态: {attachment.lifecycle_state}")
                
                return {
                    "message": "引导卷附加操作已启动",
                    "state": attachment.lifecycle_state,
                    "attachment_id": attachment.id
                }
            except Exception as e:
                logging.error(f"附加引导卷时发生错误: {str(e)}")
                if "NotAuthorizedOrNotFound" in str(e):
                    # 检查是否已经附加
                    attachments = compute_client.list_boot_volume_attachments(
                        availability_domain=instance.availability_domain,
                        compartment_id=instance.compartment_id,
                        instance_id=instance_id,
                        boot_volume_id=volume_id
                    ).data
                    
                    if attachments:
                        attachment = attachments[0]
                        return {
                            "message": "引导卷已附加",
                            "state": attachment.lifecycle_state,
                            "attachment_id": attachment.id
                        }
                raise
                
        except Exception as e:
            logging.error(f"附加引导卷失败: {str(e)}")
            raise
            
    def update_volume(self, tenant_id: str, boot_volume_id: str, size_in_gbs: Optional[int] = None, 
                     vpus_per_gb: Optional[int] = None) -> Dict[str, str]:
        """更新引导卷配置（大小只能增加不能减少）"""
        try:
            _, boot_volume_client = self._get_clients(tenant_id)
            if not boot_volume_client:
                raise ValueError("无法创建OCI客户端")
                
            # 获取当前卷信息
            current_volume = boot_volume_client.get_boot_volume(boot_volume_id).data
            
            update_details = {}
            if size_in_gbs:
                if size_in_gbs < current_volume.size_in_gbs:
                    raise ValueError("卷大小只能增加不能减少")
                update_details["size_in_gbs"] = size_in_gbs
                
            if vpus_per_gb is not None:
                update_details["vpus_per_gb"] = vpus_per_gb
                
            details = oci.core.models.UpdateBootVolumeDetails(**update_details)
            boot_volume_client.update_boot_volume(
                boot_volume_id=boot_volume_id,
                update_boot_volume_details=details
            )
            return {"message": "引导卷更新操作已启动"}
        except Exception as e:
            logging.error(f"更新引导卷失败: {str(e)}")
            raise
            
    def list_available_volumes(self, tenant_id: str, availability_domain: str) -> List[Dict[str, Any]]:
        """获取可用的引导卷列表"""
        try:
            compute_client, boot_volume_client = self._get_clients(tenant_id)
            if not compute_client or not boot_volume_client:
                raise ValueError("无法创建OCI客户端")
            
            # 获取租户的compartment_id
            tenant_config = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant_config:
                raise ValueError("找不到租户配置")
            compartment_id = tenant_config.get('compartment_id')
            if not compartment_id:
                raise ValueError("租户配置中缺少compartment_id")
            
            # 获取可用的引导卷
            try:
                volumes = boot_volume_client.list_boot_volumes(
                    availability_domain=availability_domain,
                    compartment_id=compartment_id
                ).data
                
                return [{
                    "id": volume.id,
                    "display_name": volume.display_name,
                    "size_in_gbs": volume.size_in_gbs,
                    "vpus_per_gb": volume.vpus_per_gb,
                    "lifecycle_state": volume.lifecycle_state
                } for volume in volumes if volume.lifecycle_state == "AVAILABLE"]
            except Exception as e:
                logging.error(f"获取引导卷列表失败: {str(e)}")
                # 检查是否是权限或资源不存在的错误
                if "NotAuthorizedOrNotFound" in str(e):
                    # 尝试获取实例的引导卷附件
                    boot_attachments = compute_client.list_boot_volume_attachments(
                        availability_domain=availability_domain,
                        compartment_id=compartment_id
                    ).data
                    
                    # 获取所有引导卷的ID
                    volume_ids = [attachment.boot_volume_id for attachment in boot_attachments]
                    
                    # 获取每个引导卷的详细信息
                    volumes = []
                    for volume_id in volume_ids:
                        try:
                            volume = boot_volume_client.get_boot_volume(boot_volume_id=volume_id).data
                            if volume.lifecycle_state == "AVAILABLE":
                                volumes.append({
                                    "id": volume.id,
                                    "display_name": volume.display_name,
                                    "size_in_gbs": volume.size_in_gbs,
                                    "vpus_per_gb": volume.vpus_per_gb,
                                    "lifecycle_state": volume.lifecycle_state
                                })
                        except Exception as ve:
                            logging.error(f"获取引导卷 {volume_id} 详情失败: {str(ve)}")
                            continue
                    
                    return volumes
                raise
        except Exception as e:
            logging.error(f"获取可用引导卷列表失败: {str(e)}")
            raise
            
    def get_attachment_status(self, tenant_id: str, attachment_id: str) -> Dict[str, str]:
        """获取引导卷附件状态"""
        try:
            compute_client, _ = self._get_clients(tenant_id)
            if not compute_client:
                raise ValueError("无法创建OCI客户端")
            
            logging.info(f"获取引导卷附件 {attachment_id} 的状态")
            
            try:
                attachment = compute_client.get_boot_volume_attachment(attachment_id).data
                logging.info(f"引导卷附件状态: {attachment.lifecycle_state}")
                
                return {
                    "state": attachment.lifecycle_state,
                    "message": f"引导卷附件状态: {attachment.lifecycle_state}"
                }
            except Exception as e:
                logging.error(f"获取引导卷附件状态失败: {str(e)}")
                if "NotAuthorizedOrNotFound" in str(e):
                    return {
                        "state": "DETACHED",
                        "message": "引导卷已分离"
                    }
                raise
                
        except Exception as e:
            logging.error(f"获取引导卷附件状态失败: {str(e)}")
            raise
