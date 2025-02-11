let currentTenantId = '';
let currentSecurityGroup = null;
let currentRules = {
    ingress: [],
    egress: []
};

document.addEventListener('DOMContentLoaded', function() {
    const tenantSelect = document.getElementById('tenantSelect');
    const refreshBtn = document.getElementById('refreshBtn');
    
    // 监听租户选择变化
    tenantSelect.addEventListener('change', function() {
        currentTenantId = this.value;
        console.log('选择租户:', currentTenantId);
        refreshBtn.disabled = !currentTenantId;
        if (currentTenantId) {
            loadSecurityGroups();
        } else {
            clearSecurityGroupsTable();
        }
    });

    // 刷新按钮点击事件
    refreshBtn.addEventListener('click', loadSecurityGroups);

    // 保存规则按钮点击事件
    document.getElementById('saveRules').addEventListener('click', saveRules);

    // 添加入站规则按钮点击事件
    document.getElementById('addIngressRule').addEventListener('click', () => {
        showRuleModal('ingress');
    });

    // 添加出站规则按钮点击事件
    document.getElementById('addEgressRule').addEventListener('click', () => {
        showRuleModal('egress');
    });

    // 保存规则按钮点击事件
    document.getElementById('saveRule').addEventListener('click', saveRule);

    // 监听协议选择变化
    document.getElementById('ruleProtocol').addEventListener('change', function() {
        document.getElementById('portConfig').style.display = 
            (this.value === '6' || this.value === '17') ? 'block' : 'none';
    });
});

