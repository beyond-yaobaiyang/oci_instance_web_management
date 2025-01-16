import oci
from typing import List, Optional, Dict, Any
from app import db
from app.models.network import VirtualCloudNetwork, Subnet, SecurityList, SecurityRule
from app.services.tenant_service import TenantService

class NetworkService:
    def __init__(self):
        self.tenant_service = TenantService()
    
    def get_vcns(self, tenant_id: Optional[int] = None) -> List[VirtualCloudNetwork]:
        """获取VCN列表"""
        query = VirtualCloudNetwork.query
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        return query.all()
    
    def get_vcn_by_id(self, vcn_id: int) -> Optional[VirtualCloudNetwork]:
        """根据ID获取VCN"""
        return VirtualCloudNetwork.query.get(vcn_id)
    
    def create_vcn(self, tenant_id: int, vcn_data: Dict[str, Any]) -> Optional[VirtualCloudNetwork]:
        """创建VCN"""
        try:
            # 获取OCI客户端
            compute_client = self.tenant_service.get_oci_client(tenant_id)
            if not compute_client:
                raise Exception("无法创建OCI客户端")
            
            # 创建网络客户端
            network_client = oci.core.VirtualNetworkClient(compute_client.base_client.config)
            
            # 创建VCN详情
            vcn_details = oci.core.models.CreateVcnDetails(
                compartment_id=vcn_data['compartment_id'],
                cidr_block=vcn_data['cidr_block'],
                display_name=vcn_data['name'],
                dns_label=vcn_data.get('dns_label')
            )
            
            # 调用OCI API创建VCN
            response = network_client.create_vcn(vcn_details)
            vcn_ocid = response.data.id
            
            # 创建本地VCN记录
            vcn = VirtualCloudNetwork(
                tenant_id=tenant_id,
                vcn_ocid=vcn_ocid,
                name=vcn_data['name'],
                compartment_id=vcn_data['compartment_id'],
                cidr_block=vcn_data['cidr_block'],
                dns_label=vcn_data.get('dns_label'),
                state='PROVISIONING'
            )
            
            db.session.add(vcn)
            db.session.commit()
            return vcn
            
        except Exception as e:
            print(f"创建VCN失败: {str(e)}")
            db.session.rollback()
            return None
    
    def create_subnet(self, vcn_id: int, subnet_data: Dict[str, Any]) -> Optional[Subnet]:
        """创建子网"""
        try:
            vcn = self.get_vcn_by_id(vcn_id)
            if not vcn:
                raise Exception("VCN不存在")
            
            compute_client = self.tenant_service.get_oci_client(vcn.tenant_id)
            if not compute_client:
                raise Exception("无法创建OCI客户端")
            
            network_client = oci.core.VirtualNetworkClient(compute_client.base_client.config)
            
            # 创建子网详情
            subnet_details = oci.core.models.CreateSubnetDetails(
                compartment_id=subnet_data['compartment_id'],
                vcn_id=vcn.vcn_ocid,
                cidr_block=subnet_data['cidr_block'],
                display_name=subnet_data['name'],
                dns_label=subnet_data.get('dns_label'),
                availability_domain=subnet_data.get('availability_domain')
            )
            
            # 调用OCI API创建子网
            response = network_client.create_subnet(subnet_details)
            subnet_ocid = response.data.id
            
            # 创建本地子网记录
            subnet = Subnet(
                vcn_id=vcn_id,
                subnet_ocid=subnet_ocid,
                name=subnet_data['name'],
                compartment_id=subnet_data['compartment_id'],
                cidr_block=subnet_data['cidr_block'],
                dns_label=subnet_data.get('dns_label'),
                availability_domain=subnet_data.get('availability_domain'),
                state='PROVISIONING'
            )
            
            db.session.add(subnet)
            db.session.commit()
            return subnet
            
        except Exception as e:
            print(f"创建子网失败: {str(e)}")
            db.session.rollback()
            return None
    
    def create_security_list(self, vcn_id: int, security_list_data: Dict[str, Any]) -> Optional[SecurityList]:
        """创建安全列表"""
        try:
            vcn = self.get_vcn_by_id(vcn_id)
            if not vcn:
                raise Exception("VCN不存在")
            
            compute_client = self.tenant_service.get_oci_client(vcn.tenant_id)
            if not compute_client:
                raise Exception("无法创建OCI客户端")
            
            network_client = oci.core.VirtualNetworkClient(compute_client.base_client.config)
            
            # 创建安全列表详情
            security_list_details = oci.core.models.CreateSecurityListDetails(
                compartment_id=security_list_data['compartment_id'],
                vcn_id=vcn.vcn_ocid,
                display_name=security_list_data['name'],
                egress_security_rules=[],
                ingress_security_rules=[]
            )
            
            # 调用OCI API创建安全列表
            response = network_client.create_security_list(security_list_details)
            security_list_ocid = response.data.id
            
            # 创建本地安全列表记录
            security_list = SecurityList(
                vcn_id=vcn_id,
                security_list_ocid=security_list_ocid,
                name=security_list_data['name'],
                compartment_id=security_list_data['compartment_id'],
                state='PROVISIONING'
            )
            
            db.session.add(security_list)
            db.session.commit()
            return security_list
            
        except Exception as e:
            print(f"创建安全列表失败: {str(e)}")
            db.session.rollback()
            return None
    
    def add_security_rule(self, security_list_id: int, rule_data: Dict[str, Any]) -> Optional[SecurityRule]:
        """添加安全规则"""
        try:
            security_list = SecurityList.query.get(security_list_id)
            if not security_list:
                raise Exception("安全列表不存在")
            
            vcn = self.get_vcn_by_id(security_list.vcn_id)
            if not vcn:
                raise Exception("VCN不存在")
            
            compute_client = self.tenant_service.get_oci_client(vcn.tenant_id)
            if not compute_client:
                raise Exception("无法创建OCI客户端")
            
            network_client = oci.core.VirtualNetworkClient(compute_client.base_client.config)
            
            # 获取现有安全列表
            response = network_client.get_security_list(security_list.security_list_ocid)
            security_list_details = response.data
            
            # 创建新规则
            new_rule = {
                'description': rule_data.get('description'),
                'protocol': rule_data['protocol'],
                'source': rule_data.get('source'),
                'source_type': 'CIDR_BLOCK',
                'tcp_options': None,
                'udp_options': None
            }
            
            if rule_data['protocol'] in ['6', '17']:  # TCP or UDP
                port_options = {
                    'destination_port_range': {
                        'min': rule_data['destination_port_range_min'],
                        'max': rule_data['destination_port_range_max']
                    }
                }
                if rule_data['protocol'] == '6':
                    new_rule['tcp_options'] = port_options
                else:
                    new_rule['udp_options'] = port_options
            
            # 更新规则列表
            if rule_data['direction'] == 'INGRESS':
                security_list_details.ingress_security_rules.append(new_rule)
            else:
                security_list_details.egress_security_rules.append(new_rule)
            
            # 更新安全列表
            update_details = oci.core.models.UpdateSecurityListDetails(
                egress_security_rules=security_list_details.egress_security_rules,
                ingress_security_rules=security_list_details.ingress_security_rules
            )
            
            network_client.update_security_list(security_list.security_list_ocid, update_details)
            
            # 创建本地安全规则记录
            rule = SecurityRule(
                security_list_id=security_list_id,
                direction=rule_data['direction'],
                protocol=rule_data['protocol'],
                source=rule_data.get('source'),
                destination=rule_data.get('destination'),
                source_port_range_min=rule_data.get('source_port_range_min'),
                source_port_range_max=rule_data.get('source_port_range_max'),
                destination_port_range_min=rule_data.get('destination_port_range_min'),
                destination_port_range_max=rule_data.get('destination_port_range_max'),
                description=rule_data.get('description')
            )
            
            db.session.add(rule)
            db.session.commit()
            return rule
            
        except Exception as e:
            print(f"添加安全规则失败: {str(e)}")
            db.session.rollback()
            return None
    
    def delete_vcn(self, vcn_id: int) -> bool:
        """删除VCN"""
        try:
            vcn = self.get_vcn_by_id(vcn_id)
            if not vcn:
                return False
            
            compute_client = self.tenant_service.get_oci_client(vcn.tenant_id)
            if not compute_client:
                return False
            
            network_client = oci.core.VirtualNetworkClient(compute_client.base_client.config)
            
            # 删除所有相关资源
            # 1. 删除子网
            subnets = Subnet.query.filter_by(vcn_id=vcn_id).all()
            for subnet in subnets:
                network_client.delete_subnet(subnet.subnet_ocid)
                db.session.delete(subnet)
            
            # 2. 删除安全列表
            security_lists = SecurityList.query.filter_by(vcn_id=vcn_id).all()
            for security_list in security_lists:
                network_client.delete_security_list(security_list.security_list_ocid)
                db.session.delete(security_list)
            
            # 3. 删除VCN
            network_client.delete_vcn(vcn.vcn_ocid)
            db.session.delete(vcn)
            db.session.commit()
            return True
            
        except Exception as e:
            print(f"删除VCN失败: {str(e)}")
            db.session.rollback()
            return False
