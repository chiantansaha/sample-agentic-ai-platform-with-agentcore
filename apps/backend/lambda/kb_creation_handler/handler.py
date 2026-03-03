"""
Lambda Function for KB Creation
Processes SQS messages and creates Bedrock Knowledge Bases
"""
import json
import os
import time
import boto3
from datetime import datetime  # strftime 용도로 유지

# AWS Clients
dynamodb = boto3.resource('dynamodb')
bedrock_agent = boto3.client('bedrock-agent')
opensearch = boto3.client('opensearchserverless')
sqs = boto3.client('sqs')

# Environment Variables
DYNAMODB_KB_TABLE = os.environ['DYNAMODB_KB_TABLE']
DYNAMODB_KB_VERSION_TABLE = os.environ.get('DYNAMODB_KB_VERSION_TABLE', 'agentic-ai-dev-kb-versions-dev')
OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']
OPENSEARCH_COLLECTION_ARN = os.environ['OPENSEARCH_COLLECTION_ARN']
KB_ROLE_ARN = os.environ['KB_ROLE_ARN']
EMBEDDING_MODEL_ARN = os.environ['EMBEDDING_MODEL_ARN']
KB_SYNC_QUEUE_URL = os.environ.get('KB_SYNC_QUEUE_URL')

table = dynamodb.Table(DYNAMODB_KB_TABLE)
version_table = dynamodb.Table(DYNAMODB_KB_VERSION_TABLE)


def lambda_handler(event, context):
    """Main Lambda handler"""
    print(f"Received {len(event['Records'])} messages")

    for record in event['Records']:
        try:
            message = json.loads(record['body'])
            kb_id = message['kb_id']
            action = message.get('action', 'create')  # 기본값: create

            # 파일 업데이트 액션 처리
            if action == 'update_files':
                print(f"Processing KB file update: {kb_id}")
                handle_file_update(message)
                continue

            # KB 생성 액션 처리
            print(f"Processing KB creation: {kb_id}")

            # Get current KB info from DynamoDB
            kb_info = get_kb_info(kb_id)

            # If KB and Data Source already created, just start Ingestion Job
            if kb_info and kb_info.get('KnowledgeBaseId') and kb_info.get('DataSourceId'):
                bedrock_kb_id = kb_info['KnowledgeBaseId']
                data_source_id = kb_info['DataSourceId']

                print(f"KB already created: {bedrock_kb_id}, checking status...")

                # Wait for KB to become ACTIVE (3분간 폴링)
                if not wait_for_kb_active(bedrock_kb_id, max_wait_seconds=180):
                    # 3분 후에도 ACTIVE 안되면 SQS 리트라이
                    kb_status = check_kb_status(bedrock_kb_id)
                    print(f"⏳ KB status: {kb_status}, will retry via SQS")
                    raise Exception(f"KB not ready yet (status: {kb_status}), retrying...")

                # Start Ingestion Job
                job_response = start_ingestion_job(bedrock_kb_id, data_source_id)

                # Update DynamoDB to syncing
                update_kb_status(kb_id, 'enabled', bedrock_kb_id, data_source_id)

                # Send sync check message to SQS
                send_sync_check_message(kb_id, bedrock_kb_id, data_source_id)

                print(f"✅ KB {kb_id} Ingestion Job started")
                continue

            # Create new KB
            # Create OpenSearch index
            create_opensearch_index(kb_id)

            # Wait for index propagation (1 minute)
            print(f"Waiting 1 minute for index propagation...")
            time.sleep(60)

            # Create Bedrock KB
            kb_response = create_bedrock_kb(message)

            # Create Data Source
            ds_response = create_data_source(kb_response['knowledgeBaseId'], message)

            # Wait for KB to become ACTIVE (3분간 폴링)
            if not wait_for_kb_active(kb_response['knowledgeBaseId'], max_wait_seconds=180):
                # 3분 후에도 ACTIVE 안되면 SQS 리트라이
                kb_status = check_kb_status(kb_response['knowledgeBaseId'])
                print(f"⏳ KB status: {kb_status}, will retry via SQS")
                # Save KB/DS info to DynamoDB for next retry
                update_kb_info_only(
                    kb_id=kb_id,
                    bedrock_kb_id=kb_response['knowledgeBaseId'],
                    data_source_id=ds_response['dataSourceId']
                )
                raise Exception(f"KB not ready yet (status: {kb_status}), retrying...")

            # Start Ingestion Job
            job_response = start_ingestion_job(
                kb_response['knowledgeBaseId'],
                ds_response['dataSourceId']
            )

            # Update DynamoDB
            update_kb_status(
                kb_id=kb_id,
                status='enabled',
                bedrock_kb_id=kb_response['knowledgeBaseId'],
                data_source_id=ds_response['dataSourceId']
            )

            # Send sync check message to SQS
            send_sync_check_message(
                kb_id=kb_id,
                bedrock_kb_id=kb_response['knowledgeBaseId'],
                data_source_id=ds_response['dataSourceId']
            )

            print(f"✅ KB {kb_id} created successfully")

        except Exception as e:
            print(f"❌ Error processing KB {kb_id}: {str(e)}")
            # Don't delete message - let it retry
            raise e

    return {'statusCode': 200}


