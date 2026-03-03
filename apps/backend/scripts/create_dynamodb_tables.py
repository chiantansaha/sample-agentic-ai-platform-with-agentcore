"""DynamoDB 테이블 생성 스크립트"""
import boto3
from botocore.exceptions import ClientError

def create_agent_management_table():
    """AgentManagement 테이블 생성"""
    dynamodb = boto3.client('dynamodb')
    
    table_name = 'AgentManagement'
    
    try:
        # 테이블이 이미 존재하는지 확인
        dynamodb.describe_table(TableName=table_name)
        print(f"✅ 테이블 '{table_name}'이 이미 존재합니다.")
        return
    except ClientError as e:
        if e.response['Error']['Code'] != 'ResourceNotFoundException':
            raise
    
    # 테이블 생성
    print(f"📦 테이블 '{table_name}' 생성 중...")
    
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'PK', 'KeyType': 'HASH'},   # Partition Key
            {'AttributeName': 'SK', 'KeyType': 'RANGE'}   # Sort Key
        ],
        AttributeDefinitions=[
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI2PK', 'AttributeType': 'S'},
            {'AttributeName': 'GSI2SK', 'AttributeType': 'S'},
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'GSI1',
                'KeySchema': [
                    {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            },
            {
                'IndexName': 'GSI2',
                'KeySchema': [
                    {'AttributeName': 'GSI2PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'GSI2SK', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ],
        BillingMode='PROVISIONED',
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    
    # 테이블 생성 대기
    print("⏳ 테이블 생성 대기 중...")
    waiter = dynamodb.get_waiter('table_exists')
    waiter.wait(TableName=table_name)
    
    print(f"✅ 테이블 '{table_name}' 생성 완료!")
    print(f"   - PK: Partition Key")
    print(f"   - SK: Sort Key")
    print(f"   - GSI1: 상태별 조회 (GSI1PK=STATUS#enabled, GSI1SK=CreatedAt)")
    print(f"   - GSI2: 팀 태그별 조회 (GSI2PK=TEAM_TAG#tag-id, GSI2SK=EntityType)")

if __name__ == "__main__":
    try:
        create_agent_management_table()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise
