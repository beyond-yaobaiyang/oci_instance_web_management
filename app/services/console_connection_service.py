import oci
from app.services.tenant_service import TenantService
import logging
from typing import Dict, Any

class ConsoleConnectionService:
    def __init__(self):
        self.tenant_service = TenantService()

    def create_connection(self, tenant_id: str, instance_id: str, public_key: str) -> Dict[str, Any]:
        """创建实例控制台连接"""
        try:
            if not tenant_id or not instance_id or not public_key:
                logging.error("Missing required parameters")
                return None

            # 获取计算客户端
            compute_client = self.tenant_service.get_oci_client(tenant_id, service="compute")
            if not compute_client:
                logging.error(f"Failed to create compute client for tenant {tenant_id}")
                return None

            # 获取租户信息
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant:
                logging.error(f"No tenant found for tenant_id={tenant_id}")
                return None

            compartment_id = tenant.get('compartment_id')
            if not compartment_id:
                logging.error(f"No compartment_id found for tenant {tenant_id}")
                return None

            # 创建连接
            try:
                create_connection_details = oci.core.models.CreateInstanceConsoleConnectionDetails(
                    instance_id=instance_id,
                    public_key=public_key
                )

                logging.info(f"Creating console connection for instance {instance_id}")
                response = compute_client.create_instance_console_connection(
                    create_instance_console_connection_details=create_connection_details
                )

                if response and response.data:
                    connection = response.data
                    logging.info(f"Console connection created: {connection.id}")
                    return {
                        'id': connection.id,
                        'lifecycle_state': connection.lifecycle_state
                    }
                else:
                    logging.error("Failed to create console connection: No response data")
                    return None

            except oci.exceptions.ServiceError as e:
                logging.error(f"OCI Service Error while creating console connection: {str(e)}")
                raise e

        except Exception as e:
            logging.error(f"Failed to create console connection: {str(e)}")
            return None

    def delete_connection(self, tenant_id: str, instance_id: str) -> bool:
        """删除实例控制台连接"""
        try:
            if not tenant_id or not instance_id:
                logging.error("Missing required parameters")
                return False

            # 获取计算客户端
            compute_client = self.tenant_service.get_oci_client(tenant_id, service="compute")
            if not compute_client:
                logging.error(f"Failed to create compute client for tenant {tenant_id}")
                return False

            # 获取租户信息
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant:
                logging.error(f"No tenant found for tenant_id={tenant_id}")
                return False

            compartment_id = tenant.get('compartment_id')
            if not compartment_id:
                logging.error(f"No compartment_id found for tenant {tenant_id}")
                return False

            # 先获取现有的连接
            try:
                connections = compute_client.list_instance_console_connections(
                    compartment_id=compartment_id,
                    instance_id=instance_id
                ).data

                # 查找活动的连接
                active_connection = next(
                    (conn for conn in connections if conn.lifecycle_state not in ['DELETED', 'DELETING']),
                    None
                )

                if not active_connection:
                    logging.info("No active console connection found to delete")
                    return True

                # 删除连接
                logging.info(f"Deleting console connection: {active_connection.id}")
                compute_client.delete_instance_console_connection(
                    instance_console_connection_id=active_connection.id
                )

                logging.info("Console connection deleted successfully")
                return True

            except oci.exceptions.ServiceError as e:
                logging.error(f"OCI Service Error while deleting console connection: {str(e)}")
                raise e

        except Exception as e:
            logging.error(f"Failed to delete console connection: {str(e)}")
            return False

    def get_connection(self, tenant_id: str, instance_id: str) -> Dict[str, Any]:
        """获取实例控制台连接信息"""
        try:
            if not tenant_id or not instance_id:
                logging.error("Invalid parameters: tenant_id={tenant_id}, instance_id={instance_id}")
                return None

            # 使用get_oci_client获取计算客户端
            compute_client = self.tenant_service.get_oci_client(tenant_id, service="compute")
            if not compute_client:
                logging.error(f"Failed to create compute client for tenant {tenant_id}")
                return None

            try:
                # 直接使用传入的参数查询连接
                tenant = self.tenant_service.get_tenant_by_id(tenant_id)
                if not tenant:
                    logging.error(f"No tenant found for tenant_id={tenant_id}")
                    return None

                compartment_id = tenant.get('compartment_id')
                if not compartment_id:
                    logging.error(f"No compartment_id found for tenant {tenant_id}")
                    return None

                logging.info(f"Listing console connections for instance {instance_id} in compartment {compartment_id}")
                connections = compute_client.list_instance_console_connections(
                    compartment_id=compartment_id,
                    instance_id=instance_id
                ).data

                print(f"Found {len(connections)} console connections")
                for conn in connections:
                    print(f"Connection: {conn.id} (State: {conn.lifecycle_state})")

                if not connections:
                    return None

                print("All available connections:")
                for conn in connections:
                    print(f"- Connection {conn.id}:")
                    print(f"  State: {conn.lifecycle_state}")

                # 优先使用ACTIVE状态的连接
                active_connection = next(
                    (conn for conn in connections if conn.lifecycle_state == 'ACTIVE'),
                    None
                )

                if not active_connection:
                    print("No ACTIVE connection found, checking for other valid states...")
                    # 如果没有ACTIVE状态的连接，查找其他有效状态的连接
                    active_connection = next(
                        (conn for conn in connections if conn.lifecycle_state in ['CREATING', 'PROVISIONING']),
                        None
                    )

                if not active_connection:
                    print("No valid connection found")
                    return None

                print(f"Using connection: {active_connection.id} (State: {active_connection.lifecycle_state})")

                try:
                    # 获取VNC连接命令
                    connection_response = compute_client.get_instance_console_connection(
                        active_connection.id
                    )
                    
                    if connection_response and connection_response.data:
                        # 获取原始连接命令
                        original_connection_string = connection_response.data.connection_string
                        
                        # 解析连接命令中的重要部分
                        # 示例：ocid1.instanceconsoleconnection.oc1.xxx@instance-console.region.oci.oraclecloud.com
                        connection_parts = original_connection_string.split(' ')
                        for part in connection_parts:
                            if '@instance-console' in part:
                                console_connection = part.strip("'")
                                break
                        
                        # 构建新的连接命令
                        connection_string = f"ssh -o ProxyCommand='ssh -W %h:%p -p 443 -o StrictHostKeyChecking=no {console_connection}' -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -N -L 0.0.0.0:5900:{instance_id}:5900 {instance_id}"
                        
                        print(f"Got connection string: {connection_string}")

                        return {
                            'id': active_connection.id,
                            'lifecycle_state': active_connection.lifecycle_state,
                            'connection_string': connection_string
                        }
                    else:
                        print("No connection string available")
                except Exception as e:
                    print(f"Error getting connection string: {str(e)}")

                return None
                
            except oci.exceptions.ServiceError as e:
                print(f"OCI Service Error: {str(e)}")
                if e.status == 404:
                    return None
                raise e
                
        except Exception as e:
            print(f"General Error: {str(e)}")
            logging.error(f"获取控制台连接失败: {str(e)}")
            return None
