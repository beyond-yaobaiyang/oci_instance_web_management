"""订阅路由模块"""
from flask import Blueprint, render_template, jsonify, request
from app.services.subscription_service import SubscriptionService
from app.services.tenant_service import TenantService
from app.decorators import login_required

subscription_bp = Blueprint('subscription', __name__)
subscription_service = SubscriptionService()
tenant_service = TenantService()

@subscription_bp.route('/list')
@login_required
def subscription_list():
    """订阅列表页面"""
    tenants = tenant_service.get_all_tenants()
    return render_template('subscription/list.html', tenants=tenants)

@subscription_bp.route('/api/services/<tenant_name>')
@login_required
def get_services(tenant_name):
    """获取订阅服务列表API"""
    try:
        services = subscription_service.get_subscribed_services(tenant_name)
        return jsonify({
            'status': 'success',
            'data': services
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@subscription_bp.route('/api/summary/<tenant_name>')
@login_required
def get_summary(tenant_name):
    """获取订阅汇总信息API"""
    try:
        summary = subscription_service.get_subscription_summary(tenant_name)
        return jsonify({
            'status': 'success',
            'data': summary
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
