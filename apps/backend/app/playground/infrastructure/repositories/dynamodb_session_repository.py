"""DynamoDB Session Repository Implementation"""
import boto3
from typing import Optional, List

from app.config import settings
from app.shared.utils.timestamp import parse_timestamp_value
from ...domain.repositories.session_repository import SessionRepository
from ...domain.entities.session import PlaygroundSession
from ...domain.value_objects import SessionId, Message, SessionStatus


class DynamoDBSessionRepository(SessionRepository):
    """DynamoDB Session Repository"""

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
    
    async def save(self, session: PlaygroundSession) -> PlaygroundSession:
        """세션 저장"""
        item = {
            "PK": f"SESSION#{session.id.value}",
            "SK": "METADATA",
            "EntityType": "PlaygroundSession",
            "UserId": session.user_id,
            "AgentId": session.agent_id,
            "AgentVersion": session.agent_version,
            "Status": session.status.value,
            "CreatedAt": session.created_at,
            "UpdatedAt": session.updated_at
        }

        self.table.put_item(Item=item)

        # 메시지 저장
        for msg in session.messages:
            msg_item = {
                "PK": f"SESSION#{session.id.value}",
                "SK": f"MESSAGE#{msg.timestamp}",
                "Role": msg.role,
                "Content": msg.content,
                "Timestamp": msg.timestamp
            }
            self.table.put_item(Item=msg_item)
        
        return session
    
    async def find_by_id(self, session_id: str) -> Optional[PlaygroundSession]:
        """세션 조회"""
        response = self.table.get_item(
            Key={"PK": f"SESSION#{session_id}", "SK": "METADATA"}
        )
        
        if "Item" not in response:
            return None
        
        item = response["Item"]
        
        # 메시지 조회
        msg_response = self.table.query(
            KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
            ExpressionAttributeValues={
                ":pk": f"SESSION#{session_id}",
                ":sk": "MESSAGE#"
            }
        )
        
        messages = [
            Message(
                role=msg["Role"],
                content=msg["Content"],
                timestamp=parse_timestamp_value(msg["Timestamp"])
            )
            for msg in msg_response.get("Items", [])
        ]

        return PlaygroundSession(
            id=SessionId(session_id),
            user_id=item["UserId"],
            agent_id=item["AgentId"],
            agent_version=item["AgentVersion"],
            messages=messages,
            status=SessionStatus(item["Status"]),
            created_at=parse_timestamp_value(item["CreatedAt"]),
            updated_at=parse_timestamp_value(item["UpdatedAt"])
        )
    
    async def find_by_user(self, user_id: str) -> List[PlaygroundSession]:
        """사용자별 세션 조회"""
        response = self.table.scan(
            FilterExpression="EntityType = :type AND UserId = :user_id",
            ExpressionAttributeValues={
                ":type": "PlaygroundSession",
                ":user_id": user_id
            }
        )
        
        sessions = []
        for item in response.get("Items", []):
            session_id = item["PK"].replace("SESSION#", "")
            session = await self.find_by_id(session_id)
            if session:
                sessions.append(session)
        
        return sessions
