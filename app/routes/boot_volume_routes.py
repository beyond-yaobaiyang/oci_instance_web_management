from flask import Blueprint, request, jsonify
from app.services.boot_volume_service import BootVolumeService
from app.decorators import login_required
import logging

boot_volume_bp = Blueprint('boot_volume', __name__, url_prefix='/api/boot-volume')
boot_volume_service = BootVolumeService()

@boot_volume_bp.route('/attached-volumes/<instance_id>', methods=['GET'])
@login_required
def list_attached_volumes(instance_id):
    """获取实例上已附加的引导卷列表"""
    try:
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "缺少tenant_id参数"}), 400
            
        volumes = boot_volume_service.list_attached_volumes(tenant_id, instance_id)
        return jsonify(volumes)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "获取引导卷列表失败"}), 500

@boot_volume_bp.route('/detach/<attachment_id>', methods=['POST'])
@login_required
def detach_volume(attachment_id):
    """分离引导卷（仅当实例关机时可操作）"""
    try:
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "缺少tenant_id参数"}), 400
            
        result = boot_volume_service.detach_volume(tenant_id, attachment_id)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "分离引导卷失败"}), 500

@boot_volume_bp.route('/attach', methods=['POST'])
@login_required
def attach_volume():
    """附加引导卷到实例"""
    try:
        data = request.get_json()
        if not data:
            raise ValueError("缺少请求数据")
            
        tenant_id = data.get('tenant_id')
        instance_id = data.get('instance_id')
        volume_id = data.get('volume_id')
        
        if not all([tenant_id, instance_id, volume_id]):
            raise ValueError("缺少必要参数")
            
        logging.info(f"附加引导卷请求: {data}")
        result = boot_volume_service.attach_volume(tenant_id, instance_id, volume_id)
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"附加引导卷失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@boot_volume_bp.route('/update/<volume_id>', methods=['PUT'])
@login_required
def update_volume(volume_id):
    """更新引导卷配置（大小只能增加不能减少）"""
    try:
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "缺少tenant_id参数"}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少请求数据"}), 400
            
        size_in_gbs = data.get('size_in_gbs')
        vpus_per_gb = data.get('vpus_per_gb')
        if size_in_gbs is None or vpus_per_gb is None:
            return jsonify({"error": "缺少必要参数"}), 400
            
        result = boot_volume_service.update_volume(tenant_id, volume_id, size_in_gbs, vpus_per_gb)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "更新引导卷失败"}), 500

@boot_volume_bp.route('/available-volumes/<availability_domain>')
@login_required
def list_available_volumes(availability_domain):
    """获取可用的引导卷列表"""
    try:
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "缺少tenant_id参数"}), 400
            
        volumes = boot_volume_service.list_available_volumes(tenant_id, availability_domain)
        return jsonify(volumes)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "获取可用引导卷列表失败"}), 500

@boot_volume_bp.route('/attachment/<attachment_id>/status', methods=['GET'])
def get_attachment_status(attachment_id):
    """获取引导卷附件状态"""
    try:
        tenant_id = request.args.get('tenant_id')
        if not tenant_id:
            raise ValueError("缺少tenant_id参数")
            
        result = boot_volume_service.get_attachment_status(tenant_id, attachment_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400
