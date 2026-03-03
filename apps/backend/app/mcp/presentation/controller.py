"""MCP Controllers - FastAPI Router + Business Logic"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.middleware.auth import verify_okta_token
from ..application.service import MCPApplicationService
from ..dto.request import (
    CreateExternalMCPRequest, CreateInternalDeployMCPRequest,
    CreateInternalCreateMCPRequest, MCPStatusRequest, TargetInfo,
    CreateExternalEndpointMCPRequest, CreateExternalContainerMCPRequest
)
from ..exception.exceptions import MCPDomainException
from .dependencies import get_mcp_service, get_ecr_service

router = APIRouter()


# Pydantic Models for FastAPI
class TargetInfoModel(BaseModel):
    """Target 정보 (Pydantic)

    Frontend에서 camelCase로 전송하는 필드를 snake_case로 매핑합니다.
    """
    name: str
    description: str
    endpoint: str
    method: str
    openapi_schema: Dict[str, Any] = Field(alias="openApiSchema")
    api_id: Optional[str] = Field(default=None, alias="apiId")
    team_tag_ids: Optional[List[str]] = Field(default=None, alias="teamTagIds")

    model_config = {
        "populate_by_name": True,  # Allow both alias and field name
    }


class CreateMCPRequest(BaseModel):
    """MCP 생성 요청"""
    type: str  # "external" | "external-endpoint" | "external-container" | "internal-deploy" | "internal-create"
    name: str
    description: str
    team_tags: List[str] = []  # Optional - 기능 제거됨

    # External MCP fields (Legacy Multi-MCP Proxy)
    server_name: Optional[str] = None  # Tool prefix (예: "youtube", "github")
    mcp_config: Optional[Dict[str, Any]] = None  # {command, args, env}

    # External MCP (Endpoint URL) fields
    endpoint_url: Optional[str] = None  # MCP 서버 엔드포인트 URL

    # External MCP (Container Image) fields - ecr_repository, image_tag, environment는 Internal Deploy와 공유

    # External MCP 공통 fields
    auth_type: Optional[str] = None  # "no_auth" | "oauth"
    oauth_provider_arn: Optional[str] = None  # OAuth 선택 시 AgentCore Identity OAuth2 Credential Provider ARN
    user_pool_id: Optional[str] = None  # (Legacy) OAuth 선택 시 User Pool ID

    # Internal Deploy MCP & External Container fields
    ecr_repository: Optional[str] = None
    image_tag: Optional[str] = None
    resources: Optional[dict] = None
    environment: Optional[dict] = None

    # Internal Deploy MCP Configuration
    enable_semantic_search: Optional[bool] = False  # Enable semantic search for tool discovery

    # Internal Create MCP fields
    targets: Optional[List[TargetInfoModel]] = None


class UpdateMCPRequest(BaseModel):
    """MCP 업데이트 요청"""
    description: Optional[str] = None
    team_tags: Optional[List[str]] = None
    targets: Optional[List[TargetInfoModel]] = None  # For internal-create MCP updates
    image_tag: Optional[str] = None  # For internal-deploy MCP updates
    # For external MCP (endpoint type) updates
    endpoint_url: Optional[str] = None
    auth_type: Optional[str] = None  # "no_auth" | "oauth"
    oauth_provider_arn: Optional[str] = None  # AgentCore Identity OAuth2 Credential Provider ARN
    user_pool_id: Optional[str] = None  # Legacy
    # For internal MCP (Deploy & Create) - Semantic Search
    enable_semantic_search: Optional[bool] = None


class MCPStatusToggleRequest(BaseModel):
    """MCP 상태 토글 요청"""
    status: str  # "enabled" | "disabled"


@router.get("/", response_model=dict)
async def get_mcps(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(verify_okta_token),
    service: MCPApplicationService = Depends(get_mcp_service)
):
    """MCP 목록 조회"""
    try:
        response = await service.list_mcps(
            search=search,
            type_filter=type,
            status_filter=status
        )
        return {
            "success": True,
            "data": [
                {
                    "id": mcp.id,
                    "name": mcp.name,
                    "description": mcp.description,
                    "type": mcp.type,
                    "status": mcp.status,
                    "version": mcp.version,
                    "endpoint": mcp.endpoint,
                    "toolList": mcp.toolList,
                    "teamTagIds": mcp.teamTagIds,
                    "createdAt": mcp.createdAt,
                    "updatedAt": mcp.updatedAt,
                    "enableSemanticSearch": mcp.enableSemanticSearch
                }
                for mcp in response.data
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": response.total,
                "total_pages": (response.total + page_size - 1) // page_size
            }
        }
    except MCPDomainException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_mcp(
    request: CreateMCPRequest,
    user: dict = Depends(verify_okta_token),
    service: MCPApplicationService = Depends(get_mcp_service)
):
    """MCP 생성"""
    try:
        mcp_type = request.type
        
        if mcp_type == "external":
            # Legacy External MCP (Multi-MCP Proxy)
            dto_request = CreateExternalMCPRequest(
                name=request.name,
                description=request.description,
                team_tags=request.team_tags,
                server_name=request.server_name,  # Tool prefix (예: "youtube", "github")
                mcp_config=request.mcp_config or {}  # {command, args, env}
            )
            response = await service.create_external_mcp(dto_request)

        elif mcp_type == "external-endpoint":
            # External MCP (Endpoint URL)
            dto_request = CreateExternalEndpointMCPRequest(
                name=request.name,
                description=request.description,
                team_tags=request.team_tags,
                endpoint_url=request.endpoint_url,
                auth_type=request.auth_type or "no_auth",
                oauth_provider_arn=request.oauth_provider_arn,
                user_pool_id=request.user_pool_id
            )
            response = await service.create_external_endpoint_mcp(dto_request)

        elif mcp_type == "external-container":
            # External MCP (Container Image)
            dto_request = CreateExternalContainerMCPRequest(
                name=request.name,
                description=request.description,
                team_tags=request.team_tags,
                ecr_repository=request.ecr_repository,
                image_tag=request.image_tag,
                auth_type=request.auth_type or "no_auth",
                user_pool_id=request.user_pool_id,
                environment=request.environment
            )
            response = await service.create_external_container_mcp(dto_request)

        elif mcp_type == "internal-deploy":
            dto_request = CreateInternalDeployMCPRequest(
                name=request.name,
                description=request.description,
                team_tags=request.team_tags,
                ecr_repository=request.ecr_repository,
                image_tag=request.image_tag,
                resources=request.resources or {},
                environment=request.environment or {},
                enable_semantic_search=request.enable_semantic_search or False
            )
            response = await service.create_internal_deploy_mcp(dto_request)
            
        elif mcp_type == "internal-create":
            # TargetInfoModel을 TargetInfo dataclass로 변환
            # Note: TargetInfo uses camelCase (openApiSchema), Pydantic uses snake_case (openapi_schema)
            targets = [
                TargetInfo(
                    name=t.name,
                    description=t.description,
                    endpoint=t.endpoint,
                    method=t.method,
                    openApiSchema=t.openapi_schema,
                    apiId=t.api_id,
                    teamTagIds=t.team_tag_ids
                )
                for t in (request.targets or [])
            ]
            
            dto_request = CreateInternalCreateMCPRequest(
                name=request.name,
                description=request.description,
                team_tags=request.team_tags,
                targets=targets,
                enable_semantic_search=request.enable_semantic_search or False
            )
            response = await service.create_internal_create_mcp(dto_request)
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MCP type: {mcp_type}"
            )
        
        return {
            "success": True,
            "data": {
                "id": response.id,
                "name": response.name,
                "description": response.description,
                "type": response.type,
                "status": response.status,
                "version": response.version,
                "endpoint": response.endpoint,
                "teamTagIds": response.teamTagIds,
                "toolList": response.toolList,
                "createdAt": response.createdAt,
                "updatedAt": response.updatedAt
            }
        }
        
    except MCPDomainException as e:
        if "already exists" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/stream", response_class=StreamingResponse)
async def create_mcp_stream(
    request: CreateMCPRequest,
    user: dict = Depends(verify_okta_token),
    service: MCPApplicationService = Depends(get_mcp_service)
):
    """MCP 생성 (SSE 스트리밍)

    Internal Deploy MCP 생성 시 진행 상황을 실시간으로 스트리밍합니다.
    현재는 internal-deploy 타입만 지원합니다.

    Returns:
        StreamingResponse: SSE 형식의 진행 상황 스트림
            - event: progress - 진행 상황 업데이트
            - event: result - 최종 결과 (성공/실패)
    """
    mcp_type = request.type

    if mcp_type != "internal-deploy":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSE streaming is only supported for 'internal-deploy' type. Use POST /mcps/ for other types."
        )

    dto_request = CreateInternalDeployMCPRequest(
        name=request.name,
        description=request.description,
        team_tags=request.team_tags,
        ecr_repository=request.ecr_repository,
        image_tag=request.image_tag,
        resources=request.resources or {},
        environment=request.environment or {},
        enable_semantic_search=request.enable_semantic_search or False
    )

    async def event_generator():
        async for event in service.create_internal_deploy_mcp_stream(dto_request):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# Cognito Endpoints - Must be before /{mcp_id}
@router.get("/cognito/user-pools", response_model=dict)
async def get_cognito_user_pools(
    user: dict = Depends(verify_okta_token),
    service: MCPApplicationService = Depends(get_mcp_service)
):
    """Cognito User Pool 목록 조회

    OAuth 인증 방식 선택 시 사용자가 선택할 User Pool 목록을 반환합니다.
    AWS 계정 내 모든 Cognito User Pool을 조회합니다.
    """
    try:
        user_pools = await service.list_cognito_user_pools()
        return {
            "success": True,
            "data": user_pools,
            "total": len(user_pools)
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# AgentCore Identity Endpoints - Must be before /{mcp_id}
@router.get("/identity/oauth-providers", response_model=dict)
async def get_oauth2_credential_providers(
    user: dict = Depends(verify_okta_token),
    service: MCPApplicationService = Depends(get_mcp_service)
):
    """OAuth2 Credential Provider 목록 조회

    OAuth 인증 방식 선택 시 사용자가 선택할 OAuth2 Credential Provider 목록을 반환합니다.
    AgentCore Identity에 등록된 모든 OAuth2 타입 Credential Provider를 조회합니다.
    """
    try:
        providers = await service.list_oauth2_credential_providers()
        return {
            "success": True,
            "data": providers,
            "total": len(providers)
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ECR Management Endpoints (MCP 도메인 내) - Must be before /{mcp_id}
@router.get("/ecr/repositories", response_model=dict)
async def get_ecr_repositories(
    user: dict = Depends(verify_okta_token),
    ecr_service = Depends(get_ecr_service)
):
    """ECR 레포지토리 목록 조회"""
    try:
        repositories = await ecr_service.list_repositories()
        return {
            "success": True,
            "data": repositories,
            "total": len(repositories)
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/ecr/images/by-repository", response_model=dict)
async def get_ecr_repository_images(
    repository: str,
    user: dict = Depends(verify_okta_token),
    ecr_service = Depends(get_ecr_service)
):
    """특정 ECR 레포지토리의 이미지 태그 목록 조회"""
    try:
        images = await ecr_service.list_image_tags(repository=repository)
        return {
            "success": True,
            "data": images,
            "total": len(images)
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/ecr/repository", response_model=dict)
async def get_ecr_repository(
    user: dict = Depends(verify_okta_token),
    ecr_service = Depends(get_ecr_service)
):
    """ECR 레포지토리 정보 조회 (deprecated - use /ecr/repositories)"""
    try:
        repository_info = ecr_service.get_repository_info()
        return {
            "success": True,
            "data": repository_info
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/ecr/images", response_model=dict)
async def get_ecr_images(
    user: dict = Depends(verify_okta_token),
    ecr_service = Depends(get_ecr_service)
):
    """ECR 이미지 태그 목록 조회 (deprecated - use /ecr/repositories/{name}/images)"""
    try:
        images = await ecr_service.list_image_tags()
        return {
            "success": True,
            "data": images,
            "total": len(images)
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{mcp_id}", response_model=dict)
async def get_mcp(
    mcp_id: str,
    user: dict = Depends(verify_okta_token),
    service: MCPApplicationService = Depends(get_mcp_service)
):
    """MCP 상세 조회"""
    try:
        response = await service.get_mcp(mcp_id)
        data = {
            "id": response.id,
            "name": response.name,
            "description": response.description,
            "type": response.type,
            "status": response.status,
            "version": response.version,
            "endpoint": response.endpoint,
            "toolList": response.toolList,
            "teamTagIds": response.teamTagIds,
            "createdAt": response.createdAt,
            "updatedAt": response.updatedAt
        }

        # Add type-specific fields
        # External MCP sub-type fields
        if response.subType is not None:
            data["subType"] = response.subType
        if response.endpointUrl is not None:
            data["endpointUrl"] = response.endpointUrl
        if response.authType is not None:
            data["authType"] = response.authType
        if response.oauthProviderArn is not None:
            data["oauthProviderArn"] = response.oauthProviderArn
        if response.userPoolId is not None:
            data["userPoolId"] = response.userPoolId
        if response.environment is not None:
            data["environment"] = response.environment
        if response.targetId is not None:
            data["targetId"] = response.targetId

        # Internal Create MCP fields
        if response.selectedApiTargets is not None:
            data["selectedApiTargets"] = response.selectedApiTargets

        # Legacy External MCP fields
        if response.serverUrl is not None:
            data["serverUrl"] = response.serverUrl
        if response.serverName is not None:
            data["serverName"] = response.serverName
        if response.mcpConfig is not None:
            data["mcpConfig"] = response.mcpConfig

        # Internal Deploy & External Container fields
        if response.ecrRepository is not None:
            data["ecrRepository"] = response.ecrRepository
        if response.imageTag is not None:
            data["imageTag"] = response.imageTag
        if response.runtimeId is not None:
            data["runtimeId"] = response.runtimeId
        if response.runtimeUrl is not None:
            data["runtimeUrl"] = response.runtimeUrl

        # Internal MCP (Deploy & Create) - Semantic Search
        if response.enableSemanticSearch is not None:
            data["enableSemanticSearch"] = response.enableSemanticSearch

        return {
            "success": True,
            "data": data
        }
    except MCPDomainException as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{mcp_id}", response_model=dict)
async def update_mcp(
    mcp_id: str,
    request: UpdateMCPRequest,
    user: dict = Depends(verify_okta_token),
    service: MCPApplicationService = Depends(get_mcp_service)
):
    """MCP 업데이트"""
    from ..dto.request import UpdateMCPRequest as UpdateMCPRequestDTO, TargetInfo

    try:
        # Pydantic Model을 DTO로 변환
        # Note: TargetInfo uses camelCase (openApiSchema), Pydantic uses snake_case (openapi_schema)
        targets = None
        if request.targets:
            targets = [
                TargetInfo(
                    name=t.name,
                    description=t.description,
                    endpoint=t.endpoint,
                    method=t.method,
                    openApiSchema=t.openapi_schema,
                    apiId=t.api_id,
                    teamTagIds=t.team_tag_ids
                )
                for t in request.targets
            ]

        dto_request = UpdateMCPRequestDTO(
            description=request.description,
            team_tags=request.team_tags,
            targets=targets,
            image_tag=request.image_tag,
            # External MCP (endpoint type) update fields
            endpoint_url=request.endpoint_url,
            auth_type=request.auth_type,
            oauth_provider_arn=request.oauth_provider_arn,
            user_pool_id=request.user_pool_id,
            # Internal MCP (Deploy & Create) - Semantic Search
            enable_semantic_search=request.enable_semantic_search
        )

        response = await service.update_mcp(mcp_id, dto_request)

        data = {
            "id": response.id,
            "name": response.name,
            "description": response.description,
            "type": response.type,
            "status": response.status,
            "version": response.version,
            "endpoint": response.endpoint,
            "toolList": response.toolList,
            "teamTagIds": response.teamTagIds,
            "createdAt": response.createdAt,
            "updatedAt": response.updatedAt
        }

        # Add enableSemanticSearch for internal MCP types
        if response.enableSemanticSearch is not None:
            data["enableSemanticSearch"] = response.enableSemanticSearch

        return {
            "success": True,
            "data": data
        }
    except MCPDomainException as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/{mcp_id}", response_model=dict)
async def toggle_mcp_status(
    mcp_id: str,
    request: MCPStatusToggleRequest,
    user: dict = Depends(verify_okta_token),
    service: MCPApplicationService = Depends(get_mcp_service)
):
    """MCP 상태 토글"""
    try:
        dto_request = MCPStatusRequest(status=request.status)
        response = await service.toggle_mcp_status(mcp_id, dto_request)
        return {
            "success": True,
            "data": {
                "id": response.id,
                "name": response.name,
                "status": response.status,
                "message": f"MCP status changed to {request.status}"
            }
        }
    except MCPDomainException as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{mcp_id}/versions", response_model=dict)
async def get_mcp_versions(
    mcp_id: str,
    user: dict = Depends(verify_okta_token),
    service: MCPApplicationService = Depends(get_mcp_service)
):
    """MCP 버전 히스토리 조회"""
    try:
        versions = await service.get_mcp_versions(mcp_id)
        return {
            "success": True,
            "data": [
                {
                    "version": v.version,
                    "description": v.description,
                    "changeLog": v.change_log,
                    "status": v.status.value if hasattr(v.status, 'value') else v.status,
                    "createdAt": v.created_at,
                    "createdBy": v.created_by,
                    "endpoint": v.endpoint,
                    "toolList": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.input_schema,
                            "responses": tool.responses,
                            "method": tool.method,
                            "endpoint": tool.endpoint,
                            "authType": tool.auth_type,
                        }
                        for tool in v.tool_list
                    ] if v.tool_list else []
                }
                for v in versions
            ],
            "total": len(versions)
        }
    except MCPDomainException as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{mcp_id}/health", response_model=dict)
async def check_mcp_health(
    mcp_id: str,
    user: dict = Depends(verify_okta_token),
    service: MCPApplicationService = Depends(get_mcp_service)
):
    """MCP Health 체크

    enabled 상태인 MCP의 Gateway health를 체크합니다.
    disabled MCP는 health 체크를 수행하지 않습니다.
    결과는 60초간 캐싱됩니다.
    """
    try:
        result = await service.check_mcp_health(mcp_id)
        return {
            "success": True,
            "data": result
        }
    except MCPDomainException as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/external/sync", response_model=dict)
async def sync_external_mcp_runtime(
    user: dict = Depends(verify_okta_token),
    service: MCPApplicationService = Depends(get_mcp_service)
):
    """External MCP Runtime 동기화

    DynamoDB에 저장된 모든 External MCP 설정을 Runtime에 반영합니다.
    Runtime을 재시작하고 각 MCP의 tools를 조회합니다.

    Note: 이 작업은 1-2분 정도 소요됩니다.
    """
    try:
        result = await service.sync_external_mcp_runtime()
        return {
            "success": True,
            "data": result,
            "message": "External MCP Runtime synced successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{mcp_id}/tools", response_model=dict)
async def get_mcp_tools(
    mcp_id: str,
    user: dict = Depends(verify_okta_token),
    service: MCPApplicationService = Depends(get_mcp_service)
):
    """MCP Tool 목록 조회

    Agent에서 MCP의 Tool 목록을 조회할 때 사용합니다.
    """
    try:
        mcp = await service.get_mcp(mcp_id)
        tools = mcp.toolList or []

        return {
            "success": True,
            "data": {
                "mcpId": mcp.id,
                "mcpName": mcp.name,
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema,
                        "responses": tool.responses,
                        "method": tool.method,
                        "endpoint": tool.endpoint,
                        "authType": tool.authType,
                    }
                    for tool in tools
                ]
            },
            "total": len(tools)
        }
    except MCPDomainException as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
