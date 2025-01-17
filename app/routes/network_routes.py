from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.services.network_service import NetworkService
from app.services.tenant_service import TenantService
from app.decorators import login_required

network_bp = Blueprint('network', __name__)
network_service = NetworkService()
tenant_service = TenantService()

@network_bp.route('/vcns')
@login_required
def list_vcns():
    """列出VCN"""
    tenant_id = request.args.get('tenant_id', type=int)
    vcns = network_service.get_vcns(tenant_id)
    tenants = tenant_service.get_all_tenants()
    return render_template('network/vcn_list.html', vcns=vcns, tenants=tenants)

@network_bp.route('/vcns/create', methods=['GET', 'POST'])
@login_required
def create_vcn():
    """创建VCN"""
    if request.method == 'POST':
        vcn_data = {
            'tenant_id': request.form.get('tenant_id', type=int),
            'name': request.form.get('name'),
            'compartment_id': request.form.get('compartment_id'),
            'cidr_block': request.form.get('cidr_block'),
            'dns_label': request.form.get('dns_label')
        }
        
        vcn = network_service.create_vcn(vcn_data['tenant_id'], vcn_data)
        if vcn:
            flash('VCN创建成功', 'success')
            return redirect(url_for('network.list_vcns'))
        else:
            flash('VCN创建失败', 'error')
    
    tenants = tenant_service.get_all_tenants()
    return render_template('network/vcn_create.html', tenants=tenants)

@network_bp.route('/vcns/<int:vcn_id>/delete', methods=['POST'])
@login_required
def delete_vcn(vcn_id):
    """删除VCN"""
    if network_service.delete_vcn(vcn_id):
        flash('VCN删除成功', 'success')
    else:
        flash('VCN删除失败', 'error')
    return redirect(url_for('network.list_vcns'))

@network_bp.route('/vcns/<int:vcn_id>/subnets')
@login_required
def list_subnets(vcn_id):
    """列出子网"""
    vcn = network_service.get_vcn_by_id(vcn_id)
    if not vcn:
        flash('VCN不存在', 'error')
        return redirect(url_for('network.list_vcns'))
    
    return render_template('network/subnet_list.html', vcn=vcn)

@network_bp.route('/vcns/<int:vcn_id>/subnets/create', methods=['GET', 'POST'])
@login_required
def create_subnet(vcn_id):
    """创建子网"""
    vcn = network_service.get_vcn_by_id(vcn_id)
    if not vcn:
        flash('VCN不存在', 'error')
        return redirect(url_for('network.list_vcns'))
    
    if request.method == 'POST':
        subnet_data = {
            'name': request.form.get('name'),
            'compartment_id': vcn.compartment_id,
            'cidr_block': request.form.get('cidr_block'),
            'dns_label': request.form.get('dns_label'),
            'availability_domain': request.form.get('availability_domain')
        }
        
        subnet = network_service.create_subnet(vcn_id, subnet_data)
        if subnet:
            flash('子网创建成功', 'success')
            return redirect(url_for('network.list_subnets', vcn_id=vcn_id))
        else:
            flash('子网创建失败', 'error')
    
    return render_template('network/subnet_create.html', vcn=vcn)

@network_bp.route('/vcns/<int:vcn_id>/security-lists')
@login_required
def list_security_lists(vcn_id):
    """列出安全列表"""
    vcn = network_service.get_vcn_by_id(vcn_id)
    if not vcn:
        flash('VCN不存在', 'error')
        return redirect(url_for('network.list_vcns'))
    
    return render_template('network/security_list_list.html', vcn=vcn)

@network_bp.route('/vcns/<int:vcn_id>/security-lists/create', methods=['GET', 'POST'])
@login_required
def create_security_list(vcn_id):
    """创建安全列表"""
    vcn = network_service.get_vcn_by_id(vcn_id)
    if not vcn:
        flash('VCN不存在', 'error')
        return redirect(url_for('network.list_vcns'))
    
    if request.method == 'POST':
        security_list_data = {
            'name': request.form.get('name'),
            'compartment_id': vcn.compartment_id
        }
        
        security_list = network_service.create_security_list(vcn_id, security_list_data)
        if security_list:
            flash('安全列表创建成功', 'success')
            return redirect(url_for('network.list_security_lists', vcn_id=vcn_id))
        else:
            flash('安全列表创建失败', 'error')
    
    return render_template('network/security_list_create.html', vcn=vcn)

@network_bp.route('/security-lists/<int:security_list_id>/rules/create', methods=['GET', 'POST'])
@login_required
def create_security_rule(security_list_id):
    """创建安全规则"""
    if request.method == 'POST':
        rule_data = {
            'direction': request.form.get('direction'),
            'protocol': request.form.get('protocol'),
            'source': request.form.get('source'),
            'destination': request.form.get('destination'),
            'source_port_range_min': request.form.get('source_port_range_min', type=int),
            'source_port_range_max': request.form.get('source_port_range_max', type=int),
            'destination_port_range_min': request.form.get('destination_port_range_min', type=int),
            'destination_port_range_max': request.form.get('destination_port_range_max', type=int),
            'description': request.form.get('description')
        }
        
        rule = network_service.add_security_rule(security_list_id, rule_data)
        if rule:
            flash('安全规则创建成功', 'success')
        else:
            flash('安全规则创建失败', 'error')
        return redirect(url_for('network.list_security_lists', vcn_id=rule.security_list.vcn_id))
    
    return render_template('network/security_rule_create.html', security_list_id=security_list_id)
