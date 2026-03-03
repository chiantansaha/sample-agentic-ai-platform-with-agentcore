"""S3 File Client"""
import logging
import boto3
import hashlib
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.config import settings

logger = logging.getLogger(__name__)


class S3FileClient:
    """S3 파일 관리 클라이언트"""

    def __init__(self):
        if settings.AWS_PROFILE:
            session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
            self.s3 = session.client('s3')
        else:
            self.s3 = boto3.client('s3', region_name=settings.AWS_REGION)

        self.default_bucket = settings.S3_KB_FILES_BUCKET

        if not self.default_bucket:
            if settings.ENVIRONMENT == "dev" or settings.ENVIRONMENT == "development":
                logger.warning(
                    "⚠️ S3_KB_FILES_BUCKET not set. "
                    "Knowledge Base file features will be unavailable."
                )
            else:
                raise ValueError(
                    "S3_KB_FILES_BUCKET environment variable is required. "
                    "Please set it in your .env file."
                )
    
    def upload_file(self, file: UploadFile, s3_key: str, bucket: str = None) -> tuple[str, str]:
        """파일 업로드 및 체크섬 반환"""
        bucket = bucket or self.default_bucket

        try:
            # 파일 내용 읽기
            file_content = file.file.read()
            file.file.seek(0)

            # MD5 체크섬 계산
            checksum = hashlib.md5(file_content, usedforsecurity=False).hexdigest()

            # S3 업로드
            self.s3.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=file.content_type
            )

            s3_url = f"s3://{bucket}/{s3_key}"
            return s3_url, checksum
        except Exception as e:
            raise Exception(f"Failed to upload file to S3: {e}")
    
    def upload_file_from_bytes(self, file_obj, s3_key: str, bucket: str = None) -> tuple[str, str]:
        """바이트 데이터를 S3에 업로드"""
        bucket = bucket or self.default_bucket
        
        try:
            # 파일 내용 읽기
            file_content = file_obj.read()
            
            # MD5 체크섬 계산
            checksum = hashlib.md5(file_content, usedforsecurity=False).hexdigest()
            
            # S3 업로드
            self.s3.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=file_content
            )
            
            return f"s3://{bucket}/{s3_key}", checksum
        except ClientError as e:
            raise Exception(f"Failed to upload file to S3: {e}")
    
    def delete_file(self, s3_key: str, bucket: str = None):
        """파일 삭제"""
        bucket = bucket or self.default_bucket
        
        try:
            self.s3.delete_object(Bucket=bucket, Key=s3_key)
        except ClientError as e:
            raise Exception(f"Failed to delete file from S3: {e}")
    
    def ensure_bucket_exists(self, bucket: str = None):
        """버킷 존재 확인 및 생성"""
        bucket = bucket or self.default_bucket
        
        try:
            self.s3.head_bucket(Bucket=bucket)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # 버킷 생성
                self.s3.create_bucket(Bucket=bucket)
            else:
                raise Exception(f"Failed to check bucket: {e}")
