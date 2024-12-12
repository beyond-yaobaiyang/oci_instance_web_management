import bcrypt
from datetime import datetime, timedelta
import yaml
from flask_login import UserMixin
from typing import Optional

class User(UserMixin):
    def __init__(self, username: str, password: str, role: str):
        self.id = username  # 使用username作为id
        self.username = username
        self.password = password
        self.role = role
        self.failed_login_attempts = 0
        self.is_locked = False
        self.locked_until = None

class AuthService:
    def __init__(self):
        with open('config/config.yml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.max_attempts = self.config['security']['max_login_attempts']
        self.lockout_duration = self.config['security']['lockout_duration']
        self.users = {}
        self._load_users()
        
    def _load_users(self):
        """从配置文件加载用户"""
        for user_config in self.config['auth']['users']:
            user = User(
                username=user_config['username'],
                password=user_config['password'],
                role=user_config['role']
            )
            self.users[user.username] = user
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = self.users.get(username)
        
        if not user:
            return None
            
        # 检查账户是否被锁定
        if user.is_locked and user.locked_until and user.locked_until > datetime.utcnow():
            return None
            
        # 在实际环境中,这里应该使用bcrypt或其他加密方式比较密码
        if user.password == password:  # 简单起见,这里直接比较明文密码
            # 重置登录失败次数
            user.failed_login_attempts = 0
            user.is_locked = False
            user.locked_until = None
            return user
            
        # 增加失败次数
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= self.max_attempts:
            user.is_locked = True
            user.locked_until = datetime.utcnow() + timedelta(seconds=self.lockout_duration)
        return None
    
    def change_password(self, username: str, current_password: str, new_password: str) -> bool:
        user = self.users.get(username)
        if not user:
            return False
            
        if user.password != current_password:  # 同样,这里应该使用加密比较
            return False
            
        user.password = new_password  # 这里应该加密存储
        self._save_config()
        return True
    
    def _save_config(self):
        """保存配置到文件"""
        # 更新配置中的用户密码
        for user_config in self.config['auth']['users']:
            user = self.users.get(user_config['username'])
            if user:
                user_config['password'] = user.password
        
        # 写入配置文件
        with open('config/config.yml', 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True)
    
    def get_user(self, user_id: str) -> Optional[User]:
        """通过user_id获取用户,用于flask-login"""
        return self.users.get(user_id)
