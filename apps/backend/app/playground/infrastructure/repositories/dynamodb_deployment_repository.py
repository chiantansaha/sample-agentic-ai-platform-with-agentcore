"""DynamoDB Deployment Repository Implementation (Container 방식)"""
import boto3
from typing import Optional, List

from app.config import settings
from app.shared.utils.timestamp import parse_timestamp_value
from ...domain.repositories.deployment_repository import DeploymentRepository
from ...domain.entities.deployment import Deployment
from ...domain.value_objects import DeploymentId, DeploymentStatus


class DynamoDBDeploymentRepository(DeploymentRepository):
    """DynamoDB Deployment Repository"""

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

        table_name = table_name or settings.DYNAMODB_PLAYGROUND_TABLE
        self.table = self.dynamodb.Table(table_name)

    async def save(self, deployment: Deployment) -> Deployment:
        """배포 정보 저장 (Container 방식)"""
        item = {
            "PK": f"DEPLOYMENT#{deployment.id.value}",
            "SK": "METADATA",
            "EntityType": "Deployment",
            "UserId": deployment.user_id,
            "AgentId": deployment.agent_id,
            "AgentVersion": deployment.agent_version,
            "Status": deployment.status.value,
            "RuntimeId": deployment.runtime_id,
            "RuntimeArn": deployment.runtime_arn,
            "EndpointUrl": deployment.endpoint_url,
            "ContainerUri": deployment.container_uri,  # ECR 이미지 URI
            "ConversationId": deployment.conversation_id,
            "ErrorMessage": deployment.error_message,
            "BuildId": deployment.build_id,  # CodeBuild 빌드 ID
            "BuildPhase": deployment.build_phase,  # 현재 빌드 Phase
            "BuildPhaseMessage": deployment.build_phase_message,  # Phase별 한글 메시지
            "S3Prefix": deployment.s3_prefix,  # S3 빌드 소스 경로
            "IdleTimeout": deployment.idle_timeout,
            "MaxLifetime": deployment.max_lifetime,
            "CreatedAt": deployment.created_at,
            "UpdatedAt": deployment.updated_at,
            "ExpiresAt": deployment.expires_at,
            # GSI용 복합키
            "GSI1PK": f"USER#{deployment.user_id}",
            "GSI1SK": f"AGENT#{deployment.agent_id}#VERSION#{deployment.agent_version}#STATUS#{deployment.status.value}"
        }

        # None 값 제거
        item = {k: v for k, v in item.items() if v is not None}

        self.table.put_item(Item=item)
        return deployment

    async def find_by_id(self, deployment_id: str) -> Optional[Deployment]:
        """ID로 배포 조회"""
        response = self.table.get_item(
            Key={"PK": f"DEPLOYMENT#{deployment_id}", "SK": "METADATA"}
        )

        if "Item" not in response:
            return None

        return self._item_to_deployment(response["Item"])

    async def find_by_user_agent_version(
        self,
        user_id: str,
        agent_id: str,
        agent_version: str
    ) -> Optional[Deployment]:
        """사용자/에이전트/버전으로 활성 배포 조회"""
        # 활성 상태의 배포만 조회 (READY 상태)
        response = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk AND begins_with(GSI1SK, :sk_prefix)",
            FilterExpression="#status = :status",
            ExpressionAttributeNames={"#status": "Status"},
            ExpressionAttributeValues={
                ":pk": f"USER#{user_id}",
                ":sk_prefix": f"AGENT#{agent_id}#VERSION#{agent_version}",
                ":status": DeploymentStatus.READY.value
            }
        )

        items = response.get("Items", [])
        if not items:
            return None

        return self._item_to_deployment(items[0])

    async def find_active_by_user(self, user_id: str) -> List[Deployment]:
        """사용자의 활성 배포 목록 조회"""
        response = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk",
            FilterExpression="#status = :status",
            ExpressionAttributeNames={"#status": "Status"},
            ExpressionAttributeValues={
                ":pk": f"USER#{user_id}",
                ":status": DeploymentStatus.READY.value
            }
        )

        return [self._item_to_deployment(item) for item in response.get("Items", [])]

    async def delete(self, deployment_id: str) -> None:
        """배포 정보 삭제"""
        self.table.delete_item(
            Key={"PK": f"DEPLOYMENT#{deployment_id}", "SK": "METADATA"}
        )

    def _item_to_deployment(self, item: dict) -> Deployment:
        """DynamoDB Item을 Deployment 엔티티로 변환 (Container 방식)"""
        deployment_id = item["PK"].replace("DEPLOYMENT#", "")

        return Deployment(
            id=DeploymentId(deployment_id),
            user_id=item["UserId"],
            agent_id=item["AgentId"],
            agent_version=item["AgentVersion"],
            status=DeploymentStatus(item["Status"]),
            runtime_id=item.get("RuntimeId"),
            runtime_arn=item.get("RuntimeArn"),
            endpoint_url=item.get("EndpointUrl"),
            container_uri=item.get("ContainerUri"),
            conversation_id=item.get("ConversationId"),
            error_message=item.get("ErrorMessage"),
            build_id=item.get("BuildId"),  # CodeBuild 빌드 ID
            build_phase=item.get("BuildPhase"),  # 현재 빌드 Phase
            build_phase_message=item.get("BuildPhaseMessage"),  # Phase별 한글 메시지
            s3_prefix=item.get("S3Prefix"),  # S3 빌드 소스 경로 (Runtime 결과 읽기용)
            idle_timeout=item.get("IdleTimeout", 300),
            max_lifetime=item.get("MaxLifetime", 3600),
            created_at=parse_timestamp_value(item["CreatedAt"]),
            updated_at=parse_timestamp_value(item["UpdatedAt"]),
            expires_at=parse_timestamp_value(item.get("ExpiresAt"))
        )
