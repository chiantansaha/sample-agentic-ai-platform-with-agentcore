"""DynamoDB client configuration"""

import boto3
from botocore.exceptions import ClientError
from app.config import settings


class DynamoDBClient:
    """DynamoDB client wrapper"""

    def __init__(self):
        """Initialize DynamoDB client"""
        self._client = None
        self._resource = None

        # Build kwargs for boto3 clients
        self._aws_kwargs = {'region_name': settings.AWS_REGION}
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            self._aws_kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
            self._aws_kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY

    @property
    def client(self):
        """Get DynamoDB client"""
        if self._client is None:
            self._client = boto3.client('dynamodb', **self._aws_kwargs)
        return self._client

    @property
    def resource(self):
        """Get DynamoDB resource"""
        if self._resource is None:
            self._resource = boto3.resource('dynamodb', **self._aws_kwargs)
        return self._resource

    def get_table(self, table_name: str):
        """Get DynamoDB table"""
        return self.resource.Table(table_name)

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        try:
            self.client.describe_table(TableName=table_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            raise


# Global DynamoDB client instance
dynamodb_client = DynamoDBClient()
