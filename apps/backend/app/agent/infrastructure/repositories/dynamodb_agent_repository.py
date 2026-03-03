"""DynamoDB Agent Repository Implementation"""
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from typing import Optional, List, Tuple

from app.config import settings
from app.shared.utils.timestamp import parse_timestamp_value
from ...domain.repositories import AgentRepository
from ...domain.entities import Agent
from ...domain.value_objects import AgentId, LLMModel, Instruction, Version, AgentStatus


class DynamoDBAgentRepository(AgentRepository):
    """DynamoDB Agent Repository 구현"""

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
    
    async def save(self, agent: Agent) -> Agent:
        """Agent 저장"""
        item = {
            "PK": f"AGENT#{agent.id.value}",
            "SK": "METADATA",
            "EntityType": "Agent",
            "Name": agent.name,
            "Description": agent.description,
            "LLMModel": {
                "ModelId": agent.llm_model.model_id,
                "ModelName": agent.llm_model.model_name,
                "Provider": agent.llm_model.provider
            },
            "Instruction": {
                "SystemPrompt": agent.instruction.system_prompt,
                "Temperature": Decimal(str(agent.instruction.temperature)),
                "MaxTokens": agent.instruction.max_tokens
            },
            "KnowledgeBases": agent.knowledge_bases,
            "MCPs": agent.mcps,
            "Status": agent.status.value,
            "CurrentVersion": str(agent.current_version),
            "TeamTags": agent.team_tags,
            "CreatedAt": agent.created_at,
            "UpdatedAt": agent.updated_at,
            "CreatedBy": agent.created_by,
            "UpdatedBy": agent.updated_by,
            "GSI1PK": f"STATUS#{agent.status.value}",
            "GSI1SK": f"CREATED#{agent.created_at}"
        }
        
        self.table.put_item(Item=item)
        return agent
    
    async def find_by_id(self, agent_id: str) -> Optional[Agent]:
        """ID로 Agent 조회"""
        response = self.table.get_item(
            Key={"PK": f"AGENT#{agent_id}", "SK": "METADATA"}
        )
        
        if "Item" not in response:
            return None
        
        return self._to_entity(response["Item"])
    
    def find_all(self, page: int = 1, page_size: int = 20, status: str = None) -> Tuple[List[Agent], int]:
        """Agent 목록 조회 - GSI1을 사용한 효율적인 쿼리"""

        if status:
            # Status 필터가 있으면 GSI1 사용 (효율적)
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression=Key('GSI1PK').eq(f'STATUS#{status}'),
                ScanIndexForward=False  # 최신순 정렬
            )
            agents = [self._to_entity(item) for item in response.get("Items", [])]
            total = len(agents)
        else:
            # Status 필터가 없으면 전체 조회 (Scan 사용하되 Limit 제거)
            response = self.table.scan(
                FilterExpression="EntityType = :type AND SK = :sk",
                ExpressionAttributeValues={
                    ":type": "Agent",
                    ":sk": "METADATA"
                }
            )
            agents = [self._to_entity(item) for item in response.get("Items", [])]
            total = len(agents)

        return agents, total
    
    async def find_enabled_agents(self) -> List[Agent]:
        """활성화된 Agent 목록 조회"""
        response = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk",
            ExpressionAttributeValues={":pk": "STATUS#enabled"}
        )
        
        return [self._to_entity(item) for item in response.get("Items", [])]
    
    def _to_entity(self, item: dict) -> Agent:
        """DynamoDB Item → Domain Entity"""
        return Agent(
            id=AgentId(item["PK"].replace("AGENT#", "")),
            name=item["Name"],
            description=item["Description"],
            llm_model=LLMModel(
                model_id=item["LLMModel"]["ModelId"],
                model_name=item["LLMModel"]["ModelName"],
                provider=item["LLMModel"]["Provider"]
            ),
            instruction=Instruction(
                system_prompt=item["Instruction"]["SystemPrompt"],
                temperature=float(item["Instruction"]["Temperature"]),
                max_tokens=int(item["Instruction"]["MaxTokens"])
            ),
            knowledge_bases=item.get("KnowledgeBases", []),
            mcps=item.get("MCPs", []),
            status=AgentStatus(item["Status"]),
            current_version=Version.from_string(item["CurrentVersion"]),
            team_tags=item.get("TeamTags", []),
            created_at=parse_timestamp_value(item["CreatedAt"]),
            updated_at=parse_timestamp_value(item["UpdatedAt"]),
            created_by=item["CreatedBy"],
            updated_by=item["UpdatedBy"]
        )
