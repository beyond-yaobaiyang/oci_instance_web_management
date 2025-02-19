// 创建控制台连接
function createConsoleConnection() {
    console.log('打开创建控制台连接模态框');
    const modal = new bootstrap.Modal(document.getElementById('createConsoleModal'));
    modal.show();
}

// 提交创建控制台连接
async function submitConsoleConnection() {
    console.log('开始提交创建控制台连接请求');
    const publicKey = document.getElementById('publicKey').value.trim();
    if (!publicKey) {
        showToast('error', '请输入SSH公钥');
        return;
    }

    try {
        console.log('发送创建请求，参数:', {
            tenant_id: window.tenantId,
            instance_id: window.instanceId
        });

        const response = await fetch('/console-connection/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tenant_id: window.tenantId,
                instance_id: window.instanceId,
                public_key: publicKey
            })
        });

        const data = await response.json();
        console.log('创建响应:', data);

        if (!response.ok) {
            throw new Error(data.error || '创建控制台连接失败');
        }

        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('createConsoleModal'));
        modal.hide();

        // 清空表单
        document.getElementById('publicKey').value = '';

        // 更新状态显示
        await loadConsoleConnection();
        showToast('success', '控制台连接创建成功');
    } catch (error) {
        console.error('创建控制台连接失败:', error);
        showToast('error', error.message);
    }
}

// 删除控制台连接
async function deleteConsoleConnection() {
    console.log('准备删除控制台连接');
    if (!confirm('确定要删除控制台连接吗？')) {
        return;
    }

    try {
        console.log('发送删除请求，参数:', {
            tenant_id: window.tenantId,
            instance_id: window.instanceId
        });

        const response = await fetch('/console-connection/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tenant_id: window.tenantId,
                instance_id: window.instanceId
            })
        });

        const data = await response.json();
        console.log('删除响应:', data);

        if (!response.ok) {
            throw new Error(data.error || '删除控制台连接失败');
        }

        // 更新状态显示
        await loadConsoleConnection();
        showToast('success', '控制台连接已删除');
    } catch (error) {
        console.error('删除控制台连接失败:', error);
        showToast('error', error.message);
    }
}

// 加载控制台连接状态
async function loadConsoleConnection() {
    try {
        console.log('开始加载控制台连接状态，参数:', {
            tenant_id: window.tenantId,
            instance_id: window.instanceId
        });

        const response = await fetch(`/console-connection/get/${window.tenantId}/${window.instanceId}`);
        const result = await response.json();
        
        console.log('获取到控制台连接状态:', result);

        const statusDiv = document.getElementById('console-connection-status');
        const createBtn = document.getElementById('btn-create-console');
        const deleteBtn = document.getElementById('btn-delete-console');

        if (!statusDiv) {
            console.error('未找到状态显示元素 #console-connection-status');
            return;
        }

        if (!createBtn || !deleteBtn) {
            console.error('未找到按钮元素');
            return;
        }

        if (!response.ok) {
            throw new Error(result.error || '加载控制台连接状态失败');
        }

        // 检查是否有活动的控制台连接
        const hasConnection = result.data && (
            result.data.connection_string || 
            (result.data.lifecycle_state && result.data.lifecycle_state !== 'DELETED')
        );

        console.log('连接状态检查:', {
            hasConnection,
            data: result.data
        });

        if (hasConnection) {
            // 有活动的控制台连接
            statusDiv.innerHTML = `
                <div class="mb-2">
                    <strong>状态：</strong> 
                    <span class="badge bg-success">已连接</span>
                </div>
                <div class="mb-2">
                    <strong>ID：</strong>
                    <div class="text-muted">${result.data.id}</div>
                </div>
                <div class="mb-2">
                    <strong>状态：</strong>
                    <div class="text-muted">${result.data.lifecycle_state}</div>
                </div>
                ${result.data.connection_string ? `
                <div class="mb-2">
                    <strong>VNC连接命令（Linux/Mac系统）：</strong>
                    <div class="bg-light p-2 rounded">
                        <code>${result.data.connection_string}</code>
                    </div>
                    <div class="text-muted mt-2">
                        <small>
                            1. 在本地或远程的linux/mac终端运行上述命令建立SSH隧道<br>
                            2. 使用VNC客户端连接 ssh转发隧道客户端:5900<br>
                            3. 如需在其他机器访问，请将 localhost 替换为运行命令的机器IP
                        </small>
                    </div>
                </div>
                ` : ''}
            `;
            createBtn.style.display = 'none';
            deleteBtn.style.display = 'inline-block';
        } else {
            // 无控制台连接
            statusDiv.innerHTML = `
                <div class="text-muted">
                    ${result.message || '未创建控制台连接'}
                </div>
            `;
            createBtn.style.display = 'inline-block';
            deleteBtn.style.display = 'none';
        }
    } catch (error) {
        console.error('加载控制台连接状态失败:', error);
        showToast('error', error.message);
    }
}
