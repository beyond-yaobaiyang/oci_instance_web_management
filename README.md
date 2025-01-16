# OCI Instance web Management

## 项目概述

本项目是一个基于 Oracle Cloud Infrastructure (OCI) python sdk的实例管理系统，旨在提供简单、高效的多租户实例管理解决方案。

## 快速开始

### 1. 准备环境
```bash
# 克隆项目
git clone https://github.com/beyond-yaobaiyang/oci_instance_web_management
cd oci_instance_web_management

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置租户信息
编辑 `config.yaml`，添加您的 OCI 租户配置：
users 下面是面板登录信息
```yaml

auth:
  users:
  - password: admin #密码
    role: admin
    username: admin #用户名

tenants:
- compartment_id: ocid1.tenancy.
  fingerprint: e0:fa:a8:be:c5
  key_file: c:\U
  name: 配置1
  region: ap-chuncheon-1
  tenancy: ocid1.tenancy.
  user_ocid: ocid1.user.
- compartment_id: ocid1.tenancy.
  fingerprint: e0:fa:a8:b
  key_file: c:\Us
  name: 配置2
  region: ap-sigapore-1
  tenancy: ocid1.tenancy.
  user_ocid: ocid1.user.

```
### 3.启动应用(注意启动时需要保证config.yaml配置完全)
python app.py
浏览器访问 `http://你的ip:5000`

## 🔧 配置说明
- `name`：租户的唯一标识
- `user`：OCI 用户 OCID
- `tenancy`：租户 OCID
- `fingerprint`：API 密钥指纹
- `key_file`：私钥文件路径
- `region`：可用区域
- `compartment_id` 区间ID(直接填写租户OCID即可)

## 🔒 安全建议

1. 使用强密码
2. 定期更新 OCI API 密钥

## 🔍 功能列表
### 1.面板操作
  - 查看租户信息配置列表
  - 修改面板密码
### 2. 实例操作
- 用户可以对实例执行以下操作：
  - **启动实例**：启动处于停止状态的实例。
  - **停止实例**：停止正在运行的实例。
  - **重启实例**：重启正在运行的实例。
  - **终止实例**：永久删除实例。
  - **实例的创建**：可以创建实例
    - 支持选择ubuntu和centos7的镜像
    - 支持ssh root用户登录(目前不可用户指定，一般在实例创建完成后弹出root登录密码)
  - **附加的引导卷**
    - 分离
    - 附加
    - 调整大小（只增不减与官方规则一致）
    - 调整硬盘VPU性能
  - **附加块存储**
    - 分离
    - 附加
    - 调整大小（只增不减与官方规则一致）
    - 调整硬盘VPU性能
- 每次操作后，实例状态会实时更新，用户可以看到最新的状态反馈。
### 3. 公网IP管理 （执行更换后需要刷新实例列表）
- 支持更换实例的公网IP地址。
- 用户可以在实例详情中直接更换公网IP。


## 📄 许可证

本项目基于 GNU General Public License v3.0 (GPL-3.0) 许可发布


**免责声明**：本项目为开源项目，不对使用过程中的任何损失负责。使用前请仔细阅读并遵守 Oracle Cloud Infrastructure 的使用条款。
