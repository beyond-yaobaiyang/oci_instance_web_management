// DOM 加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化模态框
    const resultModal = new bootstrap.Modal(document.getElementById('resultModal'));
    window.resultModal = resultModal; // 保存到全局变量，以便其他函数使用
});

// 获取DOM元素
const tenantSelect = document.getElementById('tenantSelect');
const availabilityDomainSelect = document.getElementById('availabilityDomain');
const imageSelect = document.getElementById('imageSelect');
const shapeSelect = document.getElementById('shape');
const subnetSelect = document.getElementById('subnet');
const flexShapeOptions = document.querySelector('.flex-shape-options');
const loginMethodRadios = document.querySelectorAll('input[name="loginMethod"]');
const sshKeyInput = document.getElementById('sshKeyInput');
const createInstanceForm = document.getElementById('createInstanceForm');

// 更新选择框的辅助函数
function updateSelect(select, data, defaultText = '请选择') {
    console.log('更新选择框:', select.id, '数据:', data);
    select.innerHTML = `<option value="">${defaultText}</option>`;
    select.disabled = false;  // 确保选择框被启用
    
    if (Array.isArray(data)) {
        data.forEach(item => {
            console.log('处理选项:', item);
            const option = document.createElement('option');
            option.value = item.id;
            option.textContent = item.name;
            select.appendChild(option);
        });
    } else {
        console.warn('传入的数据不是数组:', data);
        select.innerHTML = '<option value="">无可用选项</option>';
    }
}

// 重置所有选择框
function resetSelections() {
    availabilityDomainSelect.innerHTML = '<option value="">请先选择租户</option>';
    availabilityDomainSelect.disabled = true;
    
    imageSelect.innerHTML = '<option value="">请先选择租户</option>';
    imageSelect.disabled = true;
    
    shapeSelect.innerHTML = '<option value="">请先选择可用性区域和系统镜像</option>';
    shapeSelect.disabled = true;
    
    subnetSelect.innerHTML = '<option value="">请先选择租户</option>';
    subnetSelect.disabled = true;
    
    flexShapeOptions.style.display = 'none';
}

// 显示加载提示
function showLoading() {
    availabilityDomainSelect.innerHTML = '<option value="">加载中...</option>';
    imageSelect.innerHTML = '<option value="">加载中...</option>';
    subnetSelect.innerHTML = '<option value="">加载中...</option>';
    shapeSelect.innerHTML = '<option value="">加载中...</option>';
}

// 隐藏加载提示并启用选择框
function hideLoading() {
    availabilityDomainSelect.disabled = false;
    imageSelect.disabled = false;
    subnetSelect.disabled = false;
    shapeSelect.disabled = false;
}

// 监听租户选择变化
tenantSelect.addEventListener('change', async function() {
    resetSelections();
    
    if (!this.value) {
        return;
    }
    
    showLoading();
    console.log('选择的租户ID:', this.value);
    
    try {
        const response = await fetch(`/instance/api/resources/${this.value}`);
        const data = await response.json();
        console.log('获取到的资源数据:', data);
        
        if (response.ok) {
            // 启用所有选择框
            availabilityDomainSelect.disabled = false;
            imageSelect.disabled = false;
            subnetSelect.disabled = false;
            shapeSelect.disabled = false;
            
            if (data.availability_domains && data.availability_domains.length > 0) {
                console.log('可用域:', data.availability_domains);
                updateSelect(availabilityDomainSelect, data.availability_domains, '请选择可用域');
            } else {
                console.warn('没有可用域数据');
                availabilityDomainSelect.innerHTML = '<option value="">无可用域</option>';
            }
            
            if (data.images && data.images.length > 0) {
                console.log('系统镜像:', data.images);
                updateSelect(imageSelect, data.images, '请选择系统镜像');
            } else {
                console.warn('没有系统镜像数据');
                imageSelect.innerHTML = '<option value="">无系统镜像</option>';
            }
            
            if (data.subnets && data.subnets.length > 0) {
                console.log('子网:', data.subnets);
                updateSelect(subnetSelect, data.subnets, '请选择子网');
            } else {
                console.warn('没有子网数据');
                subnetSelect.innerHTML = '<option value="">无子网</option>';
            }
            
            if (data.shapes && data.shapes.length > 0) {
                console.log('实例规格:', data.shapes);
                window.shapesData = data.shapes;
                updateShapes();  // 立即更新实例规格
            } else {
                console.warn('没有实例规格数据');
                shapeSelect.innerHTML = '<option value="">无实例规格</option>';
            }
        } else {
            console.error('API响应错误:', data.error);
            throw new Error(data.error || '加载资源失败');
        }
    } catch (error) {
        console.error('加载资源失败:', error);
        showToast(error.message || '加载资源失败', 'error');
    } finally {
        hideLoading();
    }
});

// 监听可用区域和镜像变化
availabilityDomainSelect.addEventListener('change', function() {
    console.log('可用区域变化:', availabilityDomainSelect.value);
    updateShapes();
});

imageSelect.addEventListener('change', function() {
    console.log('镜像变化:', imageSelect.value);
    updateShapes();
});

