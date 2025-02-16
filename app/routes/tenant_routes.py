from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.decorators import login_required
from app.services.tenant_service import TenantService
from app.services.tenant_file_service import TenantFileService
import logging

tenant_bp = Blueprint('tenant', __name__, url_prefix='/tenant')
tenant_service = TenantService()
tenant_file_service = TenantFileService()

@tenant_bp.route('/list')
@login_required
def list_tenants():
    """租户列表页面"""
    tenants = tenant_service.get_all_tenants()
    return render_template('tenant/list.html', tenants=tenants)

@tenant_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_tenant():
    """创建租户"""
    if request.method == 'POST':
        try:
            # 先处理私钥文件
            key_file = request.files.get('key_file')
            if not key_file:
                flash('请上传私钥文件', 'error')
                return render_template('tenant/create.html')
            
            key_file_path = tenant_file_service.save_key_file(key_file)
            if not key_file_path:
                flash('保存私钥文件失败', 'error')
                return render_template('tenant/create.html')
            
            # 获取表单数据
            tenant_data = {
                'name': request.form.get('name'),
                'user_ocid': request.form.get('user_ocid'),
                'fingerprint': request.form.get('fingerprint'),
                'key_file': key_file_path,  # 使用保存后的文件路径
                'tenancy': request.form.get('tenancy'),
                'region': request.form.get('region'),
                'description': request.form.get('description', '')
            }
            
            # 创建租户
            if tenant_service.create_tenant(tenant_data):
                flash('租户创建成功', 'success')
                return redirect(url_for('tenant.list_tenants'))
            else:
                flash('租户创建失败', 'error')
                return render_template('tenant/create.html')
                
        except Exception as e:
            logging.error(f"创建租户失败: {str(e)}")
            flash('创建租户失败: ' + str(e), 'error')
            return render_template('tenant/create.html')
            
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
        try:
            # 处理私钥文件
            key_file = request.files.get('key_file')
            if key_file:
                key_file_path = tenant_file_service.save_key_file(key_file)
                if key_file_path:
                    tenant_data = {
                        'name': request.form.get('name'),
                        'user_ocid': request.form.get('user_ocid'),
                        'fingerprint': request.form.get('fingerprint'),
                        'key_file': key_file_path,
                        'tenancy': request.form.get('tenancy'),
                        'region': request.form.get('region'),
                        'description': request.form.get('description', '')
                    }
                else:
                    flash('保存私钥文件失败', 'error')
                    return render_template('tenant/edit.html', tenant=tenant)
            else:
                # 如果没有上传新文件，保留原来的文件路径
                tenant_data = {
                    'name': request.form.get('name'),
                    'user_ocid': request.form.get('user_ocid'),
                    'fingerprint': request.form.get('fingerprint'),
                    'key_file': tenant.get('key_file'),
                    'tenancy': request.form.get('tenancy'),
                    'region': request.form.get('region'),
                    'description': request.form.get('description', '')
                }
            
            # 更新租户
            if tenant_service.update_tenant(tenant_id, tenant_data):
                flash('租户更新成功', 'success')
                return redirect(url_for('tenant.list_tenants'))
            else:
                flash('租户更新失败', 'error')
        except Exception as e:
            flash(f'更新租户时发生错误: {str(e)}', 'error')
            logging.error(f"更新租户失败: {str(e)}", exc_info=True)
    
    return render_template('tenant/edit.html', tenant=tenant)

@tenant_bp.route('/delete/<tenant_id>')
@login_required
def delete_tenant(tenant_id):
    """删除租户"""
    try:
        if tenant_service.delete_tenant(tenant_id):
            flash('租户删除成功', 'success')
        else:
            flash('租户删除失败', 'error')
    except Exception as e:
        flash(f'删除租户时发生错误: {str(e)}', 'error')
        logging.error(f"删除租户失败: {str(e)}", exc_info=True)
    
    return redirect(url_for('tenant.list_tenants'))

@tenant_bp.route('/get/<tenant_id>')
def get_tenant(tenant_id):
    """获取租户详情"""
    try:
        tenant = tenant_service.get_tenant_by_id(tenant_id)
        if tenant:
            return jsonify(tenant)
        return jsonify({'error': '租户不存在'}), 404
    except Exception as e:
        logging.error(f"获取租户详情失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@tenant_bp.route('/<tenant_id>')
@login_required
def get_tenant_info(tenant_id):
    """获取租户信息"""
    tenant = tenant_service.get_tenant_by_id(tenant_id)
    if not tenant:
        return jsonify({'error': '租户不存在'}), 404
    return jsonify(tenant)

@tenant_bp.route('/copy/<tenant_id>', methods=['POST'])
@login_required
def copy_tenant(tenant_id):
    """复制租户配置"""
    try:
        # 获取源租户信息
        source_tenant = tenant_service.get_tenant_by_id(tenant_id)
        if not source_tenant:
            flash('源租户不存在', 'error')
            return redirect(url_for('tenant.list_tenants'))
        
        # 创建新租户数据
        new_tenant = source_tenant.copy()  # 复制源租户的所有数据
        new_tenant['name'] = request.form.get('name')  # 更新名称
        new_tenant['region'] = request.form.get('region')  # 更新区域
        
        # 创建新租户
        if tenant_service.create_tenant(new_tenant):
            flash('租户复制成功', 'success')
        else:
            flash('租户复制失败', 'error')
            
    except Exception as e:
        flash(f'复制租户时发生错误: {str(e)}', 'error')
        logging.error(f"复制租户失败: {str(e)}", exc_info=True)
        
    return redirect(url_for('tenant.list_tenants'))
