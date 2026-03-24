#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
闲鱼自动收发货工具 - Web UI 版本 (带自动消息功能)
"""

import os
import sys
import json
import time
import logging
import threading
import requests
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Flask, render_template, request, jsonify

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/xianyu-auto/logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='/opt/xianyu-auto/templates', static_folder='/opt/xianyu-auto/static')
app.secret_key = 'xianyu-auto-secret-key-2024'

class XianyuAPI:
    """闲鱼 API 封装"""
    
    BASE_URL = "https://www.goofish.com"
    API_URL = "https://www.goofish.com/api"
    
    def __init__(self, cookie: str = ""):
        self.cookie = cookie
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cookie': cookie,
            'Referer': 'https://www.goofish.com/'
        }
    
    def get_my_items(self, page: int = 1, page_size: int = 20) -> List[Dict]:
        """获取我发布的商品列表"""
        try:
            url = f"{self.API_URL}/item/v2/publishItemList"
            params = {'page': page, 'pageSize': page_size}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'data' in data:
                    items = data['data'].get('items', [])
                    return items
                else:
                    logger.error(f"获取商品列表失败: {data.get('message', '未知错误')}")
                    return []
            else:
                logger.error(f"请求失败: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"获取商品列表异常: {e}")
            return []
    
    def get_orders(self, status: str = "wait_send") -> List[Dict]:
        """获取订单列表"""
        try:
            # 闲鱼订单列表接口
            url = f"{self.API_URL}/order/v2/orderList"
            params = {
                'status': status,  # wait_send: 待发货, wait_receive: 待收货
                'page': 1,
                'pageSize': 20
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'data' in data:
                    orders = data['data'].get('orders', [])
                    return orders
            return []
            
        except Exception as e:
            logger.error(f"获取订单列表异常: {e}")
            return []
    
    def send_message(self, order_id: str, message: str) -> bool:
        """发送消息给买家"""
        try:
            # 闲鱼消息接口
            url = f"{self.API_URL}/message/send"
            
            data = {
                'orderId': order_id,
                'content': message,
                'type': 'text'
            }
            
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logger.info(f"消息发送成功: order_id={order_id}")
                    return True
                else:
                    logger.error(f"消息发送失败: {result.get('message')}")
                    return False
            else:
                logger.error(f"消息发送请求失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return False
    
    def confirm_delivery(self, order_id: str) -> bool:
        """确认发货"""
        try:
            url = f"{self.API_URL}/order/confirmDelivery"
            
            data = {'orderId': order_id}
            
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logger.info(f"发货成功: order_id={order_id}")
                    return True
            return False
            
        except Exception as e:
            logger.error(f"确认发货异常: {e}")
            return False

class MessageTemplate:
    """消息模板处理"""
    
    @staticmethod
    def render(template: str, variables: Dict[str, str]) -> str:
        """渲染消息模板"""
        result = template
        for key, value in variables.items():
            placeholder = '{' + key + '}'
            result = result.replace(placeholder, str(value))
        return result
    
    @staticmethod
    def get_default_template() -> str:
        """获取默认消息模板"""
        return """亲，您的订单已发货啦！🎉

订单信息：
- 商品：{item_title}
- 价格：{item_price}
- 订单号：{order_id}

{custom_message}