def is_kb_already_created(kb_id):
    """Check if KB is already created"""
    try:
        response = table.get_item(
            Key={'PK': f'KB#{kb_id}', 'SK': 'METADATA'}
        )
        
        if 'Item' in response:
            status = response['Item'].get('status', '')
            return status == 'enabled'
        
        return False
    except Exception as e:
        print(f"Error checking KB status: {e}")
        return False


def get_kb_info(kb_id):
    """Get KB info from DynamoDB"""
    try:
        response = table.get_item(
            Key={'PK': f'KB#{kb_id}', 'SK': 'METADATA'}
        )
        return response.get('Item')
    except Exception as e:
        print(f"Error getting KB info: {e}")
        return None


def update_kb_info_only(kb_id, bedrock_kb_id, data_source_id):
    """Update only KB/DS IDs without changing status"""
    table.update_item(
        Key={'PK': f'KB#{kb_id}', 'SK': 'METADATA'},
        UpdateExpression='SET KnowledgeBaseId = :kb_id, DataSourceId = :ds_id, UpdatedAt = :updated_at',
        ExpressionAttributeValues={
            ':kb_id': bedrock_kb_id,
            ':ds_id': data_source_id,
            ':updated_at': int(time.time())
        }
    )
    print(f"✅ Saved KB/DS IDs for retry: {bedrock_kb_id}, {data_source_id}")


