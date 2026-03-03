"""로컬 채팅 비즈니스 로직"""
import asyncio
import logging
import re
from typing import AsyncIterator

from app.agent.infrastructure.local_agent_runner import local_agent_runner
from app.agent.infrastructure.repositories.dynamodb_agent_repository import DynamoDBAgentRepository

logger = logging.getLogger(__name__)


class StreamingXMLFilter:
    """스트리밍 텍스트에서 XML 태그를 파싱하여 progress 이벤트로 변환

    청크가 태그 중간에서 잘릴 수 있음을 고려:
    - "<inv" + "oke name=...>"
    - "</thin" + "king>"
    """

    # 감지할 태그 이름들
    KNOWN_TAGS = ['invoke', 'function_calls', 'thinking', 'parameter', 'function_result']

    def __init__(self):
        self.buffer = ""
        self.in_tag = False
        self.current_tag_type = None
        self.current_tool_name = None
        self.current_tag_content = ""  # thinking 등 태그 내용 저장
        self.tag_id_counter = 0

    def _could_be_partial_tag(self, text: str) -> bool:
        """텍스트 끝이 부분 태그일 가능성이 있는지 확인

        예: "<inv", "</think", "<function_c" 등
        """
        # '<'로 시작하는 부분 찾기
        last_lt = text.rfind('<')
        if last_lt == -1:
            return False

        partial = text[last_lt:]

        # 이미 완성된 태그인지 확인 (닫는 '>' 있음)
        if '>' in partial:
            return False

        # 알려진 태그의 시작일 수 있는지 확인
        partial_lower = partial.lower()
        for tag in self.KNOWN_TAGS:
            # "<tag" 또는 "</tag" 패턴
            if f"<{tag}"[:len(partial)] == partial_lower:
                return True
            if f"</{tag}"[:len(partial)] == partial_lower:
                return True

        # "<" 하나만 있는 경우도 대기
        if partial == '<':
            return True

        return False

    def _extract_tag_info(self, tag_str: str) -> tuple[str, str]:
        """태그 문자열에서 타입과 이름 추출

        Returns: (tag_type, tool_name)
        """
        tag_lower = tag_str.lower()

        if '<invoke' in tag_lower:
            # name 속성 추출
            match = re.search(r'name="([^"]*)"', tag_str)
            tool_name = match.group(1) if match else "Unknown"
            return ('invoke', tool_name)
        elif '<function_calls' in tag_lower:
            return ('function_calls', None)
        elif '<thinking' in tag_lower:
            return ('thinking', None)
        elif '<parameter' in tag_lower:
            return ('parameter', None)
        elif '<function_result' in tag_lower:
            return ('function_result', None)

        return (None, None)

    def process_chunk(self, chunk: str) -> list[dict]:
        """청크를 처리하고 이벤트 리스트 반환"""
        events = []
        self.buffer += chunk

        while True:
            if not self.in_tag:
                # 일반 모드: 태그 시작 '<' 찾기
                lt_pos = self.buffer.find('<')

                if lt_pos == -1:
                    # '<' 없음 - 전체 버퍼 출력 가능
                    if self.buffer.strip():
                        events.append({"type": "text", "content": self.buffer})
                    self.buffer = ""
                    break

                # '<' 이전 텍스트 출력
                if lt_pos > 0:
                    text_before = self.buffer[:lt_pos]
                    if text_before.strip():
                        events.append({"type": "text", "content": text_before})
                    self.buffer = self.buffer[lt_pos:]

                # '>' 찾아서 완전한 태그인지 확인
                gt_pos = self.buffer.find('>')
                if gt_pos == -1:
                    # 아직 태그가 완성되지 않음 - 대기
                    break

                # 완전한 태그 추출
                tag_str = self.buffer[:gt_pos + 1]
                tag_type, tool_name = self._extract_tag_info(tag_str)

                if tag_type:
                    # 종료 태그인지 확인
                    if tag_str.startswith('</'):
                        # 종료 태그 - 현재 진행 중인 게 있으면 완료 처리
                        # (단독 종료 태그는 무시)
                        pass
                    else:
                        # 시작 태그 - progress 이벤트 생성
                        self.in_tag = True
                        self.current_tag_type = tag_type
                        self.current_tool_name = tool_name

                        if tag_type == 'invoke':
                            # KB 도구는 retrieve_from_xxx 형태
                            if tool_name and tool_name.startswith('retrieve_from_'):
                                kb_name = tool_name.replace('retrieve_from_', '').replace('_', ' ')
                                label = f"KB '{kb_name}' 조회"
                            else:
                                label = f"{tool_name}"
                        elif tag_type == 'thinking':
                            label = "생각"
                            self.current_tag_content = ""  # thinking 내용 저장 시작
                        elif tag_type == 'function_calls':
                            # function_calls는 건너뛰기 (invoke에서 구체적인 툴 이름이 나옴)
                            self.buffer = self.buffer[gt_pos + 1:]
                            continue
                        elif tag_type == 'function_result':
                            # function_result도 건너뛰기 (invoke done에서 이미 표시됨)
                            self.buffer = self.buffer[gt_pos + 1:]
                            continue
                        else:
                            label = "처리"

                        self.tag_id_counter += 1
                        events.append({
                            "type": "progress",
                            "id": str(self.tag_id_counter),
                            "status": "start",
                            "label": label
                        })

                    self.buffer = self.buffer[gt_pos + 1:]
                else:
                    # 알 수 없는 태그 - '<' 건너뛰고 계속
                    if self.buffer:
                        events.append({"type": "text", "content": self.buffer[0]})
                        self.buffer = self.buffer[1:]
            else:
                # 태그 내부: 종료 태그 찾기
                end_tag = f"</{self.current_tag_type}>"
                end_pos = self.buffer.lower().find(end_tag.lower())

                if end_pos != -1:
                    # 종료 태그 발견 - thinking인 경우 내용 저장
                    if self.current_tag_type == 'thinking':
                        self.current_tag_content += self.buffer[:end_pos]

                    if self.current_tag_type == 'invoke':
                        # KB 도구는 retrieve_from_xxx 형태
                        if self.current_tool_name and self.current_tool_name.startswith('retrieve_from_'):
                            kb_name = self.current_tool_name.replace('retrieve_from_', '').replace('_', ' ')
                            label = f"KB '{kb_name}' 조회"
                        else:
                            label = f"{self.current_tool_name}"
                    elif self.current_tag_type == 'thinking':
                        label = "생각"
                    elif self.current_tag_type in ('function_calls', 'function_result'):
                        # function_calls, function_result 종료는 무시
                        self.buffer = self.buffer[end_pos + len(end_tag):]
                        self.in_tag = False
                        self.current_tag_type = None
                        self.current_tool_name = None
                        continue
                    else:
                        label = "처리"

                    # done 이벤트 생성
                    done_event = {
                        "type": "progress",
                        "id": str(self.tag_id_counter),
                        "status": "done",
                        "label": label
                    }
                    # thinking인 경우 content 포함
                    if self.current_tag_type == 'thinking' and self.current_tag_content.strip():
                        done_event["content"] = self.current_tag_content.strip()

                    events.append(done_event)

                    self.buffer = self.buffer[end_pos + len(end_tag):]
                    self.in_tag = False
                    self.current_tag_type = None
                    self.current_tool_name = None
                    self.current_tag_content = ""
                else:
                    # 종료 태그 아직 없음 - 부분 종료 태그 확인
                    if self._could_be_partial_tag(self.buffer):
                        # thinking인 경우 버퍼 내용을 content에 저장 (부분 태그 제외)
                        if self.current_tag_type == 'thinking':
                            last_lt = self.buffer.rfind('<')
                            if last_lt > 0:
                                self.current_tag_content += self.buffer[:last_lt]
                                self.buffer = self.buffer[last_lt:]
                        break
                    # thinking인 경우 버퍼 내용 저장
                    if self.current_tag_type == 'thinking':
                        self.current_tag_content += self.buffer
                    self.buffer = ""
                    break

        return events

    def flush(self) -> list[dict]:
        """남은 버퍼 플러시 (스트림 종료 시)"""
        events = []

        # 진행 중인 태그가 있으면 완료 처리
        if self.in_tag:
            # function_calls, function_result는 무시
            if self.current_tag_type in ('function_calls', 'function_result'):
                self.in_tag = False
            else:
                # thinking인 경우 남은 버퍼 내용도 저장
                if self.current_tag_type == 'thinking':
                    self.current_tag_content += self.buffer

                if self.current_tag_type == 'invoke':
                    # KB 도구는 retrieve_from_xxx 형태
                    if self.current_tool_name and self.current_tool_name.startswith('retrieve_from_'):
                        kb_name = self.current_tool_name.replace('retrieve_from_', '').replace('_', ' ')
                        label = f"KB '{kb_name}' 조회"
                    else:
                        label = f"{self.current_tool_name}"
                elif self.current_tag_type == 'thinking':
                    label = "생각"
                else:
                    label = "처리"

                done_event = {
                    "type": "progress",
                    "id": str(self.tag_id_counter),
                    "status": "done",
                    "label": label
                }
                # thinking인 경우 content 포함
                if self.current_tag_type == 'thinking' and self.current_tag_content.strip():
                    done_event["content"] = self.current_tag_content.strip()

                events.append(done_event)
                self.in_tag = False
                self.current_tag_content = ""

        # 남은 텍스트 출력 (XML 태그 제거)
        if self.buffer.strip():
            # 남은 버퍼에서 XML 패턴 제거
            clean_text = re.sub(r'<[^>]*>', '', self.buffer)
            if clean_text.strip():
                events.append({"type": "text", "content": clean_text})

        self.buffer = ""
        return events


