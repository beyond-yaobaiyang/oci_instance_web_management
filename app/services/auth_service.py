import bcrypt
import os
from datetime import datetime, timedelta
import yaml
from flask_login import UserMixin
from typing import Optional
import pyotp
import qrcode
import io
import base64

class User(UserMixin):
    def __init__(self, username: str, password: str, role: str, mfa_enabled: bool = False, mfa_secret: str = None):
        self.id = username  # 使用username作为id
        self.username = username
        self.password = password
        self.role = role
        self.failed_login_attempts = 0
        self.is_locked = False
        self.locked_until = None
        self.mfa_enabled = mfa_enabled
        self.mfa_secret = mfa_secret
        self.mfa_verified = False  # 用于跟踪MFA验证状态

class AuthService:
    def __init__(self):
        with open('config/config.yml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.max_attempts = self.config['security']['max_login_attempts']
        self.lockout_duration = self.config['security']['lockout_duration']
        self.mfa_issuer = self.config['security']['mfa_issuer']
        self.users = {}
        self._load_users()
        
    def _load_users(self):
        """加载用户配置"""
        try:
            with open('config/config.yml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.config = config
                
            # 清空现有用户
            self.users = {}
            
            # 加载用户
            for user_config in config['auth']['users']:
                user = User(
                    username=user_config['username'],
                    password=user_config['password'],
                    role=user_config['role'],
                    mfa_enabled=user_config.get('mfa_enabled', False),
                    mfa_secret=user_config.get('mfa_secret')
                )
                self.users[user.username] = user
                
            print(f"已加载用户配置: {len(self.users)}个用户")  # 调试日志
        except Exception as e:
            print(f"加载用户配置出错: {str(e)}")  # 调试日志
            raise
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        # 每次验证时重新加载用户配置
        self._load_users()
        
        user = self.users.get(username)
        
        if not user:
            return None
            
        # 检查账户是否被锁定
        if user.is_locked and user.locked_until and user.locked_until > datetime.utcnow():
            return None
            
        # 在实际环境中,这里应该使用bcrypt或其他加密方式比较密码
        if user.password == password:  
            # 重置登录失败次数
            user.failed_login_attempts = 0
            user.is_locked = False
            user.locked_until = None
            
            # 如果启用了MFA，需要等待MFA验证
            if user.mfa_enabled:
                user.mfa_verified = False
                return user
            
            # 如果没有启用MFA，直接返回用户
            return user
            
        # 增加失败次数
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= self.max_attempts:
            user.is_locked = True
            user.locked_until = datetime.utcnow() + timedelta(seconds=self.lockout_duration)
        return None
    
    def verify_mfa(self, username: str, token: str) -> bool:
        """验证MFA令牌"""
        print(f"验证MFA: 用户={username}, 令牌={token}")  # 调试日志
        user = self.users.get(username)
        if not user:
            print("用户不存在")  # 调试日志
            return False
            
        if not user.mfa_enabled or not user.mfa_secret:
            print("MFA未启用或密钥不存在")  # 调试日志
            return False
            
        totp = pyotp.TOTP(user.mfa_secret)
        try:
            valid = totp.verify(str(token).strip(), valid_window=1)  # 确保token是字符串并移除空白
            print(f"MFA验证结果: {valid}, 使用密钥: {user.mfa_secret}, 当前时间: {datetime.utcnow()}")  # 调试日志
            
            if valid:
                user.mfa_verified = True
                return True
        except Exception as e:
            print(f"MFA验证出错: {str(e)}")  # 调试日志
            
        return False
    
    def setup_mfa(self, username: str) -> tuple[str, str]:
        """设置MFA"""
        user = self.users.get(username)
        if not user:
            raise ValueError("User not found")
            
        # 生成新的MFA密钥
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        
        # 生成二维码
        provisioning_uri = totp.provisioning_uri(
            name=username,
            issuer_name=self.mfa_issuer
        )
        
        # 创建二维码图像
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 将图像转换为base64字符串
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_code = base64.b64encode(buffered.getvalue()).decode()
        
        return secret, qr_code
    
    def enable_mfa(self, username: str, secret: str, token: str) -> bool:
        """启用MFA"""
        print(f"启用MFA: 用户={username}, 密钥={secret}, 令牌={token}")  # 调试日志
        user = self.users.get(username)
        if not user:
            print("用户不存在")  # 调试日志
            return False
            
        # 验证令牌是否正确
        totp = pyotp.TOTP(secret)
        if not totp.verify(token):
            print("令牌验证失败")  # 调试日志
            return False
            
        # 启用MFA
        user.mfa_enabled = True
        user.mfa_secret = secret
        
        # 更新配置文件
        with open('config/config.yml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        for user_config in config['auth']['users']:
            if user_config['username'] == username:
                user_config['mfa_enabled'] = True
                user_config['mfa_secret'] = secret
                break
                
        with open('config/config.yml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
            
        print(f"MFA已启用: enabled={user.mfa_enabled}, secret={user.mfa_secret}")  # 调试日志
        return True
    
    def disable_mfa(self, username: str) -> bool:
        """禁用MFA"""
        print(f"禁用MFA: 用户={username}")  # 调试日志
        user = self.users.get(username)
        if not user:
            print("用户不存在")  # 调试日志
            return False
            
        # 禁用MFA
        user.mfa_enabled = False
        user.mfa_secret = None
        
        # 更新配置文件
        with open('config/config.yml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        for user_config in config['auth']['users']:
            if user_config['username'] == username:
                user_config['mfa_enabled'] = False
                user_config['mfa_secret'] = None
                break
                
        with open('config/config.yml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
            
        print(f"MFA已禁用: enabled={user.mfa_enabled}, secret={user.mfa_secret}")  # 调试日志
        self._load_users()  # 重新加载用户配置
        return True
    
    def change_password(self, username: str, current_password: str, new_password: str) -> bool:
        """修改用户密码
        
        Args:
            username: 用户名
            current_password: 当前密码
            new_password: 新密码
            
        Returns:
            bool: 是否修改成功
        """
        user = self.users.get(username)
        if not user:
            return False
            
        if user.password != current_password:  # 同样,这里应该使用加密比较
            return False
            
        # 更新用户对象的密码
        user.password = new_password  # 这里应该加密存储
        
        # 更新配置文件中的密码
        for user_config in self.config['auth']['users']:
            if user_config['username'] == username:
                user_config['password'] = new_password
                break
                
        # 保存配置
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
        # 每次获取用户时重新加载配置
        self._load_users()
        return self.users.get(user_id)
