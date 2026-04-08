#!/usr/bin/env python3
"""Test script to get actual token from server config and test access"""

import sys
import os
sys.path.insert(0, '/opt/manim-dev/backend')

os.chdir('/opt/manim-dev/backend')

# Import and get settings to use real SECRET
from app.config import get_settings
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

def generate_and_test_token():
    settings = get_settings()
    print(f"Secret key length: {len(settings.SECRET_KEY)}")
    
    # Create a valid admin token
    to_encode = {"sub": "admin"}
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # Test decoding
    try:
        decoded = jwt.decode(encoded_jwt, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        print(f"Generated and validated token: {encoded_jwt[:50]}...")
        print(f"Decoded: {decoded}")
    except Exception as e:
        print(f"Failed to validate: {e}")
        return None

    return encoded_jwt

if __name__ == "__main__":
    token = generate_and_test_token()
    if token:
        print("\nTo test the API, run:")
        print(f"curl -H 'Authorization: Bearer {token}' http://localhost:8001/api/admin/article-categories")