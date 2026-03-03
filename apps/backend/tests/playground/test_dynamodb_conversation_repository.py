"""DynamoDB Conversation Repository Integration Tests"""
import pytest
import boto3
from moto import mock_aws
from datetime import datetime, timedelta

from app.playground.infrastructure.repositories.dynamodb_conversation_repository import DynamoDBConversationRepository
from app.playground.domain.entities.conversation import Conversation
from app.playground.domain.value_objects import ConversationId, ConversationStatus


@pytest.fixture
def dynamodb_table():
    """Create mock DynamoDB table"""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

        table = dynamodb.create_table(
            TableName='PlaygroundConversations',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1PK', 'AttributeType': 'S'},
                {'AttributeName': 'GSI1SK', 'AttributeType': 'S'},
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
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        table.wait_until_exists()

        yield table


@pytest.fixture
def repository(dynamodb_table):
    """Create repository with mock table"""
    repo = DynamoDBConversationRepository()
    repo.table = dynamodb_table
    return repo


@pytest.fixture
def sample_conversation():
    """Create sample conversation"""
    return Conversation(
        id=ConversationId("conv-test-123"),
        user_id="user-123",
        agent_id="agent-456",
        agent_version="1.0.0",
        title="테스트 대화",
        message_count=1,
        s3_prefix="sessions/user-123/agent-456/1.0.0/conv-test-123",
        last_message_preview="안녕하세요"
    )


class TestDynamoDBConversationRepository:
    """DynamoDB Conversation Repository 테스트"""

    @pytest.mark.asyncio
    async def test_save_conversation(self, repository, sample_conversation):
        """대화 저장 테스트"""
        # Act
        result = await repository.save(sample_conversation)

        # Assert
        assert result is not None
        assert result.id.value == sample_conversation.id.value

    @pytest.mark.asyncio
    async def test_find_by_id(self, repository, sample_conversation):
        """ID로 대화 조회 테스트"""
        # Arrange
        await repository.save(sample_conversation)

        # Act
        result = await repository.find_by_id(sample_conversation.id.value)

        # Assert
        assert result is not None
        assert result.id.value == sample_conversation.id.value
        assert result.title == sample_conversation.title
        assert result.message_count == sample_conversation.message_count

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository):
        """존재하지 않는 ID 조회 테스트"""
        # Act
        result = await repository.find_by_id("nonexistent-id")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_agent_version(self, repository):
        """Agent/버전별 대화 목록 조회 테스트"""
        # Arrange
        user_id = "user-list-test"
        agent_id = "agent-list-test"
        version = "1.0.0"

        for i in range(3):
            conv = Conversation(
                id=ConversationId(f"conv-list-{i}"),
                user_id=user_id,
                agent_id=agent_id,
                agent_version=version,
                title=f"대화 {i}",
                message_count=i + 1,
                s3_prefix=f"sessions/{user_id}/{agent_id}/{version}/conv-list-{i}"
            )
            await repository.save(conv)

        # Act
        results = await repository.list_by_agent_version(
            user_id, agent_id, version, limit=5
        )

        # Assert
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_list_by_agent_version_with_limit(self, repository):
        """대화 목록 제한 테스트"""
        # Arrange
        user_id = "user-limit-test"
        agent_id = "agent-limit-test"
        version = "1.0.0"

        for i in range(10):
            conv = Conversation(
                id=ConversationId(f"conv-limit-{i}"),
                user_id=user_id,
                agent_id=agent_id,
                agent_version=version,
                title=f"대화 {i}",
                message_count=1,
                s3_prefix=f"sessions/{user_id}/{agent_id}/{version}/conv-limit-{i}"
            )
            await repository.save(conv)

        # Act
        results = await repository.list_by_agent_version(
            user_id, agent_id, version, limit=5
        )

        # Assert
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_count_by_agent_version(self, repository):
        """Agent/버전별 대화 수 조회 테스트"""
        # Arrange
        user_id = "user-count-test"
        agent_id = "agent-count-test"
        version = "1.0.0"

        for i in range(7):
            conv = Conversation(
                id=ConversationId(f"conv-count-{i}"),
                user_id=user_id,
                agent_id=agent_id,
                agent_version=version,
                title=f"대화 {i}",
                message_count=1,
                s3_prefix=f"sessions/{user_id}/{agent_id}/{version}/conv-count-{i}"
            )
            await repository.save(conv)

        # Act
        count = await repository.count_by_agent_version(user_id, agent_id, version)

        # Assert
        assert count == 7

    @pytest.mark.asyncio
    async def test_delete_conversation(self, repository, sample_conversation):
        """대화 삭제 테스트 (soft delete - status만 변경)"""
        # Arrange
        await repository.save(sample_conversation)

        # Act
        await repository.delete(sample_conversation.id.value)

        # Assert - soft delete이므로 레코드는 존재하지만 status가 DELETED
        result = await repository.find_by_id(sample_conversation.id.value)
        assert result is not None
        assert result.status == ConversationStatus.DELETED

    @pytest.mark.asyncio
    async def test_find_oldest_by_agent_version(self, repository):
        """가장 오래된 대화 조회 테스트"""
        # Arrange
        user_id = "user-oldest-test"
        agent_id = "agent-oldest-test"
        version = "1.0.0"

        # 시간차를 두고 대화 생성
        for i in range(3):
            conv = Conversation(
                id=ConversationId(f"conv-oldest-{i}"),
                user_id=user_id,
                agent_id=agent_id,
                agent_version=version,
                title=f"대화 {i}",
                message_count=1,
                s3_prefix=f"sessions/{user_id}/{agent_id}/{version}/conv-oldest-{i}"
            )
            # 생성 시간 조정 (첫 번째가 가장 오래됨)
            conv.created_at = datetime.utcnow() - timedelta(days=3-i)
            conv.updated_at = conv.created_at
            await repository.save(conv)

        # Act
        oldest = await repository.find_oldest_by_agent_version(
            user_id, agent_id, version
        )

        # Assert
        assert oldest is not None
        assert oldest.id.value == "conv-oldest-0"

    @pytest.mark.asyncio
    async def test_update_conversation(self, repository, sample_conversation):
        """대화 업데이트 테스트"""
        # Arrange
        await repository.save(sample_conversation)

        # Act - 메시지 수 증가
        sample_conversation.message_count = 5
        sample_conversation.last_message_preview = "업데이트된 메시지"
        await repository.save(sample_conversation)

        # Assert
        result = await repository.find_by_id(sample_conversation.id.value)
        assert result.message_count == 5
        assert result.last_message_preview == "업데이트된 메시지"
