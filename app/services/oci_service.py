import oci
from app.utils.config_loader import load_config

class OCIService:
    def __init__(self):
        self.config = load_config()
        
    def get_tenants(self):
        """获取所有租户配置"""
        try:
            tenants = []
            # 从配置文件中获取租户信息
            for tenant in self.config['tenants']:
                tenants.append({
                    'id': tenant['tenant_id'],
                    'name': tenant['name'],
                    'region': tenant['region']
                })
            return tenants
        except Exception as e:
            print(f"Error getting tenants: {str(e)}")
            return []

    def get_vcns(self, tenant_id):
        """获取指定租户的所有VCN"""
        try:
            config = self._get_tenant_config(tenant_id)
            network_client = oci.core.VirtualNetworkClient(config)
            vcns = network_client.list_vcns(config["compartment_id"]).data
            return [{'id': vcn.id, 'display_name': vcn.display_name} for vcn in vcns]
        except Exception as e:
            print(f"Error getting VCNs: {str(e)}")
            return []

    def get_security_groups(self, tenant_id, vcn_id):
        """获取指定VCN下的所有安全组"""
        try:
            config = self._get_tenant_config(tenant_id)
            network_client = oci.core.VirtualNetworkClient(config)
            security_groups = network_client.list_network_security_groups(
                compartment_id=config["compartment_id"],
                vcn_id=vcn_id
            ).data
            return [{
                'id': sg.id,
                'display_name': sg.display_name,
                'lifecycle_state': sg.lifecycle_state
            } for sg in security_groups]
        except Exception as e:
            print(f"Error getting security groups: {str(e)}")
            return []

    def get_security_group_rules(self, tenant_id, security_group_id):
        """获取安全组的规则"""
        try:
            config = self._get_tenant_config(tenant_id)
            network_client = oci.core.VirtualNetworkClient(config)
            rules = network_client.list_network_security_group_security_rules(
                network_security_group_id=security_group_id
            ).data
            return [{
                'id': rule.id,
                'direction': rule.direction,
                'protocol': rule.protocol,
                'source': rule.source,
                'source_type': rule.source_type,
                'destination': rule.destination,
                'destination_type': rule.destination_type,
                'is_stateless': rule.is_stateless,
                'description': rule.description
            } for rule in rules]
        except Exception as e:
            print(f"Error getting security group rules: {str(e)}")
            return []

    def _get_tenant_config(self, tenant_id):
        """获取指定租户的配置"""
        for tenant in self.config['tenants']:
            if tenant['tenant_id'] == tenant_id:
                return {
                    "user": tenant["user"],
                    "fingerprint": tenant["fingerprint"],
                    "key_file": tenant["key_file"],
                    "tenancy": tenant["tenancy"],
                    "region": tenant["region"],
                    "compartment_id": tenant["compartment_id"]
                }
        raise Exception(f"Tenant {tenant_id} not found")
