"""DynamoDB KB Repository Implementation - 메타정보만 관리"""
import boto3
from boto3.dynamodb.conditions import Key
from typing import Optional, List, Tuple

from app.config import settings
from app.shared.utils.timestamp import parse_timestamp_value, now_timestamp
from ...domain.repositories.kb_repository import KBRepository
from ...domain.entities.knowledge_base import KnowledgeBase
from ...domain.value_objects import KBId, KBStatus


class DynamoDBKBRepository(KBRepository):
    """DynamoDB KB Repository 구현 - 메타정보만 저장"""

    def __init__(self, table_name: str = None):
        endpoint_url = settings.DYNAMODB_ENDPOINT if hasattr(settings, 'DYNAMODB_ENDPOINT') else None
        region_name = settings.AWS_REGION

        # boto3 Session을 사용하여 AWS_PROFILE 적용
        if settings.AWS_PROFILE:
            session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=region_name)
            if endpoint_url:
                self.dynamodb = session.resource('dynamodb', endpoint_url=endpoint_url)
            else:
                self.dynamodb = session.resource('dynamodb')
        else:
            if endpoint_url:
                self.dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url, region_name=region_name)
            else:
                self.dynamodb = boto3.resource('dynamodb', region_name=region_name)

        table_name = table_name or settings.DYNAMODB_KB_TABLE
        self.table = self.dynamodb.Table(table_name)

    async def save(self, kb: KnowledgeBase) -> KnowledgeBase:
        """KB 메타정보 저장"""
        item = {
            "PK": f"KB#{kb.id.value}",
            "SK": "METADATA",
            "EntityType": "KnowledgeBase",
            "Name": kb.name,
            "Description": kb.description,
            "KnowledgeBaseId": kb.bedrock_kb_id,
            "S3Bucket": kb.s3_bucket,
            "S3Prefix": kb.s3_prefix,
            "DataSourceId": kb.data_source_id,
            "Status": kb.status.value,
            "SyncStatus": kb.sync_status or "uploaded",
            "TeamTags": kb.team_tags,
            "CurrentVersion": kb.current_version,
            "CreatedAt": kb.created_at,
            "UpdatedAt": kb.updated_at,
            "CreatedBy": kb.created_by,
            "UpdatedBy": kb.updated_by,
            "GSI1PK": f"STATUS#{kb.status.value}",
            "GSI1SK": f"CREATED#{kb.created_at}"
        }

        self.table.put_item(Item=item)
        return kb

    async def find_by_id(self, kb_id: str) -> Optional[KnowledgeBase]:
        """ID로 KB 메타정보 조회"""
        response = self.table.get_item(
            Key={"PK": f"KB#{kb_id}", "SK": "METADATA"}
        )

        if "Item" not in response:
            return None

        return self._to_entity(response["Item"])

    async def find_all(self, page: int = 1, page_size: int = 20, status: str = None) -> Tuple[List[KnowledgeBase], int]:
        """KB 목록 조회 - GSI1을 사용한 효율적인 쿼리"""

        if status:
            # Status 필터가 있으면 GSI1 사용 (효율적)
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression=Key('GSI1PK').eq(f'STATUS#{status}'),
                ScanIndexForward=False  # 최신순 정렬
            )
            kbs = [self._to_entity(item) for item in response.get("Items", [])]
            total = len(kbs)
        else:
            # Status 필터가 없으면 전체 조회 (Scan 사용하되 최적화)
            response = self.table.scan(
                FilterExpression="EntityType = :type AND SK = :sk",
                ExpressionAttributeValues={
                    ":type": "KnowledgeBase",
                    ":sk": "METADATA"
                }
            )
            kbs = [self._to_entity(item) for item in response.get("Items", [])]
            total = len(kbs)

        return kbs, total

    async def delete(self, kb_id: str) -> None:
        """KB 메타정보 삭제"""
        self.table.delete_item(
            Key={"PK": f"KB#{kb_id}", "SK": "METADATA"}
        )

    def _to_entity(self, item: dict) -> KnowledgeBase:
        """DynamoDB Item → Domain Entity"""
        # 하위 호환: ISO 문자열 또는 timestamp 모두 처리
        created_at = parse_timestamp_value(item.get("CreatedAt")) or now_timestamp()
        updated_at = parse_timestamp_value(item.get("UpdatedAt")) or now_timestamp()

        return KnowledgeBase(
            id=KBId(item["PK"].replace("KB#", "")),
            name=item["Name"],
            description=item["Description"],
            bedrock_kb_id=item.get("KnowledgeBaseId", ""),
            s3_bucket=item.get("S3Bucket", ""),
            s3_prefix=item.get("S3Prefix", ""),
            data_source_id=item.get("DataSourceId", ""),
            status=KBStatus(item["Status"]),
            sync_status=item.get("SyncStatus") or item.get("sync_status"),
            team_tags=item.get("TeamTags", []),
            current_version=item.get("CurrentVersion", 0),
            created_at=created_at,
            updated_at=updated_at,
            created_by=item.get("CreatedBy", ""),
            updated_by=item.get("UpdatedBy", "")
        )