如有问题请随时联系，祝您购物愉快！😊"""

class XianyuAuto:
    """闲鱼自动收发货工具主类"""
    
    def __init__(self):
        self.config = self.load_config()
        self.running = False
        self.thread = None
        self.last_check = None
        self.status_msg = "已停止"
        self.api = XianyuAPI(self.config.get('xianyu', {}).get('cookie', ''))
        self.my_items = []
        self.auto_delivery_items = set()
        self.processed_orders = set()  # 已处理的订单，避免重复发货
        
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = '/opt/xianyu-auto/config/config.json'
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self.create_default_config()
    
    def save_config(self, config: Dict[str, Any]):
        """保存配置文件"""
        config_path = '/opt/xianyu-auto/config/config.json'
        os.makedirs('/opt/xianyu-auto/config', exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        self.config = config
        self.api.cookie = config.get('xianyu', {}).get('cookie', '')
        self.api.headers['Cookie'] = self.api.cookie
    
    def create_default_config(self) -> Dict[str, Any]:
        """创建默认配置"""
        default_config = {
            "xianyu": {"cookie": "", "token": ""},
            "auto_delivery": {
                "enabled": True,
                "check_interval": 300,
                "items": [],
                "send_message": True,  # 发货后是否发送消息
                "message_template": MessageTemplate.get_default_template(),
                "custom_message": "快递正在运输中，请注意查收~"  # 自定义消息内容
            },
            "auto_receive": {
                "enabled": True,
                "check_interval": 600,
                "delay_hours": 24
            },
            "notification": {"enabled": False, "webhook_url": ""}
        }
        self.save_config(default_config)
        logger.info("已创建默认配置文件")
        return default_config
    
    def refresh_items(self) -> List[Dict]:
        """刷新商品列表"""
        items = self.api.get_my_items()
        self.my_items = items
        
        auto_items = self.config.get('auto_delivery', {}).get('items', [])
        self.auto_delivery_items = set(auto_items)
        
        for item in items:
            item_id = item.get('itemId') or item.get('id')
            item['auto_delivery'] = item_id in self.auto_delivery_items
        
        logger.info(f"刷新商品列表: 获取到 {len(items)} 个商品")
        return items
    
    def toggle_auto_delivery(self, item_id: str, enable: bool) -> bool:
        """切换商品自动发货状态"""
        try:
            auto_items = self.config.get('auto_delivery', {}).get('items', [])
            
            if enable:
                if item_id not in auto_items:
                    auto_items.append(item_id)
                    logger.info(f"商品 {item_id} 已开启自动发货")
            else:
                if item_id in auto_items:
                    auto_items.remove(item_id)
                    logger.info(f"商品 {item_id} 已关闭自动发货")
            
            self.config['auto_delivery']['items'] = auto_items
            self.save_config(self.config)
            self.auto_delivery_items = set(auto_items)
            return True
            
        except Exception as e:
            logger.error(f"切换自动发货状态失败: {e}")
            return False
    
    def process_orders(self):
        """处理待发货订单"""
        try:
            # 获取待发货订单
            orders = self.api.get_orders(status="wait_send")
            
            for order in orders:
                order_id = order.get('orderId') or order.get('id')
                item_id = order.get('itemId')
                
                # 检查是否已经处理过
                if order_id in self.processed_orders:
                    continue
                
                # 检查商品是否开启了自动发货
                if item_id not in self.auto_delivery_items:
                    continue
                
                logger.info(f"发现待发货订单: {order_id}, 商品: {item_id}")
                
                # 执行发货
                if self.api.confirm_delivery(order_id):
                    self.processed_orders.add(order_id)
                    
                    # 发送消息（如果开启）
                    if self.config.get('auto_delivery', {}).get('send_message', True):
                        self.send_delivery_message(order, order_id)
                else:
                    logger.error(f"发货失败: {order_id}")
                    
        except Exception as e:
            logger.error(f"处理订单异常: {e}")
    
    def send_delivery_message(self, order: Dict, order_id: str):
        """发送发货消息"""
        try:
            template = self.config.get('auto_delivery', {}).get('message_template', '')
            custom_msg = self.config.get('auto_delivery', {}).get('custom_message', '')
            
            # 准备变量
            variables = {
                'item_title': order.get('itemTitle', '商品'),
                'item_price': order.get('price', '未知'),
                'order_id': order_id,
                'buyer_name': order.get('buyerName', '买家'),
                'custom_message': custom_msg
            }
            
            # 渲染模板
            message = MessageTemplate.render(template, variables)
            
            # 发送消息
            if self.api.send_message(order_id, message):
                logger.info(f"发货消息已发送: {order_id}")
            else:
                logger.error(f"发货消息发送失败: {order_id}")
                
        except Exception as e:
            logger.error(f"发送发货消息异常: {e}")
    
    def start(self):
        """启动自动处理"""
        if not self.running:
            self.running = True
            self.status_msg = "运行中"
            self.thread = threading.Thread(target=self.run_loop)
            self.thread.daemon = True
            self.thread.start()
            logger.info("自动处理已启动")
            return True
        return False
    
    def stop(self):
        """停止自动处理"""
        if self.running:
            self.running = False
            self.status_msg = "已停止"
            logger.info("自动处理已停止")
            return True
        return False
    
    def run_loop(self):
        """主运行循环"""
        logger.info("=== 闲鱼自动收发货工具启动 ===")
        
        while self.running:
            try:
                self.last_check = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.status_msg = f"检查中... {self.last_check}"
                
                # 刷新商品列表
                self.refresh_items()
                
                # 处理订单
                if self.config.get('auto_delivery', {}).get('enabled', True):
                    self.process_orders()
                
                self.status_msg = f"等待中... 最后检查: {self.last_check}"
                
                # 休眠
                sleep_time = self.config.get('auto_delivery', {}).get('check_interval', 300)
                for i in range(sleep_time):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"运行出错: {e}")
                self.status_msg = f"错误: {str(e)}"
                time.sleep(60)

# 创建全局实例
xianyu_app = XianyuAuto()

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    config = xianyu_app.config.copy()
    if config.get('xianyu', {}).get('cookie'):
        cookie = config['xianyu']['cookie']
        config['xianyu']['cookie'] = cookie[:20] + '...' if len(cookie) > 20 else '***'
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        new_config = request.json
        xianyu_app.save_config(new_config)
        logger.info("配置已更新")
        return jsonify({"success": True, "message": "配置已保存"})
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/items', methods=['GET'])
def get_items():
    """获取商品列表"""
    try:
        items = xianyu_app.refresh_items()
        return jsonify({
            "success": True,
            "items": items,
            "total": len(items),
            "auto_delivery_count": len(xianyu_app.auto_delivery_items)
        })
    except Exception as e:
        logger.error(f"获取商品列表失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/items/<item_id>/auto-delivery', methods=['POST'])
def toggle_item_auto_delivery(item_id):
    """切换商品自动发货状态"""
    try:
        data = request.json
        enable = data.get('enable', False)
        
        success = xianyu_app.toggle_auto_delivery(item_id, enable)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"已{'开启' if enable else '关闭'}自动发货",
                "item_id": item_id,
                "auto_delivery": enable
            })
        else:
            return jsonify({"success": False, "message": "操作失败"}), 500
            
    except Exception as e:
        logger.error(f"切换自动发货状态失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/start', methods=['POST'])
def start_service():
    """启动服务"""
    if xianyu_app.start():
        return jsonify({"success": True, "message": "服务已启动"})
    return jsonify({"success": False, "message": "服务已经在运行"})

@app.route('/api/stop', methods=['POST'])
def stop_service():
    """停止服务"""
    if xianyu_app.stop():
        return jsonify({"success": True, "message": "服务已停止"})
    return jsonify({"success": False, "message": "服务已经停止"})

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取状态"""
    return jsonify({
        "running": xianyu_app.running,
        "status": xianyu_app.status_msg,
        "last_check": xianyu_app.last_check,
        "auto_delivery_items": len(xianyu_app.auto_delivery_items),
        "total_items": len(xianyu_app.my_items)
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取日志"""
    try:
        lines = request.args.get('lines', 100, type=int)
        log_path = '/opt/xianyu-auto/logs/app.log'
        
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return jsonify({
                    "success": True,
                    "logs": ''.join(all_lines[-lines:])
                })
        else:
            return jsonify({"success": True, "logs": "暂无日志"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/preview-message', methods=['POST'])
def preview_message():
    """预览消息模板"""
    try:
        data = request.json
        template = data.get('template', '')
        custom_msg = data.get('custom_message', '')
        
        # 使用示例数据预览
        variables = {
            'item_title': '示例商品标题',
            'item_price': '¥99.00',
            'order_id': '1234567890',
            'buyer_name': '买家昵称',
            'custom_message': custom_msg
        }
        
        message = MessageTemplate.render(template, variables)
        
        return jsonify({
            "success": True,
            "preview": message
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

def create_templates():
    """创建 HTML 模板"""
    os.makedirs('/opt/xianyu-auto/templates', exist_ok=True)
    os.makedirs('/opt/xianyu-auto/static', exist_ok=True)
    logger.info("Web UI 模板目录已创建")

if __name__ == '__main__':
    create_templates()
    logger.info("启动 Web UI 服务...")
    app.run(host='0.0.0.0', port=5000, debug=False)
