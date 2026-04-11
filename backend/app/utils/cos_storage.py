import os
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Optional
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
from app.config import get_settings

settings = get_settings()


class COSStorage:
    def __init__(self):
        if not settings.COS_SECRET_ID or not settings.COS_SECRET_KEY:
            self.enabled = False
            self.client = None
            return
        
        self.enabled = settings.COS_ENABLE
        self.bucket = settings.COS_BUCKET
        self.region = settings.COS_REGION
        self.domain = settings.COS_DOMAIN
        
        config = CosConfig(
            Region=self.region,
            SecretId=settings.COS_SECRET_ID,
            SecretKey=settings.COS_SECRET_KEY,
        )
        self.client = CosS3Client(config)
    
    def upload_video(self, local_path: str, remote_key: str) -> Optional[str]:
        if not self.enabled or not self.client:
            return None

    def upload_image(self, body: bytes, remote_key: str, content_type: str = 'image/png') -> Optional[str]:
        if not self.enabled or not self.client:
            return None

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Body=body,
                Key=remote_key,
                ContentType=content_type,
            )
            return remote_key
        except Exception as e:
            print(f"[COS] Image upload failed: {e}")
            return None

    def get_public_url(self, key: str) -> Optional[str]:
        if not key:
            return None
        presigned = self.generate_presigned_url(key, expires=3600 * 24 * 365)
        if presigned:
            return presigned
        if self.domain:
            return f"{self.domain.rstrip('/')}/{key.lstrip('/')}"
        return None
        
        try:
            with open(local_path, 'rb') as fp:
                self.client.put_object(
                    Bucket=self.bucket,
                    Body=fp,
                    Key=remote_key,
                    ContentType='video/mp4'
                )
            return remote_key
        except Exception as e:
            print(f"[COS] Upload failed: {e}")
            return None
    
    def generate_presigned_url(self, key: str, expires: int = 3600) -> Optional[str]:
        if not self.enabled or not self.client:
            return None
        
        try:
            url = self.client.get_presigned_url(
                Method='GET',
                Bucket=self.bucket,
                Key=key,
                Expired=expires
            )
            return url
        except Exception as e:
            print(f"[COS] Generate URL failed: {e}")
            return None
    
    def delete_object(self, key: str) -> bool:
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=key
            )
            return True
        except Exception as e:
            print(f"[COS] Delete failed: {e}")
            return False
    
    def check_object_exists(self, key: str) -> bool:
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=key
            )
            return True
        except:
            return False
    
    def get_video_url(self, project_id: int, task_id: int) -> str:
        return f"videos/{project_id}_{task_id}.mp4"
    
    def upload_file(self, local_path: str, project_id: int, task_id: int) -> tuple:
        key = self.get_video_url(project_id, task_id)
        result = self.upload_video(local_path, key)
        if result:
            return True, key, self.generate_presigned_url(key)
        return False, None, None


cos_storage = COSStorage()
