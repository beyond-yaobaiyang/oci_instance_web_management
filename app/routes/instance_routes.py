import logging
import oci
import time
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from app.decorators import login_required
from app.services.instance_service import InstanceService
from app.services.tenant_service import TenantService

instance_bp = Blueprint('instance', __name__, url_prefix='/instance')
instance_service = InstanceService()
tenant_service = TenantService()

@instance_bp.route('/list')
@login_required
def instance_list():
    """实例列表页面"""
    tenants = tenant_service.get_all_tenants()
    return render_template('instance/list.html', tenants=tenants)

@instance_bp.route('/api/instances/<tenant_id>')
@login_required
def get_instances_api(tenant_id):
    """获取实例列表API"""
    try:
        instances = instance_service.list_instances(tenant_id)
        return jsonify(instances)
    except Exception as e:
        logging.error(f"获取实例列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@instance_bp.route('/api/instance/action', methods=['POST'])
@login_required
def instance_action():
    """实例操作API"""
    try:
        data = request.get_json()
        tenant_id = data.get('tenant_id')
        instance_id = data.get('instance_id')
        action = data.get('action')

        if not all([tenant_id, instance_id, action]):
            return jsonify({'error': '缺少必要参数'}), 400

        # 验证操作类型
        valid_actions = ['start', 'stop', 'reset', 'terminate']
        if action not in valid_actions:
            return jsonify({'error': '无效的操作类型'}), 400

        # 执行操作
        success = False
        if action == 'start':
            success = instance_service.start_instance(tenant_id, instance_id)
        elif action == 'stop':
            success = instance_service.stop_instance(tenant_id, instance_id)
        elif action == 'reset':
            success = instance_service.restart_instance(tenant_id, instance_id)
        elif action == 'terminate':
            success = instance_service.delete_instance(tenant_id, instance_id)

        if success:
            # 获取更新后的实例状态
            instance = instance_service.get_instance(tenant_id, instance_id)
            return jsonify({
                'success': True,
                'message': f'实例{action}操作已提交',
                'instance': instance
            })
        else:
            return jsonify({
                'success': False,
                'error': f'实例{action}操作失败'
            }), 500

    except Exception as e:
        logging.error(f"实例操作失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@instance_bp.route('/api/instance/public-ip', methods=['POST'])
@login_required
def change_public_ip():
    """更换实例公网IP"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
            
        tenant_id = data.get('tenant_id')
        instance_id = data.get('instance_id')

        if not all([tenant_id, instance_id]):
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400

        # 先获取当前实例信息，记录原IP
        try:
            original_instance = instance_service.get_instance(tenant_id, instance_id)
            if not original_instance:
                return jsonify({'success': False, 'error': '找不到实例'}), 404
            
            original_ip = original_instance.get('public_ip')
            
            # 尝试更换IP
            instance_service.change_public_ip(tenant_id, instance_id)
            
            # 等待20秒
            time.sleep(20)
            
            # 获取新的实例信息
            new_instance = instance_service.get_instance(tenant_id, instance_id)
            if not new_instance:
                return jsonify({'success': False, 'error': '无法获取更新后的实例信息'}), 500
                
            new_ip = new_instance.get('public_ip')
            
            # 比较IP是否发生变化
            if new_ip != original_ip:
                return jsonify({
                    'success': True,
                    'message': '公网IP更换成功',
                    'instance': new_instance,
                    'old_ip': original_ip,
                    'new_ip': new_ip
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'IP未发生变化，可能更换失败'
                }), 500
                
        except Exception as e:
            logging.error(f"更换公网IP时发生错误: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    except Exception as e:
        logging.error(f"处理更换公网IP请求时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': '处理请求时发生错误'
        }), 500

@instance_bp.route('/api/instance/<tenant_id>/<instance_id>')
@login_required
def get_instance_api(tenant_id, instance_id):
    """获取实例详情API"""
    try:
        instance = instance_service.get_instance(tenant_id, instance_id)
        if instance:
            return jsonify(instance)
        else:
            return jsonify({'error': '找不到实例'}), 404
    except Exception as e:
        logging.error(f"获取实例详情失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@instance_bp.route('/api/instance/<tenant_id>/<instance_id>/vnics')
@login_required
def get_instance_vnics(tenant_id, instance_id):
    """获取实例的VNIC列表"""
    try:
        vnics = instance_service.list_vnics(tenant_id, instance_id)
        return jsonify(vnics)
    except Exception as e:
        logging.error(f"获取实例VNIC列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@instance_bp.route('/api/instance/<tenant_id>/<instance_id>/vnic', methods=['POST'])
@login_required
def attach_vnic(tenant_id, instance_id):
    """附加VNIC到实例"""
    try:
        data = request.get_json()
        subnet_id = data.get('subnet_id')
        display_name = data.get('display_name')

        if not subnet_id:
            return jsonify({'error': '缺少子网ID'}), 400

        result = instance_service.attach_vnic(tenant_id, instance_id, subnet_id, display_name)
        return jsonify(result)
    except Exception as e:
        logging.error(f"附加VNIC失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@instance_bp.route('/api/instance/vnic/<tenant_id>/<attachment_id>', methods=['DELETE'])
@login_required
def detach_vnic(tenant_id, attachment_id):
    """分离VNIC"""
    try:
        success = instance_service.detach_vnic(tenant_id, attachment_id)
        return jsonify({'success': success})
    except Exception as e:
        logging.error(f"分离VNIC失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@instance_bp.route('/detail')
@login_required
def instance_detail():
    """实例详情页面"""
    tenant_id = request.args.get('tenant_id')
    instance_id = request.args.get('instance_id')
    
    if not tenant_id or not instance_id:
        flash('缺少必要的参数', 'error')
        return redirect(url_for('instance.instance_list'))
    
    try:
        instance = instance_service.get_instance(tenant_id, instance_id)
        if not instance:
            flash('找不到实例', 'error')
            return redirect(url_for('instance.instance_list'))
            
        return render_template('instance/detail.html',
                             tenant_id=tenant_id,
                             instance_id=instance_id,
                             instance_state=instance.get('lifecycle_state', ''))
    except Exception as e:
        logging.error(f"获取实例详情失败: {str(e)}")
        flash('获取实例详情失败', 'error')
        return redirect(url_for('instance.instance_list'))

@instance_bp.route('/api/instance/<tenant_id>/<instance_id>')
@login_required
def get_instance_detail(tenant_id, instance_id):
    """获取实例详情API"""
    try:
        instance = instance_service.get_instance(tenant_id, instance_id)
        if instance:
            return jsonify(instance)
        else:
            return jsonify({'error': '实例不存在'}), 404
    except Exception as e:
        logging.error(f"获取实例详情失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@instance_bp.route('/create')
@login_required
def create_instance():
    """创建实例页面"""
    tenants = tenant_service.get_all_tenants()
    return render_template('instance/create.html', tenants=tenants)

@instance_bp.route('/api/resources/<tenant_id>')
@login_required
def get_resources(tenant_id):
    """获取可用域、镜像和子网等资源"""
    try:
        resources = instance_service.get_resources(tenant_id)
        return jsonify(resources)
    except Exception as e:
        logging.error(f"获取资源列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@instance_bp.route('/api/instance/create', methods=['POST'])
@login_required
def create_instance_api():
    """创建实例API"""
    try:
        data = request.get_json()
        logging.debug(f"接收到的创建实例请求数据: {data}")
        
        required_fields = ['tenant_id', 'display_name', 'availability_domain', 'image_id', 
                         'shape', 'subnet_id', 'boot_volume_size_in_gbs', 'login_method']
        
        # 验证必需字段
        for field in required_fields:
            if field not in data:
                raise ValueError(f"缺少必需字段: {field}")
        
        # 验证登录方式相关字段
        if data['login_method'] == 'ssh' and 'ssh_key' not in data:
            raise ValueError("选择SSH登录方式时必须提供SSH密钥")
        
        # 验证弹性配置相关字段
        if data['shape'].endswith('.Flex'):
            if 'ocpus' not in data or 'memory_in_gbs' not in data:
                raise ValueError("选择弹性配置时必须提供OCPU和内存大小")
        
        result = instance_service.create_instance(data)
        return jsonify(result)
    except ValueError as e:
        logging.error(f"创建实例参数验证失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logging.error(f"创建实例失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@instance_bp.route('/api/instance/<tenant_id>/<instance_id>/shapes')
@login_required
def get_shapes(tenant_id, instance_id):
    """获取实例可用的形状列表"""
    try:
        instance_service = InstanceService()
        result = instance_service.list_available_shapes(
            tenant_id=tenant_id,
            instance_id=instance_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"获取可用实例形状失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@instance_bp.route('/api/instance/<tenant_id>/<instance_id>/shape', methods=['PUT'])
@login_required
def update_shape(tenant_id, instance_id):
    """更新实例形状"""
    try:
        data = request.get_json()
        shape = data.get('shape')
        shape_config = data.get('shape_config')

        if not shape:
            return jsonify({
                'status': 'error',
                'message': '缺少必要的参数'
            }), 400

        instance_service = InstanceService()
        result = instance_service.update_instance_shape(
            tenant_id=tenant_id,
            instance_id=instance_id,
            shape=shape,
            shape_config=shape_config
        )
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"更新实例形状失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@instance_bp.route('/api/instance/<tenant_id>/<instance_id>/change-public-ip', methods=['POST'])
@login_required
def change_instance_public_ip(tenant_id, instance_id):
    """更换实例公网IP"""
    try:
        # 更换公网IP
        result = instance_service.change_public_ip(tenant_id, instance_id)
        if result:
            return jsonify({
                'success': True,
                'message': '公网IP更换成功',
                'instance': result
            })
        else:
            return jsonify({
                'success': False,
                'error': '公网IP更换失败'
            }), 500
    except Exception as e:
        logging.error(f"更换公网IP时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@instance_bp.route('/api/instance/<tenant_id>/<instance_id>/ipv6', methods=['POST'])
@login_required
def add_ipv6_address(tenant_id, instance_id):
    """添加IPv6地址"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
        
        vnic_id = data.get('vnic_id')
        is_auto = data.get('is_auto', True)
        ipv6_address = data.get('ipv6_address') if not is_auto else None
        
        if not vnic_id:
            return jsonify({'error': '缺少VNIC ID'}), 400
            
        if not is_auto and not ipv6_address:
            return jsonify({'error': '手动模式下需要提供IPv6地址'}), 400
        
        success = instance_service.add_ipv6_address(tenant_id, instance_id, vnic_id, is_auto, ipv6_address)
        if success:
            return jsonify({'success': True, 'message': 'IPv6地址添加成功'})
        else:
            return jsonify({'error': 'IPv6地址添加失败'}), 500
            
    except Exception as e:
        logging.error(f"添加IPv6地址失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@instance_bp.route('/api/instance/<tenant_id>/<instance_id>/ipv6', methods=['DELETE'])
@login_required
def delete_ipv6_address(tenant_id, instance_id):
    """删除IPv6地址"""
    try:
        data = request.get_json()
        if not data or 'ipv6_address' not in data:
            return jsonify({'error': '无效的请求数据'}), 400
        
        ipv6_address = data['ipv6_address']
        success = instance_service.delete_ipv6_address(tenant_id, instance_id, ipv6_address)
        
        if success:
            return jsonify({'success': True, 'message': 'IPv6地址删除成功'})
        else:
            return jsonify({'error': 'IPv6地址删除失败'}), 500
            
    except Exception as e:
        logging.error(f"删除IPv6地址失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
