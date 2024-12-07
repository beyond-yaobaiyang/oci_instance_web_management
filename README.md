# OCI Instance web Management

## 🌐 项目概述

本项目是一个现代化、用户友好的 Oracle Cloud Infrastructure (OCI) 实例管理系统，旨在提供简单、高效的多租户实例监控和管理解决方案。

## ✨ 主要特性

- 多租户支持
- 实例的基础操作
- 详细实例信息展示
- 跨区域实例管理
- 直观的Web界面

## 🚀 快速开始

### 1. 准备环境
```bash
# 克隆项目
git clone https://github.com/your_username/oci-management-platform.git
cd oci-management-platform

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置租户信息
编辑 `config.yaml`，添加您的 OCI 租户配置：

```yaml
tenants:
  - name: my_tenant
    user: ocid1.user.oc1..example
    tenancy: ocid1.tenancy.oc1..example
    fingerprint: "ab:cd:ef:12:34:56"
    key_file: "/path/to/your/private_key.pem"
    regions:
      - "us-phoenix-1"
```

### 3. 启动应用
```bash
python app.py
```

浏览器访问 `http://你的ip:5000`

## 🔧 配置说明
- `name`：租户的唯一标识
- `user`：OCI 用户 OCID
- `tenancy`：租户 OCID
- `fingerprint`：API 密钥指纹
- `key_file`：私钥文件路径
- `regions`：可用区域列表

## 🔒 安全建议

1. 使用强密码
2. 定期更新 OCI API 密钥

## 🖥️ 运行应用

```bash
python app.py
```

访问 `http://localhost:5000` 查看管理平台

## 🔒 安全性

- 支持多租户隔离
- 遵循最小权限原则
- 敏感信息加密存储

## 🔍 功能列表

-  实例列表展示
-  实例详情查看
-  多区域多租户支持
-  实例启动/停止/重启
-  实例信息的查询


## 📄 许可证

本项目基于 GNU General Public License v3.0 (GPL-3.0) 许可发布


**免责声明**：本项目为开源项目，不对使用过程中的任何损失负责。使用前请仔细阅读并遵守 Oracle Cloud Infrastructure 的使用条款。
