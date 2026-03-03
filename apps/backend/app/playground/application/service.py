"""Playground Application Service"""
import uuid
import logging
import asyncio
import json
import boto3
from datetime import datetime, timedelta

from app.shared.utils.timestamp import now_timestamp
from typing import AsyncIterator, Optional

from app.config import settings
from ..domain.repositories.session_repository import SessionRepository
from ..domain.repositories.deployment_repository import DeploymentRepository
from ..domain.repositories.conversation_repository import ConversationRepository
from ..domain.entities.session import PlaygroundSession
from ..domain.entities.deployment import Deployment
from ..domain.entities.conversation import Conversation
from ..domain.value_objects import (
    SessionId, Message, SessionStatus,
    DeploymentId, DeploymentStatus,
    ConversationId, ConversationStatus
)
from ..infrastructure.clients.strands_agent_client import StrandsAgentClient, AgentSpec
from ..infrastructure.clients.agentcore_client import AgentCoreClient
from ..infrastructure.code_generator import AgentCodeGenerator
from ..dto.response import (
    SessionResponse, MessageResponse, ChatResponse,
    DeploymentResponse, DeploymentStatusResponse,
    ConversationResponse, ConversationListResponse, DestroyResponse
)
from ..exception.exceptions import (
    SessionNotFoundException, AgentNotFoundException,
    DeploymentNotFoundException, ConversationNotFoundException,
    DeploymentAlreadyExistsException, MaxConversationsExceededException
)

from app.agent.domain.repositories import AgentRepository
from app.knowledge_bases.domain.repositories.kb_repository import KBRepository
from app.mcp.domain.repositories import MCPRepository

logger = logging.getLogger(__name__)


class PlaygroundApplicationService:
    """Playground Use Cases"""

    def __init__(
        self,
        session_repository: SessionRepository,
        strands_client: StrandsAgentClient,
        agent_repository: AgentRepository
    ):
        self.session_repository = session_repository
        self.strands_client = strands_client
        self.agent_repository = agent_repository

    async def _get_agent_spec(self, agent_id: str) -> AgentSpec:
        """Agent ID로부터 AgentSpec 생성"""
        agent = await self.agent_repository.find_by_id(agent_id)
        if not agent:
            raise AgentNotFoundException(agent_id)

        return AgentSpec(
            model_id=agent.llm_model.model_id,
            model_name=agent.llm_model.model_name,
            provider=agent.llm_model.provider,
            system_prompt=agent.instruction.system_prompt or "",
            temperature=agent.instruction.temperature,
            max_tokens=agent.instruction.max_tokens,
            mcps=agent.mcps or [],
            knowledge_bases=agent.knowledge_bases or []
        )

    async def create_session(
        self,
        user_id: str,
        agent_id: str,
        agent_version: str
    ) -> SessionResponse:
        """세션 생성"""
        # Agent 존재 확인
        agent = await self.agent_repository.find_by_id(agent_id)
        if not agent:
            raise AgentNotFoundException(agent_id)

        session = PlaygroundSession(
            id=SessionId(str(uuid.uuid4())),
            user_id=user_id,
            agent_id=agent_id,
            agent_version=agent_version
        )

        saved_session = await self.session_repository.save(session)
        return self._to_response(saved_session)

    async def send_message(
        self,
        session_id: str,
        user_message: str
    ) -> ChatResponse:
        """메시지 전송 및 Agent 응답 (비스트리밍)"""
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            raise SessionNotFoundException(session_id)

        # 사용자 메시지 추가
        user_msg = Message(role="user", content=user_message)
        session.add_message(user_msg)

        # Agent 스펙 조회
        spec = await self._get_agent_spec(session.agent_id)

        # Agent 호출
        result = await self.strands_client.invoke_agent(
            session.agent_id,
            session.agent_version,
            spec,
            user_message
        )

        # Agent 응답 추가
        assistant_msg = Message(role="assistant", content=result["content"])
        session.add_message(assistant_msg)

        # 세션 저장
        await self.session_repository.save(session)

        return ChatResponse(
            session_id=session_id,
            message=MessageResponse(
                role=assistant_msg.role,
                content=assistant_msg.content,
                timestamp=assistant_msg.timestamp
            )
        )

    async def stream_message(
        self,
        agent_id: str,
        version: str,
        message: str
    ) -> AsyncIterator[dict]:
        """스트리밍 메시지 (세션 없이)"""
        try:
            # Agent 스펙 조회
            spec = await self._get_agent_spec(agent_id)
            
            # 스트리밍 응답 생성
            async for event in self.strands_client.stream_response(
                agent_id,
                version,
                spec,
                message
            ):
                yield event
        except Exception as e:
            logger.error(f"Stream message error: {e}", exc_info=True)
            yield {"type": "error", "content": f"메시지 처리 중 오류: {str(e)}"}

    async def stream_session_message(
        self,
        session_id: str,
        user_message: str
    ) -> AsyncIterator[dict]:
        """스트리밍 메시지 (세션 기반)"""
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            raise SessionNotFoundException(session_id)

        # 사용자 메시지 추가
        user_msg = Message(role="user", content=user_message)
        session.add_message(user_msg)

        # Agent 스펙 조회
        spec = await self._get_agent_spec(session.agent_id)

        # 응답 수집용
        full_content = ""

        # 스트리밍 응답
        async for event in self.strands_client.stream_response(
            session.agent_id,
            session.agent_version,
            spec,
            user_message
        ):
            # 텍스트 수집
            if event["type"] == "text":
                full_content += event.get("content", "")

            yield event

            # 완료 시 세션에 저장
            if event["type"] == "done":
                assistant_msg = Message(role="assistant", content=full_content)
                session.add_message(assistant_msg)
                await self.session_repository.save(session)

    async def get_session(self, session_id: str) -> SessionResponse:
        """세션 조회"""
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            raise SessionNotFoundException(session_id)
        return self._to_response(session)

    async def get_user_sessions(self, user_id: str) -> list[SessionResponse]:
        """사용자 세션 목록"""
        sessions = await self.session_repository.find_by_user(user_id)
        return [self._to_response(s) for s in sessions]

    def _to_response(self, session: PlaygroundSession) -> SessionResponse:
        """Entity → Response DTO"""
        return SessionResponse(
            id=session.id.value,
            user_id=session.user_id,
            agent_id=session.agent_id,
            agent_version=session.agent_version,
            messages=[
                MessageResponse(
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.timestamp
                )
                for msg in session.messages
            ],
            status=session.status.value,
            created_at=session.created_at,
            updated_at=session.updated_at
        )


