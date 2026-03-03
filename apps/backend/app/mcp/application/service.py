"""MCP Application Services"""
import uuid
from typing import List, Optional, Dict, AsyncGenerator
from app.shared.utils.timestamp import now_timestamp
from ..domain.repositories import MCPRepository
from ..domain.repositories.mcp_version_repository import MCPVersionRepository
from ..domain.entities import (
    MCP, ExternalMCP, InternalDeployMCP, InternalCreateMCP,
    ExternalEndpointMCP, ExternalContainerMCP
)
from ..domain.services import MCPFactory, GatewayService, ECRService, KEISService
from ..domain.value_objects import (
    MCPId, MCPType, Status, AuthConfig, DeploymentConfig, APITarget, MCPVersion, ExternalAuthType
)
from ..dto.request import (
    CreateExternalMCPRequest, CreateInternalDeployMCPRequest,
    CreateInternalCreateMCPRequest, UpdateMCPRequest, MCPStatusRequest,
    CreateExternalEndpointMCPRequest, CreateExternalContainerMCPRequest
)
from ..dto.response import (
    MCPResponse, MCPListResponse, DashboardStatsResponse,
    ToolResponse, ToolEndpointResponse, TeamTagResponse
)
from ..dto.progress import DeployProgress, ProgressStep, FinalResult
from ..exception.exceptions import (
    MCPNotFoundException, MCPAlreadyExistsException,
    MCPValidationException, ECRValidationException
)


