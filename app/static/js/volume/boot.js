// 引导卷管理相关的JavaScript代码
let currentBootVolumeId = null;
let detachPollingTimer = null;

// 加载引导卷列表
function loadBootVolumes() {
    if (!window.tenantId) {
        console.error('缺少tenant_id参数');
        document.getElementById('bootVolumesList').innerHTML = 
            '<tr><td colspan="5" class="text-center text-danger">加载引导卷列表失败：缺少tenant_id参数</td></tr>';
        return;
    }

    if (!window.instanceId) {
        console.error('缺少instance_id参数');
        document.getElementById('bootVolumesList').innerHTML = 
            '<tr><td colspan="5" class="text-center text-danger">加载引导卷列表失败：缺少instance_id参数</td></tr>';
        return;
    }
    
    console.log('加载引导卷列表:', { tenantId: window.tenantId, instanceId: window.instanceId });
    
    // 显示加载中
    document.getElementById('bootVolumesList').innerHTML = 
        '<tr><td colspan="5" class="text-center"><i class="fas fa-spinner fa-spin"></i> 加载中...</td></tr>';
    
    fetch(`/api/boot-volume/attached-volumes/${window.instanceId}?tenant_id=${window.tenantId}`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(error => {
                    throw new Error(error.error || '加载引导卷列表失败');
                });
            }
            return response.json();
        })
        .then(volumes => {
            const tbody = document.getElementById('bootVolumesList');
            if (!volumes || volumes.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center">暂无引导卷</td></tr>';
                return;
            }
            
            // 保存可用性域信息，供后续使用
            if (volumes[0] && volumes[0].availability_domain) {
                window.availabilityDomain = volumes[0].availability_domain;
            }
            
            tbody.innerHTML = volumes.map(volume => {
                // 根据状态决定显示的按钮
                let actionButton = '';
                const isDetached = volume.lifecycle_state === 'DETACHED';
                const isDetaching = volume.lifecycle_state === 'DETACHING';
                const isAttached = volume.lifecycle_state === 'ATTACHED';
                const isAttaching = volume.lifecycle_state === 'ATTACHING';
                
                if (isDetached) {
                    actionButton = `
                        <button class="btn btn-success btn-sm" onclick="attachBootVolume('${volume.id}')" ${window.instanceState !== 'STOPPED' ? 'disabled' : ''}>
                            <i class="fas fa-link"></i> 附加
                        </button>
                    `;
                } else if (isAttached) {
                    actionButton = `
                        <button class="btn btn-warning btn-sm" onclick="showDetachBootVolumeConfirm('${volume.attachment_id}')" ${window.instanceState !== 'STOPPED' ? 'disabled' : ''}>
                            <i class="fas fa-unlink"></i> 分离
                        </button>
                    `;
                } else if (isDetaching) {
                    actionButton = `
                        <button class="btn btn-warning btn-sm" disabled>
                            <i class="fas fa-spinner fa-spin"></i> 分离中
                        </button>
                    `;
                } else if (isAttaching) {
                    actionButton = `
                        <button class="btn btn-success btn-sm" disabled>
                            <i class="fas fa-spinner fa-spin"></i> 附加中
                        </button>
                    `;
                }
                
                return `
                    <tr>
                        <td>${volume.display_name || '-'}</td>
                        <td>${volume.size_in_gbs}</td>
                        <td>${volume.vpus_per_gb}</td>
                        <td>${volume.lifecycle_state}</td>
                        <td>
                            <div class="btn-group btn-group-sm">
                                ${actionButton}
                                <button class="btn btn-primary btn-sm" onclick="showUpdateBootVolumeModal('${volume.id}', ${volume.size_in_gbs}, ${volume.vpus_per_gb})" ${!isAttached ? 'disabled' : ''}>
                                    <i class="fas fa-edit"></i> 更新
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('bootVolumesList').innerHTML = 
                `<tr><td colspan="5" class="text-center text-danger">加载引导卷列表失败：${error.message}</td></tr>`;
        });
}

// 显示分离确认对话框
function showDetachBootVolumeConfirm(attachmentId) {
    if (window.instanceState !== 'STOPPED') {
        Swal.fire({
            icon: 'warning',
            title: '操作失败',
            text: '只能在实例关机状态下分离引导卷'
        });
        return;
    }
    
    Swal.fire({
        title: '确认分离',
        text: '确定要分离此引导卷吗？',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: '确认',
        cancelButtonText: '取消'
    }).then((result) => {
        if (result.isConfirmed) {
            detachBootVolume(attachmentId);
        }
    });
}

// 分离引导卷
function detachBootVolume(attachmentId) {
    if (!window.tenantId) {
        Swal.fire({
            icon: 'error',
            title: '操作失败',
            text: '缺少tenant_id参数'
        });
        return;
    }
    
    // 显示加载提示
    Swal.fire({
        title: '正在分离引导卷...',
        text: '请稍候',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    console.log('分离引导卷:', { attachmentId });
    fetch(`/api/boot-volume/detach/${attachmentId}?tenant_id=${window.tenantId}`, {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(error => {
                throw new Error(error.error || '分离引导卷失败');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('分离引导卷响应:', data);
        Swal.close();
        
        if (data.state === 'DETACHED') {
            Swal.fire({
                icon: 'success',
                title: '操作成功',
                text: '引导卷已分离'
            }).then(() => {
                setTimeout(loadBootVolumes, 1000); // 延迟1秒后刷新
            });
        } else {
            Swal.fire({
                icon: 'success',
                title: '操作成功',
                text: '引导卷分离操作已启动'
            }).then(() => {
                // 开始轮询状态
                pollAttachmentStatus(attachmentId);
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        Swal.close();
        Swal.fire({
            icon: 'error',
            title: '操作失败',
            text: error.message || '分离引导卷失败'
        });
    });
}

// 轮询附件状态
function pollAttachmentStatus(attachmentId, retries = 30) {
    if (!window.tenantId) {
        console.error('缺少tenant_id参数');
        return;
    }
    
    if (retries <= 0) {
        console.log('轮询超时，刷新列表');
        loadBootVolumes();
        return;
    }
    
    console.log('轮询附件状态:', { attachmentId, retries });
    fetch(`/api/boot-volume/attachment/${attachmentId}/status?tenant_id=${window.tenantId}`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(error => {
                    throw new Error(error.error || '获取附件状态失败');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('附件状态:', data);
            if (data.state === 'ATTACHED' || data.state === 'DETACHED') {
                Swal.fire({
                    icon: 'success',
                    title: '操作成功',
                    text: data.message || '操作完成'
                }).then(() => {
                    setTimeout(loadBootVolumes, 1000); // 延迟1秒后刷新
                });
            } else if (data.state === 'ATTACHING' || data.state === 'DETACHING') {
                // 继续轮询
                setTimeout(() => pollAttachmentStatus(attachmentId, retries - 1), 2000);
            } else {
                // 其他状态，刷新列表
                setTimeout(loadBootVolumes, 1000); // 延迟1秒后刷新
            }
        })
        .catch(error => {
            console.error('Error:', error);
            // 发生错误也继续轮询
            setTimeout(() => pollAttachmentStatus(attachmentId, retries - 1), 2000);
        });
}

// 附加引导卷
function attachBootVolume(volumeId) {
    if (!window.tenantId || !window.instanceId) {
        Swal.fire({
            icon: 'error',
            title: '操作失败',
            text: '缺少必要参数'
        });
        return;
    }
    
    // 显示加载提示
    Swal.fire({
        title: '正在附加引导卷...',
        text: '请稍候',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    console.log('附加引导卷:', { volumeId, instanceId: window.instanceId, tenantId: window.tenantId });
    fetch('/api/boot-volume/attach', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            tenant_id: window.tenantId,
            instance_id: window.instanceId,
            volume_id: volumeId
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(error => {
                throw new Error(error.error || '附加引导卷失败');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('附加引导卷响应:', data);
        Swal.close();
        
        if (data.state === 'ATTACHED') {
            Swal.fire({
                icon: 'success',
                title: '操作成功',
                text: '引导卷已附加'
            }).then(() => {
                setTimeout(loadBootVolumes, 1000); // 延迟1秒后刷新
            });
        } else {
            Swal.fire({
                icon: 'success',
                title: '操作成功',
                text: '引导卷附加操作已启动'
            }).then(() => {
                // 开始轮询状态
                pollAttachmentStatus(data.attachment_id);
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        Swal.close();
        Swal.fire({
            icon: 'error',
            title: '操作失败',
            text: error.message || '附加引导卷失败'
        });
    });
}

// 显示更新引导卷模态框
function showUpdateBootVolumeModal(volumeId, currentSize, currentVpu) {
    currentBootVolumeId = volumeId;
    
    document.getElementById('bootVolumeSizeInput').value = currentSize;
    document.getElementById('bootVolumeVpuInput').value = currentVpu;
    
    const modal = new bootstrap.Modal(document.getElementById('updateBootVolumeModal'));
    modal.show();
}

// 更新引导卷
function updateBootVolume() {
    const sizeInput = document.getElementById('bootVolumeSizeInput');
    const vpuInput = document.getElementById('bootVolumeVpuInput');
    
    const size = parseInt(sizeInput.value);
    const vpu = parseInt(vpuInput.value);
    
    if (!size || !vpu) {
        Swal.fire({
            icon: 'error',
            title: '操作失败',
            text: '请输入有效的大小和VPU值'
        });
        return;
    }
    
    fetch(`/api/boot-volume/update/${currentBootVolumeId}?tenant_id=${window.tenantId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            size_in_gbs: size,
            vpus_per_gb: vpu
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(error => {
                throw new Error(error.error || '更新引导卷失败');
            });
        }
        return response.json();
    })
    .then(result => {
        Swal.fire({
            icon: 'success',
            title: '操作成功',
            text: result.message || '引导卷更新成功'
        }).then(() => {
            const modal = bootstrap.Modal.getInstance(document.getElementById('updateBootVolumeModal'));
            modal.hide();
            setTimeout(loadBootVolumes, 1000); // 延迟1秒后刷新
        });
    })
    .catch(error => {
        console.error('Error:', error);
        Swal.fire({
            icon: 'error',
            title: '操作失败',
            text: error.message || '更新引导卷失败'
        });
    });
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    if (typeof window.instanceId !== 'undefined') {
        loadBootVolumes();
    }
});