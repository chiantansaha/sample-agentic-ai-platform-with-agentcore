"""Bedrock Knowledge Base Client"""
import boto3
from botocore.exceptions import ClientError
from .opensearch_helper import create_opensearch_index

from app.config import settings


class BedrockKBClient:
    """Bedrock Knowledge Base API 클라이언트"""

    def __init__(self):
        # boto3 Session을 사용하여 AWS_PROFILE 적용
        if settings.AWS_PROFILE:
            session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
            self.bedrock_agent = session.client('bedrock-agent')
        else:
            self.bedrock_agent = boto3.client('bedrock-agent', region_name=settings.AWS_REGION)

        self.kb_role_arn = settings.BEDROCK_KB_ROLE_ARN
        self.embedding_model_arn = settings.EMBEDDING_MODEL_ARN
        self.opensearch_collection_arn = settings.OPENSEARCH_COLLECTION_ARN
    
    def create_knowledge_base(self, name: str, description: str, kb_id: str) -> str:
        """Bedrock KB 생성"""
        try:
            # OpenSearch 인덱스 먼저 생성 (5분 대기 포함)
            create_opensearch_index(kb_id)
            response = self.bedrock_agent.create_knowledge_base(
                name=f"{name}-{kb_id}",
                description=description,
                roleArn=self.kb_role_arn,
                knowledgeBaseConfiguration={
                    'type': 'VECTOR',
                    'vectorKnowledgeBaseConfiguration': {
                        'embeddingModelArn': self.embedding_model_arn
                    }
                },
                storageConfiguration={
                    'type': 'OPENSEARCH_SERVERLESS',
                    'opensearchServerlessConfiguration': {
                        'collectionArn': self.opensearch_collection_arn,
                        'vectorIndexName': f'kb-{kb_id}',
                        'fieldMapping': {
                            'vectorField': 'embedding',
                            'textField': 'text',
                            'metadataField': 'metadata'
                        }
                    }
                }
            )
            return response['knowledgeBase']['knowledgeBaseId']
        except ClientError as e:
            raise Exception(f"Failed to create Bedrock KB: {e}")
    
    def create_data_source(self, bedrock_kb_id: str, kb_id: str, s3_bucket: str, s3_prefix: str) -> str:
        """Data Source 생성"""
        try:
            response = self.bedrock_agent.create_data_source(
                knowledgeBaseId=bedrock_kb_id,
                name=f"s3-datasource-{kb_id}",
                dataSourceConfiguration={
                    'type': 'S3',
                    's3Configuration': {
                        'bucketArn': f'arn:aws:s3:::{s3_bucket}',
                        'inclusionPrefixes': [s3_prefix]
                    }
                }
            )
            return response['dataSource']['dataSourceId']
        except ClientError as e:
            raise Exception(f"Failed to create Data Source: {e}")
    
    def start_ingestion_job(self, bedrock_kb_id: str, data_source_id: str) -> str:
        """Sync 작업 시작"""
        try:
            response = self.bedrock_agent.start_ingestion_job(
                knowledgeBaseId=bedrock_kb_id,
                dataSourceId=data_source_id
            )
            return response['ingestionJob']['ingestionJobId']
        except ClientError as e:
            raise Exception(f"Failed to start ingestion job: {e}")
    
    def get_ingestion_job_status(self, bedrock_kb_id: str, data_source_id: str, job_id: str) -> str:
        """Sync 상태 조회"""
        try:
            response = self.bedrock_agent.get_ingestion_job(
                knowledgeBaseId=bedrock_kb_id,
                dataSourceId=data_source_id,
                ingestionJobId=job_id
            )
            return response['ingestionJob']['status']
        except ClientError as e:
            raise Exception(f"Failed to get ingestion job status: {e}")
    
    def update_data_source(self, bedrock_kb_id: str, data_source_id: str, s3_bucket: str, s3_prefix: str):
        """Data Source의 S3 prefix 업데이트"""
        try:
            self.bedrock_agent.update_data_source(
                knowledgeBaseId=bedrock_kb_id,
                dataSourceId=data_source_id,
                dataSourceConfiguration={
                    'type': 'S3',
                    's3Configuration': {
                        'bucketArn': f'arn:aws:s3:::{s3_bucket}',
                        'inclusionPrefixes': [s3_prefix]
                    }
                }
            )
        except ClientError as e:
            raise Exception(f"Failed to update Data Source: {e}")