// 加载安全组列表
async function loadSecurityGroups() {
    if (!currentTenantId) return;
    
    showLoading(true);
    try {
        const response = await fetch(`/network/api/security_groups/${currentTenantId}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '获取安全组列表失败');
        }
        const groups = await response.json();
        renderSecurityGroups(groups);
    } catch (error) {
        console.error('加载安全组失败:', error);
        showToast(error.message);
        clearSecurityGroupsTable();
    } finally {
        showLoading(false);
    }
}

// 渲染安全组列表
function renderSecurityGroups(groups) {
    const tbody = document.getElementById('securityGroupsTableBody');
    if (!groups || groups.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">暂无安全组</td></tr>';
        return;
    }

    tbody.innerHTML = groups.map(group => `
        <tr>
            <td>${group.display_name}</td>
            <td>${group.lifecycle_state}</td>
            <td>${new Date(group.time_created).toLocaleString()}</td>
            <td>
                <button class="btn btn-sm btn-info" onclick="viewRules('${group.id}')">
                    <i class="fas fa-list"></i> 管理规则
                </button>
            </td>
        </tr>
    `).join('');
}

// 查看/编辑规则
async function viewRules(securityGroupId) {
    showLoading(true);
    try {
        const response = await fetch(`/network/api/security_lists/${currentTenantId}/${securityGroupId}/rules`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '获取规则失败');
        }
        const rules = await response.json();
        currentSecurityGroup = { id: securityGroupId };
        currentRules = rules; 
        renderRules();
        const modal = new bootstrap.Modal(document.getElementById('rulesModal'));
        modal.show();
    } catch (error) {
        console.error('加载规则失败:', error);
        showToast(error.message);
    } finally {
        showLoading(false);
    }
}

// 渲染规则
function renderRules() {
    renderIngressRules();
    renderEgressRules();
}

// 渲染入站规则
function renderIngressRules() {
    const tbody = document.getElementById('ingressRulesTableBody');
    if (!currentRules.ingress_rules || currentRules.ingress_rules.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">暂无入站规则</td></tr>';
        return;
    }

    tbody.innerHTML = currentRules.ingress_rules.map((rule, index) => `
        <tr>
            <td>${rule.is_stateless ? '无状态' : '有状态'}</td>
            <td>${rule.source}</td>
            <td>
                ${getProtocolName(rule.protocol)}
                ${rule.tcp_options ? `<br>端口: ${formatPortRange(rule.tcp_options)}` : ''}
                ${rule.udp_options ? `<br>端口: ${formatPortRange(rule.udp_options)}` : ''}
            </td>
            <td>${rule.description || '-'}</td>
            <td>
                <button class="btn btn-sm btn-primary me-1" onclick="editRule('ingress', ${index})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteRule('ingress', ${index})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// 渲染出站规则
function renderEgressRules() {
    const tbody = document.getElementById('egressRulesTableBody');
    if (!currentRules.egress_rules || currentRules.egress_rules.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">暂无出站规则</td></tr>';
        return;
    }

    tbody.innerHTML = currentRules.egress_rules.map((rule, index) => `
        <tr>
            <td>${rule.is_stateless ? '无状态' : '有状态'}</td>
            <td>${rule.destination}</td>
            <td>
                ${getProtocolName(rule.protocol)}
                ${rule.tcp_options ? `<br>端口: ${formatPortRange(rule.tcp_options)}` : ''}
                ${rule.udp_options ? `<br>端口: ${formatPortRange(rule.udp_options)}` : ''}
            </td>
            <td>${rule.description || '-'}</td>
            <td>
                <button class="btn btn-sm btn-primary me-1" onclick="editRule('egress', ${index})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteRule('egress', ${index})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// 显示规则模态框
function showRuleModal(direction, editIndex = null) {
    const form = document.getElementById('ruleForm');
    form.reset();
    
    // 如果是编辑现有规则
    if (editIndex !== null) {
        const rule = currentRules[direction + '_rules'][editIndex];
        document.getElementById('ruleStateless').value = rule.is_stateless.toString();
        document.getElementById('ruleSource').value = direction === 'ingress' ? rule.source : rule.destination;
        document.getElementById('ruleProtocol').value = rule.protocol;
        document.getElementById('ruleDescription').value = rule.description || '';
        
        // 设置端口信息
        if (rule.tcp_options || rule.udp_options) {
            const options = rule.tcp_options || rule.udp_options;
            if (options.source_port_range) {
                document.getElementById('sourcePortMin').value = options.source_port_range.min;
                document.getElementById('sourcePortMax').value = options.source_port_range.max;
            }
            if (options.destination_port_range) {
                document.getElementById('destPortMin').value = options.destination_port_range.min;
                document.getElementById('destPortMax').value = options.destination_port_range.max;
            }
        }
    }
    
    // 显示/隐藏端口配置
    const protocol = document.getElementById('ruleProtocol').value;
    document.getElementById('portConfig').style.display = 
        (protocol === '6' || protocol === '17') ? 'block' : 'none';
    
    const modal = new bootstrap.Modal(document.getElementById('ruleModal'));
    document.getElementById('ruleModal').dataset.direction = direction;
    document.getElementById('ruleModal').dataset.editIndex = editIndex !== null ? editIndex : '';
    modal.show();
}

// 编辑规则
function editRule(direction, index) {
    showRuleModal(direction, index);
}

// 保存规则
function saveRule() {
    const direction = document.getElementById('ruleModal').dataset.direction;
    const editIndex = document.getElementById('ruleModal').dataset.editIndex;
    const protocol = document.getElementById('ruleProtocol').value;
    
    const rule = {
        is_stateless: document.getElementById('ruleStateless').value === 'true',
        protocol: protocol,
        description: document.getElementById('ruleDescription').value
    };

    // 设置源/目标
    if (direction === 'ingress') {
        rule.source = document.getElementById('ruleSource').value;
    } else {
        rule.destination = document.getElementById('ruleSource').value;
    }

    // 添加端口配置
    if (protocol === '6' || protocol === '17') {
        const portOptions = {
            source_port_range: null,
            destination_port_range: null
        };

        const sourcePortMin = document.getElementById('sourcePortMin').value;
        const sourcePortMax = document.getElementById('sourcePortMax').value;
        const destPortMin = document.getElementById('destPortMin').value;
        const destPortMax = document.getElementById('destPortMax').value;

        if (sourcePortMin && sourcePortMax) {
            portOptions.source_port_range = {
                min: parseInt(sourcePortMin),
                max: parseInt(sourcePortMax)
            };
        }

        if (destPortMin && destPortMax) {
            portOptions.destination_port_range = {
                min: parseInt(destPortMin),
                max: parseInt(destPortMax)
            };
        }

        if (protocol === '6') {
            rule.tcp_options = portOptions;
        } else {
            rule.udp_options = portOptions;
        }
    }

    // 更新或添加规则
    if (editIndex !== '') {
        currentRules[direction + '_rules'][editIndex] = rule;
    } else {
        if (!currentRules[direction + '_rules']) {
            currentRules[direction + '_rules'] = [];
        }
        currentRules[direction + '_rules'].push(rule);
    }

    renderRules();
    bootstrap.Modal.getInstance(document.getElementById('ruleModal')).hide();
}

// 删除规则
function deleteRule(direction, index) {
    if (confirm('确定要删除此规则吗？')) {
        currentRules[direction + '_rules'].splice(index, 1);
        renderRules();
    }
}

// 保存所有规则
async function saveRules() {
    if (!currentSecurityGroup) return;

    showLoading(true);
    try {
        const response = await fetch(`/network/api/security_lists/${currentTenantId}/${currentSecurityGroup.id}/rules`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(currentRules)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '保存规则失败');
        }

        showToast('规则保存成功', 'success');
        bootstrap.Modal.getInstance(document.getElementById('rulesModal')).hide();
    } catch (error) {
        console.error('保存规则失败:', error);
        showToast(error.message);
    } finally {
        showLoading(false);
    }
}

// 获取协议名称
function getProtocolName(protocol) {
    const protocols = {
        'all': '全部',
        '6': 'TCP',
        '17': 'UDP',
        '1': 'ICMP'
    };
    return protocols[protocol] || protocol;
}

// 显示/隐藏加载指示器
function showLoading(show) {
    document.getElementById('loading-indicator').style.display = show ? 'block' : 'none';
}

// 清空安全组列表
function clearSecurityGroupsTable() {
    document.getElementById('securityGroupsTableBody').innerHTML = 
        '<tr><td colspan="4" class="text-center">请选择租户</td></tr>';
}

// 显示提示消息
function showToast(message, type = 'error') {
    const toast = document.getElementById('toast');
    toast.querySelector('.toast-body').textContent = message;
    toast.classList.remove('bg-success', 'bg-danger');
    toast.classList.add(type === 'success' ? 'bg-success' : 'bg-danger');
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// 格式化端口范围显示
function formatPortRange(options) {
    const ranges = [];
    if (options.source_port_range) {
        ranges.push(`源端口: ${options.source_port_range.min}-${options.source_port_range.max}`);
    }
    if (options.destination_port_range) {
        ranges.push(`目标端口: ${options.destination_port_range.min}-${options.destination_port_range.max}`);
    }
    return ranges.join(', ') || '所有端口';
}
