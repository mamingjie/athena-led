import requests
import json
import time
import logging
from flask import Flask, jsonify

# 配置日志
logging.basicConfig(
    filename='/var/log/network_speed_monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('network_speed_monitor')

# API 配置
BASE_URL = 'http://10.0.1.1/cgi-bin/luci'
SPEED_API = f'{BASE_URL}/istore/u/network/statistics/'
LOGIN_API = f'{BASE_URL}/'

# 认证信息
USERNAME = 'root'
PASSWORD = 'password'

# Flask 应用
app = Flask(__name__)
cookie = None
request_flag = False

def login():
    """登录获取 Cookie，处理 302 重定向"""
    global cookie
    try:
        logger.info("尝试登录获取 Cookie")
        
        # 使用 application/x-www-form-urlencoded 格式
        data = {
            'luci_username': USERNAME,
            'luci_password': PASSWORD
        }
        
        # 创建会话对象，用于跟踪 Cookie
        session = requests.Session()
        
        # 发送登录请求，禁用自动重定向
        response = session.post(LOGIN_API, data=data, allow_redirects=False)
        
        # 处理重定向
        if response.status_code == 302:
            logger.info(f"登录成功，收到重定向响应: {response.headers.get('Location')}")
            
            # 获取初始登录后的 Cookie
            initial_cookies = session.cookies.get_dict()
            logger.debug(f"初始 Cookie: {initial_cookies}")
            
            # 手动处理重定向
            redirect_url = response.headers.get('Location')
            if redirect_url:
                # 如果重定向 URL 是相对路径，构建完整 URL
                if not redirect_url.startswith('http'):
                    redirect_url = BASE_URL + redirect_url if redirect_url.startswith('/') else BASE_URL + '/' + redirect_url
                
                logger.info(f"跟随重定向到: {redirect_url}")
                
                # 发送重定向请求，携带初始 Cookie
                redirect_response = session.get(redirect_url)
                
                # 获取最终的 Cookie
                final_cookies = session.cookies.get_dict()
                logger.debug(f"最终 Cookie: {final_cookies}")
                
                # 保存 Cookie
                cookie = session.cookies
                logger.info("成功获取并保存 Cookie")
                return True
            else:
                logger.error("重定向响应中缺少 Location 头")
                return False
        elif response.status_code == 200:
            # 某些情况下可能直接返回 200
            logger.info("登录成功，直接返回 200")
            cookie = session.cookies
            return True
        else:
            logger.error(f"登录失败，状态码: {response.status_code}, 响应: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"登录过程发生异常: {str(e)}")
        return False

def get_network_speed():
    """获取网络速度数据"""
    global cookie
    global request_flag
    download_str = '0B'
    upload_str = '0B'
    try:
        # 先尝试使用现有 Cookie 请求数据
        response = requests.get(SPEED_API, cookies=cookie)
        
        # 检查是否需要认证
        if response.status_code == 200:
            data = response.json()
            if 'success' in data and data['success'] == -1001:
                logger.info("认证失败，需要重新登录")
                # 登录获取新 Cookie
                login()
            # 检查是否包含预期的数据结构
            if 'result' in data and 'items' in data['result'] and len(data['result']['items']) > 0:
                # 获取最后一条记录
                last_item = data['result']['items'][-1]
                download_speed = last_item['downloadSpeed']
                upload_speed = last_item['uploadSpeed']
                
                # 转换单位
                download_str = convert_speed(download_speed)
                upload_str = convert_speed(upload_speed)
            else:
                logger.warning(f"返回数据格式不符合预期: {response.text}")
        else:
            logger.error(f"接口返回未知错误: {response.text}")
    except Exception as e:
        logger.error(f"获取网络速度时发生异常: {str(e)}")

    if request_flag:
        request_flag = False
        return f"<{upload_str}"

    request_flag = True
    return f">{download_str}"

def convert_speed(speed_bytes):
    """将字节速度转换为人类可读的格式"""
    units = ['B', 'K', 'M', 'G']
    unit_index = 0
    
    while speed_bytes >= 1024 and unit_index < len(units) - 1:
        speed_bytes /= 1024
        unit_index += 1
    
    # 保留一位小数
    speed_str = f"{int(speed_bytes)}" if int(speed_bytes) > 99 else f"{speed_bytes:.1f}"
    return f"{speed_str}{units[unit_index]}"

@app.route('/api/network/speed', methods=['GET'])
def api_network_speed():
    """API 接口：获取网络速度"""
    return get_network_speed()

if __name__ == '__main__':
    # 启动时先登录获取 Cookie
    login()
    # 启动 Flask 应用
    app.run(host='0.0.0.0', port=8000)
