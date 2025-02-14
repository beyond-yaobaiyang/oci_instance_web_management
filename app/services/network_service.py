import oci
import logging
from typing import Dict, Any, List, Optional, Tuple
from app.services.tenant_service import TenantService

class NetworkService:
    def __init__(self):
        self.tenant_service = TenantService()
    
    def _get_clients(self, tenant_id: str) -> Tuple[Optional[oci.core.VirtualNetworkClient], str]:
        """获取OCI网络客户端和租户ID"""
        try:
            network_client = self.tenant_service.get_oci_client(tenant_id, service="network")
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError("租户不存在")
            return network_client, tenant['compartment_id']
        except Exception as e:
            logging.error(f"创建OCI网络客户端失败: {str(e)}")
            raise

    def list_vcns(self, tenant_id: str) -> List[Dict[str, Any]]:
        """获取VCN列表"""
        try:
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError("租户不存在")
            
            network_client = self.tenant_service.get_oci_client(tenant_id, service="network")
            vcns = network_client.list_vcns(tenant['compartment_id']).data
            logging.info(f"找到 {len(vcns)} 个VCN")
            
            return [{
                'id': vcn.id,
                'display_name': vcn.display_name,
                'cidr_block': vcn.cidr_block,
                'lifecycle_state': vcn.lifecycle_state,
                'time_created': vcn.time_created.isoformat()
            } for vcn in vcns]
        except Exception as e:
            logging.error(f"获取VCN列表失败: {str(e)}")
            raise

    def list_security_groups(self, tenant_id: str, vcn_id: str = None) -> List[Dict[str, Any]]:
        """获取安全组列表"""
        try:
            network_client, compartment_id = self._get_clients(tenant_id)
            security_groups = network_client.list_network_security_groups(
                compartment_id=compartment_id
            ).data
            return [{
                'id': sg.id,
                'display_name': sg.display_name,
                'lifecycle_state': sg.lifecycle_state,
                'time_created': sg.time_created.isoformat(),
                'vcn_id': sg.vcn_id
            } for sg in security_groups]
        except Exception as e:
            logging.error(f"获取安全组列表失败: {str(e)}")
            raise

    def list_security_groups_by_compartment(self, tenant_id: str, compartment_id: str) -> List[Dict[str, Any]]:
        """根据区间ID获取安全组列表"""
        try:
            network_client = self.tenant_service.get_oci_client(tenant_id, service="network")
            security_lists = network_client.list_security_lists(
                compartment_id=compartment_id
            ).data
            return [{
                'id': sl.id,
                'display_name': sl.display_name,
                'lifecycle_state': sl.lifecycle_state,
                'time_created': sl.time_created.isoformat(),
                'vcn_id': sl.vcn_id
            } for sl in security_lists]
        except Exception as e:
            logging.error(f"获取安全组列表失败: {str(e)}")
            raise

    def list_security_group_rules(self, tenant_id: str, security_group_id: str) -> List[Dict[str, Any]]:
        """获取安全组规则列表"""
        try:
            network_client = self.tenant_service.get_oci_client(tenant_id, service="network")
            security_list = network_client.get_security_list(security_group_id).data
            
            ingress_rules = [{
                'id': f"ingress_{i}",
                'direction': 'INGRESS',
                'protocol': rule.protocol,
                'source': rule.source,
                'source_type': 'CIDR_BLOCK',
                'description': rule.description,
                'is_stateless': rule.is_stateless,
                'time_created': security_list.time_created.isoformat()
            } for i, rule in enumerate(security_list.ingress_security_rules)]
            
            egress_rules = [{
                'id': f"egress_{i}",
                'direction': 'EGRESS',
                'protocol': rule.protocol,
                'destination': rule.destination,
                'destination_type': 'CIDR_BLOCK',
                'description': rule.description,
                'is_stateless': rule.is_stateless,
                'time_created': security_list.time_created.isoformat()
            } for i, rule in enumerate(security_list.egress_security_rules)]
            
            return ingress_rules + egress_rules
        except Exception as e:
            logging.error(f"获取安全组规则失败: {str(e)}")
            raise

    def get_security_group(self, tenant_id: str, security_group_id: str) -> Dict[str, Any]:
        """获取安全组"""
        try:
            network_client = self.tenant_service.get_oci_client(tenant_id, service="network")
            security_group = network_client.get_network_security_group(security_group_id).data
            return {
                'id': security_group.id,
                'display_name': security_group.display_name,
                'lifecycle_state': security_group.lifecycle_state,
                'time_created': security_group.time_created.isoformat(),
                'vcn_id': security_group.vcn_id
            }
        except Exception as e:
            logging.error(f"获取安全组失败: {str(e)}")
            raise

    def create_security_group(self, tenant_id: str, vcn_id: str, display_name: str, description: str = None) -> Dict[str, Any]:
        """创建安全组"""
        try:
            network_client, compartment_id = self._get_clients(tenant_id)
            details = oci.core.models.CreateNetworkSecurityGroupDetails(
                compartment_id=compartment_id,
                vcn_id=vcn_id,
                display_name=display_name,
                description=description
            )
            response = network_client.create_network_security_group(details)
            return {
                'id': response.data.id,
                'display_name': response.data.display_name,
                'lifecycle_state': response.data.lifecycle_state,
                'time_created': response.data.time_created.isoformat(),
                'vcn_id': response.data.vcn_id
            }
        except Exception as e:
            logging.error(f"创建安全组失败: {str(e)}")
            raise

    def delete_security_group(self, tenant_id: str, security_group_id: str) -> bool:
        """删除安全组"""
        try:
            network_client, _ = self._get_clients(tenant_id)
            network_client.delete_network_security_group(security_group_id)
            return True
        except Exception as e:
            logging.error(f"删除安全组失败: {str(e)}")
            raise

    def add_security_rule(self, tenant_id: str, security_group_id: str, 
                         direction: str, protocol: str, 
                         source: str = None, source_type: str = None,
                         destination: str = None, destination_type: str = None,
                         is_stateless: bool = False, description: str = None) -> Dict[str, Any]:
        """添加安全组规则"""
        try:
            network_client, _ = self._get_clients(tenant_id)
            details = oci.core.models.AddNetworkSecurityGroupSecurityRulesDetails(
                security_rules=[
                    oci.core.models.AddSecurityRuleDetails(
                        direction=direction,
                        protocol=protocol,
                        source=source,
                        source_type=source_type,
                        destination=destination,
                        destination_type=destination_type,
                        is_stateless=is_stateless,
                        description=description
                    )
                ]
            )
            response = network_client.add_network_security_group_security_rules(
                security_group_id, details
            )
            return response.data.security_rules[0]
        except Exception as e:
            logging.error(f"添加安全组规则失败: {str(e)}")
            raise

    def remove_security_rule(self, tenant_id: str, security_group_id: str, rule_id: str) -> bool:
        """删除安全组规则"""
        try:
            network_client, _ = self._get_clients(tenant_id)
            network_client.remove_network_security_group_security_rules(
                security_group_id,
                oci.core.models.RemoveNetworkSecurityGroupSecurityRulesDetails(
                    security_rule_ids=[rule_id]
                )
            )
            return True
        except Exception as e:
            logging.error(f"删除安全组规则失败: {str(e)}")
            raise

    def get_security_list_rules(self, tenant_id: str, security_list_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """获取安全组规则"""
        try:
            network_client = self.tenant_service.get_oci_client(tenant_id, service="network")
            security_list = network_client.get_security_list(security_list_id).data
            
            return {
                'ingress_rules': [
                    {
                        'is_stateless': rule.is_stateless,
                        'protocol': rule.protocol,
                        'source': rule.source,
                        'source_type': rule.source_type,
                        'description': rule.description,
                        'tcp_options': {
                            'source_port_range': {
                                'min': rule.tcp_options.source_port_range.min if rule.tcp_options and rule.tcp_options.source_port_range else None,
                                'max': rule.tcp_options.source_port_range.max if rule.tcp_options and rule.tcp_options.source_port_range else None
                            } if rule.tcp_options and rule.tcp_options.source_port_range else None,
                            'destination_port_range': {
                                'min': rule.tcp_options.destination_port_range.min if rule.tcp_options and rule.tcp_options.destination_port_range else None,
                                'max': rule.tcp_options.destination_port_range.max if rule.tcp_options and rule.tcp_options.destination_port_range else None
                            } if rule.tcp_options and rule.tcp_options.destination_port_range else None
                        } if rule.tcp_options else None,
                        'udp_options': {
                            'source_port_range': {
                                'min': rule.udp_options.source_port_range.min if rule.udp_options and rule.udp_options.source_port_range else None,
                                'max': rule.udp_options.source_port_range.max if rule.udp_options and rule.udp_options.source_port_range else None
                            } if rule.udp_options and rule.udp_options.source_port_range else None,
                            'destination_port_range': {
                                'min': rule.udp_options.destination_port_range.min if rule.udp_options and rule.udp_options.destination_port_range else None,
                                'max': rule.udp_options.destination_port_range.max if rule.udp_options and rule.udp_options.destination_port_range else None
                            } if rule.udp_options and rule.udp_options.destination_port_range else None
                        } if rule.udp_options else None
                    }
                    for rule in security_list.ingress_security_rules
                ],
                'egress_rules': [
                    {
                        'is_stateless': rule.is_stateless,
                        'protocol': rule.protocol,
                        'destination': rule.destination,
                        'destination_type': rule.destination_type,
                        'description': rule.description,
                        'tcp_options': {
                            'source_port_range': {
                                'min': rule.tcp_options.source_port_range.min if rule.tcp_options and rule.tcp_options.source_port_range else None,
                                'max': rule.tcp_options.source_port_range.max if rule.tcp_options and rule.tcp_options.source_port_range else None
                            } if rule.tcp_options and rule.tcp_options.source_port_range else None,
                            'destination_port_range': {
                                'min': rule.tcp_options.destination_port_range.min if rule.tcp_options and rule.tcp_options.destination_port_range else None,
                                'max': rule.tcp_options.destination_port_range.max if rule.tcp_options and rule.tcp_options.destination_port_range else None
                            } if rule.tcp_options and rule.tcp_options.destination_port_range else None
                        } if rule.tcp_options else None,
                        'udp_options': {
                            'source_port_range': {
                                'min': rule.udp_options.source_port_range.min if rule.udp_options and rule.udp_options.source_port_range else None,
                                'max': rule.udp_options.source_port_range.max if rule.udp_options and rule.udp_options.source_port_range else None
                            } if rule.udp_options and rule.udp_options.source_port_range else None,
                            'destination_port_range': {
                                'min': rule.udp_options.destination_port_range.min if rule.udp_options and rule.udp_options.destination_port_range else None,
                                'max': rule.udp_options.destination_port_range.max if rule.udp_options and rule.udp_options.destination_port_range else None
                            } if rule.udp_options and rule.udp_options.destination_port_range else None
                        } if rule.udp_options else None
                    }
                    for rule in security_list.egress_security_rules
                ]
            }
        except Exception as e:
            logging.error(f"获取安全组规则失败: {str(e)}")
            raise

    def update_security_list_rules(
        self,
        tenant_id: str,
        security_list_id: str,
        ingress_rules: List[Dict[str, Any]],
        egress_rules: List[Dict[str, Any]]
    ) -> None:
        """更新安全组规则"""
        try:
            network_client = self.tenant_service.get_oci_client(tenant_id, service="network")
            security_list = network_client.get_security_list(security_list_id).data
            
            def create_port_range(options, direction):
                if not options:
                    return None
                port_range = options.get(f'{direction}_port_range')
                if not port_range:
                    return None
                return oci.core.models.PortRange(
                    min=port_range['min'],
                    max=port_range['max']
                )

            # 创建更新请求
            update_security_list_details = oci.core.models.UpdateSecurityListDetails(
                ingress_security_rules=[
                    oci.core.models.IngressSecurityRule(
                        is_stateless=rule['is_stateless'],
                        protocol=rule['protocol'],
                        source=rule['source'],
                        source_type=rule.get('source_type', 'CIDR_BLOCK'),
                        description=rule.get('description', ''),
                        tcp_options=oci.core.models.TcpOptions(
                            source_port_range=create_port_range(rule.get('tcp_options'), 'source'),
                            destination_port_range=create_port_range(rule.get('tcp_options'), 'destination')
                        ) if rule.get('tcp_options') else None,
                        udp_options=oci.core.models.UdpOptions(
                            source_port_range=create_port_range(rule.get('udp_options'), 'source'),
                            destination_port_range=create_port_range(rule.get('udp_options'), 'destination')
                        ) if rule.get('udp_options') else None
                    )
                    for rule in ingress_rules
                ],
                egress_security_rules=[
                    oci.core.models.EgressSecurityRule(
                        is_stateless=rule['is_stateless'],
                        protocol=rule['protocol'],
                        destination=rule['destination'],
                        destination_type=rule.get('destination_type', 'CIDR_BLOCK'),
                        description=rule.get('description', ''),
                        tcp_options=oci.core.models.TcpOptions(
                            source_port_range=create_port_range(rule.get('tcp_options'), 'source'),
                            destination_port_range=create_port_range(rule.get('tcp_options'), 'destination')
                        ) if rule.get('tcp_options') else None,
                        udp_options=oci.core.models.UdpOptions(
                            source_port_range=create_port_range(rule.get('udp_options'), 'source'),
                            destination_port_range=create_port_range(rule.get('udp_options'), 'destination')
                        ) if rule.get('udp_options') else None
                    )
                    for rule in egress_rules
                ]
            )
            
            # 更新安全组规则
            network_client.update_security_list(
                security_list_id=security_list_id,
                update_security_list_details=update_security_list_details
            )
        except Exception as e:
            logging.error(f"更新安全组规则失败: {str(e)}")
            raise

    def list_route_tables(self, tenant_id: str, vcn_id: str = None) -> List[Dict[str, Any]]:
        """获取路由表列表"""
        try:
            network_client, compartment_id = self._get_clients(tenant_id)
            route_tables = network_client.list_route_tables(
                compartment_id=compartment_id,
                vcn_id=vcn_id
            ).data
            return [{
                'id': rt.id,
                'display_name': rt.display_name,
                'vcn_id': rt.vcn_id,
                'lifecycle_state': rt.lifecycle_state,
                'time_created': rt.time_created.isoformat(),
                'route_rules': [{
                    'destination': rule.destination,
                    'destination_type': rule.destination_type,
                    'network_entity_id': rule.network_entity_id,
                    'description': rule.description
                } for rule in rt.route_rules]
            } for rt in route_tables]
        except Exception as e:
            logging.error(f"获取路由表列表失败: {str(e)}")
            raise

    def get_route_table(self, tenant_id: str, route_table_id: str) -> Dict[str, Any]:
        """获取路由表详情"""
        try:
            network_client = self.tenant_service.get_oci_client(tenant_id, service="network")
            route_table = network_client.get_route_table(route_table_id).data
            return {
                'id': route_table.id,
                'display_name': route_table.display_name,
                'vcn_id': route_table.vcn_id,
                'lifecycle_state': route_table.lifecycle_state,
                'time_created': route_table.time_created.isoformat(),
                'route_rules': [{
                    'destination': rule.destination,
                    'destination_type': rule.destination_type,
                    'network_entity_id': rule.network_entity_id,
                    'description': rule.description
                } for rule in route_table.route_rules]
            }
        except Exception as e:
            logging.error(f"获取路由表详情失败: {str(e)}")
            raise

    def update_route_table(self, tenant_id: str, route_table_id: str, route_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """更新路由表规则"""
        try:
            network_client = self.tenant_service.get_oci_client(tenant_id, service="network")
            
            # 构建路由规则
            route_table_rules = []
            for rule in route_rules:
                route_table_rules.append(
                    oci.core.models.RouteRule(
                        destination=rule['destination'],
                        destination_type=rule['destination_type'],
                        network_entity_id=rule['network_entity_id'],
                        description=rule.get('description', '')
                    )
                )
            
            # 更新路由表
            details = oci.core.models.UpdateRouteTableDetails(
                route_rules=route_table_rules
            )
            
            result = network_client.update_route_table(
                route_table_id,
                details
            ).data
            
            return {
                'id': result.id,
                'display_name': result.display_name,
                'vcn_id': result.vcn_id,
                'lifecycle_state': result.lifecycle_state,
                'time_created': result.time_created.isoformat(),
                'route_rules': [{
                    'destination': rule.destination,
                    'destination_type': rule.destination_type,
                    'network_entity_id': rule.network_entity_id,
                    'description': rule.description
                } for rule in result.route_rules]
            }
        except Exception as e:
            logging.error(f"更新路由表失败: {str(e)}")
            raise

    def list_network_entities(self, tenant_id: str, vcn_id: str) -> List[Dict[str, Any]]:
        """获取网络实体列表（互联网网关、NAT网关、服务网关等）"""
        try:
            network_client = self.tenant_service.get_oci_client(tenant_id, service="network")
            tenant = self.tenant_service.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError("租户不存在")

            entities = []
            
            # 获取互联网网关
            internet_gateways = network_client.list_internet_gateways(
                compartment_id=tenant['compartment_id'],
                vcn_id=vcn_id
            ).data
            for ig in internet_gateways:
                entities.append({
                    'id': ig.id,
                    'display_name': ig.display_name,
                    'type': 'Internet Gateway',
                    'lifecycle_state': ig.lifecycle_state
                })

            # 获取NAT网关
            nat_gateways = network_client.list_nat_gateways(
                compartment_id=tenant['compartment_id'],
                vcn_id=vcn_id
            ).data
            for ng in nat_gateways:
                entities.append({
                    'id': ng.id,
                    'display_name': ng.display_name,
                    'type': 'NAT Gateway',
                    'lifecycle_state': ng.lifecycle_state
                })

            # 获取服务网关
            service_gateways = network_client.list_service_gateways(
                compartment_id=tenant['compartment_id'],
                vcn_id=vcn_id
            ).data
            for sg in service_gateways:
                entities.append({
                    'id': sg.id,
                    'display_name': sg.display_name,
                    'type': 'Service Gateway',
                    'lifecycle_state': sg.lifecycle_state
                })

            # 获取本地对等网关
            local_peering_gateways = network_client.list_local_peering_gateways(
                compartment_id=tenant['compartment_id'],
                vcn_id=vcn_id
            ).data
            for lpg in local_peering_gateways:
                entities.append({
                    'id': lpg.id,
                    'display_name': lpg.display_name,
                    'type': 'Local Peering Gateway',
                    'lifecycle_state': lpg.lifecycle_state
                })

            return entities

        except Exception as e:
            logging.error(f"获取网络实体列表失败: {str(e)}")
            raise
