"""DynamoDB Deployment Repository Integration Tests"""
import pytest
import boto3
from moto import mock_aws
from datetime import datetime

from app.playground.infrastructure.repositories.dynamodb_deployment_repository import DynamoDBDeploymentRepository
from app.playground.domain.entities.deployment import Deployment
from app.playground.domain.value_objects import DeploymentId, DeploymentStatus


@pytest.fixture
def dynamodb_table():
    """Create mock DynamoDB table"""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

        table = dynamodb.create_table(
            TableName='PlaygroundDeployments',
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
    repo = DynamoDBDeploymentRepository()
    repo.table = dynamodb_table
    return repo


@pytest.fixture
def sample_deployment():
    """Create sample deployment"""
    return Deployment(
        id=DeploymentId("deploy-test-123"),
        user_id="user-123",
        agent_id="agent-456",
        agent_version="1.0.0"
    )


class TestDynamoDBDeploymentRepository:
    """DynamoDB Deployment Repository 테스트"""

    @pytest.mark.asyncio
    async def test_save_deployment(self, repository, sample_deployment):
        """배포 저장 테스트"""
        # Act
        result = await repository.save(sample_deployment)

        # Assert
        assert result is not None
        assert result.id.value == sample_deployment.id.value

    @pytest.mark.asyncio
    async def test_find_by_id(self, repository, sample_deployment):
        """ID로 배포 조회 테스트"""
        # Arrange
        await repository.save(sample_deployment)

        # Act
        result = await repository.find_by_id(sample_deployment.id.value)

        # Assert
        assert result is not None
        assert result.id.value == sample_deployment.id.value
        assert result.user_id == sample_deployment.user_id
        assert result.agent_id == sample_deployment.agent_id

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository):
        """존재하지 않는 ID 조회 테스트"""
        # Act
        result = await repository.find_by_id("nonexistent-id")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_user_agent_version(self, repository, sample_deployment):
        """사용자/Agent/버전으로 조회 테스트 (READY 상태만 조회됨)"""
        # Arrange - READY 상태로 설정해야 조회됨
        sample_deployment.status = DeploymentStatus.READY
        await repository.save(sample_deployment)

        # Act
        result = await repository.find_by_user_agent_version(
            sample_deployment.user_id,
            sample_deployment.agent_id,
            sample_deployment.agent_version
        )

        # Assert
        assert result is not None
        assert result.id.value == sample_deployment.id.value

    @pytest.mark.asyncio
    async def test_find_active_by_user(self, repository):
        """사용자의 활성 배포 목록 조회 테스트"""
        # Arrange
        user_id = "user-active-test"

        # 활성 배포 생성
        active_deployment = Deployment(
            id=DeploymentId("deploy-active-1"),
            user_id=user_id,
            agent_id="agent-1",
            agent_version="1.0.0"
        )
        active_deployment.status = DeploymentStatus.READY
        await repository.save(active_deployment)

        # 비활성 배포 생성
        inactive_deployment = Deployment(
            id=DeploymentId("deploy-inactive-1"),
            user_id=user_id,
            agent_id="agent-2",
            agent_version="1.0.0"
        )
        inactive_deployment.status = DeploymentStatus.DELETED
        await repository.save(inactive_deployment)

        # Act
        results = await repository.find_active_by_user(user_id)

        # Assert
        assert len(results) == 1
        assert results[0].id.value == "deploy-active-1"

    @pytest.mark.asyncio
    async def test_delete_deployment(self, repository, sample_deployment):
        """배포 삭제 테스트"""
        # Arrange
        await repository.save(sample_deployment)

        # Act
        await repository.delete(sample_deployment.id.value)

        # Assert
        result = await repository.find_by_id(sample_deployment.id.value)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_deployment_status(self, repository, sample_deployment):
        """배포 상태 업데이트 테스트"""
        # Arrange
        await repository.save(sample_deployment)

        # Act - 상태 변경
        sample_deployment.status = DeploymentStatus.READY
        sample_deployment.runtime_id = "runtime-123"
        sample_deployment.runtime_arn = "arn:aws:runtime"
        await repository.save(sample_deployment)

        # Assert
        result = await repository.find_by_id(sample_deployment.id.value)
        assert result.status == DeploymentStatus.READY
        assert result.runtime_id == "runtime-123"