# ==================== AgentCore Runtime Services ====================

class DeploymentService:
    """AgentCore Runtime 배포 서비스"""

    MAX_CONVERSATIONS = 5

    def __init__(
        self,
        deployment_repository: DeploymentRepository,
        conversation_repository: ConversationRepository,
        agent_repository: AgentRepository,
        kb_repository: KBRepository,
        agentcore_client: AgentCoreClient,
        code_generator: AgentCodeGenerator,
        mcp_repository: Optional[MCPRepository] = None
    ):
        self.deployment_repository = deployment_repository
        self.conversation_repository = conversation_repository
        self.agent_repository = agent_repository
        self.kb_repository = kb_repository
        self.agentcore_client = agentcore_client
        self.code_generator = code_generator
        self.mcp_repository = mcp_repository
        self.session_bucket = settings.PLAYGROUND_SESSIONS_BUCKET
        self.base_image_uri = settings.BASE_IMAGE_URI

    async def deploy_agent(
        self,
        user_id: str,
        agent_id: str,
        version: str,
        conversation_id: Optional[str] = None,
        force_rebuild: bool = False
    ) -> DeploymentResponse:
        """Agent를 AgentCore Runtime으로 배포 (Container 방식) - 비동기 시작"""
        # Agent 존재 확인
        agent = await self.agent_repository.find_by_id(agent_id)
        if not agent:
            raise AgentNotFoundException(agent_id)

        # Conversation 처리
        is_resumed = False
        message_count = 0
        if conversation_id:
            conv = await self.conversation_repository.find_by_id(conversation_id)
            if conv:
                is_resumed = True
                message_count = conv.message_count
            else:
                # Conversation이 DynamoDB에 없으면 생성
                # (S3에는 메시지가 있을 수 있음 - "이어하기" 시나리오)
                logger.warning(f"Conversation {conversation_id} not found in DynamoDB, creating placeholder")
                s3_prefix = Conversation.generate_s3_prefix(user_id, agent_id, version, conversation_id)
                placeholder_conv = Conversation(
                    id=ConversationId(conversation_id),
                    user_id=user_id,
                    agent_id=agent_id,
                    agent_version=version,
                    title="이전 대화",  # S3에서 첫 메시지를 읽어서 title을 생성할 수도 있지만, 간단히 placeholder 사용
                    message_count=0,  # S3에서 실제 개수를 읽어올 수 있지만, 일단 0으로 설정
                    s3_prefix=s3_prefix,
                    last_message_preview=""
                )
                await self.conversation_repository.save(placeholder_conv)
                logger.info(f"Created placeholder conversation {conversation_id} in DynamoDB")
                is_resumed = True  # 이어하기 시나리오로 처리

        # 버전 정규화 (v1.9.0 -> 1.9.0)
        version_normalized = version.lstrip("v")

        # 기존 활성 배포 확인 (정규화된 버전과 원본 버전 모두 확인)
        existing = await self.deployment_repository.find_by_user_agent_version(
            user_id, agent_id, version_normalized
        )
        # 원본 버전으로도 확인 (기존 배포가 v1.9.0 형태로 저장된 경우)
        if not existing and version_normalized != version:
            existing = await self.deployment_repository.find_by_user_agent_version(
                user_id, agent_id, version
            )

        # 기존 ready deployment 재사용 (force_rebuild가 아닌 경우)
        # Agent Edit에서 이미 build + runtime 배포를 했으므로, Playground에서는 invoke만 하면 됨
        if existing and existing.status.value == 'ready' and not force_rebuild:
            logger.info(f"Reusing existing deployment {existing.id.value} (force_rebuild={force_rebuild})")
            # conversation_id 업데이트 (있는 경우에만)
            if conversation_id:
                existing.conversation_id = conversation_id
                await self.deployment_repository.save(existing)
            return self._to_deployment_response(existing, is_resumed, message_count)

        # force_rebuild이거나 기존 배포가 ready가 아닌 경우: 기존 활성 배포 종료 후 새로 생성
        if existing and existing.is_active():
            try:
                # 기존 Runtime 종료
                if existing.runtime_id:
                    await self.agentcore_client.delete_runtime(existing.runtime_id)
                existing.mark_deleted()
                await self.deployment_repository.save(existing)
                logger.info(f"Terminated existing deployment: {existing.id.value} (force_rebuild={force_rebuild})")
            except Exception as e:
                logger.warning(f"Failed to cleanup existing deployment: {e}")

        # Deployment 생성 (pending 상태) - 정규화된 버전 사용
        deployment_id = str(uuid.uuid4())
        deployment = Deployment(
            id=DeploymentId(deployment_id),
            user_id=user_id,
            agent_id=agent_id,
            agent_version=version_normalized,
            conversation_id=conversation_id
        )

        await self.deployment_repository.save(deployment)

        # 백그라운드 Task로 실제 배포 수행
        # noqa: S1481 - Task는 백그라운드에서 실행되므로 await하지 않음
        _task = asyncio.create_task(
            self._execute_deployment(deployment_id, agent_id, version_normalized, force_rebuild)
        )
        logger.info(f"Deployment task created: {deployment_id}")

        # 즉시 pending 상태 반환
        return self._to_deployment_response(deployment, is_resumed, message_count)

    async def _execute_deployment(
        self,
        deployment_id: str,
        agent_id: str,
        version: str,
        force_rebuild: bool
    ):
        """실제 배포 작업 수행 (백그라운드)"""
        try:
            deployment = await self.deployment_repository.find_by_id(deployment_id)
            if not deployment:
                logger.error(f"Deployment not found: {deployment_id}")
                return

            agent = await self.agent_repository.find_by_id(agent_id)
            if not agent:
                logger.error(f"Agent not found: {agent_id}")
                deployment.mark_failed("Agent not found")
                await self.deployment_repository.save(deployment)
                return

            # KB 메타데이터 조회
            kb_configs = []
            for kb_id in (agent.knowledge_bases or []):
                kb = await self.kb_repository.find_by_id(kb_id)
                if kb:
                    kb_configs.append({
                        "id": kb.id.value if hasattr(kb.id, 'value') else kb.id,
                        "name": kb.name,
                        "knowledge_base_id": kb.bedrock_kb_id
                    })

            # MCP 설정 생성
            mcp_configs = await self._get_mcp_configs(agent.mcps or [])

            # Agent 코드 생성
            agent_config = {
                "agent_id": agent_id,
                "agent_name": agent.name,
                "version": version,
                "model_id": agent.llm_model.model_id,
                "system_prompt": agent.instruction.system_prompt or "",
                "temperature": agent.instruction.temperature,
                "max_tokens": agent.instruction.max_tokens,
                "knowledge_bases": kb_configs,
                "mcp_servers": mcp_configs  # ✅ MCP 설정 추가!
            }

            session_prefix = f"sessions/{deployment.user_id}/{agent_id}/{version}"

            # Runtime 이름 생성 (영문, 숫자, _만 허용)
            def sanitize_name(s: str, max_len: int = 8) -> str:
                return ''.join(c if c.isalnum() else '_' for c in s)[:max_len]

            # Runtime 이름에 version 포함 (같은 agent라도 version별로 구분)
            # version에서 v 접두사 제거 후 통일된 형식으로 생성
            version_clean = version.lstrip("v")
            version_tag = version_clean.replace(".", "_")
            runtime_name = f"pg_{sanitize_name(agent_id)}_{sanitize_name(version_tag, 10)}_{sanitize_name(deployment_id)}"

            # Container 배포 플로우 (Docker + ECR)
            logger.info(f"Starting Container deployment for agent {agent_id}")

            # 1. 이미지 태그 생성 (agent_id + version 기반 - 재사용 가능)
            image_tag = self.agentcore_client.generate_image_tag(agent_id, version)
            logger.info(f"Image tag: {image_tag}, force_rebuild: {force_rebuild}")

            # 2. 기존 이미지 확인 (force_rebuild가 아닌 경우만)
            container_uri = None
            deployment_marked_ready = False  # 중복 처리 방지 플래그
            if not force_rebuild:
                container_uri = await self.agentcore_client.check_image_exists(image_tag)

            if container_uri and not force_rebuild:
                # 기존 이미지 재사용 - building 단계 건너뛰기, Runtime은 Python에서 생성
                logger.info(f"Reusing existing ECR image: {container_uri}")
                deployment.container_uri = container_uri
                await self.deployment_repository.save(deployment)

                # Python에서 Runtime 생성
                result = await self.agentcore_client.create_runtime_with_container(
                    name=runtime_name,
                    container_uri=container_uri,
                    description=f"Playground: {agent.name} ({version})"
                )

                # Runtime 생성 중 상태로 변경
                deployment.mark_creating(result["runtime_id"])
                await self.deployment_repository.save(deployment)

                # Ready 대기
                runtime_info = await self.agentcore_client.wait_for_ready(result["runtime_id"])
            else:
                # 새 이미지 빌드 필요
                logger.info(f"Building new image: {image_tag}")

                # 코드 생성 (Dockerfile 포함)
                files = self.code_generator.generate(
                    agent_config,
                    session_bucket=self.session_bucket,
                    session_prefix=session_prefix,
                    base_image_uri=self.base_image_uri
                )

                # Docker 빌드 + Runtime 생성 (CodeBuild에서 한 번에 처리)
                container_uri, build_id, s3_prefix = await self.agentcore_client.build_and_push_container(
                    files=files,
                    image_tag=image_tag,
                    user_id=deployment.user_id,
                    agent_id=agent_id,
                    version=version,
                    deployment_id=deployment_id,
                    repository_name=None,  # 기본 repository 사용
                    force_rebuild=force_rebuild,
                    runtime_name=runtime_name  # Runtime 생성도 CodeBuild에서 처리
                )

                # build_id가 있으면 실제로 빌드 중 (없으면 기존 이미지 재사용)
                if build_id:
                    # Building 상태로 즉시 변경 (UI가 "빌드 중" 표시)
                    deployment.mark_building()
                    deployment.container_uri = container_uri
                    deployment.build_id = build_id
                    deployment.s3_prefix = s3_prefix  # S3 prefix 저장 (Runtime 결과 읽기용)
                    await self.deployment_repository.save(deployment)
                    logger.info(f"Deployment marked as building: {deployment_id}")

                    # 빌드 완료 대기 (Runtime 생성까지 완료)
                    await self.agentcore_client.wait_for_build_completion(build_id, s3_prefix)
                    logger.info(f"Build + Runtime creation completed: {build_id}")

                    # S3에서 Runtime 결과 읽기 (cleanup 전에 먼저 읽기!)
                    runtime_result = await self.agentcore_client.get_runtime_result_from_s3(s3_prefix)

                    # S3 소스 파일 정리 (runtime_result 읽은 후)
                    try:
                        await self.agentcore_client.cleanup_s3_source(s3_prefix)
                        logger.info(f"Cleaned up S3 source: {s3_prefix}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup S3 source: {cleanup_error}")

                    if runtime_result and runtime_result.get('status') == 'ready':
                        runtime_info = {
                            "runtime_id": runtime_result.get('runtime_id'),
                            "runtime_arn": runtime_result.get('runtime_arn'),
                            "endpoint_url": runtime_result.get('endpoint_url')
                        }
                        logger.info(f"Runtime info from S3: {runtime_info}")

                        # Runtime 생성 완료 - deployment를 ready로 업데이트
                        deployment.runtime_id = runtime_info["runtime_id"]
                        expires_at = now_timestamp() + deployment.max_lifetime
                        deployment.mark_ready(
                            runtime_arn=runtime_info["runtime_arn"],
                            endpoint_url=runtime_info["endpoint_url"],
                            expires_at=expires_at
                        )
                        await self.deployment_repository.save(deployment)
                        deployment_marked_ready = True  # 플래그 설정
                        logger.info(f"Deployment marked as ready: {deployment_id}")
                    else:
                        error_msg = runtime_result.get('error', 'Unknown error') if runtime_result else 'Runtime result not found in S3'
                        raise RuntimeError(f"Runtime creation failed: {error_msg}")
                else:
                    # 기존 이미지 재사용 - building 단계 건너뛰기, Runtime은 Python에서 생성
                    logger.info(f"Reusing existing ECR image: {container_uri}")
                    deployment.container_uri = container_uri
                    await self.deployment_repository.save(deployment)

                    # 기존 이미지 사용 시에만 Python에서 Runtime 생성
                    result = await self.agentcore_client.create_runtime_with_container(
                        name=runtime_name,
                        container_uri=container_uri,
                        description=f"Playground: {agent.name} ({version})"
                    )

                    # Runtime 생성 중 상태로 변경
                    deployment.mark_creating(result["runtime_id"])
                    await self.deployment_repository.save(deployment)

                    # Ready 대기
                    runtime_info = await self.agentcore_client.wait_for_ready(result["runtime_id"])

            # 완료 처리 (expires_at는 Unix timestamp)
            # CodeBuild 경로에서 이미 처리한 경우 건너뛰기
            if not deployment_marked_ready:
                expires_at = now_timestamp() + deployment.max_lifetime
                deployment.mark_ready(
                    runtime_arn=runtime_info["runtime_arn"],
                    endpoint_url=runtime_info["endpoint_url"],
                    expires_at=expires_at
                )
                await self.deployment_repository.save(deployment)
                logger.info(f"Deployment marked as ready: {deployment_id}")

        except Exception as e:
            logger.error(f"Deployment failed: {e}", exc_info=True)
            deployment = await self.deployment_repository.find_by_id(deployment_id)
            if deployment:
                deployment.mark_failed(str(e))
                await self.deployment_repository.save(deployment)

    async def build_agent_image_only(
        self,
        agent_id: str,
        version: str,
        user_id: str,
        force_rebuild: bool = True
    ) -> Optional[str]:
        """Agent 이미지만 빌드 (Runtime 생성 없음)

        Agent Save 시 백그라운드에서 호출되어 이미지를 미리 빌드.
        Playground에서 해당 Agent를 테스트할 때 이미지가 이미 있으므로 즉시 시작 가능.

        Args:
            agent_id: Agent ID
            version: Agent 버전
            user_id: 사용자 ID
            force_rebuild: 강제 재빌드 여부 (기본값: True - Save 시에는 항상 새 빌드)

        Returns:
            빌드된 이미지 URI 또는 None (실패 시)
        """
        try:
            agent = await self.agent_repository.find_by_id(agent_id)
            if not agent:
                logger.error(f"Agent not found: {agent_id}")
                return None

            # KB 메타데이터 조회
            kb_configs = []
            for kb_id in (agent.knowledge_bases or []):
                kb = await self.kb_repository.find_by_id(kb_id)
                if kb:
                    kb_configs.append({
                        "id": kb.id.value if hasattr(kb.id, 'value') else kb.id,
                        "name": kb.name,
                        "knowledge_base_id": kb.bedrock_kb_id
                    })

            # MCP 설정 생성
            mcp_configs = await self._get_mcp_configs(agent.mcps or [])

            # Agent 코드 생성
            agent_config = {
                "agent_id": agent_id,
                "agent_name": agent.name,
                "version": version,
                "model_id": agent.llm_model.model_id,
                "system_prompt": agent.instruction.system_prompt or "",
                "temperature": agent.instruction.temperature,
                "max_tokens": agent.instruction.max_tokens,
                "knowledge_bases": kb_configs,
                "mcp_servers": mcp_configs
            }

            session_prefix = f"sessions/{user_id}/{agent_id}/{version}"

            # 이미지 태그 생성
            image_tag = self.agentcore_client.generate_image_tag(agent_id, version)
            logger.info(f"[Background Build] Image tag: {image_tag}")

            # 기존 이미지 확인 (force_rebuild=True이면 건너뜀)
            container_uri = None
            if not force_rebuild:
                container_uri = await self.agentcore_client.check_image_exists(image_tag)
                if container_uri:
                    logger.info(f"[Background Build] Reusing existing image: {container_uri}")
                    return container_uri

            # 새 이미지 빌드
            logger.info(f"[Background Build] Building new image: {image_tag}")

            # 코드 생성 (Dockerfile 포함)
            files = self.code_generator.generate(
                agent_config,
                session_bucket=self.session_bucket,
                session_prefix=session_prefix,
                base_image_uri=self.base_image_uri
            )

            # Docker 빌드 시작
            deployment_id = f"bg-{uuid.uuid4().hex[:8]}"  # 백그라운드 빌드용 ID
            container_uri, build_id, s3_prefix = await self.agentcore_client.build_and_push_container(
                files=files,
                image_tag=image_tag,
                user_id=user_id,
                agent_id=agent_id,
                version=version,
                deployment_id=deployment_id,
                repository_name=None,
                force_rebuild=force_rebuild
            )

            if build_id:
                # 빌드 완료 대기
                await self.agentcore_client.wait_for_build_completion(build_id, s3_prefix)
                logger.info(f"[Background Build] Build completed: {build_id}")

                # S3 소스 파일 정리
                try:
                    await self.agentcore_client.cleanup_s3_source(s3_prefix)
                    logger.info(f"[Background Build] Cleaned up S3 source: {s3_prefix}")
                except Exception as cleanup_error:
                    logger.warning(f"[Background Build] Failed to cleanup S3 source: {cleanup_error}")

            return container_uri

        except Exception as e:
            logger.error(f"[Background Build] Failed for agent {agent_id}: {e}", exc_info=True)
            return None

    async def get_deployment_status(self, deployment_id: str) -> DeploymentStatusResponse:
        """배포 상태 조회"""
        deployment = await self.deployment_repository.find_by_id(deployment_id)
        if not deployment:
            raise DeploymentNotFoundException(deployment_id)

        # 빌드 중이고 build_id가 있으면 실시간 phase 정보 조회
        build_phase = deployment.build_phase
        build_phase_message = deployment.build_phase_message

        if deployment.status.value == 'building' and deployment.build_id:
            try:
                phase_info = await self.agentcore_client.get_build_phases(deployment.build_id)
                if phase_info:
                    build_phase = phase_info['current_phase']
                    build_phase_message = phase_info['phase_message']
                    # Deployment entity 업데이트 (다음 조회 시 캐시로 사용)
                    deployment.update_build_phase(build_phase, build_phase_message)
                    await self.deployment_repository.save(deployment)
            except Exception as e:
                logger.warning(f"Failed to get build phases: {e}")

        return DeploymentStatusResponse(
            deployment_id=deployment.id.value,
            agent_id=deployment.agent_id,
            version=deployment.agent_version,
            status=deployment.status.value,
            runtime_id=deployment.runtime_id,
            runtime_arn=deployment.runtime_arn,
            endpoint_url=deployment.endpoint_url,
            build_id=deployment.build_id,
            build_phase=build_phase,
            build_phase_message=build_phase_message,
            created_at=deployment.created_at,
            idle_timeout=deployment.idle_timeout,
            max_lifetime=deployment.max_lifetime,
            expires_at=deployment.expires_at
        )

    async def get_active_deployment(
        self,
        user_id: str,
        agent_id: str,
        version: str
    ) -> Optional[DeploymentStatusResponse]:
        """
        기존 활성 배포 조회 (ready 상태인 것만 반환)
        페이지 새로고침 후 이전 대화를 선택할 때 사용
        """
        version_normalized = version.lstrip("v")

        # 정규화된 버전으로 조회
        existing = await self.deployment_repository.find_by_user_agent_version(
            user_id, agent_id, version_normalized
        )
        # 원본 버전으로도 확인
        if not existing and version_normalized != version:
            existing = await self.deployment_repository.find_by_user_agent_version(
                user_id, agent_id, version
            )

        if not existing or existing.status.value != 'ready':
            return None

        return DeploymentStatusResponse(
            deployment_id=existing.id.value,
            agent_id=existing.agent_id,
            version=existing.agent_version,
            status=existing.status.value,
            runtime_id=existing.runtime_id,
            runtime_arn=existing.runtime_arn,
            endpoint_url=existing.endpoint_url,
            build_id=existing.build_id,
            build_phase=existing.build_phase,
            build_phase_message=existing.build_phase_message,
            created_at=existing.created_at,
            idle_timeout=existing.idle_timeout,
            max_lifetime=existing.max_lifetime,
            expires_at=existing.expires_at
        )

    async def destroy_deployment(self, deployment_id: str) -> DestroyResponse:
        """배포 종료"""
        deployment = await self.deployment_repository.find_by_id(deployment_id)
        if not deployment:
            raise DeploymentNotFoundException(deployment_id)

        if deployment.runtime_id:
            deployment.mark_deleting()
            await self.deployment_repository.save(deployment)

            try:
                await self.agentcore_client.delete_runtime(deployment.runtime_id)
            except Exception as e:
                logger.warning(f"Failed to cleanup runtime: {e}")

        deployment.mark_deleted()
        await self.deployment_repository.save(deployment)

        return DestroyResponse(
            deployment_id=deployment_id,
            status="destroyed",
            message="Runtime이 성공적으로 종료되었습니다."
        )

    async def stream_runtime_chat(
        self,
        deployment_id: str,
        message: str
    ) -> AsyncIterator[dict]:
        """Runtime 채팅 (스트리밍)"""
        deployment = await self.deployment_repository.find_by_id(deployment_id)
        if not deployment:
            raise DeploymentNotFoundException(deployment_id)

        if not deployment.is_active():
            raise RuntimeError(f"Deployment is not active: {deployment.status.value}")

        # 세션 ID 결정: 기존 conversation_id 사용 또는 새로 생성
        if deployment.conversation_id:
            session_id = deployment.conversation_id
        else:
            # 첫 메시지인 경우: Conversation 생성 + deployment 업데이트
            session_id = str(uuid.uuid4())

            # Conversation 엔티티 생성 (DynamoDB에 저장)
            title = Conversation.generate_title_from_message(message)
            s3_prefix = Conversation.generate_s3_prefix(
                deployment.user_id,
                deployment.agent_id,
                deployment.agent_version,
                session_id
            )

            conversation = Conversation(
                id=ConversationId(session_id),
                user_id=deployment.user_id,
                agent_id=deployment.agent_id,
                agent_version=deployment.agent_version,
                title=title,
                message_count=1,
                s3_prefix=s3_prefix,
                last_message_preview=message[:100]
            )

            await self.conversation_repository.save(conversation)
            logger.info(f"Auto-created conversation {session_id} for deployment {deployment_id}")

            # Deployment에 conversation_id 저장
            deployment.conversation_id = session_id
            await self.deployment_repository.save(deployment)

        async for event in self.agentcore_client.invoke(
            deployment.runtime_arn,
            {"prompt": message},
            session_id=session_id
        ):
            yield event

    async def _get_mcp_configs(self, mcp_ids: list[str]) -> list[dict]:
        """MCP ID로부터 MCP 설정 조회

        MCP 타입별 변환 로직:
        - ExternalEndpointMCP: endpoint_url 사용, gateway 있으면 IAM 인증
        - ExternalContainerMCP: runtime_url 사용 (배포된 경우)
        - ExternalMCP (Legacy): mcp_config 사용 (stdio 방식)
        - InternalDeployMCP: endpoint (gateway) 사용, IAM 인증
        - InternalCreateMCP: endpoint (gateway) 사용, IAM 인증

        모든 Gateway는 Inbound에서 IAM 인증을 사용합니다.
        Gateway → Runtime 간의 Cognito JWT는 Gateway 내부에서 처리됩니다.

        Returns:
            Agent Code Generator의 mcp_servers 형식
        """
        if not mcp_ids:
            return []

        if not self.mcp_repository:
            logger.warning(f"MCP repository not available, skipping {len(mcp_ids)} MCP(s)")
            return []

        from app.mcp.domain.entities import (
            ExternalMCP, ExternalEndpointMCP, ExternalContainerMCP,
            InternalDeployMCP, InternalCreateMCP
        )
        from app.mcp.domain.value_objects import MCPId, Status

        configs = []

        for mcp_id in mcp_ids:
            try:
                mcp = await self.mcp_repository.find_by_id(MCPId(mcp_id))

                if not mcp:
                    logger.warning(f"MCP not found: {mcp_id}")
                    continue

                if mcp.status != Status.ENABLED:
                    logger.info(f"MCP {mcp_id} is disabled, skipping")
                    continue

                config = self._convert_mcp_to_config(mcp)
                if config:
                    configs.append(config)
                    logger.info(f"MCP config added: {mcp.name} ({type(mcp).__name__})")

            except Exception as e:
                logger.error(f"Failed to get MCP config for {mcp_id}: {e}")
                continue

        logger.info(f"Loaded {len(configs)} MCP configs from {len(mcp_ids)} MCP IDs")
        return configs

    def _convert_mcp_to_config(self, mcp) -> Optional[dict]:
        """MCP 엔티티를 Agent Code Generator용 config로 변환"""
        from app.mcp.domain.entities import (
            ExternalMCP, ExternalEndpointMCP, ExternalContainerMCP,
            InternalDeployMCP, InternalCreateMCP
        )
        import re

        def sanitize_name(name: str) -> str:
            """MCP 이름을 Python 변수명으로 사용 가능하도록 정제"""
            sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
            if sanitized and sanitized[0].isdigit():
                sanitized = '_' + sanitized
            return sanitized.lower()

        # ExternalEndpointMCP: URL 직접 연결
        if isinstance(mcp, ExternalEndpointMCP):
            if not mcp.endpoint_url:
                logger.warning(f"ExternalEndpointMCP {mcp.name} has no endpoint_url")
                return None

            config = {
                "name": sanitize_name(mcp.name),
                "transport": "http",
                "url": mcp.endpoint_url,
            }

            # Gateway를 통한 IAM 인증
            if mcp.gateway_id:
                config["auth_type"] = "iam"
                if mcp.endpoint:
                    config["url"] = mcp.endpoint

            return config

        # ExternalContainerMCP: Runtime URL 사용
        if isinstance(mcp, ExternalContainerMCP):
            if not mcp.runtime_url:
                logger.warning(f"ExternalContainerMCP {mcp.name} has no runtime_url")
                return None

            return {
                "name": sanitize_name(mcp.name),
                "transport": "http",
                "url": mcp.runtime_url,
                "auth_type": "iam" if mcp.gateway_id else "no_auth",
            }

        # ExternalMCP (Legacy): stdio 방식
        if isinstance(mcp, ExternalMCP):
            if mcp.command:
                return {
                    "name": mcp.server_name or sanitize_name(mcp.name),
                    "transport": "stdio",
                    "command": mcp.command,
                    "args": mcp.args or [],
                }
            elif mcp.runtime_url:
                return {
                    "name": mcp.server_name or sanitize_name(mcp.name),
                    "transport": "http",
                    "url": mcp.runtime_url,
                    "auth_type": "iam" if mcp.gateway_id else "no_auth",
                }
            else:
                logger.warning(f"ExternalMCP {mcp.name} has no command or runtime_url")
                return None

        # InternalDeployMCP: Gateway endpoint 사용 (IAM 인증)
        # Agent → Gateway: IAM 인증 (inbound)
        # Gateway → Runtime: Cognito JWT (outbound, Gateway가 내부적으로 처리)
        if isinstance(mcp, InternalDeployMCP):
            if not mcp.endpoint:
                logger.warning(f"InternalDeployMCP {mcp.name} has no endpoint (gateway not created?)")
                return None

            return {
                "name": sanitize_name(mcp.name),
                "transport": "http",
                "url": mcp.endpoint,
                "auth_type": "iam",  # Gateway inbound는 IAM 인증
            }

        # InternalCreateMCP: Gateway endpoint 사용 (IAM 인증)
        # Agent → Gateway: IAM 인증 (inbound)
        if isinstance(mcp, InternalCreateMCP):
            if not mcp.endpoint:
                logger.warning(f"InternalCreateMCP {mcp.name} has no endpoint (gateway not created?)")
                return None

            return {
                "name": sanitize_name(mcp.name),
                "transport": "http",
                "url": mcp.endpoint,
                "auth_type": "iam",  # Gateway inbound는 IAM 인증
            }

        logger.warning(f"Unknown MCP type: {type(mcp).__name__}")
        return None

    def _to_deployment_response(
        self,
        deployment: Deployment,
        is_resumed: bool = False,
        message_count: int = 0
    ) -> DeploymentResponse:
        """Entity → Response DTO"""
        return DeploymentResponse(
            id=deployment.id.value,
            agent_id=deployment.agent_id,
            version=deployment.agent_version,
            status=deployment.status.value,
            runtime_id=deployment.runtime_id,
            runtime_arn=deployment.runtime_arn,
            endpoint_url=deployment.endpoint_url,
            conversation_id=deployment.conversation_id,
            is_resumed=is_resumed,
            message_count=message_count,
            build_id=deployment.build_id,
            build_phase=deployment.build_phase,
            build_phase_message=deployment.build_phase_message,
            idle_timeout=deployment.idle_timeout,
            max_lifetime=deployment.max_lifetime,
            created_at=deployment.created_at,
            updated_at=deployment.updated_at,
            expires_at=deployment.expires_at,
            error_message=deployment.error_message
        )


