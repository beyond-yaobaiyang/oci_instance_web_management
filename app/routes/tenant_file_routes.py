from flask import Blueprint, request, jsonify
from app.decorators import login_required
from app.services.tenant_file_service import TenantFileService

tenant_file_bp = Blueprint('tenant_file', __name__, url_prefix='/tenant/file')
tenant_file_service = TenantFileService()

@tenant_file_bp.route('/upload', methods=['POST'])
@login_required
def upload_key_file():
    """上传私钥文件"""
    try:
        if 'key_file' not in request.files:
            return jsonify({'error': '未找到文件'}), 400
            
        file = request.files['key_file']
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400
            
        if not file.filename.endswith('.pem'):
            return jsonify({'error': '只支持.pem格式的文件'}), 400

        file_path = tenant_file_service.save_key_file(file)
        return jsonify({'file_path': file_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tenant_file_bp.route('/delete', methods=['POST'])
@login_required
def delete_key_file():
    """删除私钥文件"""
    try:
        file_path = request.form.get('file_path')
        if not file_path:
            return jsonify({'error': '未提供文件路径'}), 400

        if tenant_file_service.delete_key_file(file_path):
            return jsonify({'message': '删除成功'})
        else:
            return jsonify({'error': '删除失败'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
