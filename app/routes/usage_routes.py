from flask import Blueprint, jsonify, request, render_template
from app.services.usage_service import UsageService
from app.services.tenant_service import TenantService
from app.decorators import login_required
import logging

usage_bp = Blueprint('usage', __name__)
usage_service = UsageService()
tenant_service = TenantService()

@usage_bp.route('/list')
@login_required
def list_usage():
    """使用量查询页面"""
    try:
        # 获取所有租户列表供选择
        tenants = tenant_service.get_all_tenants()
        
        # 只在有查询参数时才获取数据
        is_query = 'tenant_id' in request.args
        tenant_id = request.args.get('tenant_id')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        usage_data = None
        error = None
        
        if is_query and tenant_id:
            try:
                usage_data = usage_service.get_usage(
                    tenant_id=tenant_id,
                    start_time=start_time,
                    end_time=end_time
                )
            except Exception as e:
                error = str(e)
                logging.error(f"获取使用量数据失败: {str(e)}")
        
        return render_template('usage/list.html', 
                             tenants=tenants,
                             usage_data=usage_data,
                             tenant_id=tenant_id,
                             start_time=start_time,
                             end_time=end_time,
                             error=error,
                             is_query=is_query)
    except Exception as e:
        logging.error(f"加载使用量查询页面失败: {str(e)}")
        return render_template('usage/list.html', error=str(e))

@usage_bp.route('/api/compute', methods=['GET'])
@login_required
def get_compute_usage():
    """获取计算资源使用量数据"""
    try:
        tenant_id = request.args.get('tenant_id')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        if not tenant_id:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数: tenant_id'
            }), 400
            
        usage_data = usage_service.get_usage(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time
        )
        
        return jsonify({
            'status': 'success',
            'data': usage_data
        }), 200
    except Exception as e:
        logging.error(f"获取计算资源使用量失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@usage_bp.route('/api/storage', methods=['GET'])
@login_required
def get_storage_usage():
    """获取存储资源使用量数据"""
    try:
        tenant_id = request.args.get('tenant_id')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        if not tenant_id:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数: tenant_id'
            }), 400
            
        usage_data = usage_service.get_usage(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time
        )
        
        return jsonify({
            'status': 'success',
            'data': usage_data
        }), 200
    except Exception as e:
        logging.error(f"获取存储资源使用量失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
