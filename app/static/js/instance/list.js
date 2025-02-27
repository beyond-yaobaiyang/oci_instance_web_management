let confirmCallback = null;
const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
const toast = new bootstrap.Toast(document.getElementById('toast'));
let currentTenantId = '';

// 全局变量用于跟踪轮询状态
const pollingInstances = new Set();
const pollingIntervals = {};

// 开始轮询实例状态
function startPolling(instanceId) {
    if (pollingInstances.has(instanceId)) {
        return;
    }
    
    pollingInstances.add(instanceId);
    pollingIntervals[instanceId] = setInterval(async () => {
        try {
            const response = await fetch(`/instance/api/instance/${currentTenantId}/${instanceId}`);
            if (!response.ok) {
                throw new Error('获取实例状态失败');
            }
            
            const instance = await response.json();
            updateInstanceRow(instance);
            
            // 如果实例状态已稳定，停止轮询
            if (!['PROVISIONING', 'STARTING', 'STOPPING', 'TERMINATING'].includes(instance.lifecycle_state)) {
                stopPolling(instanceId);
            }
        } catch (error) {
            console.error('轮询实例状态失败:', error);
            stopPolling(instanceId);
        }
    }, 5000); // 每5秒轮询一次
}

// 停止轮询实例状态
function stopPolling(instanceId) {
    if (pollingIntervals[instanceId]) {
        clearInterval(pollingIntervals[instanceId]);
        delete pollingIntervals[instanceId];
        pollingInstances.delete(instanceId);
    }
}

