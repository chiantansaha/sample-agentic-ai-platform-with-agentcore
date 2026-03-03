"""Strands Agent Client - Agent 스펙 기반 동적 Agent 생성"""
from typing import AsyncIterator, Any
import asyncio
import json
import logging

from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters

# Bedrock KB Retrieval Tool (optional)
try:
    from strands_tools import retrieve
    HAS_RETRIEVE_TOOL = True
except ImportError:
    HAS_RETRIEVE_TOOL = False

logger = logging.getLogger(__name__)


class AgentSpec:
    """Agent 설정 스펙"""
    def __init__(
        self,
        model_id: str,
        model_name: str,
        provider: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        mcps: list[str] = None,
        knowledge_bases: list[str] = None
    ):
        self.model_id = model_id
        self.model_name = model_name
        self.provider = provider
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.mcps = mcps or []
        self.knowledge_bases = knowledge_bases or []


class StrandsAgentClient:
    """Strands Agent 클라이언트 - Agent 스펙 기반 동적 생성"""

    def __init__(self):
        self._agents: dict[str, Agent] = {}
        self._mcp_clients: dict[str, list[MCPClient]] = {}

    def _create_bedrock_model(self, spec: AgentSpec) -> BedrockModel:
        """Bedrock 모델 생성"""
        return BedrockModel(
            model_id=spec.model_id,
            temperature=spec.temperature,
            max_tokens=spec.max_tokens
        )

    def _create_mcp_clients(self, mcp_configs: list[str]) -> list[MCPClient]:
        """MCP 클라이언트들 생성

        mcp_configs: MCP 설정 리스트
        지원 형식:
        1. JSON 형식: '{"command": "uvx", "args": ["server@latest"]}'
        2. 간단 형식: "uvx:awslabs.aws-documentation-mcp-server@latest"
        3. MCP ID 형식: "mcp-uuid" (TODO: MCP Management 연동 필요)
        """
        clients = []

        for config in mcp_configs:
            try:
                # JSON 형식
                if config.startswith("{"):
                    parsed = json.loads(config)
                    command = parsed.get("command", "uvx")
                    args = parsed.get("args", [])
                # 간단 형식: "command:arg1,arg2,..."
                elif ":" in config:
                    parts = config.split(":", 1)
                    command = parts[0]
                    args = parts[1].split(",") if len(parts) > 1 else []
                else:
                    # MCP ID 형식 - TODO: MCP Management 연동 필요
                    # 현재는 ID를 uvx 패키지명으로 간주
                    logger.warning(f"MCP ID format not fully supported yet: {config}")
                    command = "uvx"
                    args = [config]

                mcp_client = MCPClient(lambda cmd=command, a=args: stdio_client(
                    StdioServerParameters(command=cmd, args=a)
                ))
                clients.append(mcp_client)

            except Exception as e:
                logger.warning(f"Failed to create MCP client for {config}: {e}")

        return clients

    def _create_kb_tools(self, knowledge_bases: list[str]) -> list:
        """Knowledge Base Retrieval 도구 생성

        knowledge_bases: KB ID 리스트
        - Bedrock KB ID를 사용하여 retrieve 도구 설정
        """
        if not HAS_RETRIEVE_TOOL or not knowledge_bases:
            return []

        # retrieve 도구에 KB ID 설정
        # strands_tools의 retrieve는 환경변수나 설정으로 KB ID를 받음
        # 여러 KB를 사용하는 경우 첫 번째 KB를 기본으로 설정
        # TODO: 다중 KB 지원 개선 필요

        tools = []
        if knowledge_bases:
            # retrieve 도구 추가 (KB ID는 환경변수로 설정)
            import os
            os.environ["BEDROCK_KB_ID"] = knowledge_bases[0]
            tools.append(retrieve)
            logger.info(f"Added retrieve tool with KB: {knowledge_bases[0]}")

        return tools

    def get_or_create_agent(self, agent_id: str, version: str, spec: AgentSpec) -> Agent:
        """Agent 인스턴스 생성 또는 재사용"""
        key = f"{agent_id}:{version}"

        if key not in self._agents:
            # 모델 생성
            model = self._create_bedrock_model(spec)

            # MCP 클라이언트 생성
            mcp_clients = self._create_mcp_clients(spec.mcps)
            self._mcp_clients[key] = mcp_clients

            # Knowledge Base 도구 생성
            kb_tools = self._create_kb_tools(spec.knowledge_bases)

            # Agent 생성
            tools = mcp_clients + kb_tools

            self._agents[key] = Agent(
                model=model,
                tools=tools if tools else None,
                system_prompt=spec.system_prompt
            )

            logger.info(f"Created new Strands Agent: {key} with {len(mcp_clients)} MCPs and {len(kb_tools)} KB tools")

        return self._agents[key]

    async def invoke_agent(
        self,
        agent_id: str,
        version: str,
        spec: AgentSpec,
        message: str,
        messages: list = None
    ) -> dict:
        """Agent 호출 (비스트리밍)

        Returns:
            dict: {
                "content": str,
                "metadata": {
                    "input_tokens": int,
                    "output_tokens": int,
                    "model": str
                }
            }
        """
        agent = self.get_or_create_agent(agent_id, version, spec)

        try:
            # Agent 호출
            result = agent(message)

            # 응답 추출
            content = ""
            if result.message and "content" in result.message:
                for block in result.message["content"]:
                    if "text" in block:
                        content += block["text"]

            # 메트릭 추출
            metrics = result.metrics if hasattr(result, "metrics") else {}

            return {
                "content": content,
                "metadata": {
                    "input_tokens": metrics.get("inputTokens", 0),
                    "output_tokens": metrics.get("outputTokens", 0),
                    "model": spec.model_id
                }
            }

        except Exception as e:
            logger.error(f"Agent invocation error: {e}")
            return {
                "content": f"에이전트 호출 중 오류가 발생했습니다: {str(e)}",
                "metadata": {
                    "error": str(e),
                    "model": spec.model_id
                }
            }

    async def stream_response(
        self,
        agent_id: str,
        version: str,
        spec: AgentSpec,
        message: str,
        messages: list = None
    ) -> AsyncIterator[dict]:
        """스트리밍 응답

        Yields:
            dict: {
                "type": "text" | "tool_use" | "tool_result" | "done",
                "content": str,
                "tool_name": str (optional),
                "metadata": dict (optional)
            }
        """
        agent = self.get_or_create_agent(agent_id, version, spec)

        # 스트리밍을 위한 큐
        queue: asyncio.Queue = asyncio.Queue()

        def streaming_callback(**kwargs):
            """Callback handler for streaming"""
            if "data" in kwargs:
                # 텍스트 청크
                asyncio.get_event_loop().call_soon_threadsafe(
                    queue.put_nowait,
                    {"type": "text", "content": kwargs["data"]}
                )
            elif "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
                # Tool 사용 시작
                tool_name = kwargs["current_tool_use"]["name"]
                asyncio.get_event_loop().call_soon_threadsafe(
                    queue.put_nowait,
                    {"type": "tool_use", "tool_name": tool_name}
                )
            elif "message" in kwargs and kwargs["message"].get("role") == "user":
                # Tool 결과 (toolResult)
                content = kwargs["message"].get("content", [])
                for block in content:
                    if "toolResult" in block:
                        status = block["toolResult"].get("status", "unknown")
                        asyncio.get_event_loop().call_soon_threadsafe(
                            queue.put_nowait,
                            {"type": "tool_result", "status": status}
                        )

        # 원래 callback 저장
        original_callback = agent.callback_handler
        agent.callback_handler = streaming_callback

        try:
            # 백그라운드에서 Agent 실행
            loop = asyncio.get_event_loop()

            async def run_agent():
                try:
                    result = await loop.run_in_executor(None, lambda: agent(message))

                    # 메트릭 전송
                    metrics = result.metrics if hasattr(result, "metrics") else {}
                    await queue.put({
                        "type": "done",
                        "metadata": {
                            "input_tokens": metrics.get("inputTokens", 0),
                            "output_tokens": metrics.get("outputTokens", 0),
                            "model": spec.model_id
                        }
                    })
                except Exception as e:
                    await queue.put({
                        "type": "error",
                        "content": str(e)
                    })

            # Agent 실행 태스크 시작
            task = asyncio.create_task(run_agent())

            # 큐에서 이벤트 읽기
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield event

                    if event["type"] in ("done", "error"):
                        break

                except asyncio.TimeoutError:
                    # 태스크가 완료되었는지 확인
                    if task.done():
                        # 남은 이벤트 처리
                        while not queue.empty():
                            yield await queue.get()
                        break
                    continue

            # 태스크 완료 대기
            await task

        finally:
            # 원래 callback 복원
            agent.callback_handler = original_callback

    def cleanup(self, agent_id: str = None, version: str = None):
        """Agent 리소스 정리"""
        if agent_id and version:
            key = f"{agent_id}:{version}"
            if key in self._agents:
                del self._agents[key]
            if key in self._mcp_clients:
                del self._mcp_clients[key]
        else:
            # 전체 정리
            self._agents.clear()
            self._mcp_clients.clear()
