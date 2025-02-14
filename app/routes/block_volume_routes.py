from flask import Blueprint, request, jsonify
from app.decorators import login_required
from app.services.block_volume_service import BlockVolumeService
import logging

block_volume_bp = Blueprint('block_volume', __name__, url_prefix='/api/block-volume')
block_volume_service = BlockVolumeService()

@block_volume_bp.route('/attached-volumes/<instance_id>')
@login_required
def list_attached_volumes(instance_id):
    """获取实例上已附加的块存储卷列表"""
    try:
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "缺少tenant_id参数"}), 400
            
        volumes = block_volume_service.list_attached_volumes(tenant_id, instance_id)
        return jsonify(volumes)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "获取块存储卷列表失败"}), 500

@block_volume_bp.route('/detach/<attachment_id>', methods=['POST'])
@login_required
def detach_volume(attachment_id):
    """分离块存储卷"""
    try:
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "缺少tenant_id参数"}), 400
            
        result = block_volume_service.detach_volume(tenant_id, attachment_id)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "分离块存储卷失败"}), 500

@block_volume_bp.route('/attach', methods=['POST'])
@login_required
def attach_volume():
    """附加块存储卷到实例"""
    try:
        tenant_id = request.args.get('tenant_id')
        logging.info(f"收到附加块存储卷请求，tenant_id: {tenant_id}")
        
        if not tenant_id:
            return jsonify({"error": "缺少tenant_id参数"}), 400
            
        data = request.get_json()
        logging.info(f"请求数据: {data}")
        
        if not data:
            return jsonify({"error": "缺少请求数据"}), 400
            
        instance_id = data.get('instance_id')
        volume_id = data.get('volume_id')
        logging.info(f"解析参数 - instance_id: {instance_id}, volume_id: {volume_id}")
        
        if not instance_id or not volume_id:
            logging.error(f"缺少必要参数 - instance_id: {instance_id}, volume_id: {volume_id}")
            return jsonify({"error": "缺少必要参数"}), 400
            
        result = block_volume_service.attach_volume(tenant_id, instance_id, volume_id)
        logging.info(f"附加块存储卷成功: {result}")
        return jsonify(result)
    except ValueError as e:
        logging.error(f"附加块存储卷参数错误: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"附加块存储卷失败: {str(e)}")
        return jsonify({"error": "附加块存储卷失败"}), 500

@block_volume_bp.route('/update/<volume_id>', methods=['PUT'])
@login_required
def update_volume(volume_id):
    """更新块存储卷或引导卷的性能"""
    try:
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "缺少tenant_id参数"}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少请求数据"}), 400
            
        vpus_per_gb = data.get('vpus_per_gb')
        if vpus_per_gb is None:
            return jsonify({"error": "缺少必要参数 vpus_per_gb"}), 400
            
        logging.info(f"更新卷 {volume_id} 的性能为 {vpus_per_gb} VPUS/GB")
        result = block_volume_service.update_volume(tenant_id, volume_id, vpus_per_gb)
        return jsonify(result)
    except ValueError as e:
        logging.error(f"更新卷失败: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"更新卷失败: {str(e)}")
        return jsonify({"error": "更新卷失败"}), 500

@block_volume_bp.route('/available-volumes/<availability_domain>', methods=['GET'])
def list_available_volumes(availability_domain: str):
    """获取可用的块存储卷和已分离的引导卷列表"""
    try:
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({'error': '缺少tenant_id参数'}), 400
            
        volumes = block_volume_service.list_available_volumes(tenant_id, availability_domain)
        return jsonify(volumes)
        
    except Exception as e:
        logging.error(f"获取可用卷列表失败: {str(e)}")
        return jsonify({'error': str(e)}), 500
