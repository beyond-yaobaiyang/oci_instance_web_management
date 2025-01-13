 // 从URL获取参数
const urlParams = new URLSearchParams(window.location.search);
const tenantId = urlParams.get('tenant_id');
const instanceId = urlParams.get('instance_id');

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    if (!tenantId || !instanceId) {
        showToast('缺少必要的参数', 'error');
        return;
    }
    loadInstanceDetail();
    startPolling();
    startPollingVnics();
});

let pollingTimer = null;
let vnicPollingInterval = null;
const POLLING_INTERVAL = 5000; // 5秒轮询一次

// 加载实例详情
function loadInstanceDetail() {
    showLoading(true);
    fetch(`/instance/api/instance/${tenantId}/${instanceId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            updateInstanceInfo(data);
            updatePowerButtons(data.lifecycle_state);
        })
        .catch(error => {
            console.error('Error:', error);
            showToast(error.message, 'danger');
        })
        .finally(() => {
            showLoading(false);
        });
}

// 加载VNIC列表
async function loadVnics() {
    try {
        showLoading(true);
        const response = await fetch(`/instance/api/instance/${tenantId}/${instanceId}/vnics`);
        const vnics = await response.json();
        
        if (!Array.isArray(vnics)) {
            throw new Error(vnics.error || '加载VNIC列表失败');
        }
        
        const vnicList = document.getElementById('vnic-list');
        vnicList.innerHTML = '';
        
        vnics.forEach(vnic => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${vnic.display_name || '-'}</td>
                <td>${vnic.private_ip || '-'}</td>
                <td>${vnic.public_ip || '-'}</td>
                <td>${vnic.mac_address || '-'}</td>
                <td>${vnic.is_primary ? '<span class="badge bg-success">是</span>' : '<span class="badge bg-secondary">否</span>'}</td>
                <td>${getVnicStateLabel(vnic.state)}</td>
                <td>
                    ${!vnic.is_primary ? `
                        <button type="button" class="btn btn-danger btn-sm" onclick="detachVnic('${vnic.attachment_id}')">
                            <i class="fas fa-unlink"></i> 分离
                        </button>
                    ` : '-'}
                </td>
            `;
            vnicList.appendChild(tr);
        });
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// 显示附加VNIC模态框
async function showAttachVnicModal() {
    try {
        // 加载子网列表
        const response = await fetch(`/instance/api/resources/${tenantId}`);
        const resources = await response.json();
        
        if (!resources.subnets) {
            throw new Error('加载子网列表失败');
        }
        
        const subnetSelect = document.getElementById('subnetSelect');
        subnetSelect.innerHTML = '<option value="">请选择子网</option>';
        
        resources.subnets.forEach(subnet => {
            const option = document.createElement('option');
            option.value = subnet.id;
            option.textContent = `${subnet.display_name} (${subnet.cidr_block})`;
            subnetSelect.appendChild(option);
        });
        
        const modal = new bootstrap.Modal(document.getElementById('attachVnicModal'));
        modal.show();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 附加VNIC
async function attachVnic() {
    const vnicName = document.getElementById('vnicName').value;
    const subnetId = document.getElementById('subnetSelect').value;
    
    if (!vnicName || !subnetId) {
        showToast('请填写完整信息', 'error');
        return;
    }
    
    showLoading(true);
    fetch(`/instance/api/instance/${tenantId}/${instanceId}/vnic`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            display_name: vnicName,
            subnet_id: subnetId
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || `请求失败: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            showToast(data.error, 'error');
        } else {
            showToast('VNIC附加操作已开始，请等待状态更新');
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('attachVnicModal'));
            modal.hide();
            // 开始轮询VNIC状态
            startPollingVnics();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast(error.message, 'error');
    })
    .finally(() => {
        showLoading(false);
    });
}

// 分离VNIC
function detachVnic(attachmentId) {
    showConfirmModal('确认分离', '确定要分离此VNIC吗？').then((confirmed) => {
        if (confirmed) {
            showLoading(true);
            fetch(`/instance/api/instance/vnic/${tenantId}/${attachmentId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || `请求失败: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    showToast(data.error, 'error');
                } else {
                    showToast('VNIC分离操作已开始，请等待状态更新');
                    // 开始轮询VNIC状态
                    startPollingVnics();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast(error.message, 'error');
            })
            .finally(() => {
                showLoading(false);
            });
        }
    });
}

// 开始轮询VNIC状态
function startPollingVnics() {
    // 如果已经在轮询，先停止
    if (vnicPollingInterval) {
        clearInterval(vnicPollingInterval);
    }

    // 立即执行一次
    updateVnicList();

    // 开始定时轮询
    vnicPollingInterval = setInterval(() => {
        updateVnicList();
    }, POLLING_INTERVAL);
}

// 停止轮询VNIC状态
function stopPollingVnics() {
    if (vnicPollingInterval) {
        clearInterval(vnicPollingInterval);
        vnicPollingInterval = null;
    }
}

// 更新VNIC列表
function updateVnicList() {
    fetch(`/instance/api/instance/${tenantId}/${instanceId}/vnics`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `请求失败: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(vnics => {
            const vnicList = document.getElementById('vnic-list');
            vnicList.innerHTML = '';

            vnics.forEach(vnic => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${vnic.display_name || '-'}</td>
                    <td>${vnic.private_ip || '-'}</td>
                    <td>${vnic.public_ip || '-'}</td>
                    <td>${vnic.mac_address || '-'}</td>
                    <td>
                        <span class="badge ${vnic.is_primary ? 'bg-success' : 'bg-secondary'}">
                            ${vnic.is_primary ? '是' : '否'}
                        </span>
                    </td>
                    <td>${getVnicStateLabel(vnic.state)}</td>
                    <td>
                        ${!vnic.is_primary ? 
                            `<button class="btn btn-sm btn-danger" onclick="detachVnic('${vnic.attachment_id}')">分离</button>` : 
                            '-'}
                    </td>
                `;
                vnicList.appendChild(tr);
            });
        })
        .catch(error => {
            console.error('Error:', error);
            showToast(error.message, 'error');
            // 如果发生错误，停止轮询
            stopPollingVnics();
        });
}

function updateInstanceInfo(instance) {
    // 基本信息
    document.getElementById('instance-name').textContent = instance.display_name || '-';
    document.getElementById('instance-state').innerHTML = getStateLabel(instance.lifecycle_state);
    document.getElementById('instance-ad').textContent = instance.availability_domain || '-';
    document.getElementById('instance-shape').textContent = instance.shape || '-';
    document.getElementById('instance-ocpu').textContent = instance.ocpu_count || '-';
    document.getElementById('instance-memory').textContent = instance.memory_in_gbs ? `${instance.memory_in_gbs} GB` : '-';
    document.getElementById('instance-created').textContent = formatDateTime(instance.time_created);
    
    // 网络信息
    document.getElementById('instance-public-ip').textContent = instance.public_ip || '-';
    document.getElementById('instance-private-ip').textContent = instance.private_ip || '-';
    
    // 更新电源按钮状态
    updatePowerButtons(instance.lifecycle_state);
    
    // 更新调整形状按钮状态
    const adjustShapeBtn = document.getElementById('btn-adjust-shape');
    if (adjustShapeBtn) {
        if (instance.shape && instance.shape.endsWith('.Flex')) {
            adjustShapeBtn.style.display = 'inline-block';
        } else {
            adjustShapeBtn.style.display = 'none';
        }
    }
}

function formatMemorySize(sizeInGB) {
    if (!sizeInGB) return null;
    return `${sizeInGB} GB`;
}

function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return null;
    return new Date(dateTimeStr).toLocaleString('zh-CN');
}

function performInstanceAction(action) {
    const actionMap = {
        'start': '启动',
        'stop': '停止',
        'reset': '重启',
        'terminate': '终止'
    };

    showConfirmModal(`确认${actionMap[action]}`, `确定要${actionMap[action]}该实例吗？`)
        .then(confirmed => {
            if (confirmed) {
                showLoading(true);
                fetch(`/instance/api/instance/action`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tenant_id: tenantId,
                        instance_id: instanceId,
                        action: action
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        throw new Error(data.error);
                    }
                    showToast(`实例${actionMap[action]}操作已发送`);
                    startPolling();
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast(error.message, 'danger');
                })
                .finally(() => {
                    showLoading(false);
                });
            }
        });
}

function startPolling() {
    if (pollingTimer) {
        clearInterval(pollingTimer);
    }
    
    pollingTimer = setInterval(() => {
        fetch(`/instance/api/instance/${tenantId}/${instanceId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                updateInstanceInfo(data);
                updatePowerButtons(data.lifecycle_state);
                
                // 如果实例状态为RUNNING或STOPPED，停止轮询
                if (['RUNNING', 'STOPPED'].includes(data.lifecycle_state)) {
                    stopPolling();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                stopPolling();
            });
    }, 5000);
}

function stopPolling() {
    if (pollingTimer) {
        clearInterval(pollingTimer);
        pollingTimer = null;
    }
}

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

// 获取VNIC状态标签
function getVnicStateLabel(state) {
    const stateMap = {
        'PROVISIONING': '<span class="badge bg-info">配置中</span>',
        'AVAILABLE': '<span class="badge bg-success">可用</span>',
        'TERMINATING': '<span class="badge bg-warning">终止中</span>',
        'TERMINATED': '<span class="badge bg-danger">已终止</span>'
    };
    return stateMap[state] || `<span class="badge bg-secondary">${state}</span>`;
}

function showLoading(show) {
    document.getElementById('loading-indicator').style.display = show ? 'block' : 'none';
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastBody = toast.querySelector('.toast-body');
    toast.className = `toast border-${type}`;
    toastBody.textContent = message;
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

function showConfirmModal(title, message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        const titleEl = modal.querySelector('.modal-title');
        const bodyEl = modal.querySelector('.modal-body');
        const confirmBtn = document.getElementById('confirmModalConfirm');
        
        titleEl.textContent = title;
        bodyEl.textContent = message;
        
        const bsModal = new bootstrap.Modal(modal);
        
        const handleConfirm = () => {
            bsModal.hide();
            confirmBtn.removeEventListener('click', handleConfirm);
            resolve(true);
        };
        
        const handleHide = () => {
            modal.removeEventListener('hidden.bs.modal', handleHide);
            confirmBtn.removeEventListener('click', handleConfirm);
            resolve(false);
        };
        
        confirmBtn.addEventListener('click', handleConfirm);
        modal.addEventListener('hidden.bs.modal', handleHide);
        
        bsModal.show();
    });
}

// 显示调整形状对话框
async function showShapeModal() {
    const modal = new bootstrap.Modal(document.getElementById('shapeModal'));
    const currentShape = document.getElementById('instance-shape').textContent;
    const shapeSelect = document.getElementById('shapeSelect');
    const flexShapeConfig = document.getElementById('flexShapeConfig');
    
    try {
        showLoading(true);
        // 获取可用的实例形状
        const response = await fetch(`/instance/api/instance/${tenantId}/${instanceId}/shapes`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        
        if (result.status === 'success') {
            // 清空现有选项
            shapeSelect.innerHTML = '';
            
            // 按处理器类型分组
            const shapeGroups = {};
            result.data.forEach(shape => {
                const processorType = shape.processor_description.includes('AMD') ? 'AMD' :
                                    shape.processor_description.includes('ARM') ? 'ARM' : '其他';
                if (!shapeGroups[processorType]) {
                    shapeGroups[processorType] = [];
                }
                shapeGroups[processorType].push(shape);
            });
            
            // 添加分组选项
            Object.entries(shapeGroups).forEach(([processorType, shapes]) => {
                const optgroup = document.createElement('optgroup');
                optgroup.label = `${processorType} 实例`;
                
                shapes.forEach(shape => {
                    const option = document.createElement('option');
                    option.value = shape.shape;
                    option.textContent = `${shape.shape} (${shape.ocpus} OCPU, ${shape.memory_in_gbs}GB 内存)`;
                    option.dataset.shape = JSON.stringify(shape);
                    if (shape.shape === currentShape) {
                        option.selected = true;
                    }
                    optgroup.appendChild(option);
                });
                
                shapeSelect.appendChild(optgroup);
            });
            
            modal.show();
            
            // 设置灵活形状配置
            const updateFlexConfig = () => {
                const selectedOption = shapeSelect.selectedOptions[0];
                if (selectedOption) {
                    const shapeData = JSON.parse(selectedOption.dataset.shape);
                    if (shapeData.is_flex_shape) {
                        flexShapeConfig.classList.remove('d-none');
                        // 更新OCPU和内存输入框的限制
                        const ocpuInput = document.getElementById('ocpuInput');
                        const memoryInput = document.getElementById('memoryInput');
                        
                        ocpuInput.min = shapeData.min_ocpus || 1;
                        ocpuInput.max = shapeData.max_ocpus || 64;
                        ocpuInput.value = shapeData.ocpus;
                        
                        memoryInput.min = shapeData.min_memory_in_gbs || 1;
                        memoryInput.max = shapeData.max_memory_in_gbs || 1024;
                        memoryInput.value = shapeData.memory_in_gbs;
                    } else {
                        flexShapeConfig.classList.add('d-none');
                    }
                }
            };
            
            shapeSelect.addEventListener('change', updateFlexConfig);
            updateFlexConfig();
        } else {
            throw new Error(result.message);
        }
    } catch (error) {
        showToast(`获取可用实例形状失败: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// 更新实例形状
async function updateShape() {
    const shapeSelect = document.getElementById('shapeSelect');
    const ocpuInput = document.getElementById('ocpuInput');
    const memoryInput = document.getElementById('memoryInput');
    
    showLoading(true);
    
    try {
        const shape = shapeSelect.value;
        const data = {
            shape: shape
        };
        
        // 如果是灵活形状，添加配置
        if (shape.includes('Flex')) {
            data.shape_config = {
                ocpus: parseInt(ocpuInput.value),
                memory_in_gbs: parseInt(memoryInput.value)
            };
        }
        
        const response = await fetch(`/instance/api/instance/${tenantId}/${instanceId}/shape`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showToast('实例形状更新已开始，请等待几分钟');
            bootstrap.Modal.getInstance(document.getElementById('shapeModal')).hide();
            // 开始轮询实例状态
            startPolling();
        } else {
            throw new Error(result.message);
        }
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function refreshInstanceDetails() {
    try {
        // 显示加载提示
        const loadingToast = Swal.fire({
            title: '正在刷新...',
            allowOutsideClick: false,
            showConfirmButton: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        // 获取当前URL中的实例ID
        const pathParts = window.location.pathname.split('/');
        const instanceId = pathParts[pathParts.length - 1];

        // 刷新页面
        window.location.reload();

    } catch (error) {
        console.error('Error refreshing instance details:', error);
        Swal.fire({
            icon: 'error',
            title: '刷新失败',
            text: '无法刷新实例详情'
        });
    }
}

function updatePowerButtons(state) {
    const startBtn = document.getElementById('btn-start');
    const stopBtn = document.getElementById('btn-stop');
    const resetBtn = document.getElementById('btn-reset');
    switch(state.toLowerCase()) {
        case 'running':
            startBtn.disabled = true;
            stopBtn.disabled = false;
            resetBtn.disabled = false;
            break;
        case 'stopped':
            startBtn.disabled = false;
            stopBtn.disabled = true;
            resetBtn.disabled = true;
            break;
        case 'stopping':
        case 'starting':
        case 'provisioning':
            startBtn.disabled = true;
            stopBtn.disabled = true;
            resetBtn.disabled = true;
            break;
        default:
            startBtn.disabled = false;
            stopBtn.disabled = false;
            resetBtn.disabled = false;
    }
}