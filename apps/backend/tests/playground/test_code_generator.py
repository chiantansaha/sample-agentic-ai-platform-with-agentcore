"""Agent Code Generator Tests"""
import pytest
from app.playground.infrastructure.code_generator import AgentCodeGenerator


@pytest.fixture
def code_generator():
    return AgentCodeGenerator()


class TestAgentCodeGenerator:
    """AgentCodeGenerator 테스트"""

    def test_generate_basic_agent(self, code_generator):
        """기본 Agent 코드 생성 테스트"""
        # Arrange
        agent_config = {
            "agent_id": "agent-123",
            "agent_name": "Test Agent",
            "version": "1.0.0",
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "system_prompt": "You are a helpful assistant.",
            "temperature": 0.7,
            "max_tokens": 2000,
            "knowledge_bases": []
        }

        # Act
        files = code_generator.generate(agent_config)

        # Assert
        assert "agent.py" in files
        assert "requirements.txt" in files
        assert "strands-agents" in files["requirements.txt"]
        assert "bedrock-agentcore" in files["requirements.txt"]
        # AgentCore Runtime entrypoint
        assert "@app.entrypoint" in files["agent.py"]
        assert "def invoke" in files["agent.py"]
        assert "BedrockAgentCoreApp" in files["agent.py"]

    def test_generate_agent_with_knowledge_bases(self, code_generator):
        """Knowledge Base가 있는 Agent 코드 생성 테스트"""
        # Arrange
        agent_config = {
            "agent_id": "agent-123",
            "agent_name": "KB Agent",
            "version": "1.0.0",
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "system_prompt": "You can search knowledge bases.",
            "temperature": 0.7,
            "max_tokens": 2000,
            "knowledge_bases": [
                {"id": "kb-001", "name": "Product KB"},
                {"id": "kb-002", "name": "FAQ KB"}
            ]
        }

        # Act
        files = code_generator.generate(agent_config)

        # Assert
        assert "agent.py" in files
        assert "kb_tools.py" in files
        assert "requirements.txt" in files
        # KB IDs are embedded in agent.py as KB_IDS variable
        assert "kb-001" in files["agent.py"]
        assert "kb-002" in files["agent.py"]
        # kb_tools.py contains the utility functions
        assert "create_kb_tools" in files["kb_tools.py"]

    def test_generate_agent_with_session_manager(self, code_generator):
        """Session Manager가 있는 Agent 코드 생성 테스트"""
        # Arrange
        agent_config = {
            "agent_id": "agent-123",
            "agent_name": "Session Agent",
            "version": "1.0.0",
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "system_prompt": "You maintain conversation state.",
            "temperature": 0.7,
            "max_tokens": 2000,
            "knowledge_bases": []
        }

        # Act
        files = code_generator.generate(
            agent_config,
            session_bucket="my-bucket",
            session_prefix="sessions/user/agent"
        )

        # Assert
        assert "agent.py" in files
        assert "my-bucket" in files["agent.py"]
        assert "sessions/user/agent" in files["agent.py"]

    def test_generate_s3_prefix(self, code_generator):
        """S3 prefix 생성 테스트"""
        # Arrange
        user_id = "user-123"
        agent_id = "agent-456"
        version = "1.0.0"
        deployment_id = "deploy-789"

        # Act
        prefix = code_generator.generate_s3_prefix(
            user_id, agent_id, version, deployment_id
        )

        # Assert
        assert prefix == "agents/user-123/agent-456/1.0.0/deploy-789"

    def test_generate_with_normalized_kb_ids(self, code_generator):
        """KB ID 정규화 테스트 (string 형식)"""
        # Arrange
        agent_config = {
            "agent_id": "agent-123",
            "agent_name": "Test Agent",
            "version": "1.0.0",
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "system_prompt": "Test",
            "knowledge_bases": ["kb-string-id-001"]  # String 형식
        }

        # Act
        files = code_generator.generate(agent_config)

        # Assert - KB IDs are embedded in agent.py as KB_IDS variable
        assert "agent.py" in files
        assert "kb_tools.py" in files
        assert "kb-string-id-001" in files["agent.py"]


class TestTemplateRendering:
    """템플릿 렌더링 테스트"""

    def test_agent_template_contains_entrypoint(self, code_generator):
        """agent.py에 AgentCore Runtime entrypoint가 포함되어 있는지 테스트"""
        # Arrange
        agent_config = {
            "agent_id": "agent-123",
            "agent_name": "Test",
            "version": "1.0.0",
            "model_id": "test-model",
            "system_prompt": "Test prompt"
        }

        # Act
        files = code_generator.generate(agent_config)

        # Assert - AgentCore Runtime entrypoint
        assert "@app.entrypoint" in files["agent.py"]
        assert "def invoke" in files["agent.py"]
        assert "BedrockAgentCoreApp" in files["agent.py"]
        assert "Agent(" in files["agent.py"]
        # /invocations and /ping endpoint documentation
        assert "/invocations" in files["agent.py"]
        assert "/ping" in files["agent.py"]

    def test_requirements_contains_core_deps(self, code_generator):
        """requirements.txt에 핵심 의존성이 포함되어 있는지 테스트"""
        # Arrange
        agent_config = {
            "agent_id": "agent-123",
            "agent_name": "Test",
            "version": "1.0.0",
            "model_id": "test-model",
            "system_prompt": "Test prompt"
        }

        # Act
        files = code_generator.generate(agent_config)

        # Assert
        assert "strands-agents" in files["requirements.txt"]
        assert "boto3" in files["requirements.txt"]
