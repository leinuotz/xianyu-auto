<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Flask-2.0+-green.svg" alt="Flask">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg" alt="Platform">
</p>

<h1 align="center">闲鱼自动收发货工具</h1>

<p align="center">
  <b>自动化管理闲鱼订单，提升卖家效率</b>
</p>

---

## 声明

> 因作者写作能力有限，本项目的发布页面和介绍文档使用了 AI 辅助完成。

---

## 项目介绍

这是一个开源的闲鱼自动收发货管理工具，帮助闲鱼卖家自动化处理订单，支持自动发货、自动收货和自动发送消息功能。采用现代化的 Web 界面，操作简单直观。

### 主要功能

| 功能 | 描述 | 状态 |
|------|------|------|
| 商品管理 | 查看和管理发布的商品列表 | 已完成 |
| 自动发货 | 自动处理待发货订单 | 已完成 |
| 自动收货 | 自动确认收货（可设置延迟） | 已完成 |
| 自动消息 | 发货后自动发送消息给买家 | 已完成 |
| Web UI | 美观的网页管理界面 | 已完成 |
| 响应式设计 | 支持桌面和移动设备 | 已完成 |

---

## 快速开始

### 环境要求

- Python 3.9+
- pip
- 现代浏览器（Chrome/Firefox/Edge）

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/leinuotz/xianyu-auto.git
cd xianyu-auto

# 2. 安装依赖
pip install -r requirements.txt

# 3. 复制配置文件模板
cp config/config.example.json config/config.json

# 4. 编辑配置文件，填入你的闲鱼 Cookie
# 详见下方"获取 Cookie"说明
nano config/config.json

# 5. 运行
python web_app.py

# 6. 打开浏览器访问
# http://localhost:5000
```

### Linux 系统服务部署（推荐）

```bash
# 复制服务文件
sudo cp xianyu-auto.service /etc/systemd/system/

# 编辑服务文件，修改工作目录和用户名
sudo nano /etc/systemd/system/xianyu-auto.service

# 启用并启动服务
sudo systemctl enable xianyu-auto
sudo systemctl start xianyu-auto

# 查看状态
sudo systemctl status xianyu-auto
```

---

## 配置说明

### 获取 Cookie

> 重要：Cookie 包含敏感信息，请勿泄露或提交到 GitHub

1. 使用 Chrome/Edge 浏览器登录 [闲鱼网页版](https://www.goofish.com)
2. 按 F12 打开开发者工具
3. 切换到 Network/网络 标签
4. 按 F5 刷新页面
5. 点击任意一个请求（如 publishItemList）
6. 在右侧 Headers 中找到 Cookie
7. 复制完整的 Cookie 值
8. 粘贴到 config/config.json 中

### 配置文件详解

```json
{
  "xianyu": {
    "cookie": "你的闲鱼 Cookie（必填）"
  },
  "auto_delivery": {
    "enabled": true,
    "check_interval": 300,
    "items": [],
    "send_message": true,
    "message_template": "...",
    "custom_message": "..."
  },
  "auto_receive": {
    "enabled": true,
    "check_interval": 600,
    "delay_hours": 24
  }
}
```

---

## 消息模板变量

| 变量 | 说明 | 示例 |
|------|------|------|
| item_title | 商品标题 | iPhone 14 Pro |
| item_price | 商品价格 | 5999.00 |
| order_id | 订单号 | 1234567890 |
| buyer_name | 买家昵称 | 买家小王 |
| custom_message | 自定义内容 | 快递正在运输中 |

### 默认消息模板

```
亲，您的订单已发货啦！

订单信息：
- 商品：{item_title}
- 价格：{item_price}
- 订单号：{order_id}

{custom_message}

如有问题请随时联系，祝您购物愉快！
```

---

## 安全提示

- Cookie 安全：Cookie 包含敏感信息，请勿泄露给他人
- 使用风险：自动化工具有可能触发平台风控，请谨慎使用
- 频率控制：建议设置合理的检查间隔（300秒以上），避免频繁请求
- 备份配置：定期备份 config/config.json 文件

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境搭建

```bash
# 克隆项目
git clone https://github.com/leinuotz/xianyu-auto.git
cd xianyu-auto

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行
python web_app.py
```

---

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

---

## 免责声明

本项目仅供学习交流使用，使用本项目产生的任何后果由使用者自行承担。请遵守闲鱼平台的使用规则和相关法律法规。

---

<p align="center">
  Made by Leinuo
</p>

<p align="center">
  <a href="https://github.com/leinuotz/xianyu-auto/stargazers">Star</a>
  ·
  <a href="https://github.com/leinuotz/xianyu-auto/issues">Issue</a>
  ·
  <a href="https://github.com/leinuotz/xianyu-auto/fork">Fork</a>
</p>
