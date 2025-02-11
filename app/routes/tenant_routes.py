from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.decorators import login_required
from app.services.tenant_service import TenantService

tenant_bp = Blueprint('tenant', __name__)
tenant_service = TenantService()

@tenant_bp.route('/list')
@login_required
def list_tenants():
    """租户列表页面"""
    tenants = tenant_service.get_all_tenants()
    if request.headers.get('Accept') == 'application/json':
        return jsonify(tenants)
    return render_template('tenant/list.html', tenants=tenants)

@tenant_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_tenant():
    """创建租户"""
    if request.method == 'POST':
        tenant_data = {
            'name': request.form['name'],
            'user_ocid': request.form['user_ocid'],
            'fingerprint': request.form['fingerprint'],
            'key_file': request.form['key_file'],
            'tenancy': request.form['tenancy'],
            'region': request.form['region'],
            'compartment_id': request.form.get('compartment_id')
        }
        
        if tenant_service.create_tenant(tenant_data):
            flash('租户创建成功', 'success')
            return redirect(url_for('tenant.list_tenants'))
        else:
            flash('租户创建失败', 'error')
    
    return render_template('tenant/create.html')

@tenant_bp.route('/edit/<tenant_id>', methods=['GET', 'POST'])
@login_required
def edit_tenant(tenant_id):
    """编辑租户"""
    tenant = tenant_service.get_tenant_by_id(tenant_id)
    if not tenant:
        flash('租户不存在', 'error')
        return redirect(url_for('tenant.list_tenants'))
    
    if request.method == 'POST':
        tenant_data = {
            'name': request.form['name'],
            'user_ocid': request.form['user_ocid'],
            'fingerprint': request.form['fingerprint'],
            'key_file': request.form['key_file'],
            'tenancy': request.form['tenancy'],
            'region': request.form['region'],
            'compartment_id': request.form.get('compartment_id')
        }
        
        if tenant_service.update_tenant(tenant_id, tenant_data):
            flash('租户更新成功', 'success')
            return redirect(url_for('tenant.list_tenants'))
        else:
            flash('租户更新失败', 'error')
    
    return render_template('tenant/edit.html', tenant=tenant)

@tenant_bp.route('/delete/<tenant_id>')
@login_required
def delete_tenant(tenant_id):
    """删除租户"""
    if tenant_service.delete_tenant(tenant_id):
        flash('租户删除成功', 'success')
    else:
        flash('租户删除失败', 'error')
    return redirect(url_for('tenant.list_tenants'))