def create_opensearch_index(kb_id):
    """Create OpenSearch index"""
    from opensearchpy import OpenSearch, RequestsHttpConnection
    from requests_aws4auth import AWS4Auth
    
    # AWS Auth - Lambda에서는 AWS_REGION이 자동 설정됨
    session = boto3.Session()
    credentials = session.get_credentials()
    aws_region = session.region_name or os.environ.get('AWS_REGION')
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        aws_region,
        'aoss',
        session_token=credentials.token
    )
    
    # OpenSearch client
    # OpenSearch Serverless는 443 포트 사용
    opensearch_host = OPENSEARCH_ENDPOINT.replace('https://', '').replace(':9200', '')
    
    client = OpenSearch(
        hosts=[{'host': opensearch_host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30
    )
    
    index_name = f'kb-{kb_id}'
    
    # Index body
    index_body = {
        "settings": {
            "index.knn": True
        },
        "mappings": {
            "properties": {
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 1536,
                    "method": {
                        "engine": "faiss",
                        "name": "hnsw"
                    }
                },
                "text": {"type": "text"},
                "metadata": {"type": "text"},
                "AMAZON_BEDROCK_METADATA": {
                    "type": "text",
                    "index": False
                },
                "AMAZON_BEDROCK_TEXT_CHUNK": {
                    "type": "text"
                }
            }
        }
    }
    
    # Create index
    try:
        client.indices.create(index=index_name, body=index_body)
        print(f"✅ OpenSearch index created: {index_name}")
    except Exception as e:
        if 'resource_already_exists_exception' in str(e):
            print(f"⚠️ Index already exists: {index_name}, skipping creation")
        else:
            print(f"❌ Error creating index: {e}")
            raise


def create_bedrock_kb(message):
    """Create Bedrock Knowledge Base"""
    response = bedrock_agent.create_knowledge_base(
        name=message['kb_name'],
        description=message.get('description') or 'Knowledge Base',
        roleArn=KB_ROLE_ARN,
        knowledgeBaseConfiguration={
            'type': 'VECTOR',
            'vectorKnowledgeBaseConfiguration': {
                'embeddingModelArn': EMBEDDING_MODEL_ARN
            }
        },
        storageConfiguration={
            'type': 'OPENSEARCH_SERVERLESS',
            'opensearchServerlessConfiguration': {
                'collectionArn': OPENSEARCH_COLLECTION_ARN,
                'vectorIndexName': f'kb-{message["kb_id"]}',
                'fieldMapping': {
                    'vectorField': 'embedding',
                    'textField': 'text',
                    'metadataField': 'metadata'
                }
            }
        }
    )
    
    print(f"✅ Bedrock KB created: {response['knowledgeBase']['knowledgeBaseId']}")
    return response['knowledgeBase']


def create_data_source(kb_id, message):
    """Create Data Source"""
    import re
    from datetime import datetime
    
    # Data Source 이름: KB ID 기반 (항상 유효한 이름)
    # 형식: kb-{kb_id}-ds-{timestamp}
    timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    kb_id_short = message["kb_id"][:8]  # KB ID 앞 8자리
    ds_name = f'kb-{kb_id_short}-ds-{timestamp}'
    
    response = bedrock_agent.create_data_source(
        knowledgeBaseId=kb_id,
        name=ds_name,
        dataSourceConfiguration={
            'type': 'S3',
            's3Configuration': {
                'bucketArn': f'arn:aws:s3:::{message["s3_bucket"]}',
                'inclusionPrefixes': [message['s3_prefix']]
            }
        }
    )
    
    print(f"✅ Data Source created: {response['dataSource']['dataSourceId']}")
    return response['dataSource']


def start_ingestion_job(kb_id, data_source_id):
    """Start Ingestion Job to sync S3 files to OpenSearch"""
    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=data_source_id
    )
    
    print(f"✅ Ingestion Job started: {response['ingestionJob']['ingestionJobId']}")
    return response['ingestionJob']


def check_kb_status(kb_id):
    """Check KB status"""
    response = bedrock_agent.get_knowledge_base(knowledgeBaseId=kb_id)
    return response['knowledgeBase']['status']


def wait_for_kb_active(kb_id, max_wait_seconds=180):
    """
    KB가 ACTIVE 상태가 될 때까지 폴링

    Args:
        kb_id: Knowledge Base ID
        max_wait_seconds: 최대 대기 시간 (기본 3분)

    Returns:
        bool: ACTIVE 상태가 되면 True, 타임아웃 시 False
    """
    poll_interval = 30  # 30초마다 체크
    max_attempts = max_wait_seconds // poll_interval

    for attempt in range(max_attempts):
        status = check_kb_status(kb_id)

        if status == 'ACTIVE':
            print(f"✅ KB is now ACTIVE after {attempt * poll_interval} seconds")
            return True

        print(f"⏳ Attempt {attempt + 1}/{max_attempts}: KB status = {status}, waiting {poll_interval}s...")

        if attempt < max_attempts - 1:  # 마지막 시도에서는 sleep 안 함
            time.sleep(poll_interval)

    print(f"⚠️ KB still not ACTIVE after {max_wait_seconds} seconds")
    return False


def send_sync_check_message(kb_id, bedrock_kb_id, data_source_id):
    """Send message to sync checker SQS queue"""
    if not KB_SYNC_QUEUE_URL:
        print(f"⚠️ KB_SYNC_QUEUE_URL not set, skipping sync check message")
        return

    message_body = {
        'kb_id': kb_id,
        'bedrock_kb_id': bedrock_kb_id,
        'data_source_id': data_source_id
    }

    try:
        sqs.send_message(
            QueueUrl=KB_SYNC_QUEUE_URL,
            MessageBody=json.dumps(message_body)
        )
        print(f"✅ Sent sync check message to SQS for KB {kb_id}")
    except Exception as e:
        print(f"⚠️ Failed to send sync check message: {e}")


