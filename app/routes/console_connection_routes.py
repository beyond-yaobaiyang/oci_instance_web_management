import logging
from flask import Blueprint, jsonify, request
from app.decorators import login_required
from app.services.console_connection_service import ConsoleConnectionService

console_connection_bp = Blueprint('console_connection', __name__, url_prefix='/console-connection')
console_connection_service = ConsoleConnectionService()

@console_connection_bp.route('/create', methods=['POST'])
@login_required
def create_console_connection():
    """创建实例控制台连接"""
    try:
        data = request.get_json()
        tenant_id = data.get('tenant_id')
        instance_id = data.get('instance_id')
        public_key = data.get('public_key')

        if not all([tenant_id, instance_id, public_key]):
            return jsonify({'error': '缺少必要参数'}), 400

        result = console_connection_service.create_connection(tenant_id, instance_id, public_key)
        return jsonify(result)
    except Exception as e:
        logging.error(f"创建控制台连接失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@console_connection_bp.route('/delete', methods=['POST'])
@login_required
def delete_console_connection():
    """删除实例控制台连接"""
    try:
        data = request.get_json()
        tenant_id = data.get('tenant_id')
        instance_id = data.get('instance_id')

        if not all([tenant_id, instance_id]):
            return jsonify({'error': '缺少必要参数'}), 400

        success = console_connection_service.delete_connection(tenant_id, instance_id)
        return jsonify({'success': success})
    except Exception as e:
        logging.error(f"删除控制台连接失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@console_connection_bp.route('/get/<tenant_id>/<instance_id>')
@login_required
def get_console_connection(tenant_id, instance_id):
    """获取实例控制台连接信息"""
    try:
        connection = console_connection_service.get_connection(tenant_id, instance_id)
        if connection is None:
            return jsonify({
                'success': True,
                'message': '未找到控制台连接',
                'data': None
            })
        return jsonify({
            'success': True,
            'data': connection
        })
    except Exception as e:
        logging.error(f"获取控制台连接信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