class MCPApplicationService:
    """MCP 애플리케이션 서비스"""

    def __init__(
        self,
        mcp_repository: MCPRepository,
        version_repository: MCPVersionRepository,
        gateway_service: GatewayService,
        ecr_service: ECRService,
        keis_service: KEISService
    ):
        self.mcp_repository = mcp_repository
        self.version_repository = version_repository
        self.gateway_service = gateway_service
        self.ecr_service = ecr_service
        self.keis_service = keis_service
        self.mcp_factory = MCPFactory()

    async def create_external_mcp(self, request: CreateExternalMCPRequest) -> MCPResponse:
        """외부 MCP 생성 (Multi-MCP Proxy 방식)

        표준 MCP 서버 설정 JSON을 사용하여 외부 MCP를 연동합니다.
        - 공유 Multi-MCP Proxy Runtime에 설정 추가
        - 공유 Gateway에 Target 추가
        """
        # 중복 이름 검사
        existing = await self.mcp_repository.find_by_name(request.name)
        if existing:
            raise MCPAlreadyExistsException(request.name)

        # MCP 생성
        mcp_id = MCPId(f"mcp-{uuid.uuid4().hex[:8]}")
        team_tag_ids = request.team_tags

        mcp = self.mcp_factory.create_external_mcp(
            id=mcp_id,
            name=request.name,
            description=request.description,
            team_tag_ids=team_tag_ids,
            server_name=request.server_name,  # Tool prefix
            mcp_config=request.mcp_config     # {command, args, env}
        )

        # 설정 검증
        if not mcp.validate_configuration():
            raise MCPValidationException("External MCP configuration is invalid. 'command' field is required.")

        # External MCP 인프라 생성 (Multi-MCP Proxy Runtime + 공유 Gateway Target)
        gateway_id = await self.gateway_service.create_external_mcp_infrastructure(mcp)
        mcp.set_gateway_id(gateway_id)

        # 저장
        await self.mcp_repository.save(mcp)

        # 초기 버전 히스토리 저장
        initial_version = self._create_version_snapshot(
            mcp=mcp,
            change_log="Initial version created"
        )
        await self.version_repository.save(initial_version)

        return await self._to_response(mcp)

    async def create_external_endpoint_mcp(self, request: CreateExternalEndpointMCPRequest) -> MCPResponse:
        """외부 MCP 생성 (Endpoint URL 타입)

        기존 MCP 서버의 엔드포인트 URL에 직접 연결합니다.
        - auth_type='no_auth': 공용 Cognito 사용
        - auth_type='oauth': 사용자가 선택한 AgentCore Identity OAuth Provider 사용
        """
        # 중복 이름 검사
        existing = await self.mcp_repository.find_by_name(request.name)
        if existing:
            raise MCPAlreadyExistsException(request.name)

        # MCP 생성
        mcp_id = MCPId(f"mcp-{uuid.uuid4().hex[:8]}")
        auth_type = ExternalAuthType(request.auth_type)

        mcp = self.mcp_factory.create_external_endpoint_mcp(
            id=mcp_id,
            name=request.name,
            description=request.description,
            team_tag_ids=request.team_tags,
            endpoint_url=request.endpoint_url,
            auth_type=auth_type,
            oauth_provider_arn=request.oauth_provider_arn,
            user_pool_id=request.user_pool_id
        )

        # 설정 검증
        if not mcp.validate_configuration():
            raise MCPValidationException("External Endpoint MCP configuration is invalid.")

        # Gateway Target 생성 (공유 Gateway에 MCP Server Target 추가) + Tools 조회
        gateway_id, target_id, tools = await self.gateway_service.create_external_endpoint_target(mcp)

        # 저장
        await self.mcp_repository.save(mcp)

        # 초기 버전 히스토리 저장
        initial_version = self._create_version_snapshot(
            mcp=mcp,
            change_log="Initial version created"
        )
        await self.version_repository.save(initial_version)

        return await self._to_response(mcp)

    async def create_external_container_mcp(self, request: CreateExternalContainerMCPRequest) -> MCPResponse:
        """외부 MCP 생성 (Container Image 타입)

        ECR 이미지를 Runtime으로 배포 후 Gateway Target으로 연결합니다.
        - Runtime 생성 (ECR 이미지)
        - 공유 Gateway에 Runtime Target 추가
        """
        # 중복 이름 검사
        existing = await self.mcp_repository.find_by_name(request.name)
        if existing:
            raise MCPAlreadyExistsException(request.name)

        # ECR 이미지 검증
        if not await self.ecr_service.validate_image_exists(request.ecr_repository, request.image_tag):
            raise ECRValidationException(request.ecr_repository, request.image_tag)

        # MCP 생성
        mcp_id = MCPId(f"mcp-{uuid.uuid4().hex[:8]}")
        auth_type = ExternalAuthType(request.auth_type)

        mcp = self.mcp_factory.create_external_container_mcp(
            id=mcp_id,
            name=request.name,
            description=request.description,
            team_tag_ids=request.team_tags,
            ecr_repository=request.ecr_repository,
            image_tag=request.image_tag,
            auth_type=auth_type,
            user_pool_id=request.user_pool_id,
            environment=request.environment
        )

        # 설정 검증
        if not mcp.validate_configuration():
            raise MCPValidationException("External Container MCP configuration is invalid.")

        # Runtime 생성 + Gateway Target 생성
        gateway_id, target_id, runtime_id, runtime_url = await self.gateway_service.create_external_container_target(mcp)

        # 저장
        await self.mcp_repository.save(mcp)

        # 초기 버전 히스토리 저장
        initial_version = self._create_version_snapshot(
            mcp=mcp,
            change_log="Initial version created"
        )
        await self.version_repository.save(initial_version)

        return await self._to_response(mcp)

    async def list_cognito_user_pools(self) -> List[dict]:
        """AWS 계정 내 모든 Cognito User Pool 목록 조회"""
        return await self.gateway_service.cognito_service.list_all_user_pools()

    async def list_oauth2_credential_providers(self) -> List[dict]:
        """AgentCore Identity OAuth2 Credential Provider 목록 조회"""
        return await self.gateway_service.list_oauth2_credential_providers()

    async def create_internal_deploy_mcp(self, request: CreateInternalDeployMCPRequest) -> MCPResponse:
        """내부 배포 MCP 생성 (Container 기반)

        ECR 이미지를 AgentCore Runtime으로 배포하고
        Gateway + MCP Server Target을 생성합니다.
        """
        # 중복 이름 검사
        existing = await self.mcp_repository.find_by_name(request.name)
        if existing:
            raise MCPAlreadyExistsException(request.name)

        # ECR 이미지 검증
        if not await self.ecr_service.validate_image_exists(request.ecr_repository, request.image_tag):
            raise ECRValidationException(request.ecr_repository, request.image_tag)

        # MCP 생성
        mcp_id = MCPId(f"mcp-{uuid.uuid4().hex[:8]}")
        team_tag_ids = request.team_tags
        deployment_config = DeploymentConfig(
            resources=request.resources,
            environment=request.environment
        )

        mcp = self.mcp_factory.create_internal_deploy_mcp(
            id=mcp_id,
            name=request.name,
            description=request.description,
            team_tag_ids=team_tag_ids,
            ecr_repository=request.ecr_repository,
            image_tag=request.image_tag,
            deployment_config=deployment_config,
            enable_semantic_search=request.enable_semantic_search
        )

        # Deploy MCP 인프라 생성 (Runtime + Gateway + Target)
        gateway_id = await self.gateway_service.create_deploy_mcp_infrastructure(mcp)
        mcp.set_dedicated_gateway_id(gateway_id)

        # 저장
        await self.mcp_repository.save(mcp)

        # 초기 버전 히스토리 저장
        initial_version = self._create_version_snapshot(
            mcp=mcp,
            change_log="Initial version created"
        )
        await self.version_repository.save(initial_version)

        return await self._to_response(mcp)

    async def create_internal_deploy_mcp_stream(
        self,
        request: CreateInternalDeployMCPRequest
    ) -> AsyncGenerator[str, None]:
        """내부 배포 MCP 생성 (SSE 스트리밍)

        각 단계별 진행 상황을 SSE 형식으로 스트리밍합니다.
        """
        progress = DeployProgress(mcp_name=request.name)

        try:
            # Step 0: 초기화
            yield progress.get_current_progress().to_sse()

            # 중복 이름 검사
            existing = await self.mcp_repository.find_by_name(request.name)
            if existing:
                yield progress.step_failed(f"MCP '{request.name}'가 이미 존재합니다").to_sse()
                yield FinalResult(success=False, error=f"MCP '{request.name}'가 이미 존재합니다").to_sse()
                return

            # ECR 이미지 검증
            if not await self.ecr_service.validate_image_exists(request.ecr_repository, request.image_tag):
                yield progress.step_failed(f"ECR 이미지를 찾을 수 없습니다: {request.ecr_repository}:{request.image_tag}").to_sse()
                yield FinalResult(success=False, error="ECR 이미지를 찾을 수 없습니다").to_sse()
                return

            # MCP 엔티티 생성
            mcp_id = MCPId(f"mcp-{uuid.uuid4().hex[:8]}")
            team_tag_ids = request.team_tags
            deployment_config = DeploymentConfig(
                resources=request.resources,
                environment=request.environment
            )

            mcp = self.mcp_factory.create_internal_deploy_mcp(
                id=mcp_id,
                name=request.name,
                description=request.description,
                team_tag_ids=team_tag_ids,
                ecr_repository=request.ecr_repository,
                image_tag=request.image_tag,
                deployment_config=deployment_config,
                enable_semantic_search=request.enable_semantic_search
            )

            # Deploy MCP 인프라 생성 (with progress callbacks)
            async for step_progress in self.gateway_service.create_deploy_mcp_infrastructure_stream(mcp):
                # 진행 상황을 SSE로 전송
                yield step_progress.to_sse()

                # 에러 체크
                if step_progress.status.value == "failed":
                    yield FinalResult(success=False, error=step_progress.details).to_sse()
                    return

            # 성공적으로 완료
            gateway_id = mcp.dedicated_gateway_id

            # 저장
            await self.mcp_repository.save(mcp)

            # 초기 버전 히스토리 저장
            initial_version = self._create_version_snapshot(
                mcp=mcp,
                change_log="Initial version created"
            )
            await self.version_repository.save(initial_version)

            # 완료 이벤트 전송
            response = await self._to_response(mcp)
            yield progress.finish(mcp.id.value).to_sse()
            yield FinalResult(
                success=True,
                mcp_id=mcp.id.value,
                data={
                    "id": response.id,
                    "name": response.name,
                    "description": response.description,
                    "type": response.type,
                    "status": response.status,
                    "version": response.version,
                    "endpoint": response.endpoint,
                    "toolList": [
                        {
                            "name": t.name,
                            "description": t.description,
                            "inputSchema": t.inputSchema
                        } for t in (response.toolList or [])
                    ],
                    "teamTagIds": response.teamTagIds,
                    "createdAt": response.createdAt,
                    "updatedAt": response.updatedAt
                }
            ).to_sse()

        except Exception as e:
            yield progress.step_failed(str(e)).to_sse()
            yield FinalResult(success=False, error=str(e)).to_sse()

    async def create_internal_create_mcp(self, request: CreateInternalCreateMCPRequest) -> MCPResponse:
        """내부 생성 MCP 생성 (API 기반)"""
        # 중복 이름 검사
        existing = await self.mcp_repository.find_by_name(request.name)
        if existing:
            raise MCPAlreadyExistsException(request.name)

        # Task 2: Frontend에서 받은 targets 직접 사용 (KEIS Service 조회 제거)
        if not request.targets:
            raise MCPValidationException("No targets provided")

        # TargetInfo를 APITarget으로 변환
        api_targets = []
        for target in request.targets:
            # OpenAPI Schema에서 auth_type 추출
            auth_type = self._extract_auth_type_from_openapi(target.openApiSchema)

            api_targets.append(APITarget(
                id=f"target-{uuid.uuid4().hex[:8]}",
                name=target.name,
                api_id=target.apiId,  # Frontend에서 선택한 API Catalog의 실제 API ID
                endpoint=target.endpoint,
                method=target.method,
                auth_type=auth_type,  # OpenAPI Schema에서 추출한 인증 타입
                openapi_schema=target.openApiSchema,
                team_tag_ids=target.teamTagIds  # Target의 team tag IDs
            ))

        # MCP 생성
        mcp_id = MCPId(f"mcp-{uuid.uuid4().hex[:8]}")
        team_tag_ids = request.team_tags

        mcp = self.mcp_factory.create_internal_create_mcp(
            id=mcp_id,
            name=request.name,
            description=request.description,
            team_tag_ids=team_tag_ids,
            selected_api_targets=api_targets,
            enable_semantic_search=request.enable_semantic_search
        )

        # 전용 Gateway 생성
        gateway_id = await self.gateway_service.create_dedicated_gateway(mcp, enable_semantic_search=mcp.enable_semantic_search)
        mcp.set_dedicated_gateway_id(gateway_id)

        # 저장
        await self.mcp_repository.save(mcp)

        # 초기 버전 히스토리 저장
        initial_version = self._create_version_snapshot(
            mcp=mcp,
            change_log="Initial version created"
        )
        await self.version_repository.save(initial_version)

        return await self._to_response(mcp)
    
    async def get_mcp(self, mcp_id: str) -> MCPResponse:
        """MCP 조회"""
        mcp = await self.mcp_repository.find_by_id(MCPId(mcp_id))
        if not mcp:
            raise MCPNotFoundException(mcp_id)

        return await self._to_response(mcp)
    
    async def list_mcps(
        self,
        search: str = None,
        type_filter: str = None,
        status_filter: str = None,
        team_tag_ids: list = None
    ) -> MCPListResponse:
        """MCP 목록 조회 (필터링 지원)"""
        # 전체 조회
        mcps = await self.mcp_repository.find_all()

        # 필터링 (서버 사이드 필터링은 향후 페이지네이션을 위해 유지)
        filtered_mcps = mcps

        # 검색어 필터링 (이름 또는 설명)
        if search:
            search_lower = search.lower()
            filtered_mcps = [
                mcp for mcp in filtered_mcps
                if search_lower in mcp.name.lower() or search_lower in mcp.description.lower()
            ]

        # 타입 필터링
        if type_filter and type_filter != 'all':
            if type_filter == 'internal':
                # "internal" 선택 시 internal-deploy와 internal-create 모두 포함
                filtered_mcps = [
                    mcp for mcp in filtered_mcps
                    if mcp.type.value in ['internal-deploy', 'internal-create']
                ]
            else:
                filtered_mcps = [
                    mcp for mcp in filtered_mcps
                    if mcp.type.value == type_filter
                ]

        # 상태 필터링
        if status_filter and status_filter != 'all':
            filtered_mcps = [
                mcp for mcp in filtered_mcps
                if mcp.status.value == status_filter
            ]

        # 팀 태그 필터링
        if team_tag_ids and len(team_tag_ids) > 0:
            filtered_mcps = [
                mcp for mcp in filtered_mcps
                if any(tag_id in mcp.team_tag_ids for tag_id in team_tag_ids)
            ]

        # Convert MCPs to responses (async)
        responses = []
        for mcp in filtered_mcps:
            response = await self._to_response(mcp)
            responses.append(response)

        return MCPListResponse(
            data=responses,
            total=len(responses)
        )
    
    async def update_mcp(self, mcp_id: str, request: UpdateMCPRequest) -> MCPResponse:
        """MCP 업데이트"""
        mcp = await self.mcp_repository.find_by_id(MCPId(mcp_id))
        if not mcp:
            raise MCPNotFoundException(mcp_id)

        # 변경 사항 추적
        changes = []
        if request.description and request.description != mcp.description:
            changes.append("description")
        if request.team_tags and request.team_tags != mcp.team_tag_ids:
            changes.append("team tags")
        if request.targets:
            changes.append("targets")

        # MCP 업데이트 (항상 호출하여 updated_at 갱신)
        team_tag_ids = request.team_tags if request.team_tags is not None else mcp.team_tag_ids
        mcp.update_basic_info(
            description=request.description if request.description is not None else mcp.description,
            team_tag_ids=team_tag_ids
        )

        # Internal Create MCP의 경우 targets 업데이트
        if request.targets and isinstance(mcp, InternalCreateMCP):
            # TargetInfo를 APITarget으로 변환
            api_targets = []
            for target in request.targets:
                # OpenAPI Schema에서 auth_type 추출
                auth_type = self._extract_auth_type_from_openapi(target.openApiSchema)

                api_targets.append(APITarget(
                    id=f"target-{uuid.uuid4().hex[:8]}",
                    name=target.name,
                    api_id=target.apiId,  # Frontend에서 선택한 API Catalog의 실제 API ID
                    endpoint=target.endpoint,
                    method=target.method,
                    auth_type=auth_type,  # OpenAPI Schema에서 추출한 인증 타입
                    openapi_schema=target.openApiSchema,
                    team_tag_ids=target.teamTagIds  # Target의 team tag IDs
                ))
            mcp.update_targets(api_targets)

            # Gateway 업데이트 (AgentCore Gateway에 실제 반영)
            await self.gateway_service.update_dedicated_gateway(mcp)

        # Internal Deploy MCP의 경우 image_tag 업데이트
        if request.image_tag and isinstance(mcp, InternalDeployMCP):
            if request.image_tag != mcp.image_tag:
                changes.append("image tag")
                # ECR 이미지 검증
                if not await self.ecr_service.validate_image_exists(mcp.ecr_repository, request.image_tag):
                    raise ECRValidationException(mcp.ecr_repository, request.image_tag)
                # 이미지 태그 업데이트
                mcp.update_image_tag(request.image_tag)
                # 인프라 재생성 (Runtime 재생성, Gateway Target 업데이트)
                await self.gateway_service.update_deploy_mcp_infrastructure(mcp)

        # Internal MCP (Deploy & Create)의 경우 enable_semantic_search 업데이트
        if request.enable_semantic_search is not None:
            if isinstance(mcp, (InternalDeployMCP, InternalCreateMCP)):
                if request.enable_semantic_search != mcp.enable_semantic_search:
                    changes.append("semantic search")
                    mcp.update_enable_semantic_search(request.enable_semantic_search)
                    # Gateway 업데이트 (searchType 변경: SEMANTIC ↔ KEYWORD)
                    if isinstance(mcp, InternalCreateMCP):
                        await self.gateway_service.update_dedicated_gateway(mcp)
                    elif isinstance(mcp, InternalDeployMCP):
                        await self.gateway_service.update_deploy_mcp_infrastructure(mcp)

        # External Endpoint MCP의 경우 endpoint_url, auth_type, oauth_provider_arn 업데이트
        if isinstance(mcp, ExternalEndpointMCP):
            needs_infra_update = False

            if request.endpoint_url and request.endpoint_url != mcp.endpoint_url:
                changes.append("endpoint URL")
                mcp.update_endpoint_url(request.endpoint_url)
                needs_infra_update = True

            if request.auth_type and request.auth_type != mcp.auth_type.value:
                changes.append("auth type")
                from ..domain.value_objects import ExternalAuthType
                mcp.update_auth_type(ExternalAuthType(request.auth_type))
                needs_infra_update = True

            if request.oauth_provider_arn is not None and request.oauth_provider_arn != mcp.oauth_provider_arn:
                changes.append("OAuth provider")
                mcp.update_oauth_provider_arn(request.oauth_provider_arn)
                needs_infra_update = True

            if request.user_pool_id is not None and request.user_pool_id != mcp.user_pool_id:
                changes.append("user pool")
                mcp.update_user_pool_id(request.user_pool_id)
                needs_infra_update = True

            # 인프라 업데이트가 필요한 경우 (Target 재생성)
            if needs_infra_update:
                await self.gateway_service.update_external_endpoint_target(mcp)

        # 버전 증가
        mcp.increment_version()

        # 저장
        await self.mcp_repository.save(mcp)

        # 새 버전 히스토리 저장 (업데이트 후 상태)
        change_log = f"Updated {', '.join(changes)}" if changes else "No changes"
        new_version_snapshot = self._create_version_snapshot(
            mcp=mcp,
            change_log=change_log
        )
        await self.version_repository.save(new_version_snapshot)

        return await self._to_response(mcp)
    
    async def toggle_mcp_status(self, mcp_id: str, request: MCPStatusRequest) -> MCPResponse:
        """MCP 상태 토글"""
        mcp = await self.mcp_repository.find_by_id(MCPId(mcp_id))
        if not mcp:
            raise MCPNotFoundException(mcp_id)

        # Status 검증 및 변환
        if request.status == "enabled":
            new_status = Status.ENABLED
            mcp.enable()  # Entity 상태도 변경 (validation)
        elif request.status == "disabled":
            new_status = Status.DISABLED
            mcp.disable()  # Entity 상태도 변경 (validation)
        else:
            raise MCPValidationException(f"Invalid status: {request.status}")

        # DB에 status만 업데이트 (전체 객체 저장 안함)
        await self.mcp_repository.update_status(MCPId(mcp_id), new_status)

        return await self._to_response(mcp)

    async def get_mcp_versions(self, mcp_id: str) -> List[MCPVersion]:
        """MCP의 모든 버전 히스토리 조회 (최신순)"""
        # MCP 존재 확인
        mcp = await self.mcp_repository.find_by_id(MCPId(mcp_id))
        if not mcp:
            raise MCPNotFoundException(mcp_id)

        # 버전 히스토리 조회
        versions = await self.version_repository.find_by_mcp_id(mcp_id)
        return versions

    async def get_mcp_version_detail(self, mcp_id: str, version: str) -> Optional[MCPVersion]:
        """MCP의 특정 버전 상세 조회"""
        # MCP 존재 확인
        mcp = await self.mcp_repository.find_by_id(MCPId(mcp_id))
        if not mcp:
            raise MCPNotFoundException(mcp_id)

        # 특정 버전 조회
        version_detail = await self.version_repository.find_by_mcp_id_and_version(mcp_id, version)
        return version_detail
    
    async def get_mcp_stats(self) -> dict:
        """MCP 통계 조회 (Dashboard용)

        실제 Gateway health를 체크하여 healthy 개수를 계산합니다.
        """
        import asyncio

        all_mcps = await self.mcp_repository.find_all()
        enabled_mcps = await self.mcp_repository.find_by_status(Status.ENABLED)

        # 실제 healthy 개수 계산 (병렬 처리)
        healthy_count = 0
        if enabled_mcps:
            async def check_health(mcp) -> bool:
                """개별 MCP health 체크"""
                try:
                    # Gateway ID 확인
                    gateway_id = None
                    if hasattr(mcp, 'dedicated_gateway_id') and mcp.dedicated_gateway_id:
                        gateway_id = mcp.dedicated_gateway_id
                    elif hasattr(mcp, 'gateway_id') and mcp.gateway_id:
                        gateway_id = mcp.gateway_id

                    if not gateway_id:
                        return False

                    # Gateway health 체크
                    health_result = await self.gateway_service.check_gateway_health(gateway_id)
                    return health_result.get('healthy', False)
                except Exception:
                    return False

            # 병렬로 health 체크 수행
            health_results = await asyncio.gather(
                *[check_health(mcp) for mcp in enabled_mcps],
                return_exceptions=True
            )
            healthy_count = sum(1 for r in health_results if r is True)

        return {
            "total": len(all_mcps),
            "enabled": len(enabled_mcps),
            "healthy": healthy_count
        }

    async def check_mcp_health(self, mcp_id: str) -> dict:
        """MCP Health 체크

        enabled 상태인 MCP에 대해서만 Gateway health를 체크합니다.
        disabled MCP는 health 체크를 수행하지 않습니다.

        Args:
            mcp_id: MCP ID

        Returns:
            dict: {
                'mcpId': str,
                'mcpName': str,
                'status': str (MCP status: enabled/disabled),
                'health': {
                    'healthy': bool,
                    'gatewayStatus': str,
                    'message': str,
                    'cached': bool
                } | None (disabled인 경우)
            }
        """
        mcp = await self.mcp_repository.find_by_id(MCPId(mcp_id))
        if not mcp:
            raise MCPNotFoundException(mcp_id)

        result = {
            'mcpId': mcp.id.value,
            'mcpName': mcp.name,
            'status': mcp.status.value,
            'health': None
        }

        # disabled MCP는 health 체크 안함
        if mcp.status != Status.ENABLED:
            result['health'] = {
                'healthy': None,
                'gatewayStatus': 'N/A',
                'message': 'Health check is only available for enabled MCPs',
                'cached': False
            }
            return result

        # Gateway ID 확인
        gateway_id = None
        if hasattr(mcp, 'dedicated_gateway_id') and mcp.dedicated_gateway_id:
            gateway_id = mcp.dedicated_gateway_id
        elif hasattr(mcp, 'gateway_id') and mcp.gateway_id:
            gateway_id = mcp.gateway_id

        if not gateway_id:
            result['health'] = {
                'healthy': False,
                'gatewayStatus': 'NO_GATEWAY',
                'message': 'No gateway associated with this MCP',
                'cached': False
            }
            return result

        # Gateway health 체크
        health_result = await self.gateway_service.check_gateway_health(gateway_id)

        result['health'] = {
            'healthy': health_result.get('healthy', False),
            'gatewayStatus': health_result.get('status', 'UNKNOWN'),
            'message': health_result.get('message', ''),
            'cached': health_result.get('cached', False)
        }

        return result

    async def sync_external_mcp_runtime(self) -> dict:
        """External MCP Runtime 동기화

        DynamoDB에 저장된 모든 External MCP 설정을 Runtime에 반영합니다.
        Runtime을 재시작하고 각 MCP의 tools를 조회하여 DB에 업데이트합니다.

        Returns:
            dict: sync 결과
        """
        # Gateway Service의 sync 메서드 호출
        result = await self.gateway_service.sync_external_mcp_runtime()

        # 각 서버의 tools를 해당 MCP에 업데이트
        servers = result.get('servers', {})
        updated_mcps = []

        for server_name, tools in servers.items():
            # server_name으로 MCP 찾기
            mcps = await self.mcp_repository.find_all()
            for mcp in mcps:
                if isinstance(mcp, ExternalMCP) and mcp.server_name == server_name:
                    # Tools 업데이트
                    if tools:
                        from ..domain.value_objects import Tool
                        mcp.clear_tools()
                        for tool_data in tools:
                            tool = Tool(
                                name=tool_data['name'],
                                description=tool_data.get('description', ''),
                                input_schema=tool_data.get('inputSchema', {})
                            )
                            mcp.add_tool(tool)
                        # 저장
                        await self.mcp_repository.save(mcp)
                        updated_mcps.append({
                            'mcpId': mcp.id.value,
                            'serverName': server_name,
                            'toolCount': len(tools)
                        })
                    break

        result['updatedMcps'] = updated_mcps
        return result

    def _extract_auth_type_from_openapi(self, openapi_schema: dict) -> str:
        """OpenAPI Schema에서 인증 타입 추출

        Args:
            openapi_schema: OpenAPI 3.0 Schema

        Returns:
            str: 'oauth' | 'api_key' | 'none'
        """
        if not openapi_schema:
            return 'api_key'  # 기본값

        # components.securitySchemes에서 인증 타입 추출
        components = openapi_schema.get('components', {})
        security_schemes = components.get('securitySchemes', {})

        if not security_schemes:
            return 'api_key'  # 기본값

        # 첫 번째 security scheme의 타입 확인
        first_scheme = list(security_schemes.values())[0]
        scheme_type = first_scheme.get('type', '').lower()

        if scheme_type == 'oauth2':
            return 'oauth'
        elif scheme_type == 'apikey':
            return 'api_key'
        else:
            return 'api_key'  # 알 수 없는 타입은 api_key로 처리

    def _create_version_snapshot(self, mcp: MCP, change_log: str) -> MCPVersion:
        """현재 MCP 상태의 버전 스냅샷 생성"""
        # Type-specific fields
        server_url = None
        auth_config = None
        ecr_repository = None
        image_tag = None
        targets = None

        if isinstance(mcp, ExternalMCP):
            server_url = mcp.server_url
            auth_config = mcp.auth_config
        elif isinstance(mcp, InternalDeployMCP):
            ecr_repository = mcp.ecr_repository
            image_tag = mcp.image_tag
        elif isinstance(mcp, InternalCreateMCP):
            targets = mcp.selected_api_targets

        return MCPVersion(
            mcp_id=mcp.id.value,
            version=mcp.version,
            endpoint=mcp.endpoint,
            description=mcp.description,
            change_log=change_log,
            status=mcp.status,
            tool_list=mcp.tool_list,
            created_at=now_timestamp(),
            created_by="system",  # TODO: Get actual user from JWT token
            mcp_type=mcp.type,
            team_tag_ids=mcp.team_tag_ids,
            server_url=server_url,
            auth_config=auth_config,
            ecr_repository=ecr_repository,
            image_tag=image_tag,
            targets=targets
        )

    async def _to_response(self, mcp: MCP) -> MCPResponse:
        """MCP를 Response DTO로 변환"""
        tool_list = []
        for tool in mcp.tool_list:
            # Map endpoints if present
            endpoints = None
            if tool.endpoints:
                endpoints = [
                    ToolEndpointResponse(
                        method=ep.method,
                        path=ep.path,
                        summary=ep.summary,
                        inputSchema=ep.input_schema,  # camelCase for API response
                        responses=ep.responses
                    )
                    for ep in tool.endpoints
                ]

            tool_list.append(ToolResponse(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.input_schema,  # camelCase for API response
                endpoints=endpoints,  # 여러 endpoint 정보
                responses=tool.responses,  # OpenAPI responses schema
                method=tool.method,  # HTTP method
                endpoint=tool.endpoint,  # API endpoint
                authType=tool.auth_type  # Authentication type (camelCase for API response)
            ))

        response = MCPResponse(
            id=mcp.id.value,
            name=mcp.name,
            description=mcp.description,
            type=mcp.type.value,
            status=mcp.status.value,
            version=mcp.version,
            endpoint=mcp.endpoint,
            toolList=tool_list,
            teamTagIds=mcp.team_tag_ids,
            createdAt=mcp.created_at,
            updatedAt=mcp.updated_at
        )

        # 타입별 추가 필드
        # Note: Check ExternalEndpointMCP and ExternalContainerMCP BEFORE ExternalMCP
        # because they are subclasses with type=EXTERNAL
        if isinstance(mcp, ExternalEndpointMCP):
            response.subType = "endpoint"
            response.endpointUrl = mcp.endpoint_url
            response.authType = mcp.auth_type.value
            response.oauthProviderArn = mcp.oauth_provider_arn
            response.userPoolId = mcp.user_pool_id
            response.targetId = mcp.target_id

        elif isinstance(mcp, ExternalContainerMCP):
            response.subType = "container"
            response.ecrRepository = mcp.ecr_repository
            response.imageTag = mcp.image_tag
            response.authType = mcp.auth_type.value
            response.userPoolId = mcp.user_pool_id
            response.environment = mcp.environment
            response.targetId = mcp.target_id
            response.runtimeId = mcp.runtime_id
            response.runtimeUrl = mcp.runtime_url

        elif isinstance(mcp, ExternalMCP):
            # Legacy External MCP (Multi-MCP Proxy)
            response.subType = "legacy"
            response.serverName = mcp.server_name
            response.mcpConfig = {
                "command": mcp.command,
                "args": mcp.args,
                "env": {k: "***" for k in mcp.env.keys()} if mcp.env else {}  # env values 마스킹
            }
            # Legacy fields for backward compatibility
            response.serverUrl = mcp.server_url
            response.authConfig = {
                "type": mcp.auth_config.type,
                "apiKey": "***" if mcp.auth_config.api_key else None
            }
            response.config = mcp.config
            response.runtimeId = mcp.runtime_id
            response.runtimeUrl = mcp.runtime_url
            response.targetId = mcp.target_id

        elif isinstance(mcp, InternalDeployMCP):
            response.ecrRepository = mcp.ecr_repository
            response.imageTag = mcp.image_tag
            response.runtimeId = mcp.runtime_id
            response.runtimeUrl = mcp.runtime_url
            response.enableSemanticSearch = mcp.enable_semantic_search
        elif isinstance(mcp, InternalCreateMCP):
            # Map targets directly (no API Catalog dependency)
            targets = []
            for target in mcp.selected_api_targets:
                # Extract description from OpenAPI schema if available
                description = ""
                if target.openapi_schema:
                    description = target.openapi_schema.get("info", {}).get("description", "")

                targets.append({
                    "id": target.id,
                    "name": target.name,
                    "description": description,
                    "endpoint": target.endpoint,
                    "method": target.method,
                    "authType": target.auth_type,
                    "openApiSchema": target.openapi_schema
                })

            response.selectedApiTargets = targets
            response.enableSemanticSearch = mcp.enable_semantic_search

        return response
