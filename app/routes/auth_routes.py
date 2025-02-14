from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app.services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        mfa_token = request.form.get('mfa_token')
        
        user = auth_service.authenticate_user(username, password)
        if user:
            if user.mfa_enabled:
                if mfa_token:
                    if auth_service.verify_mfa(username, mfa_token):
                        print("MFA验证成功，准备登录用户")  
                        user.mfa_verified = True
                        login_user(user)
                        print(f"用户登录状态: {current_user.is_authenticated}")  
                        return redirect(url_for('main.index'))
                    else:
                        print("MFA验证失败")  
                        flash('MFA验证码错误', 'error')
                        return render_template('auth/login.html', show_mfa=True, username=username, password=password)
                else:
                    print("需要MFA令牌")  
                    return render_template('auth/login.html', show_mfa=True, username=username, password=password)
            else:
                print("不需要MFA，直接登录")  
                login_user(user)
                return redirect(url_for('main.index'))
        flash('用户名或密码错误', 'error')
    
    return render_template('auth/login.html', show_mfa=False)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if new_password != confirm_password:
        flash('新密码和确认密码不匹配', 'error')
        return redirect(url_for('auth.settings'))
    
    if auth_service.change_password(current_user.username, current_password, new_password):
        flash('密码修改成功', 'success')
    else:
        flash('当前密码错误', 'error')
    
    return redirect(url_for('auth.settings'))

@auth_bp.route('/mfa/setup', methods=['POST'])
@login_required
def setup_mfa():
    try:
        secret, qr_code = auth_service.setup_mfa(current_user.username)
        return jsonify({
            'success': True,
            'secret': secret,
            'qr_code': qr_code
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@auth_bp.route('/mfa/enable', methods=['POST'])
@login_required
def enable_mfa():
    data = request.get_json()
    secret = data.get('secret')
    token = data.get('token')
    
    if not secret or not token:
        return jsonify({
            'success': False,
            'message': '缺少必要参数'
        })
    
    if auth_service.enable_mfa(current_user.username, secret, token):
        return jsonify({
            'success': True,
            'message': 'MFA已启用'
        })
    else:
        return jsonify({
            'success': False,
            'message': '验证码错误或MFA设置失败'
        })

@auth_bp.route('/mfa/disable', methods=['POST'])
@login_required
def disable_mfa():
    try:
        if auth_service.disable_mfa(current_user.username):
            # 重新加载用户配置
            auth_service._load_users()
            # 更新当前用户状态
            user = auth_service.get_user(current_user.username)
            if user:
                current_user.mfa_enabled = user.mfa_enabled
                current_user.mfa_secret = user.mfa_secret
            return jsonify({'success': True, 'message': 'MFA已禁用'})
        return jsonify({'success': False, 'message': '禁用MFA失败'})
    except Exception as e:
        print(f"禁用MFA出错: {str(e)}")  # 调试日志
        return jsonify({'success': False, 'message': '禁用MFA失败'})

@auth_bp.route('/settings')
@login_required
def settings():
    auth_service._load_users()
    user = auth_service.get_user(current_user.username)
    if user:
        current_user.mfa_enabled = user.mfa_enabled
        current_user.mfa_secret = user.mfa_secret
    return render_template('auth/settings.html')

@auth_bp.route('/mfa/setup/page')
@login_required
def setup_mfa_page():
    if current_user.mfa_enabled:
        flash('MFA已经启用', 'warning')
        return redirect(url_for('auth.settings'))
    return render_template('auth/mfa_setup.html')
