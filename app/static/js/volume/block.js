// 块存储卷管理相关的JavaScript代码
console.log('Block volume management script loaded');  // 添加初始化日志
let currentBlockVolumeId = null;

// 等待变量初始化
function waitForInitialization() {
    return new Promise((resolve) => {
        const checkVariables = () => {
            if (window.instanceId && window.tenantId) {
                console.log('初始化块存储卷列表:', { tenantId: window.tenantId, instanceId: window.instanceId });
                resolve();
            } else {
                setTimeout(checkVariables, 100); // 每100ms检查一次
            }
        };
        checkVariables();
    });
}

// 加载已附加的块存储卷列表
function loadAttachedVolumes() {
    console.log('Loading attached volumes...');  // 添加函数调用日志
    const volumesList = document.getElementById('blockVolumesList');
    if (!volumesList) {
        console.log('volumesList element not found');  // 添加元素检查日志
        return;
    }
    
    if (!window.instanceId) {
        console.error('缺少instance_id参数');
        volumesList.innerHTML = '<tr><td colspan="5" class="text-center text-danger">加载块存储卷列表失败：缺少instance_id参数</td></tr>';
        return;
    }
    
    // 显示加载中状态
    volumesList.innerHTML = '<tr><td colspan="5" class="text-center">加载中...</td></tr>';
    
    fetch(`/api/block-volume/attached-volumes/${window.instanceId}?tenant_id=${window.tenantId}`)
        .then(response => {
            console.log('Response status:', response.status);  // 添加响应状态日志
            if (!response.ok) {
                return response.json().then(error => {
                    throw new Error(error.error || '获取已附加的块存储卷列表失败');
                });
            }
            return response.json();
        })
        .then(volumes => {
            console.log('Received volumes:', volumes);  // 添加数据日志
            console.log('Volumes:', volumes); // 添加调试日志
            if (!volumes || volumes.length === 0) {
                volumesList.innerHTML = '<tr><td colspan="5" class="text-center">没有已附加的块存储卷</td></tr>';
                return;
            }
            
            volumesList.innerHTML = volumes.map(volume => `
                <tr>
                    <td>${volume.display_name || '未命名'}</td>
                    <td>${volume.size_in_gbs}</td>
                    <td>${volume.vpus_per_gb}</td>
                    <td>${volume.lifecycle_state}</td>
                    <td>
                        <button class="btn btn-primary btn-sm me-1" onclick="showUpdateBlockVolumeModal('${volume.id}', ${volume.size_in_gbs}, ${volume.vpus_per_gb})">
                            <i class="fas fa-edit"></i> 更新
                        </button>
                        <button class="btn btn-danger btn-sm" onclick="detachBlockVolume('${volume.attachment_id}')">
                            <i class="fas fa-unlink"></i> 分离
                        </button>
                    </td>
                </tr>
            `).join('');
        })
        .catch(error => {
            console.error('Error details:', error);  // 添加详细错误日志
            console.error('Error:', error); // 添加详细错误日志
            volumesList.innerHTML = '<tr><td colspan="5" class="text-center text-danger">加载失败: ' + error.message + '</td></tr>';
        });
}

// 显示更新块存储卷模态框
function showUpdateBlockVolumeModal(volumeId, currentSize, currentVpu) {
    currentBlockVolumeId = volumeId;
    const sizeInput = document.getElementById('blockVolumeSizeInput');
    const vpuInput = document.getElementById('blockVolumeVpuInput');
    
    sizeInput.value = currentSize;
    vpuInput.value = currentVpu;
    
    const modal = new bootstrap.Modal(document.getElementById('updateBlockVolumeModal'));
    modal.show();
}

// 显示分离确认对话框
function showDetachBlockVolumeConfirm(attachmentId) {
    Swal.fire({
        title: '确认分离块存储卷？',
        text: '此操作不可逆，请确认！',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: '确认',
        cancelButtonText: '取消'
    }).then((result) => {
        if (result.isConfirmed) {
            detachBlockVolume(attachmentId);
        }
    });
}

// 分离块存储卷
function detachBlockVolume(attachmentId) {
    fetch(`/api/block-volume/detach/${attachmentId}?tenant_id=${window.tenantId}`, {
        method: 'POST'
    })
    .then(response => {
        console.log('Response status:', response.status);  // 添加响应状态日志
        if (!response.ok) {
            return response.json().then(error => {
                throw new Error(error.error || '分离块存储卷失败');
            });
        }
        return response.json();
    })
    .then(result => {
        Swal.fire({
            icon: 'success',
            title: '操作成功',
            text: result.message || '块存储卷分离操作已启动'
        }).then(() => {
            loadAttachedVolumes();  // 重新加载列表
        });
    })
    .catch(error => {
        console.error('Error details:', error);  // 添加详细错误日志
        Swal.fire({
            icon: 'error',
            title: '操作失败',
            text: error.message || '分离块存储卷失败'
        });
    });
}