// 停止所有轮询
function stopAllPolling() {
    pollingInstances.forEach(instanceId => {
        stopPolling(instanceId);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const tenantSelect = document.getElementById('tenantSelect');
    
    // 监听租户选择变化
    tenantSelect.addEventListener('change', function() {
        loadInstances();
    });
    
    // 如果有选中的租户，加载实例列表
    if (tenantSelect.value) {
        loadInstances();
    }
});

// 加载实例列表
async function loadInstances() {
    const tenantId = document.getElementById('tenantSelect').value;
    if (!tenantId) {
        showInstanceTable([]);
        return;
    }
    
    currentTenantId = tenantId;
    showLoading(true);
    
    try {
        // 停止所有现有的轮询
        stopAllPolling();
        
        const response = await fetch(`/instance/api/instances/${tenantId}`);
        if (!response.ok) {
            throw new Error('加载实例列表失败');
        }
        const instances = await response.json();
        showInstanceTable(instances);
        
        // 对所有处于过渡状态的实例开始轮询
        instances.forEach(instance => {
            if (['PROVISIONING', 'STARTING', 'STOPPING', 'TERMINATING'].includes(instance.lifecycle_state)) {
                startPolling(instance.id);
            }
        });
    } catch (error) {
        showToast(error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// 显示实例表格
function showInstanceTable(instances) {
    updateInstanceStats(instances);  // 添加这一行来更新统计
    const tbody = document.getElementById('instanceTableBody');
    if (!instances || instances.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">没有找到实例</td></tr>';
        return;
    }
    
    tbody.innerHTML = instances.map(instance => {
        // 获取主VNIC的IP地址
        return `
            <tr data-instance-id="${instance.id}">
                <td>${instance.display_name || '-'}</td>
                <td>${getStateLabel(instance.lifecycle_state)}</td>
                <td>${instance.shape || '-'}</td>
                <td>${instance.public_ip || '-'}</td>
                <td>${instance.private_ip || '-'}</td>
                <td>${getActionButtons(instance)}</td>
            </tr>
        `;
    }).join('');
}

// 更新实例统计
function updateInstanceStats(instances) {
    const stats = {
        total: instances.length,
        running: 0,
        stopped: 0,
        terminated: 0
    };
    
    instances.forEach(instance => {
        if (instance.lifecycle_state === 'RUNNING') {
            stats.running++;
        } else if (instance.lifecycle_state === 'STOPPED') {
            stats.stopped++;
        } else if (instance.lifecycle_state === 'TERMINATED') {
            stats.terminated++;
        }
    });
    
    document.getElementById('total-instances').textContent = stats.total;
    document.getElementById('running-instances').textContent = stats.running;
    document.getElementById('stopped-instances').textContent = stats.stopped;
    document.getElementById('terminated-instances').textContent = stats.terminated;
}

// 获取状态标签
function getStateLabel(state) {
    const stateMap = {
        'PROVISIONING': '<span class="badge bg-info">配置中</span>',
        'RUNNING': '<span class="badge bg-success">运行中</span>',
        'STARTING': '<span class="badge bg-info">启动中</span>',
        'STOPPING': '<span class="badge bg-warning">停止中</span>',
        'STOPPED': '<span class="badge bg-secondary">已停止</span>',
        'TERMINATING': '<span class="badge bg-danger">终止中</span>',
        'TERMINATED': '<span class="badge bg-danger">已终止</span>'
    };
    return stateMap[state] || `<span class="badge bg-secondary">${state}</span>`;
}

// 获取操作按钮
function getActionButtons(instance) {
    const buttons = [];
    
    // 查看详情按钮
    buttons.push(`
        <a href="/instance/detail?tenant_id=${currentTenantId}&instance_id=${instance.id}" 
           class="btn btn-sm btn-info" title="查看详情">
            <i class="fas fa-info-circle"></i>
        </a>
    `);
    
    // 根据实例状态显示不同的操作按钮
    switch (instance.lifecycle_state) {
        case 'RUNNING':
            // 停止按钮
            buttons.push(`
                <button class="btn btn-sm btn-warning" onclick="performInstanceAction('${instance.id}', 'stop')" title="停止">
                    <i class="fas fa-stop"></i>
                </button>
            `);
            // 重启按钮
            buttons.push(`
                <button class="btn btn-sm btn-primary" onclick="performInstanceAction('${instance.id}', 'reset')" title="重启">
                    <i class="fas fa-sync"></i>
                </button>
            `);
            break;
            
        case 'STOPPED':
            // 启动按钮
            buttons.push(`
                <button class="btn btn-sm btn-success" onclick="performInstanceAction('${instance.id}', 'start')" title="启动">
                    <i class="fas fa-play"></i>
                </button>
            `);
            break;
            
        case 'PROVISIONING':
        case 'STARTING':
        case 'STOPPING':
        case 'TERMINATING':
            // 过渡状态下禁用所有操作按钮
            break;
    }
    
    // 如果实例正在运行且有公网IP，显示更换IP按钮
    if (instance.lifecycle_state === 'RUNNING') {
        buttons.push(`
            <button class="btn btn-sm btn-secondary" 
                onclick="changePublicIP('${instance.id}')"
                type="button"
                title="更换公网IP">
                <i class="fas fa-exchange-alt"></i> 更换IP
            </button>
        `);
    }
    
    // 如果实例不在终止状态，显示终止按钮
    if (instance.lifecycle_state !== 'TERMINATED' && instance.lifecycle_state !== 'TERMINATING') {
        buttons.push(`
            <button class="btn btn-sm btn-danger" onclick="performInstanceAction('${instance.id}', 'terminate')" title="终止">
                <i class="fas fa-trash"></i>
            </button>
        `);
    }
    
    return buttons.join(' ');
}

// 执行实例操作
async function performInstanceAction(instanceId, action) {
    const tenantId = document.getElementById('tenantSelect').value;
    if (!tenantId) {
        showToast('请先选择租户', 'warning');
        return;
    }
    
    const actionMap = {
        'start': '启动',
        'stop': '停止',
        'reset': '重启',
        'terminate': '终止'
    };
    
    try {
        if (['stop', 'reset', 'terminate'].includes(action)) {
            await showConfirmModal(
                `确认${actionMap[action]}`,
                `确认要${actionMap[action]}此实例吗？${action === 'terminate' ? '此操作不可恢复！' : ''}`
            );
        }
        
        const response = await fetch('/instance/api/instance/action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tenant_id: tenantId,
                instance_id: instanceId,
                action: action
            })
        });
        
        const result = await response.json();
        if (result.success) {
            showToast(`${actionMap[action]}操作已发送`, 'success');
            if (result.instance) {
                updateInstanceRow(result.instance);
            }
            // 开始轮询实例状态
            startPolling(instanceId);
        } else {
            throw new Error(result.error || `${actionMap[action]}操作失败`);
        }
    } catch (error) {
        showToast(error.message, 'danger');
    }
}

// 更换公网IP
async function changePublicIP(instanceId) {
    console.log('changePublicIP called with instanceId:', instanceId);
    if (!instanceId) {
        console.error('No instanceId provided');
        return;
    }
    
    // 确认对话框
    const result = await Swal.fire({
        title: '确认更换IP',
        text: '确定要更换此实例的公网IP吗？',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33'
    });
    
    if (result.isConfirmed) {
        try {
            // 发送更换IP请求
            fetch('/instance/api/instance/public-ip', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tenant_id: currentTenantId,
                    instance_id: instanceId
                })
            });
            
            // 显示操作已发送的提示
            await Swal.fire({
                icon: 'info',
                title: '更换IP请求已发送',
                text: '请稍后刷新实例列表查看结果',
                confirmButtonText: '确定'
            });
            
        } catch (error) {
            console.error('Error changing IP:', error);
            await Swal.fire({
                icon: 'error',
                title: '发送请求失败',
                text: error.message || '无法发送更换IP请求'
            });
        }
    }
}