// 更新实例规格选项
function updateShapes() {
    console.log('更新实例规格选项');
    console.log('shapesData:', window.shapesData);
    
    shapeSelect.innerHTML = '<option value="">请选择实例规格</option>';
    shapeSelect.disabled = false;  // 确保实例规格选择框被启用
    
    if (!window.shapesData) {
        console.warn('没有实例规格数据');
        return;
    }
    
    window.shapesData.forEach(shape => {
        const option = document.createElement('option');
        option.value = shape.name;
        option.textContent = `${shape.name} (${shape.ocpus} OCPU, ${shape.memory_in_gbs}GB 内存)`;
        option.dataset.isFlex = shape.is_flex;
        shapeSelect.appendChild(option);
    });
}

// 监听实例规格变化
shapeSelect.addEventListener('change', function() {
    const selectedOption = this.options[this.selectedIndex];
    flexShapeOptions.style.display = selectedOption && selectedOption.dataset.isFlex === 'true' ? 'block' : 'none';
});

// 监听登录方式变化
loginMethodRadios.forEach(radio => {
    radio.addEventListener('change', function() {
        sshKeyInput.style.display = this.value === 'ssh' ? 'block' : 'none';
        if (this.value === 'ssh') {
            document.getElementById('sshKey').setAttribute('required', '');
        } else {
            document.getElementById('sshKey').removeAttribute('required');
        }
    });
});

// 处理表单提交
createInstanceForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // 显示加载动画
    const submitButton = document.getElementById('submitButton');
    const spinner = submitButton.querySelector('.spinner-border');
    const buttonText = submitButton.querySelector('.button-text');
    
    submitButton.disabled = true;
    spinner.style.display = 'inline-block';
    buttonText.textContent = '创建中...';
    
    const formData = {
        tenant_id: tenantSelect.value,
        display_name: document.getElementById('displayName').value,
        availability_domain: availabilityDomainSelect.value,
        image_id: imageSelect.value,
        shape: shapeSelect.value,
        subnet_id: subnetSelect.value,
        boot_volume_size_in_gbs: parseInt(document.getElementById('bootVolume').value),
        login_method: document.querySelector('input[name="loginMethod"]:checked').value
    };
    
    // 如果是弹性配置，添加OCPU和内存配置
    if (shapeSelect.options[shapeSelect.selectedIndex].dataset.isFlex === 'true') {
        formData.ocpus = parseInt(document.getElementById('ocpus').value);
        formData.memory_in_gbs = parseInt(document.getElementById('memory_in_gbs').value);
    }
    
    // 如果是SSH登录方式，添加SSH密钥
    if (formData.login_method === 'ssh') {
        formData.ssh_key = document.getElementById('sshKey').value.trim();
        if (!formData.ssh_key) {
            showToast('请输入SSH公钥', 'error');
            // 恢复按钮状态
            submitButton.disabled = false;
            spinner.style.display = 'none';
            buttonText.textContent = '创建实例';
            return;
        }
    }
    
    try {
        const response = await fetch('/instance/api/instance/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        console.log('创建实例结果:', result); // 添加日志
        
        // 更新成功信息
        document.getElementById('successMessage').style.display = result.success ? 'block' : 'none';
        document.getElementById('errorMessage').style.display = result.success ? 'none' : 'block';
        
        if (result.success) {
            // 显示实例信息
            document.getElementById('resultInstanceName').textContent = result.instance.display_name;
            document.getElementById('resultInstanceId').textContent = result.instance.id;
            document.getElementById('resultInstanceState').textContent = result.instance.lifecycle_state;
            
            // 如果是密码登录，显示密码
            if (formData.login_method === 'password' && result.password) {
                document.getElementById('passwordSection').style.display = 'block';
                document.getElementById('instancePassword').value = result.password;
            } else {
                document.getElementById('passwordSection').style.display = 'none';
            }
            
            // 重置表单
            this.reset();
            resetSelections();
        } else {
            document.getElementById('errorMessage').textContent = result.error || '创建实例失败';
        }
        
        // 无论成功还是失败都显示模态框
        window.resultModal.show();
        
    } catch (error) {
        console.error('创建实例失败:', error);
        document.getElementById('successMessage').style.display = 'none';
        document.getElementById('errorMessage').style.display = 'block';
        document.getElementById('errorMessage').textContent = error.message || '创建实例失败';
        window.resultModal.show();
    } finally {
        // 恢复按钮状态
        submitButton.disabled = false;
        spinner.style.display = 'none';
        buttonText.textContent = '创建实例';
    }
});

// 复制密码到剪贴板
function copyPassword(button) {
    const passwordInput = document.getElementById('instancePassword');
    passwordInput.select();
    document.execCommand('copy');
    
    const originalText = button.textContent;
    button.textContent = '已复制';
    button.disabled = true;
    
    setTimeout(() => {
        button.textContent = originalText;
        button.disabled = false;
    }, 2000);
}

// 显示提示信息
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.appendChild(toast);
    document.body.appendChild(container);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        container.remove();
    });
}