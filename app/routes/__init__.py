"""路由注册模块"""
from typing import List, Tuple
from flask import Flask, Blueprint
from .auth_routes import auth_bp
from .tenant_routes import tenant_bp
from .compute_routes import compute_bp
from .instance_routes import instance_bp
from .main_routes import main_bp
from .subscription_routes import subscription_bp
from .quota_routes import quota_bp
from .block_volume_routes import block_volume_bp
from .boot_volume_routes import boot_volume_bp
from .network import network_bp
# 定义所有蓝图及其URL前缀
BLUEPRINTS: List[Tuple[Blueprint, str]] = [
    (auth_bp, '/auth'),        # 认证相关路由
    (tenant_bp, '/tenant'),    # 租户管理
    (compute_bp, '/compute'),  # 计算功能
    (instance_bp, '/instance'), # 实例管理
    (subscription_bp, '/subscription'), # 订阅管理
    (main_bp, ''),    # 主路由，无前缀
    (quota_bp, '/quota'),
    (block_volume_bp, '/api/block-volume'),  # 块存储卷管理
    (boot_volume_bp, '/api/boot-volume'),     # 引导卷管理
    (network_bp, '/network')     # 网络管理
]

def init_routes(app: Flask) -> None:
    """
    初始化并注册所有路由蓝图
    
    Args:
        app: Flask应用实例
    """
    for blueprint, url_prefix in BLUEPRINTS:
        try:
            app.register_blueprint(blueprint, url_prefix=url_prefix)
            app.logger.info(f'已注册蓝图: {blueprint.name} -> {url_prefix or "/"} 路径')
        except Exception as e:
            app.logger.error(f'注册蓝图 {blueprint.name} 失败: {str(e)}')
            raise
