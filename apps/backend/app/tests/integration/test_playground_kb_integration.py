"""Playground-KB 통합 테스트"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.playground.infrastructure.clients.strands_agent_client import (
    StrandsAgentClient,
    AgentSpec,
)


@pytest.fixture
def agent_spec_with_kb():
    """KB가 포함된 Agent 스펙"""
    return AgentSpec(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        model_name="Claude 3 Sonnet",
        provider="bedrock",
        system_prompt="You are a helpful assistant with access to knowledge bases.",
        temperature=0.7,
        max_tokens=2000,
        knowledge_bases=["bedrock-kb-123", "bedrock-kb-456"],
    )


@pytest.mark.asyncio
async def test_create_kb_retrieve_tool(agent_spec_with_kb):
    """KB Retrieve 도구 생성"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-kb"
    version = "1.0.0"

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            with patch("app.playground.infrastructure.clients.strands_agent_client.retrieve") as mock_retrieve:
                mock_retrieve.return_value = MagicMock()
                mock_agent = MagicMock()
                mock_agent_class.return_value = mock_agent

                agent = client.get_or_create_agent(agent_id, version, agent_spec_with_kb)

                # Then
                assert agent is not None
                assert len(agent_spec_with_kb.knowledge_bases) == 2
                # retrieve 함수가 KB 개수만큼 호출되었는지 확인
                assert mock_retrieve.call_count == 2


@pytest.mark.asyncio
async def test_agent_with_single_kb():
    """단일 KB를 가진 Agent"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-single-kb"
    version = "1.0.0"
    spec = AgentSpec(
        model_id="test-model",
        model_name="Test Model",
        provider="bedrock",
        system_prompt="Test prompt",
        knowledge_bases=["bedrock-kb-123"],
    )

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            with patch("app.playground.infrastructure.clients.strands_agent_client.retrieve") as mock_retrieve:
                mock_retrieve.return_value = MagicMock()
                mock_agent = MagicMock()
                mock_agent_class.return_value = mock_agent

                agent = client.get_or_create_agent(agent_id, version, spec)

                # Then
                assert agent is not None
                mock_retrieve.assert_called_once()


@pytest.mark.asyncio
async def test_kb_retrieve_in_streaming(agent_spec_with_kb):
    """스트리밍 중 KB Retrieve 도구 사용"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-kb-stream"
    version = "1.0.0"
    message = "Search in knowledge base"

    # Mock streaming response with KB retrieve
    async def mock_stream(*args, **kwargs):
        yield {"type": "text", "content": "Searching"}
        yield {
            "type": "tool_use",
            "tool_name": "retrieve",
            "arguments": {"query": "test query"},
        }
        yield {
            "type": "tool_result",
            "status": "success",
            "result": "Found documents",
        }
        yield {"type": "text", "content": "Based on the documents"}
        yield {"type": "done"}

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            with patch("app.playground.infrastructure.clients.strands_agent_client.retrieve"):
                mock_agent = MagicMock()
                mock_agent.invoke = mock_stream
                mock_agent_class.return_value = mock_agent

                events = []
                async for event in client.stream_response(
                    agent_id, version, agent_spec_with_kb, message
                ):
                    events.append(event)

                # Then
                assert len(events) == 5
                tool_use_event = events[1]
                assert tool_use_event["type"] == "tool_use"
                assert tool_use_event["tool_name"] == "retrieve"
                tool_result_event = events[2]
                assert tool_result_event["type"] == "tool_result"
                assert tool_result_event["status"] == "success"