// 附加块存储卷
function attachBlockVolume() {
    const volumeId = document.getElementById('blockVolumeSelect').value;
    if (!volumeId) {
        Swal.fire({
            icon: 'error',
            title: '错误',
            text: '请选择要附加的块存储卷'
        });
        return;
    }

    const data = {
        instance_id: window.instanceId,
        volume_id: volumeId
    };
    console.log('附加块存储卷请求数据:', data);
    console.log('tenant_id:', window.tenantId);
    console.log('URL:', `/api/block-volume/attach?tenant_id=${window.tenantId}`);

    fetch(`/api/block-volume/attach?tenant_id=${window.tenantId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        console.log('Response status:', response.status);  // 添加响应状态日志
        if (!response.ok) {
            return response.json().then(error => {
                throw new Error(error.error || '附加块存储卷失败');
            });
        }
        return response.json();
    })
    .then(result => {
        Swal.fire({
            icon: 'success',
            title: '操作成功',
            text: result.message || '块存储卷附加操作已启动'
        }).then(() => {
            const modal = bootstrap.Modal.getInstance(document.getElementById('attachBlockVolumeModal'));
            modal.hide();
            loadAttachedVolumes();  // 重新加载列表
        });
    })
    .catch(error => {
        console.error('Error details:', error);  // 添加详细错误日志
        Swal.fire({
            icon: 'error',
            title: '操作失败',
            text: error.message || '附加块存储卷失败'
        });
    });
}

// 显示附加块存储卷模态框
function showAttachBlockVolumeModal() {
    const availabilityDomain = document.getElementById('instance-ad').textContent.trim();
    
    fetch(`/api/block-volume/available-volumes/${availabilityDomain}?tenant_id=${window.tenantId}`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(error => {
                    throw new Error(error.error || '获取可用的块存储卷列表失败');
                });
            }
            return response.json();
        })
        .then(volumes => {
            const select = document.getElementById('blockVolumeSelect');
            select.innerHTML = '<option value="">选择块存储卷...</option>';
            
            if (volumes && volumes.length > 0) {
                volumes.forEach(volume => {
                    select.innerHTML += `<option value="${volume.id}">${volume.display_name || '未命名'} (${volume.size_in_gbs}GB)</option>`;
                });
            } else {
                select.innerHTML += '<option disabled>没有可用的块存储卷</option>';
            }
            
            const modal = new bootstrap.Modal(document.getElementById('attachBlockVolumeModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire({
                icon: 'error',
                title: '加载失败',
                text: error.message || '获取可用的块存储卷列表失败'
            });
        });
}

// 更新块存储卷
function updateBlockVolume() {
    const sizeInput = document.getElementById('blockVolumeSizeInput');
    const vpuInput = document.getElementById('blockVolumeVpuInput');
    
    if (!currentBlockVolumeId) {
        Swal.fire({
            icon: 'error',
            title: '操作失败',
            text: '找不到要更新的块存储卷'
        });
        return;
    }
    
    fetch(`/api/block-volume/update/${currentBlockVolumeId}?tenant_id=${window.tenantId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            size_in_gbs: parseInt(sizeInput.value),
            vpus_per_gb: parseInt(vpuInput.value)
        })
    })
    .then(response => {
        console.log('Response status:', response.status);  // 添加响应状态日志
        if (!response.ok) {
            return response.json().then(error => {
                throw new Error(error.error || '更新块存储卷失败');
            });
        }
        return response.json();
    })
    .then(result => {
        Swal.fire({
            icon: 'success',
            title: '操作成功',
            text: result.message || '块存储卷更新操作已启动'
        }).then(() => {
            const modal = bootstrap.Modal.getInstance(document.getElementById('updateBlockVolumeModal'));
            modal.hide();
            loadAttachedVolumes();  // 重新加载列表
        });
    })
    .catch(error => {
        console.error('Error details:', error);  // 添加详细错误日志
        Swal.fire({
            icon: 'error',
            title: '操作失败',
            text: error.message || '更新块存储卷失败'
        });
    });
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded');  // 添加DOM加载日志
    // 等待变量初始化后再加载卷列表
    waitForInitialization().then(() => {
        loadAttachedVolumes();
    });
});