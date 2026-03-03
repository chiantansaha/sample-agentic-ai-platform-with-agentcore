"""Playground SSE 스트리밍 테스트"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.playground.infrastructure.clients.strands_agent_client import (
    StrandsAgentClient,
    AgentSpec,
)


@pytest.fixture
def agent_spec():
    """Agent 스펙 Fixture"""
    return AgentSpec(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        model_name="Claude 3 Sonnet",
        provider="bedrock",
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        max_tokens=2000,
    )


@pytest.mark.asyncio
async def test_stateless_streaming(agent_spec):
    """Stateless SSE 스트리밍"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-stream"
    version = "1.0.0"
    message = "Tell me a story"

    # Mock streaming response
    async def mock_stream(*args, **kwargs):
        yield {"type": "text", "content": "Once"}
        yield {"type": "text", "content": " upon"}
        yield {"type": "text", "content": " a time"}
        yield {"type": "done", "metadata": {"input_tokens": 10, "output_tokens": 20}}

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.invoke = mock_stream
            mock_agent_class.return_value = mock_agent

            events = []
            async for event in client.stream_response(agent_id, version, agent_spec, message):
                events.append(event)

            # Then
            assert len(events) == 4
            assert events[0]["type"] == "text"
            assert events[0]["content"] == "Once"
            assert events[-1]["type"] == "done"
            assert "metadata" in events[-1]


@pytest.mark.asyncio
async def test_streaming_with_tool_use(agent_spec):
    """도구 사용이 포함된 스트리밍"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-tool-stream"
    version = "1.0.0"
    message = "Search for information"

    # Mock streaming response with tool use
    async def mock_stream(*args, **kwargs):
        yield {"type": "text", "content": "Let me search"}
        yield {"type": "tool_use", "tool_name": "search", "arguments": {"query": "test"}}
        yield {"type": "tool_result", "status": "success", "result": "Found results"}
        yield {"type": "text", "content": "Here are the results"}
        yield {"type": "done"}

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.invoke = mock_stream
            mock_agent_class.return_value = mock_agent

            events = []
            async for event in client.stream_response(agent_id, version, agent_spec, message):
                events.append(event)

            # Then
            assert len(events) == 5
            assert events[1]["type"] == "tool_use"
            assert events[1]["tool_name"] == "search"
            assert events[2]["type"] == "tool_result"
            assert events[2]["status"] == "success"


@pytest.mark.asyncio
async def test_streaming_error_handling(agent_spec):
    """스트리밍 에러 처리"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-error"
    version = "1.0.0"
    message = "Cause an error"

    # Mock streaming response with error
    async def mock_stream(*args, **kwargs):
        yield {"type": "text", "content": "Starting"}
        yield {"type": "error", "content": "Something went wrong"}

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.invoke = mock_stream
            mock_agent_class.return_value = mock_agent

            events = []
            async for event in client.stream_response(agent_id, version, agent_spec, message):
                events.append(event)

            # Then
            assert len(events) == 2
            assert events[-1]["type"] == "error"
            assert "Something went wrong" in events[-1]["content"]


@pytest.mark.asyncio
async def test_streaming_with_conversation_history(agent_spec):
    """대화 이력이 포함된 스트리밍"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-history"
    version = "1.0.0"
    message = "Continue the conversation"
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    # Mock streaming response
    async def mock_stream(*args, **kwargs):
        yield {"type": "text", "content": "Continuing"}
        yield {"type": "done"}

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.invoke = mock_stream
            mock_agent_class.return_value = mock_agent

            events = []
            async for event in client.stream_response(
                agent_id, version, agent_spec, message, messages=messages
            ):
                events.append(event)

            # Then
            assert len(events) == 2
            mock_agent.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_streaming_metadata(agent_spec):
    """스트리밍 메타데이터 검증"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-metadata"
    version = "1.0.0"
    message = "Test metadata"

    # Mock streaming response with metadata
    async def mock_stream(*args, **kwargs):
        yield {"type": "text", "content": "Response"}
        yield {
            "type": "done",
            "metadata": {
                "input_tokens": 100,
                "output_tokens": 200,
                "model": "claude-3-sonnet",
                "latency_ms": 1500,
            },
        }

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.invoke = mock_stream
            mock_agent_class.return_value = mock_agent

            events = []
            async for event in client.stream_response(agent_id, version, agent_spec, message):
                events.append(event)

            # Then
            done_event = events[-1]
            assert done_event["type"] == "done"
            assert done_event["metadata"]["input_tokens"] == 100
            assert done_event["metadata"]["output_tokens"] == 200
            assert done_event["metadata"]["model"] == "claude-3-sonnet"


@pytest.mark.asyncio
async def test_streaming_empty_response(agent_spec):
    """빈 응답 스트리밍"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-empty"
    version = "1.0.0"
    message = "Empty response"

    # Mock empty streaming response
    async def mock_stream(*args, **kwargs):
        yield {"type": "done"}

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.invoke = mock_stream
            mock_agent_class.return_value = mock_agent

            events = []
            async for event in client.stream_response(agent_id, version, agent_spec, message):
                events.append(event)

            # Then
            assert len(events) == 1
            assert events[0]["type"] == "done"


@pytest.mark.asyncio
async def test_streaming_large_response(agent_spec):
    """대용량 응답 스트리밍"""
    # Given
    client = StrandsAgentClient()
    agent_id = "agent-large"
    version = "1.0.0"
    message = "Generate large response"

    # Mock large streaming response
    async def mock_stream(*args, **kwargs):
        for i in range(100):
            yield {"type": "text", "content": f"Chunk {i}"}
        yield {"type": "done"}

    # When
    with patch("app.playground.infrastructure.clients.strands_agent_client.BedrockModel"):
        with patch("app.playground.infrastructure.clients.strands_agent_client.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.invoke = mock_stream
            mock_agent_class.return_value = mock_agent

            events = []
            async for event in client.stream_response(agent_id, version, agent_spec, message):
                events.append(event)

            # Then
            assert len(events) == 101
            assert all(e["type"] in ["text", "done"] for e in events)
