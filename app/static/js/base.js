// 自动关闭警告消息
document.addEventListener('DOMContentLoaded', function() {
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 3000);
    });
});

// 密码确认验证
document.addEventListener('DOMContentLoaded', function() {
    var form = document.querySelector('#changePasswordModal form');
    if (form) {
        form.addEventListener('submit', function(event) {
            var newPassword = document.querySelector('#new_password').value;
            var confirmPassword = document.querySelector('#confirm_password').value;
            
            if (newPassword !== confirmPassword) {
                event.preventDefault();
                alert('新密码和确认密码不匹配！');
            }
        });
    }
});
