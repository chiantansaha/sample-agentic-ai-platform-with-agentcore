"""DynamoDB KB Version Repository Implementation"""
from typing import List, Optional
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key
import json

from app.config import settings
from app.shared.utils.timestamp import parse_timestamp_value
from ...domain.repositories.version_repository import VersionRepository
from ...domain.entities.knowledge_base_version import KnowledgeBaseVersion
from ...domain.value_objects.knowledge_base_file import KnowledgeBaseFile
from ...domain.value_objects.version_changes import VersionChanges
from ...domain.value_objects.sync_status import SyncStatus


class DynamoDBVersionRepository(VersionRepository):
    """DynamoDB 버전 저장소 구현"""

    def __init__(self):
        self.table_name = settings.DYNAMODB_KB_VERSIONS_TABLE if hasattr(settings, 'DYNAMODB_KB_VERSIONS_TABLE') else 'agentic-kb-versions-dev'
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

        self.table = self.dynamodb.Table(self.table_name)

    def _serialize_version(self, version: KnowledgeBaseVersion) -> dict:
        """버전 엔티티를 DynamoDB 아이템으로 직렬화"""
        item = {
            'kb_id': version.kb_id,
            'version': version.version,
            'files': [
                {
                    'name': f.name,
                    'size': f.size,
                    'content_type': f.content_type,
                    's3_key': f.s3_key,
                    'checksum': f.checksum,
                    'uploaded_at': f.uploaded_at
                }
                for f in version.files
            ],
            'change_log': version.change_log,
            'changes': {
                'added': version.changes.added,
                'deleted': version.changes.deleted,
                'modified': version.changes.modified
            },
            'sync_status': version.sync_status.value,
            'created_by': version.created_by,
            'created_at': version.created_at,
        }

        if version.sync_job_id:
            item['sync_job_id'] = version.sync_job_id
        if version.sync_started_at:
            item['sync_started_at'] = version.sync_started_at
        if version.sync_completed_at:
            item['sync_completed_at'] = version.sync_completed_at

        return item

    def _deserialize_version(self, item: dict) -> KnowledgeBaseVersion:
        """DynamoDB 아이템을 버전 엔티티로 역직렬화"""
        files = [
            KnowledgeBaseFile(
                name=f['name'],
                size=int(f['size']),
                content_type=f['content_type'],
                s3_key=f['s3_key'],
                checksum=f['checksum'],
                uploaded_at=parse_timestamp_value(f.get('uploaded_at'))
            )
            for f in item['files']
        ]

        changes = VersionChanges(
            added=item['changes']['added'],
            deleted=item['changes']['deleted'],
            modified=item['changes']['modified']
        )

        version = KnowledgeBaseVersion(
            kb_id=item['kb_id'],
            version=int(item['version']),
            files=files,
            change_log=item['change_log'],
            changes=changes,
            sync_status=SyncStatus(item['sync_status']),
            created_by=item['created_by'],
            created_at=parse_timestamp_value(item.get('created_at')) or 0
        )

        if item.get('sync_job_id'):
            version.sync_job_id = item['sync_job_id']
        if item.get('sync_started_at'):
            version.sync_started_at = parse_timestamp_value(item['sync_started_at'])
        if item.get('sync_completed_at'):
            version.sync_completed_at = parse_timestamp_value(item['sync_completed_at'])

        return version

    async def save(self, version: KnowledgeBaseVersion) -> KnowledgeBaseVersion:
        """버전 저장"""
        item = self._serialize_version(version)
        self.table.put_item(Item=item)
        return version

    async def find_by_kb_id(self, kb_id: str) -> List[KnowledgeBaseVersion]:
        """KB ID로 모든 버전 조회"""
        response = self.table.query(
            KeyConditionExpression=Key('kb_id').eq(kb_id),
            ScanIndexForward=False  # 최신 버전부터 정렬
        )

        versions = []
        for item in response.get('Items', []):
            versions.append(self._deserialize_version(item))

        return versions

    async def find_by_kb_id_and_version(
        self, kb_id: str, version: int
    ) -> Optional[KnowledgeBaseVersion]:
        """KB ID와 버전 번호로 특정 버전 조회"""
        response = self.table.get_item(
            Key={
                'kb_id': kb_id,
                'version': version
            }
        )

        if 'Item' in response:
            return self._deserialize_version(response['Item'])
        return None

    async def find_latest_by_kb_id(self, kb_id: str) -> Optional[KnowledgeBaseVersion]:
        """KB ID로 최신 버전 조회"""
        response = self.table.query(
            KeyConditionExpression=Key('kb_id').eq(kb_id),
            ScanIndexForward=False,  # 최신 버전부터 정렬
            Limit=1
        )

        items = response.get('Items', [])
        if items:
            return self._deserialize_version(items[0])
        return None

    async def batch_find_latest_by_kb_ids(self, kb_ids: List[str]) -> dict:
        """여러 KB의 최신 버전을 배치 조회 - N+1 문제 해결"""
        if not kb_ids:
            return {}

        import asyncio

        # asyncio.gather로 병렬 조회
        tasks = [self.find_latest_by_kb_id(kb_id) for kb_id in kb_ids]
        versions = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과를 딕셔너리로 변환
        result = {}
        for kb_id, version in zip(kb_ids, versions):
            if isinstance(version, Exception):
                print(f"⚠️ Failed to fetch version for KB {kb_id}: {version}")
                continue
            if version:
                result[kb_id] = version

        return result

    async def delete_by_kb_id(self, kb_id: str) -> None:
        """KB ID로 모든 버전 삭제"""
        # 먼저 모든 버전 조회
        versions = await self.find_by_kb_id(kb_id)

        # 각 버전 삭제
        for version in versions:
            self.table.delete_item(
                Key={
                    'kb_id': kb_id,
                    'version': version.version
                }
            )