import time
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

from app.config import settings


def create_opensearch_index(kb_id: str):
    """OpenSearch Serverless에 벡터 인덱스 생성"""
    collection_arn = settings.OPENSEARCH_COLLECTION_ARN
    # ARN 형식: arn:aws:aoss:us-east-1:982534381466:collection/lesehl8ukihaiuj8wpdg
    collection_id = collection_arn.split('/')[-1]
    host = f"{collection_id}.{settings.AWS_REGION}.aoss.amazonaws.com"

    # boto3 Session을 사용하여 AWS_PROFILE 적용
    if settings.AWS_PROFILE:
        session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
    else:
        session = boto3.Session(region_name=settings.AWS_REGION)

    credentials = session.get_credentials()
    auth = AWSV4SignerAuth(credentials, settings.AWS_REGION, 'aoss')
    
    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=300
    )
    
    index_name = f'kb-{kb_id}'
    
    # 인덱스 생성
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
                        "name": "hnsw",
                        "engine": "faiss"
                    }
                },
                "text": {
                    "type": "text"
                },
                "metadata": {
                    "type": "text"
                },
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
    
    try:
        if not client.indices.exists(index=index_name):
            client.indices.create(index=index_name, body=index_body)
            print(f"✅ Created index: {index_name}")
            # AWS 권장: 인덱스 생성 후 5분 대기 (OpenSearch Serverless 전파 시간)
            # https://repost.aws/knowledge-center/bedrock-knowledge-base-permission-errors
            print("⏳ Waiting 5 minutes for index propagation across OpenSearch Serverless...")
            time.sleep(300)  # 5 minutes
            print("✅ Index propagation complete")
        else:
            print(f"ℹ️ Index already exists: {index_name}")
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        raise
