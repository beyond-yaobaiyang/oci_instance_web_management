from flask import Blueprint, render_template
from app.decorators import login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    """主页"""
    return render_template('main/index.html')
