"""DynamoDB Agent Version Repository Implementation"""
import boto3
from typing import List, Optional
from decimal import Decimal

from app.config import settings
from app.shared.utils.timestamp import parse_timestamp_value
from ...domain.repositories.agent_version_repository import AgentVersionRepository
from ...domain.entities.agent_version import AgentVersion
from ...domain.value_objects import Version


def convert_floats_to_decimal(obj):
    """재귀적으로 float를 Decimal로 변환"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    return obj


class DynamoDBAgentVersionRepository(AgentVersionRepository):
    """DynamoDB Agent Version Repository 구현"""

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

        table_name = table_name or settings.DYNAMODB_AGENT_TABLE
        self.table = self.dynamodb.Table(table_name)
    
    async def save(self, version: AgentVersion) -> AgentVersion:
        """버전 저장"""
        item = {
            "PK": f"AGENT#{version.agent_id}",
            "SK": f"VERSION#{version.version}",
            "EntityType": "AgentVersion",
            "VersionId": version.id,
            "Version": str(version.version),
            "ChangeLog": version.change_log,
            "Snapshot": convert_floats_to_decimal(version.snapshot),
            "DeployedBy": version.deployed_by,
            "DeployedAt": version.deployed_at
        }
        
        self.table.put_item(Item=item)
        return version
    
    async def find_by_agent_id(self, agent_id: str) -> List[AgentVersion]:
        """Agent ID로 버전 목록 조회"""
        response = self.table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
            ExpressionAttributeValues={
                ":pk": f"AGENT#{agent_id}",
                ":sk": "VERSION#"
            },
            ScanIndexForward=False  # 최신순 정렬
        )
        
        return [self._to_entity(item, agent_id) for item in response.get("Items", [])]
    
    async def find_latest_version(self, agent_id: str) -> Optional[AgentVersion]:
        """최신 버전 조회"""
        versions = await self.find_by_agent_id(agent_id)
        return versions[0] if versions else None
    
    def _to_entity(self, item: dict, agent_id: str) -> AgentVersion:
        """DynamoDB Item → Domain Entity"""
        return AgentVersion(
            id=item["VersionId"],
            agent_id=agent_id,
            version=Version.from_string(item["Version"]),
            change_log=item["ChangeLog"],
            snapshot=item["Snapshot"],
            deployed_by=item["DeployedBy"],
            deployed_at=parse_timestamp_value(item["DeployedAt"])
        )