class ConversationService:
    """대화 관리 서비스"""

    MAX_CONVERSATIONS = 5

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        agent_repository: AgentRepository
    ):
        self.conversation_repository = conversation_repository
        self.agent_repository = agent_repository
        self.session_bucket = settings.PLAYGROUND_SESSIONS_BUCKET

    async def list_conversations(
        self,
        user_id: str,
        agent_id: str,
        version: str
    ) -> ConversationListResponse:
        """대화 목록 조회"""
        conversations = await self.conversation_repository.list_by_agent_version(
            user_id, agent_id, version, limit=self.MAX_CONVERSATIONS
        )

        total = await self.conversation_repository.count_by_agent_version(
            user_id, agent_id, version
        )

        # Agent 이름 조회
        agent = await self.agent_repository.find_by_id(agent_id)
        agent_name = agent.name if agent else None

        return ConversationListResponse(
            conversations=[
                self._to_conversation_response(c, agent_name) for c in conversations
            ],
            total=total,
            max_allowed=self.MAX_CONVERSATIONS
        )

    async def create_conversation(
        self,
        user_id: str,
        agent_id: str,
        version: str,
        first_message: str
    ) -> ConversationResponse:
        """대화 생성"""
        # 최대 개수 확인 및 자동 삭제
        count = await self.conversation_repository.count_by_agent_version(
            user_id, agent_id, version
        )

        if count >= self.MAX_CONVERSATIONS:
            # 가장 오래된 대화 삭제
            oldest = await self.conversation_repository.find_oldest_by_agent_version(
                user_id, agent_id, version
            )
            if oldest:
                await self.conversation_repository.delete(oldest.id.value)
                logger.info(f"Auto-deleted oldest conversation: {oldest.id.value}")

        # 새 대화 생성
        conversation_id = str(uuid.uuid4())
        title = Conversation.generate_title_from_message(first_message)
        s3_prefix = Conversation.generate_s3_prefix(user_id, agent_id, version, conversation_id)

        conversation = Conversation(
            id=ConversationId(conversation_id),
            user_id=user_id,
            agent_id=agent_id,
            agent_version=version,
            title=title,
            message_count=1,
            s3_prefix=s3_prefix,
            last_message_preview=first_message[:100]
        )

        await self.conversation_repository.save(conversation)

        agent = await self.agent_repository.find_by_id(agent_id)
        return self._to_conversation_response(conversation, agent.name if agent else None)

    async def get_conversation_messages(
        self,
        user_id: str,
        conversation_id: str
    ) -> list[dict]:
        """대화 메시지 이력 조회 (S3에서 읽기)

        Strands S3SessionManager가 저장한 메시지를 S3에서 읽어옵니다.
        """
        conversation = await self.conversation_repository.find_by_id(conversation_id)
        if not conversation:
            raise ConversationNotFoundException(conversation_id)

        if conversation.user_id != user_id:
            raise ConversationNotFoundException(conversation_id)

        if not self.session_bucket:
            logger.warning("PLAYGROUND_SESSIONS_BUCKET not configured, returning empty messages")
            return []

        # S3에서 메시지 읽기
        try:
            logger.info(f"Reading messages for conversation: {conversation_id}")
            logger.info(f"  user_id: {conversation.user_id}")
            logger.info(f"  agent_id: {conversation.agent_id}")
            logger.info(f"  version: {conversation.agent_version}")

            messages = await self._read_messages_from_s3(
                user_id=conversation.user_id,
                agent_id=conversation.agent_id,
                version=conversation.agent_version,
                conversation_id=conversation_id
            )

            logger.info(f"Successfully read {len(messages)} messages from S3")
            return messages
        except Exception as e:
            logger.error(f"Failed to read messages from S3: {e}", exc_info=True)
            return []

    async def _read_messages_from_s3(
        self,
        user_id: str,
        agent_id: str,
        version: str,
        conversation_id: str
    ) -> list[dict]:
        """S3에서 Strands SessionManager가 저장한 메시지 읽기

        저장 구조:
        s3://bucket/sessions/{user_id}/{agent_id}/{version}/session_{conversation_id}/agents/agent_{uuid}/messages/

        주의: Strands S3SessionManager는 항상 'sessions/' prefix를 사용합니다.
        DynamoDB의 S3Prefix 필드는 무시하고, 여기서 직접 경로를 생성합니다.
        """
        # boto3 Session을 사용하여 AWS_PROFILE 적용
        if settings.AWS_PROFILE:
            session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
            s3_client = session.client('s3')
        else:
            s3_client = boto3.client('s3')

        # Base prefix - Strands가 사용하는 실제 경로
        # 형식: sessions/{user_id}/{agent_id}/{version}/session_{conversation_id}/agents/
        base_prefix = f"sessions/{user_id}/{agent_id}/{version}/session_{conversation_id}/agents/"

        # agents/ 하위의 agent_* 폴더 찾기
        try:
            response = s3_client.list_objects_v2(
                Bucket=self.session_bucket,
                Prefix=base_prefix,
                Delimiter='/'
            )

            agent_folders = [
                prefix['Prefix'] for prefix in response.get('CommonPrefixes', [])
                if 'agent_' in prefix['Prefix']
            ]

            if not agent_folders:
                logger.warning(f"No agent folders found in S3 prefix: {base_prefix}")
                logger.warning(f"Available prefixes: {response.get('CommonPrefixes', [])}")
                return []

            # 첫 번째 agent 폴더 사용 (일반적으로 하나만 존재)
            agent_folder = agent_folders[0]
            messages_prefix = f"{agent_folder}messages/"
            logger.info(f"Reading messages from: {messages_prefix}")

            # messages/ 폴더의 모든 message_*.json 파일 나열
            response = s3_client.list_objects_v2(
                Bucket=self.session_bucket,
                Prefix=messages_prefix
            )

            if 'Contents' not in response:
                logger.info(f"No messages found in S3 for conversation {conversation_id}")
                return []

            # 메시지 파일들을 message_id 순서로 정렬
            message_files = sorted(
                [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.json')],
                key=lambda x: int(x.split('message_')[-1].replace('.json', ''))
            )

            # 각 파일 읽어서 파싱
            messages = []
            for file_key in message_files:
                try:
                    obj = s3_client.get_object(Bucket=self.session_bucket, Key=file_key)
                    content = obj['Body'].read().decode('utf-8')
                    session_message = json.loads(content)

                    # SessionMessage 형식 파싱
                    message_data = session_message.get('message', {})
                    role = message_data.get('role', 'unknown')
                    timestamp = session_message.get('created_at', datetime.utcnow().isoformat())

                    # content 추출 (Strands는 content를 리스트 또는 문자열로 저장)
                    content_raw = message_data.get('content', '')
                    tool_uses = []  # 도구 사용 이력 수집 (tools 배열로 변환)

                    if isinstance(content_raw, list):
                        # Strands 형식 1: [{"text": "..."}] 또는
                        # Claude API 형식: [{"type": "text", "text": "..."}]
                        text_blocks = []

                        for block in content_raw:
                            if isinstance(block, dict):
                                # toolUse 블록 수집
                                if 'toolUse' in block:
                                    tool_use = block['toolUse']
                                    tool_name = tool_use.get('name', 'Unknown Tool')
                                    # KB 도구명 변환
                                    if tool_name.startswith('retrieve_from_'):
                                        kb_name = tool_name.replace('retrieve_from_', '').replace('_', '-')
                                        display_name = f"Knowledge Base \"{kb_name}\" 조회"
                                    else:
                                        display_name = f"\"{tool_name}\" 도구 사용"

                                    tool_uses.append({
                                        'id': f"tool-{len(tool_uses)}",
                                        'name': display_name,
                                        'status': 'completed'
                                    })
                                    continue

                                # toolResult 블록은 건너뛰기
                                if 'toolResult' in block:
                                    continue

                                # 텍스트 추출
                                text = None
                                if 'type' in block:
                                    if block.get('type') == 'text':
                                        text = block.get('text', '')
                                else:
                                    # type 없이 text만 있는 경우
                                    text = block.get('text', '')

                                if text:
                                    text_blocks.append(text)

                            elif isinstance(block, str):
                                # 문자열이 직접 들어있는 경우
                                text_blocks.append(block)

                        content = ''.join(text_blocks)
                    else:
                        # 단순 문자열
                        content = str(content_raw) if content_raw else ''

                    # 메시지 생성 (tools 배열 포함)
                    if content and content.strip():
                        message_id = session_message.get('id') or f"msg-{session_message.get('message_id', len(messages))}"
                        message = {
                            'id': message_id,
                            'role': role,
                            'content': content,
                            'timestamp': timestamp
                        }

                        # assistant 메시지에 tools 배열 추가
                        if role == 'assistant' and tool_uses:
                            message['tools'] = tool_uses

                        messages.append(message)

                except Exception as e:
                    logger.warning(f"Failed to parse message file {file_key}: {e}")
                    continue

            return messages

        except Exception as e:
            logger.error(f"S3 read error: {e}", exc_info=True)
            raise

    async def delete_conversation(
        self,
        user_id: str,
        conversation_id: str
    ) -> DestroyResponse:
        """대화 삭제"""
        conversation = await self.conversation_repository.find_by_id(conversation_id)
        if not conversation:
            raise ConversationNotFoundException(conversation_id)

        if conversation.user_id != user_id:
            raise ConversationNotFoundException(conversation_id)

        await self.conversation_repository.delete(conversation_id)

        return DestroyResponse(
            conversation_id=conversation_id,
            status="deleted",
            message="대화가 삭제되었습니다."
        )

    def _to_conversation_response(
        self,
        conversation: Conversation,
        agent_name: Optional[str] = None
    ) -> ConversationResponse:
        """Entity → Response DTO"""
        return ConversationResponse(
            id=conversation.id.value,
            agent_id=conversation.agent_id,
            agent_version=conversation.agent_version,
            agent_name=agent_name,
            title=conversation.title,
            message_count=conversation.message_count,
            last_message_preview=conversation.last_message_preview,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )
