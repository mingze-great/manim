import os
import base64
from cryptography.fernet import Fernet
from app.config import get_settings

settings = get_settings()

# 从配置获取加密密钥，如果没有则生成一个（生产环境应该配置固定密钥）
ENCRYPTION_KEY = settings.API_KEY_ENCRYPTION_KEY or Fernet.generate_key()
_fernet = Fernet(ENCRYPTION_KEY)


def encrypt_api_key(api_key: str) -> str:
    """加密 API key"""
    if not api_key:
        return ""
    encrypted = _fernet.encrypt(api_key.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """解密 API key"""
    if not encrypted_key:
        return ""
    try:
        decoded = base64.b64decode(encrypted_key.encode())
        decrypted = _fernet.decrypt(decoded)
        return decrypted.decode()
    except Exception:
        return ""


def is_valid_api_key_format(api_key: str) -> bool:
    """检查 API key 格式是否有效（非空且长度合理）"""
    if not api_key:
        return False
    return len(api_key) >= 10 and len(api_key) <= 200