// 刷新实例列表
function refreshInstanceList() {
    loadInstances();
}

// 显示确认对话框
function showConfirmModal(title, message) {
    return new Promise((resolve, reject) => {
        const modal = document.getElementById('confirmModal');
        const titleEl = modal.querySelector('.modal-title');
        const bodyEl = modal.querySelector('.modal-body');
        const confirmBtn = modal.querySelector('#confirmModalButton');
        
        titleEl.textContent = title;
        bodyEl.textContent = message;
        
        // 设置确认回调
        confirmCallback = () => {
            confirmModal.hide();
            resolve();
        };
        
        confirmBtn.onclick = confirmCallback;
        confirmModal.show();
        
        // 处理取消
        modal.addEventListener('hidden.bs.modal', () => {
            if (confirmCallback) {
                reject(new Error('用户取消操作'));
                confirmCallback = null;
            }
        }, { once: true });
    });
}

// 显示/隐藏加载指示器
function showLoading(show) {
    document.getElementById('loading-indicator').style.display = show ? 'block' : 'none';
    document.getElementById('instance-table-container').style.display = show ? 'none' : 'block';
}

// 显示提示消息
function showToast(message, type = 'success') {
    const toastEl = document.getElementById('toast');
    const titleEl = document.getElementById('toastTitle');
    const messageEl = document.getElementById('toastMessage');
    
    // 设置标题
    titleEl.textContent = type === 'success' ? '成功' : '错误';
    
    // 设置消息
    messageEl.textContent = message;
    
    // 设置样式
    toastEl.className = `toast border-${type}`;
    
    // 显示提示框
    toast.show();
}

// 更新实例行
function updateInstanceRow(instance) {
    const row = document.querySelector(`tr[data-instance-id="${instance.id}"]`);
    if (row) {
        const stateCell = row.querySelector('td:nth-child(2)');
        const publicIpCell = row.querySelector('td:nth-child(4)');
        const privateIpCell = row.querySelector('td:nth-child(5)');
        const actionsCell = row.querySelector('td:nth-child(6)');
        
        if (stateCell) stateCell.innerHTML = getStateLabel(instance.lifecycle_state);
        if (publicIpCell) {
            publicIpCell.innerHTML = instance.public_ip ? `
                ${instance.public_ip}
                ${instance.lifecycle_state === 'RUNNING' ? `
                    <button class="btn btn-sm btn-outline-secondary ms-2" onclick="changePublicIP('${instance.id}')" title="更换公网IP">
                        <i class="fas fa-exchange-alt"></i>
                    </button>
                ` : ''}
            ` : '-';
        }
        if (privateIpCell) privateIpCell.textContent = instance.private_ip || '-';
        if (actionsCell) actionsCell.innerHTML = getActionButtons(instance);
        
        // 获取所有实例并更新统计信息
        const rows = document.querySelectorAll('#instanceTableBody tr[data-instance-id]');
        const instances = Array.from(rows).map(row => {
            const stateCell = row.querySelector('td:nth-child(2)');
            const stateText = stateCell.textContent.trim();
            return {
                lifecycle_state: stateText.includes('运行中') ? 'RUNNING' :
                               stateText.includes('已停止') ? 'STOPPED' :
                               stateText.includes('已终止') ? 'TERMINATED' :
                               'OTHER'
            };
        });
        updateInstanceStats(instances);
    }
}
