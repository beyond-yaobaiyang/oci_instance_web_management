from flask import Blueprint, jsonify, request
from app.services.instance_service import InstanceService
from app.decorators import login_required
import logging

compute_bp = Blueprint('compute', __name__)
instance_service = InstanceService()

@compute_bp.route('/list_instances')
@login_required
def list_instances():
    """获取实例列表"""
    try:
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({
                'success': False,
                'message': '请选择租户'
            })
        
        instances = instance_service.get_instances(tenant_id)
        return jsonify({
            'success': True,
            'instances': instances
        })
    except Exception as e:
        error_msg = str(e)
        logging.error(f"获取实例列表失败: {error_msg}", exc_info=True)
        return jsonify({
            'success': False,
            'message': error_msg
        })
