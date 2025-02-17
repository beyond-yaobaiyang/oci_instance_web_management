import logging
import oci
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.decorators import login_required
from app.services.network_service import NetworkService
from app.services.tenant_service import TenantService

network_bp = Blueprint('network', __name__, url_prefix='/network')
network_service = NetworkService()
tenant_service = TenantService()

@network_bp.route('/')
@login_required
def index():
    """网络管理首页重定向到路由表页面"""
    return redirect(url_for('network.route_tables'))

@network_bp.route('/security_groups')
@login_required
def security_groups():
    """安全组列表页面"""
    tenants = tenant_service.get_all_tenants()
    return render_template('network/security_groups.html', tenants=tenants)

@network_bp.route('/api/vcns/<tenant_id>')
@login_required
def get_vcns(tenant_id):
    """获取VCN列表API"""
    try:
        logging.info(f"获取VCN列表, tenant_id: {tenant_id}")
        vcns = network_service.list_vcns(tenant_id)
        logging.info(f"VCN列表: {vcns}")
        return jsonify(vcns)
    except Exception as e:
        logging.error(f"获取VCN列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@network_bp.route('/api/security_groups/<tenant_id>')
@login_required
def get_security_groups(tenant_id):
    """获取安全组列表API"""
    try:
        tenant = tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            return jsonify({'error': '租户不存在'}), 404
            
        logging.info(f"获取安全组列表, tenant_id: {tenant_id}, compartment_id: {tenant['compartment_id']}")
        security_groups = network_service.list_security_groups_by_compartment(tenant_id, tenant['compartment_id'])
        logging.info(f"安全组列表: {security_groups}")
        return jsonify(security_groups)
    except Exception as e:
        logging.error(f"获取安全组列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@network_bp.route('/api/security_group_rules/<tenant_id>/<security_group_id>')
@login_required
def get_security_group_rules(tenant_id, security_group_id):
    """获取安全组规则列表API"""
    try:
        logging.info(f"获取安全组规则, tenant_id: {tenant_id}, security_group_id: {security_group_id}")
        rules = network_service.list_security_group_rules(tenant_id, security_group_id)
        logging.info(f"安全组规则: {rules}")
        return jsonify(rules)
    except Exception as e:
        logging.error(f"获取安全组规则失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@network_bp.route('/security_list_rules')
@login_required
def security_list_rules():
    """安全组规则管理页面"""
    tenants = tenant_service.get_all_tenants()
    return render_template('network/security_list_rules.html', tenants=tenants)

@network_bp.route('/api/security_lists/<tenant_id>')
@login_required
def get_security_lists(tenant_id):
    """获取安全组列表API"""
    try:
        tenant = tenant_service.get_tenant_by_id(tenant_id)
        if not tenant:
            return jsonify({'error': '租户不存在'}), 404
            
        logging.info(f"获取安全组列表, tenant_id: {tenant_id}, compartment_id: {tenant['compartment_id']}")
        security_lists = network_service.list_security_lists_by_compartment(tenant_id, tenant['compartment_id'])
        logging.info(f"安全组列表: {security_lists}")
        return jsonify(security_lists)
    except Exception as e:
        logging.error(f"获取安全组列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@network_bp.route('/api/security_lists/<tenant_id>/<security_list_id>/rules')
@login_required
def get_security_list_rules(tenant_id, security_list_id):
    """获取安全组规则API"""
    try:
        rules = network_service.get_security_list_rules(tenant_id, security_list_id)
        return jsonify(rules)
    except Exception as e:
        logging.error(f"获取安全组规则失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@network_bp.route('/api/security_lists/<tenant_id>/<security_list_id>/rules', methods=['PUT'])
@login_required
def update_security_list_rules(tenant_id, security_list_id):
    """更新安全组规则API"""
    try:
        data = request.get_json()
        network_service.update_security_list_rules(
            tenant_id=tenant_id,
            security_list_id=security_list_id,
            ingress_rules=data['ingress_rules'],
            egress_rules=data['egress_rules']
        )
        return jsonify({'message': '更新成功'})
    except Exception as e:
        logging.error(f"更新安全组规则失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@network_bp.route('/route_tables')
@login_required
def route_tables():
    """路由表管理页面"""
    tenants = tenant_service.get_all_tenants()
    return render_template('network/route_tables.html', tenants=tenants)

@network_bp.route('/api/route_tables/<tenant_id>')
@login_required
def get_route_tables(tenant_id):
    """获取路由表列表API"""
    try:
        vcn_id = request.args.get('vcn_id')
        logging.info(f"获取路由表列表, tenant_id: {tenant_id}, vcn_id: {vcn_id}")
        route_tables = network_service.list_route_tables(tenant_id, vcn_id)
        logging.info(f"路由表列表: {route_tables}")
        return jsonify(route_tables)
    except Exception as e:
        logging.error(f"获取路由表列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@network_bp.route('/api/route_tables/<tenant_id>/<route_table_id>')
@login_required
def get_route_table(tenant_id, route_table_id):
    """获取路由表详情API"""
    try:
        logging.info(f"获取路由表详情, tenant_id: {tenant_id}, route_table_id: {route_table_id}")
        route_table = network_service.get_route_table(tenant_id, route_table_id)
        logging.info(f"路由表详情: {route_table}")
        return jsonify(route_table)
    except Exception as e:
        logging.error(f"获取路由表详情失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@network_bp.route('/api/route_tables/<tenant_id>/<route_table_id>/rules')
@login_required
def get_route_table_rules(tenant_id, route_table_id):
    """获取路由表规则API"""
    try:
        logging.info(f"获取路由表规则, tenant_id: {tenant_id}, route_table_id: {route_table_id}")
        route_table = network_service.get_route_table(tenant_id, route_table_id)
        logging.info(f"路由表规则: {route_table}")
        return jsonify(route_table)
    except Exception as e:
        logging.error(f"获取路由表规则失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@network_bp.route('/api/route_tables/<tenant_id>/<route_table_id>', methods=['PUT'])
@login_required
def update_route_table(tenant_id, route_table_id):
    """更新路由表规则API"""
    try:
        data = request.get_json()
        route_rules = data.get('route_rules', [])
        
        logging.info(f"更新路由表, tenant_id: {tenant_id}, route_table_id: {route_table_id}")
        logging.info(f"路由规则: {route_rules}")
        
        result = network_service.update_route_table(tenant_id, route_table_id, route_rules)
        return jsonify(result)
    except Exception as e:
        logging.error(f"更新路由表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@network_bp.route('/api/route_tables/<tenant_id>/<route_table_id>/rules', methods=['PUT'])
@login_required
def update_route_table_rules(tenant_id, route_table_id):
    """更新路由表规则API"""
    try:
        data = request.get_json()
        route_rules = data.get('route_rules', [])
        
        logging.info(f"更新路由表规则, tenant_id: {tenant_id}, route_table_id: {route_table_id}")
        logging.info(f"路由规则: {route_rules}")
        
        result = network_service.update_route_table(tenant_id, route_table_id, route_rules)
        return jsonify(result)
    except Exception as e:
        logging.error(f"更新路由表规则失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@network_bp.route('/api/network_entities/<tenant_id>/<vcn_id>')
@login_required
def get_network_entities(tenant_id, vcn_id):
    """获取网络实体列表API"""
    try:
        logging.info(f"获取网络实体列表, tenant_id: {tenant_id}, vcn_id: {vcn_id}")
        entities = network_service.list_network_entities(tenant_id, vcn_id)
        logging.info(f"网络实体列表: {entities}")
        return jsonify(entities)
    except Exception as e:
        logging.error(f"获取网络实体列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500