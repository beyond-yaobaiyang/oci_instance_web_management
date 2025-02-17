from flask import Flask
from flask_login import LoginManager
from app.services.auth_service import AuthService
import os
import yaml
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(app):
    log_dir = Path('logs')
    if not log_dir.exists():
        log_dir.mkdir(parents=True)
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addHandler(file_handler)
    
    return app

def create_app():
    # 获取当前文件所在目录的绝对路径
    app_dir = os.path.abspath(os.path.dirname(__file__))
    
    # 创建Flask应用实例，指定模板和静态文件的绝对路径
    app = Flask(__name__,
                template_folder=os.path.join(app_dir, 'templates'),
                static_folder=os.path.join(app_dir, 'static'))
    
    app.logger.info(f'模板目录: {app.template_folder}')
    app.logger.info(f'静态文件目录: {app.static_folder}')
    
    # 加载配置
    config_path = os.path.join(os.path.dirname(app_dir), 'config', 'config.yml')
    app.logger.info(f'配置文件路径: {config_path}')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        app.config['SECRET_KEY'] = config['app']['secret_key']
    except Exception as e:
        app.logger.error(f'加载配置文件失败: {str(e)}')
        # 使用默认密钥
        app.config['SECRET_KEY'] = 'dev'
    
    # 配置日志
    app = setup_logging(app)
    app.logger.info('应用启动')
    
    # 初始化Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'
    
    auth_service = AuthService()
    
    @login_manager.user_loader
    def load_user(user_id):
        return auth_service.get_user(user_id)
    
    # 注册所有路由
    from app.routes import init_routes
    init_routes(app)
    
    
    app.logger.info('所有蓝图注册完成')
    return app