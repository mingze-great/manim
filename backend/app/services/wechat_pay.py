import hashlib
import time
import random
import string
import xml.etree.ElementTree as ET
from typing import Optional
import requests
from app.config import get_settings

settings = get_settings()


class WeChatPayService:
    """微信支付服务"""
    
    BASE_URL = "https://api.mch.weixin.qq.com/pay/unifiedorder"
    QUERY_URL = "https://api.mch.weixin.qq.com/pay/orderquery"
    
    def __init__(self):
        self.mch_id = settings.WX_MCH_ID
        self.app_id = settings.WX_APP_ID
        self.api_key = settings.WX_API_KEY
        self.notify_url = settings.WX_NOTIFY_URL
    
    def _generate_nonce_str(self, length: int = 32) -> str:
        """生成随机字符串"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def _generate_sign(self, params: dict) -> str:
        """生成签名"""
        sorted_params = sorted([(k, v) for k, v in params.items() if k and v])
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
        sign_str += f"&key={self.api_key}"
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
    
    def _dict_to_xml(self, params: dict) -> str:
        """字典转XML"""
        root = ET.Element('xml')
        for key, value in params.items():
            child = ET.SubElement(root, key)
            child.text = str(value)
        return ET.tostring(root, encoding='utf-8').decode('utf-8')
    
    def _xml_to_dict(self, xml_str: str) -> dict:
        """XML转字典"""
        root = ET.fromstring(xml_str)
        return {child.tag: child.text for child in root}
    
    def create_unified_order(
        self,
        order_id: str,
        amount: int,
        description: str,
        openid: Optional[str] = None
    ) -> dict:
        """
        创建统一下单
        amount: 金额，单位为分
        """
        params = {
            'appid': self.app_id,
            'mch_id': self.mch_id,
            'nonce_str': self._generate_nonce_str(),
            'body': description,
            'out_trade_no': order_id,
            'total_fee': amount,
            'spbill_create_ip': '8.136.60.253',
            'notify_url': self.notify_url,
            'trade_type': 'NATIVE',  # NATIVE扫码支付
        }
        
        if openid:
            params['openid'] = openid
            params['trade_type'] = 'JSAPI'
        
        params['sign'] = self._generate_sign(params)
        
        xml_data = self._dict_to_xml(params)
        
        try:
            response = requests.post(
                self.BASE_URL,
                data=xml_data.encode('utf-8'),
                headers={'Content-Type': 'application/xml'},
                timeout=10
            )
            
            result = self._xml_to_dict(response.text)
            
            if result.get('return_code') == 'SUCCESS' and result.get('result_code') == 'SUCCESS':
                return {
                    'success': True,
                    'code_url': result.get('code_url'),
                    'prepay_id': result.get('prepay_id'),
                    'trade_type': result.get('trade_type'),
                }
            else:
                return {
                    'success': False,
                    'error': result.get('err_code_des', result.get('return_msg', 'Unknown error')),
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    def query_order(self, order_id: str) -> dict:
        """查询订单状态"""
        params = {
            'appid': self.app_id,
            'mch_id': self.mch_id,
            'out_trade_no': order_id,
            'nonce_str': self._generate_nonce_str(),
        }
        params['sign'] = self._generate_sign(params)
        
        xml_data = self._dict_to_xml(params)
        
        try:
            response = requests.post(
                self.QUERY_URL,
                data=xml_data.encode('utf-8'),
                headers={'Content-Type': 'application/xml'},
                timeout=10
            )
            
            result = self._xml_to_dict(response.text)
            
            if result.get('return_code') == 'SUCCESS':
                trade_state = result.get('trade_state', 'UNKNOWN')
                return {
                    'success': True,
                    'trade_state': trade_state,
                    'transaction_id': result.get('transaction_id'),
                    'trade_state_desc': result.get('trade_state_desc'),
                }
            else:
                return {
                    'success': False,
                    'error': result.get('return_msg', 'Unknown error'),
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    def verify_notify(self, params: dict) -> bool:
        """验证回调签名"""
        sign = params.get('sign')
        if not sign:
            return False
        
        calculated_sign = self._generate_sign(params)
        return sign == calculated_sign


def get_wechat_pay_service() -> WeChatPayService:
    return WeChatPayService()
