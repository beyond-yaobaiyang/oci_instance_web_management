from flask import Flask
from flask_login import LoginManager
import yaml
import os
import logging
from logging.handlers import RotatingFileHandler

# 初始化扩展
login_manager = LoginManager()

def create_app():
    app = Flask(__name__,
                template_folder=os.path.join('app', 'templates'),
                static_folder=os.path.join('app', 'static'))
    
    # 加载配置
    with open('config/config.yml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 配置应用
    app.config['SECRET_KEY'] = config['app']['secret_key']
    
    # 配置日志
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # 配置日志处理器
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.DEBUG)
    
    # 配置应用的日志
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.DEBUG)
    app.logger.info('应用启动')
    
    # 配置全局日志
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler],
        format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    
    # 初始化扩展
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'
    
    # 注册蓝图
    from app.routes.auth_routes import auth_bp
    from app.routes.tenant_routes import tenant_bp
    from app.routes.instance_routes import instance_bp
    from app.routes.compute_routes import compute_bp
    from app.routes.main_routes import main_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tenant_bp, url_prefix='/tenant')
    app.register_blueprint(instance_bp, url_prefix='/instance')
    app.register_blueprint(compute_bp, url_prefix='/compute')
    app.register_blueprint(main_bp)
    
    app.logger.info('所有蓝图注册完成')
    
    return app
