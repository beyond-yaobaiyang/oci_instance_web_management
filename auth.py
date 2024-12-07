import yaml
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import generate_csrf

class User(UserMixin):
    def __init__(self, username, password_hash):
        self.id = username
        self.username = username
        self.password_hash = password_hash

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_tenant(self):
        """
        默认返回第一个租户
        实际应该根据用户权限和配置动态获取
        """
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # 返回第一个租户的名称
        tenants = config.get('tenants', [])
        return tenants[0]['name'] if tenants else 'default_tenant'

    def get_regions(self):
        """
        默认返回第一个租户的区域
        实际应该根据用户权限和配置动态获取
        """
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # 返回第一个租户的区域
        tenants = config.get('tenants', [])
        return tenants[0].get('regions', []) if tenants else []

class AuthManager:
    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.users = {}
        self._load_users()

    def _load_users(self):
        for user_config in self.config.get('users', []):
            username = user_config['username']
            # Generate password hash if not already hashed
            password_hash = generate_password_hash(user_config['password'])
            self.users[username] = User(username, password_hash)

    def authenticate(self, username, password):
        user = self.users.get(username)
        if user and user.check_password(password):
            return user
        return None

    def setup_login_manager(self, app):
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'login'

        @login_manager.user_loader
        def load_user(user_id):
            return self.users.get(user_id)

        return login_manager

def init_auth_routes(app, auth_manager):
    from flask import request, render_template, redirect, url_for, flash
    from flask_login import login_required, current_user, logout_user

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            # 为登录页面生成 CSRF 令牌
            csrf_token = generate_csrf()
            return render_template('login.html', csrf_token=csrf_token)
        
        if request.method == 'POST':
            # 支持 JSON 和 form 数据
            data = request.get_json() or request.form
            username = data.get('username')
            password = data.get('password')
            
            user = auth_manager.authenticate(username, password)
            if user:
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password')
                return render_template('login.html', error='Invalid username or password'), 400

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html', username=current_user.id)