class LocalChatService:
    """로컬 Agent 채팅 서비스"""

    def __init__(self):
        self.agent_repo = DynamoDBAgentRepository()

    async def prepare_agent(
        self,
        agent_id: str,
        user_id: str,
        system_prompt: str,
        model: str,
        mcp_ids: list[str],
        kb_ids: list[str],
    ) -> str:
        """Agent 준비 및 세션 ID 반환"""
        # Agent 존재 확인 (temp-로 시작하는 신규 Agent는 DB 조회 스킵)
        if not agent_id.startswith("temp-"):
            agent = await self.agent_repo.find_by_id(agent_id)
            if not agent:
                raise ValueError(f"Agent not found: {agent_id}")

        # 로컬 Agent 생성 (MCP 설정 조회가 async이므로 await 필요)
        session_id = await local_agent_runner.create_agent(
            agent_id=agent_id,
            user_id=user_id,
            system_prompt=system_prompt,
            model=model,
            mcp_ids=mcp_ids,
            kb_ids=kb_ids,
        )

        logger.info(f"Local agent prepared: {session_id} for agent {agent_id}")
        return session_id

    async def stream_chat(
        self,
        session_id: str,
        message: str,
    ) -> AsyncIterator[dict]:
        """채팅 응답 스트리밍 (XML 태그 필터링 포함)"""
        agent = local_agent_runner.get_agent(session_id)
        if not agent:
            raise ValueError(f"Session not found: {session_id}")

        # 스트리밍을 위한 큐
        queue: asyncio.Queue = asyncio.Queue()

        # XML 필터 인스턴스
        xml_filter = StreamingXMLFilter()

        # 중복 로깅 방지를 위한 tool_id 추적
        logged_tool_ids = set()

        def streaming_callback(**kwargs):
            """Callback handler for streaming (XML 태그 필터링)"""
            try:
                # 1. 텍스트 스트림 데이터
                if "data" in kwargs:
                    data = kwargs["data"]
                    logger.info(f"[STRANDS] data: {repr(data)}")
                    events = xml_filter.process_chunk(data)
                    for evt in events:
                        if evt.get("type") == "text":
                            content = evt.get("content", "")
                            # 의미있는 텍스트만 로깅 (공백 제외, 50자 이상)
                            if len(content.strip()) > 50:
                                logger.info(f"[STREAM] 텍스트: {content[:80]}...")
                        asyncio.get_event_loop().call_soon_threadsafe(
                            queue.put_nowait,
                            evt
                        )

                # 2. MCP/KB 도구 호출 시작
                elif "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
                    tool_use = kwargs["current_tool_use"]
                    tool_name = tool_use.get("name")
                    tool_id = tool_use.get("toolUseId", "")
                    tool_input = tool_use.get("input", {})

                    # 중복 로깅 방지: 이미 로깅한 tool_id는 스킵
                    if tool_id not in logged_tool_ids:
                        logged_tool_ids.add(tool_id)

                        # MCP 도구인지 KB 도구인지 구분하여 로깅
                        if tool_name.startswith("retrieve_from_"):
                            kb_name = tool_name.replace("retrieve_from_", "").replace("_", " ")
                            logger.info(f"[MCP] KB 조회 시작: {kb_name} | 입력: {tool_input}")
                        else:
                            # MCP 도구: 전체 입력 파라미터 로깅
                            import json
                            try:
                                input_str = json.dumps(tool_input, ensure_ascii=False, default=str)
                            except Exception:
                                input_str = str(tool_input)
                            logger.info(f"[MCP] 도구 호출: {tool_name}")
                            logger.info(f"[MCP] 입력 파라미터: {input_str}")

                    asyncio.get_event_loop().call_soon_threadsafe(
                        queue.put_nowait,
                        {"type": "tool_use", "tool_name": tool_name, "tool_id": tool_id}
                    )

                # 3. 도구 실행 결과
                elif "message" in kwargs:
                    msg = kwargs["message"]
                    role = msg.get("role", "unknown")

                    if role == "user":
                        content = msg.get("content", [])
                        for block in content:
                            if "toolResult" in block:
                                tool_result = block["toolResult"]
                                status = tool_result.get("status", "unknown")
                                tool_use_id = tool_result.get("toolUseId", "")
                                result_content = tool_result.get("content", [])

                                # 도구 결과 로깅 (성공/실패 모두)
                                if status == "success":
                                    # 결과 미리보기 (첫 번째 텍스트 블록)
                                    preview = ""
                                    for item in result_content:
                                        if isinstance(item, dict) and "text" in item:
                                            preview = item["text"][:100]
                                            break
                                    logger.info(f"[MCP] 도구 완료: {status} | 결과: {preview}...")
                                else:
                                    logger.error(f"[MCP] 도구 실패: {result_content}")

                                asyncio.get_event_loop().call_soon_threadsafe(
                                    queue.put_nowait,
                                    {"type": "tool_result", "status": status, "tool_id": tool_use_id}
                                )
                # 그 외 이벤트는 무시 (stop_reason 등)
            except Exception as e:
                logger.error(f"Callback error: {e}", exc_info=True)

        # 원래 callback 저장 및 교체
        original_callback = agent.callback_handler
        agent.callback_handler = streaming_callback

        try:
            # 백그라운드에서 Agent 실행
            loop = asyncio.get_event_loop()

            async def run_agent():
                logger.info(f"[AGENT] Starting agent execution for session: {session_id}")
                logger.info(f"[AGENT] User message: {message[:200]}..." if len(message) > 200 else f"[AGENT] User message: {message}")

                try:
                    result = await loop.run_in_executor(None, lambda: agent(message))

                    # Agent 실행 결과 로깅
                    logger.info(f"[AGENT] Execution completed successfully")
                    if result:
                        if hasattr(result, 'message'):
                            logger.info(f"[AGENT] Result message: {result.message}")
                        if hasattr(result, 'stop_reason'):
                            logger.info(f"[AGENT] Stop reason: {result.stop_reason}")

                    # XML 필터 버퍼 flush
                    flush_events = xml_filter.flush()
                    for event in flush_events:
                        await queue.put(event)

                    await queue.put({"type": "done"})
                except Exception as e:
                    logger.error(f"[AGENT] Execution error: {e}", exc_info=True)
                    await queue.put({"type": "error", "content": str(e)})

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

        except Exception as e:
            logger.error(f"Error streaming chat: {e}")
            yield {"type": "error", "content": str(e)}
        finally:
            # 원래 callback 복원
            agent.callback_handler = original_callback

    def cleanup(self, session_id: str):
        """세션 정리"""
        local_agent_runner.cleanup_session(session_id)
        logger.info(f"Session cleaned up: {session_id}")
