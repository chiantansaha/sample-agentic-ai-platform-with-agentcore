"""DynamoDB Conversation Repository Implementation"""
import boto3
from typing import Optional, List

from app.config import settings
from app.shared.utils.timestamp import parse_timestamp_value, now_timestamp
from ...domain.repositories.conversation_repository import ConversationRepository
from ...domain.entities.conversation import Conversation
from ...domain.value_objects import ConversationId, ConversationStatus


class DynamoDBConversationRepository(ConversationRepository):
    """DynamoDB Conversation Repository"""

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

        table_name = table_name or settings.DYNAMODB_PLAYGROUND_CONVERSATIONS_TABLE
        self.table = self.dynamodb.Table(table_name)

    async def save(self, conversation: Conversation) -> Conversation:
        """대화 메타데이터 저장"""
        item = {
            "PK": f"CONVERSATION#{conversation.id.value}",
            "SK": "METADATA",
            "EntityType": "Conversation",
            "UserId": conversation.user_id,
            "AgentId": conversation.agent_id,
            "AgentVersion": conversation.agent_version,
            "Title": conversation.title,
            "MessageCount": conversation.message_count,
            "S3Prefix": conversation.s3_prefix,
            "Status": conversation.status.value,
            "LastMessagePreview": conversation.last_message_preview,
            "CreatedAt": conversation.created_at,
            "UpdatedAt": conversation.updated_at,
            # GSI용 복합키
            "GSI1PK": f"USER#{conversation.user_id}#AGENT#{conversation.agent_id}#VERSION#{conversation.agent_version}",
            "GSI1SK": f"UPDATED#{conversation.updated_at}"
        }

        # None 값 제거
        item = {k: v for k, v in item.items() if v is not None}

        self.table.put_item(Item=item)
        return conversation

    async def find_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """ID로 대화 조회"""
        response = self.table.get_item(
            Key={"PK": f"CONVERSATION#{conversation_id}", "SK": "METADATA"}
        )

        if "Item" not in response:
            return None

        return self._item_to_conversation(response["Item"])

    async def list_by_agent_version(
        self,
        user_id: str,
        agent_id: str,
        agent_version: str,
        limit: int = 5
    ) -> List[Conversation]:
        """에이전트/버전별 대화 목록 조회 (최신순, 최대 limit개)"""
        response = self.table.query(
            IndexName="UserConversationsIndex",
            KeyConditionExpression="GSI1PK = :pk",
            FilterExpression="#status = :status",
            ExpressionAttributeNames={"#status": "Status"},
            ExpressionAttributeValues={
                ":pk": f"USER#{user_id}#AGENT#{agent_id}#VERSION#{agent_version}",
                ":status": ConversationStatus.ACTIVE.value
            },
            ScanIndexForward=False,  # 최신순
            Limit=limit
        )

        return [self._item_to_conversation(item) for item in response.get("Items", [])]

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Conversation]:
        """사용자의 전체 대화 목록 조회 (최신순)"""
        response = self.table.scan(
            FilterExpression="EntityType = :type AND UserId = :user_id AND #status = :status",
            ExpressionAttributeNames={"#status": "Status"},
            ExpressionAttributeValues={
                ":type": "Conversation",
                ":user_id": user_id,
                ":status": ConversationStatus.ACTIVE.value
            }
        )

        items = response.get("Items", [])
        # 최신순 정렬
        items.sort(key=lambda x: x.get("UpdatedAt", ""), reverse=True)

        return [self._item_to_conversation(item) for item in items[:limit]]

    async def count_by_agent_version(
        self,
        user_id: str,
        agent_id: str,
        agent_version: str
    ) -> int:
        """에이전트/버전별 대화 수 조회"""
        response = self.table.query(
            IndexName="UserConversationsIndex",
            KeyConditionExpression="GSI1PK = :pk",
            FilterExpression="#status = :status",
            ExpressionAttributeNames={"#status": "Status"},
            ExpressionAttributeValues={
                ":pk": f"USER#{user_id}#AGENT#{agent_id}#VERSION#{agent_version}",
                ":status": ConversationStatus.ACTIVE.value
            },
            Select="COUNT"
        )

        return response.get("Count", 0)

    async def delete(self, conversation_id: str) -> None:
        """대화 삭제 (메타데이터만, S3는 별도 처리)"""
        # Soft delete - 상태만 변경
        self.table.update_item(
            Key={"PK": f"CONVERSATION#{conversation_id}", "SK": "METADATA"},
            UpdateExpression="SET #status = :status, UpdatedAt = :updated_at",
            ExpressionAttributeNames={"#status": "Status"},
            ExpressionAttributeValues={
                ":status": ConversationStatus.DELETED.value,
                ":updated_at": now_timestamp()
            }
        )

    async def find_oldest_by_agent_version(
        self,
        user_id: str,
        agent_id: str,
        agent_version: str
    ) -> Optional[Conversation]:
        """가장 오래된 대화 조회 (5개 초과 시 삭제용)"""
        response = self.table.query(
            IndexName="UserConversationsIndex",
            KeyConditionExpression="GSI1PK = :pk",
            FilterExpression="#status = :status",
            ExpressionAttributeNames={"#status": "Status"},
            ExpressionAttributeValues={
                ":pk": f"USER#{user_id}#AGENT#{agent_id}#VERSION#{agent_version}",
                ":status": ConversationStatus.ACTIVE.value
            },
            ScanIndexForward=True,  # 오래된 순
            Limit=1
        )

        items = response.get("Items", [])
        if not items:
            return None

        return self._item_to_conversation(items[0])

    def _item_to_conversation(self, item: dict) -> Conversation:
        """DynamoDB Item을 Conversation 엔티티로 변환"""
        conversation_id = item["PK"].replace("CONVERSATION#", "")

        return Conversation(
            id=ConversationId(conversation_id),
            user_id=item["UserId"],
            agent_id=item["AgentId"],
            agent_version=item["AgentVersion"],
            title=item["Title"],
            message_count=item.get("MessageCount", 0),
            s3_prefix=item.get("S3Prefix", ""),
            status=ConversationStatus(item["Status"]),
            last_message_preview=item.get("LastMessagePreview"),
            created_at=parse_timestamp_value(item["CreatedAt"]),
            updated_at=parse_timestamp_value(item["UpdatedAt"])
        )
