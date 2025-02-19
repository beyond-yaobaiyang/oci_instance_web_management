from flask import Blueprint, jsonify, request, render_template
from ..services.quota_service import QuotaService
from ..services.tenant_service import TenantService
import logging
import oci

quota_bp = Blueprint('quota', __name__, url_prefix='/quota')
quota_service = QuotaService()
tenant_service = TenantService()

@quota_bp.route('/')
def quota_list():
    """配额查询页面"""
    tenants = tenant_service.get_all_tenants()
    return render_template('quota/list.html', tenants=tenants)

@quota_bp.route('/api/availability-domains/<tenant_id>')
def get_availability_domains(tenant_id):
    """获取可用性域列表"""
    try:
        domains = quota_service.get_availability_domains(tenant_id)
        return jsonify(domains)
    except Exception as e:
        logging.error(f"获取可用性域列表失败: {str(e)}")
        return jsonify({"error": str(e)}), 400

@quota_bp.route('/api/services/<tenant_id>')
def get_services(tenant_id):
    """获取服务列表"""
    try:
        services = quota_service.get_services(tenant_id)
        return jsonify(services)
    except Exception as e:
        logging.error(f"获取服务列表失败: {str(e)}")
        return jsonify({"error": str(e)}), 400

@quota_bp.route('/api/quotas/<tenant_id>')
def get_quotas(tenant_id):
    """获取配额信息"""
    try:
        service_name = request.args.get('service_name')
        availability_domain = request.args.get('availability_domain')
        
        if not service_name:
            return jsonify({"error": "请指定服务名称"}), 400
            
        quotas = quota_service.get_service_quotas(tenant_id, service_name, availability_domain)
        return jsonify(quotas)
    except Exception as e:
        logging.error(f"获取配额信息失败: {str(e)}")
        return jsonify({"error": str(e)}), 400
