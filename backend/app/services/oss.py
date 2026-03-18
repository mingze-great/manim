import oss2
from app.config import get_settings

settings = get_settings()


class OSSService:
    def __init__(self):
        self.auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
        self.bucket = oss2.Bucket(self.auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET_NAME)
    
    def upload_file(self, local_file: str, object_name: str) -> str:
        result = self.bucket.put_object_from_file(object_name, local_file)
        if result.status == 200:
            return f"https://{settings.OSS_BUCKET_NAME}.{settings.OSS_ENDPOINT}/{object_name}"
        raise Exception("Upload failed")
    
    def get_signed_url(self, object_name: str, expires: int = 3600) -> str:
        return self.bucket.sign_url('GET', object_name, expires)
    
    def delete_file(self, object_name: str):
        self.bucket.delete_object(object_name)
