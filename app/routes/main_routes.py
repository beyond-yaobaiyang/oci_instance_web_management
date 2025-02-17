from flask import Blueprint, jsonify, request, render_template
from oci import management_agent
from app.decorators import login_required

main_bp = Blueprint('main', __name__, url_prefix='/')

@main_bp.route('/')
@login_required
def index():
    """主页"""
    return render_template('main/index.html')

@main_bp.route('/health')
def health_check():
    """健康检查端点"""
    return {'status': 'healthy'}, 200