@pytest.mark.asyncio
async def test_multiple_kb_retrieves():
    """여러 KB에서 순차적으로 검색"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-multi-kb-retrieve"
    version = "1.0.0"
    spec = AgentSpec(
        model_id="test-model",
        model_name="Test Model",
        provider="bedrock",
        system_prompt="Test prompt",
        knowledge_bases=["kb-1", "kb-2", "kb-3"],
    )
    message = "Search in all knowledge bases"

    # Mock streaming response with multiple KB retrieves
    async def mock_stream(*args, **kwargs):
        yield {"type": "tool_use", "tool_name": "retrieve", "kb_id": "kb-1"}
        yield {"type": "tool_result", "status": "success", "kb_id": "kb-1"}
        yield {"type": "tool_use", "tool_name": "retrieve", "kb_id": "kb-2"}
        yield {"type": "tool_result", "status": "success", "kb_id": "kb-2"}
        yield {"type": "text", "content": "Combined results"}
        yield {"type": "done"}

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            with patch("app.playground.infrastructure.clients.strands_agent_client.retrieve"):
                mock_agent = MagicMock()
                mock_agent.invoke = mock_stream
                mock_agent_class.return_value = mock_agent

                events = []
                async for event in client.stream_response(agent_id, version, spec, message):
                    events.append(event)

                # Then
                tool_use_events = [e for e in events if e["type"] == "tool_use"]
                assert len(tool_use_events) == 2


@pytest.mark.asyncio
async def test_kb_retrieve_error_handling():
    """KB Retrieve 에러 처리"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-kb-error"
    version = "1.0.0"
    spec = AgentSpec(
        model_id="test-model",
        model_name="Test Model",
        provider="bedrock",
        system_prompt="Test prompt",
        knowledge_bases=["invalid-kb"],
    )
    message = "Search in invalid KB"

    # Mock streaming response with KB error
    async def mock_stream(*args, **kwargs):
        yield {"type": "tool_use", "tool_name": "retrieve"}
        yield {
            "type": "tool_result",
            "status": "error",
            "error": "KB not found",
        }
        yield {"type": "text", "content": "Unable to retrieve"}
        yield {"type": "done"}

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            with patch("app.playground.infrastructure.clients.strands_agent_client.retrieve"):
                mock_agent = MagicMock()
                mock_agent.invoke = mock_stream
                mock_agent_class.return_value = mock_agent

                events = []
                async for event in client.stream_response(agent_id, version, spec, message):
                    events.append(event)

                # Then
                tool_result_event = [e for e in events if e["type"] == "tool_result"][0]
                assert tool_result_event["status"] == "error"
                assert "KB not found" in tool_result_event["error"]


@pytest.mark.asyncio
async def test_agent_without_kb():
    """KB가 없는 Agent"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-no-kb"
    version = "1.0.0"
    spec = AgentSpec(
        model_id="test-model",
        model_name="Test Model",
        provider="bedrock",
        system_prompt="Test prompt",
        knowledge_bases=[],  # KB 없음
    )

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            with patch("app.playground.infrastructure.clients.strands_agent_client.retrieve") as mock_retrieve:
                mock_agent = MagicMock()
                mock_agent_class.return_value = mock_agent

                agent = client.get_or_create_agent(agent_id, version, spec)

                # Then
                assert agent is not None
                mock_retrieve.assert_not_called()  # retrieve 함수 호출 안 됨


@pytest.mark.asyncio
async def test_kb_retrieve_with_filters():
    """필터가 포함된 KB Retrieve"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-kb-filter"
    version = "1.0.0"
    spec = AgentSpec(
        model_id="test-model",
        model_name="Test Model",
        provider="bedrock",
        system_prompt="Test prompt",
        knowledge_bases=["kb-1"],
    )
    message = "Search with filters"

    # Mock streaming response with filtered retrieve
    async def mock_stream(*args, **kwargs):
        yield {
            "type": "tool_use",
            "tool_name": "retrieve",
            "arguments": {
                "query": "test",
                "filters": {"category": "documentation"},
            },
        }
        yield {"type": "tool_result", "status": "success"}
        yield {"type": "done"}

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            with patch("app.playground.infrastructure.clients.strands_agent_client.retrieve"):
                mock_agent = MagicMock()
                mock_agent.invoke = mock_stream
                mock_agent_class.return_value = mock_agent

                events = []
                async for event in client.stream_response(agent_id, version, spec, message):
                    events.append(event)

                # Then
                tool_use_event = events[0]
                assert "filters" in tool_use_event["arguments"]