def update_kb_status(kb_id, status, bedrock_kb_id, data_source_id, version=1):
    """Update KB status in DynamoDB (both KB and Version tables)"""
    # 1. KB 메타정보 업데이트 (syncing 상태)
    table.update_item(
        Key={'PK': f'KB#{kb_id}', 'SK': 'METADATA'},
        UpdateExpression='SET #status = :status, SyncStatus = :sync_status, KnowledgeBaseId = :kb_id, DataSourceId = :ds_id, UpdatedAt = :updated_at',
        ExpressionAttributeNames={'#status': 'Status'},
        ExpressionAttributeValues={
            ':status': status,
            ':sync_status': 'syncing',  # Ingestion Job 실행 중
            ':kb_id': bedrock_kb_id,
            ':ds_id': data_source_id,
            ':updated_at': int(time.time())
        }
    )

    print(f"✅ DynamoDB updated: KB {kb_id} Status = {status}, SyncStatus = syncing")

    # 2. 버전 테이블 업데이트 (syncing 상태)
    try:
        version_table.update_item(
            Key={'kb_id': kb_id, 'version': version},
            UpdateExpression='SET sync_status = :sync_status',
            ExpressionAttributeValues={
                ':sync_status': 'syncing'
            }
        )
        print(f"✅ Version table updated: KB {kb_id} Version {version} sync_status = syncing")
    except Exception as e:
        print(f"⚠️ Failed to update version table: {e}")


def handle_file_update(message):
    """
    KB 파일 업데이트 처리
    - Data Source의 S3 prefix 업데이트
    - Ingestion Job 시작
    - DynamoDB 상태 업데이트
    """
    kb_id = message['kb_id']
    s3_bucket = message['s3_bucket']
    s3_prefix = message['s3_prefix']
    version = message.get('version', 2)

    print(f"📦 Updating KB files: {kb_id}, version: {version}")
    print(f"   S3 prefix: {s3_prefix}")

    # Get KB info from DynamoDB
    kb_info = get_kb_info(kb_id)
    if not kb_info:
        raise Exception(f"KB {kb_id} not found in DynamoDB")

    bedrock_kb_id = kb_info.get('KnowledgeBaseId')
    data_source_id = kb_info.get('DataSourceId')

    if not bedrock_kb_id or not data_source_id:
        raise Exception(f"KB {kb_id} missing KnowledgeBaseId or DataSourceId")

    # Wait for KB to become ACTIVE
    if not wait_for_kb_active(bedrock_kb_id, max_wait_seconds=180):
        kb_status = check_kb_status(bedrock_kb_id)
        print(f"⏳ KB status: {kb_status}, will retry via SQS")
        raise Exception(f"KB not ready yet (status: {kb_status}), retrying...")

    # Get existing Data Source name
    try:
        ds_response = bedrock_agent.get_data_source(
            knowledgeBaseId=bedrock_kb_id,
            dataSourceId=data_source_id
        )
        ds_name = ds_response['dataSource']['name']
        print(f"✅ Data Source name: {ds_name}")
    except Exception as e:
        print(f"❌ Failed to get Data Source: {e}")
        raise

    # Update Data Source S3 configuration
    try:
        bedrock_agent.update_data_source(
            knowledgeBaseId=bedrock_kb_id,
            dataSourceId=data_source_id,
            name=ds_name,  # Required parameter
            dataSourceConfiguration={
                'type': 'S3',
                's3Configuration': {
                    'bucketArn': f'arn:aws:s3:::{s3_bucket}',
                    'inclusionPrefixes': [s3_prefix]
                }
            }
        )
        print(f"✅ Data Source S3 prefix updated: {s3_prefix}")
    except Exception as e:
        print(f"❌ Failed to update Data Source: {e}")
        raise

    # Start Ingestion Job
    try:
        job_response = start_ingestion_job(bedrock_kb_id, data_source_id)
        print(f"✅ Ingestion Job started: {job_response['ingestionJobId']}")
    except Exception as e:
        print(f"❌ Failed to start Ingestion Job: {e}")
        raise

    # Update DynamoDB status
    update_kb_status(kb_id, 'enabled', bedrock_kb_id, data_source_id, version=version)

    # Send sync check message to SQS
    send_sync_check_message(kb_id, bedrock_kb_id, data_source_id)

    print(f"✅ KB {kb_id} file update completed")
