"""Pytest Configuration and Fixtures"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_dynamodb_table():
    """Mock DynamoDB Table"""
    return MagicMock()


@pytest.fixture
def mock_s3_client():
    """Mock S3 Client"""
    return MagicMock()


@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock Agent Runtime Client"""
    return MagicMock()


# Common test data fixtures
@pytest.fixture
def sample_agent_config():
    """Sample Agent Configuration"""
    return {
        "agent_id": "test-agent-123",
        "agent_name": "Test Agent",
        "version": "1.0.0",
        "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
        "system_prompt": "You are a helpful assistant.",
        "temperature": 0.7,
        "max_tokens": 2000,
        "knowledge_bases": []
    }


@pytest.fixture
def sample_user_id():
    """Sample User ID"""
    return "test-user-123"


@pytest.fixture
def sample_deployment_id():
    """Sample Deployment ID"""
    return "test-deployment-456"


@pytest.fixture
def sample_conversation_id():
    """Sample Conversation ID"""
    return "test-conversation-789"
