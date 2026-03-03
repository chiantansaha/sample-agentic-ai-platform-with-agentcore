"""
Lambda Function for KB Sync Status Checker
Triggered by SQS messages to check Ingestion Job status
"""
import json
import os
import time
import boto3

# AWS Clients
dynamodb = boto3.resource('dynamodb')
bedrock_agent = boto3.client('bedrock-agent')
sqs = boto3.client('sqs')

# Environment Variables
DYNAMODB_KB_TABLE = os.environ['DYNAMODB_KB_TABLE']
DYNAMODB_KB_VERSION_TABLE = os.environ['DYNAMODB_KB_VERSION_TABLE']
KB_SYNC_QUEUE_URL = os.environ.get('KB_SYNC_QUEUE_URL')

kb_table = dynamodb.Table(DYNAMODB_KB_TABLE)
version_table = dynamodb.Table(DYNAMODB_KB_VERSION_TABLE)


def lambda_handler(event, context):
    """Check KB sync status from SQS messages"""
    print(f"Received {len(event['Records'])} messages")

    failed_message_ids = []

    for record in event['Records']:
        try:
            message = json.loads(record['body'])
            kb_id = message['kb_id']
            bedrock_kb_id = message['bedrock_kb_id']
            data_source_id = message['data_source_id']

            print(f"🔍 Checking sync status for KB {kb_id}")

            # Get latest ingestion job
            jobs_response = bedrock_agent.list_ingestion_jobs(
                knowledgeBaseId=bedrock_kb_id,
                dataSourceId=data_source_id,
                maxResults=1
            )

            jobs = jobs_response.get('ingestionJobSummaries', [])
            if not jobs:
                print(f"⚠️ No ingestion jobs found for KB {kb_id}, will retry")
                # 메시지를 실패로 표시하여 재시도
                failed_message_ids.append(record['messageId'])
                continue

            latest_job = jobs[0]
            job_status = latest_job['status']

            print(f"KB {kb_id}: Ingestion Job {latest_job['ingestionJobId']} status = {job_status}")

            # Update if completed or failed
            if job_status == 'COMPLETE':
                update_sync_status(kb_id, 'completed')
                print(f"✅ KB {kb_id} sync completed")
            elif job_status == 'FAILED':
                update_sync_status(kb_id, 'failed')
                print(f"❌ KB {kb_id} sync failed")
            elif job_status in ['IN_PROGRESS', 'STARTING']:
                # 아직 진행 중이면 메시지를 실패로 표시하여 재시도
                print(f"⏳ KB {kb_id} still syncing... will retry in 5 minutes")
                failed_message_ids.append(record['messageId'])

        except Exception as e:
            print(f"❌ Error checking KB sync: {e}")
            # 에러 발생 시 메시지를 실패로 표시하여 재시도
            failed_message_ids.append(record['messageId'])

    # Return batch item failures for retry
    if failed_message_ids:
        return {
            'batchItemFailures': [
                {'itemIdentifier': msg_id} for msg_id in failed_message_ids
            ]
        }

    return {'statusCode': 200}


def update_sync_status(kb_id, sync_status):
    """Update sync status in both tables"""
    # Update KB table
    kb_table.update_item(
        Key={'PK': f'KB#{kb_id}', 'SK': 'METADATA'},
        UpdateExpression='SET SyncStatus = :status, UpdatedAt = :updated_at',
        ExpressionAttributeValues={
            ':status': sync_status,
            ':updated_at': int(time.time())
        }
    )

    # Update version table (latest version)
    try:
        # Query to get latest version
        version_response = version_table.query(
            KeyConditionExpression='kb_id = :kb_id',
            ExpressionAttributeValues={':kb_id': kb_id},
            ScanIndexForward=False,
            Limit=1
        )

        if version_response.get('Items'):
            latest_version = version_response['Items'][0]
            version_table.update_item(
                Key={'kb_id': kb_id, 'version': latest_version['version']},
                UpdateExpression='SET sync_status = :status',
                ExpressionAttributeValues={':status': sync_status}
            )
    except Exception as e:
        print(f"⚠️ Failed to update version table: {e}")
