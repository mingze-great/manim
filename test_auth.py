#!/usr/bin/env python3
"""Test script to verify admin API access"""

from jose import jwt
from datetime import datetime, timedelta

# Load settings
SECRET_KEY = 'your-dev-secret-key-change-this!'
ALGORITHM = 'HS256'

def create_test_token(username: str):
    """创建测试token模拟admin用户"""
    to_encode = {"sub": username}
    expire = datetime.utcnow() + timedelta(hours=24)  # 24小时过期
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

if __name__ == "__main__":
    # 获取测试token
    token = create_test_token("admin")
    print(f"Admin Test Token: {token}")