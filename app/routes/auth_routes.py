from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = auth_service.authenticate_user(username, password)
        if user:
            login_user(user)
            return redirect(url_for('main.index'))
        flash('用户名或密码错误', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    if new_password != confirm_password:
        return jsonify({'success': False, 'message': '新密码和确认密码不匹配'})
    
    if auth_service.change_password(current_user.username, current_password, new_password):
        return jsonify({'success': True, 'message': '密码修改成功'})
    else:
        return jsonify({'success': False, 'message': '当前密码错误'})
