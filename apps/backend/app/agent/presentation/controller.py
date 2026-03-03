"""Agent REST API Controller"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from typing import List, Dict
import boto3
import json
import uuid
import logging

logger = logging.getLogger(__name__)

from app.config import settings
from app.middleware.auth import verify_okta_token
from ..application.service import AgentApplicationService
from ..infrastructure.repositories import DynamoDBAgentRepository
from ..infrastructure.repositories.dynamodb_agent_version_repository import DynamoDBAgentVersionRepository
from ..infrastructure.repositories.mock_agent_repository import MockAgentRepository
from ..infrastructure.repositories.mock_agent_version_repository import MockAgentVersionRepository
from ..dto.request import CreateAgentRequest, UpdateAgentRequest, AgentStatusUpdate, DeployDraftAgentRequest
from ..dto.response import AgentResponse, AgentListResponse
from ..exception.exceptions import AgentNotFoundException

# Playground 관련 import
from app.playground.infrastructure.repositories.dynamodb_session_repository import DynamoDBSessionRepository
from app.playground.infrastructure.clients.strands_agent_client import StrandsAgentClient

router = APIRouter()

# 싱글톤 클라이언트
_strands_client = StrandsAgentClient()
_session_repository = DynamoDBSessionRepository()

# boto3 Session을 사용하여 AWS_PROFILE 적용
if settings.AWS_PROFILE:
    _boto_session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
    _bedrock_runtime = _boto_session.client('bedrock-runtime')
else:
    _bedrock_runtime = boto3.client('bedrock-runtime', region_name=settings.AWS_REGION)


class MCPInfo(BaseModel):
    name: str
    description: str = ""


class KBInfo(BaseModel):
    id: str
    name: str
    description: str = ""


class InstructionGenerateRequest(BaseModel):
    name: str
    description: str = ""
    model: str
    knowledgeBases: List[KBInfo] = []
    mcps: List[MCPInfo] = []


class TestChatRequest(BaseModel):
    name: str
    instructions: str
    model: str
    knowledgeBases: List[str] = []
    mcps: List[str] = []


class TestMessageRequest(BaseModel):
    message: str


def _is_mock_mode() -> bool:
    """Mock 모드 여부 확인"""
    return settings.ENVIRONMENT in ("dev", "development", "local")


def get_agent_service() -> AgentApplicationService:
    """Agent Service 의존성 주입"""
    if _is_mock_mode() and not settings.DYNAMODB_AGENT_TABLE:
        logger.info("📦 Using MockAgentRepository (demo mode)")
        agent_repository = MockAgentRepository()
        version_repository = MockAgentVersionRepository()
    else:
        agent_repository = DynamoDBAgentRepository()
        version_repository = DynamoDBAgentVersionRepository()
    return AgentApplicationService(agent_repository, version_repository)


@router.get("/llms", response_model=dict)
async def get_available_llms(token_payload: dict = Depends(verify_okta_token)):
    """Get available LLM models from Bedrock (Inference Profiles for CRIS)"""
    try:
        # boto3 Session을 사용하여 AWS_PROFILE 적용
        if settings.AWS_PROFILE:
            session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
            bedrock = session.client('bedrock')
        else:
            bedrock = boto3.client('bedrock', region_name=settings.AWS_REGION)
        
        # Get inference profiles (includes CRIS models)
        response = bedrock.list_inference_profiles(
            maxResults=100
        )
        
        models_dict = {}
        for profile in response.get('inferenceProfileSummaries', []):
            profile_id = profile['inferenceProfileId']
            profile_name = profile['inferenceProfileName']
            profile_type = profile.get('type', 'SYSTEM_DEFINED')
            
            # Extract model info from profile
            models = profile.get('models', [])
            if models:
                # Use first model's ARN to extract provider
                model_arn = models[0].get('modelArn', '')
                provider = 'Unknown'
                if 'anthropic' in model_arn.lower():
                    provider = 'Anthropic'
                elif 'amazon' in model_arn.lower():
                    provider = 'Amazon'
                elif 'meta' in model_arn.lower():
                    provider = 'Meta'
                elif 'mistral' in model_arn.lower():
                    provider = 'Mistral AI'
                
                models_dict[profile_id] = {
                    "id": profile_id,
                    "name": profile_name,
                    "provider": provider,
                    "modelId": profile_id,
                    "type": profile_type,
                    "status": profile.get('status', 'ACTIVE')
                }
        
        # Convert to list
        models = list(models_dict.values())
        models.sort(key=lambda x: (x['provider'], x['name']))
        
        print(f"✅ Found {len(models)} Bedrock inference profiles")
        return {"data": models, "status": 200}

    except Exception as e:
        # Fallback to default models if Bedrock is not accessible
        print(f"⚠️ Bedrock API error: {str(e)}")
        return {
            "data": [
                {
                    "id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
                    "name": "Claude 3.5 Sonnet",
                    "provider": "Anthropic",
                    "modelId": "anthropic.claude-3-5-sonnet-20240620-v1:0",
                    "status": "available"
                },
                {
                    "id": "anthropic.claude-3-haiku-20240307-v1:0",
                    "name": "Claude 3 Haiku",
                    "provider": "Anthropic",
                    "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                    "status": "available"
                },
                {
                    "id": "anthropic.claude-3-sonnet-20240229-v1:0",
                    "name": "Claude 3 Sonnet",
                    "provider": "Anthropic",
                    "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
                    "status": "available"
                }
            ],
            "status": 200
        }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: CreateAgentRequest,
    token_payload: dict = Depends(verify_okta_token),
    service: AgentApplicationService = Depends(get_agent_service)
):
    """Agent 생성"""
    user_id = token_payload["sub"]
    agent = await service.create_agent(request, user_id)
    return {"data": agent.dict(), "status": 201}


@router.get("/{agent_id}", response_model=dict)
async def get_agent(
    agent_id: str,
    token_payload: dict = Depends(verify_okta_token),
    service: AgentApplicationService = Depends(get_agent_service)
):
    """Agent 상세 조회"""
    try:
        agent = await service.get_agent(agent_id)
        return {"data": agent.dict(), "status": 200}
    except AgentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=dict)
async def list_agents(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    status: str = None,
    token_payload: dict = Depends(verify_okta_token),
    service: AgentApplicationService = Depends(get_agent_service)
):
    """Agent 목록 조회 (검색, 상태 필터 지원)"""
    result = await service.list_agents(
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        team_tags=None
    )
    return {
        "data": [item.dict() for item in result.items],
        "pagination": {
            "page": result.page,
            "pageSize": result.page_size,
            "totalItems": result.total,
            "totalPages": (result.total + result.page_size - 1) // result.page_size
        }
    }


@router.put("/{agent_id}", response_model=dict)
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    token_payload: dict = Depends(verify_okta_token),
    service: AgentApplicationService = Depends(get_agent_service)
):
    """Agent 수정"""
    try:
        user_id = token_payload["sub"]
        agent = await service.update_agent(agent_id, request, user_id)
        return {"data": agent.dict(), "status": 200}
    except AgentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{agent_id}", response_model=dict)
async def change_agent_status(
    agent_id: str,
    request: AgentStatusUpdate,
    token_payload: dict = Depends(verify_okta_token),
    service: AgentApplicationService = Depends(get_agent_service)
):
    """Agent 상태 변경"""
    try:
        agent = await service.change_agent_status(agent_id, request.enabled)
        return {"data": agent.dict(), "status": 200}
    except AgentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{agent_id}/versions", response_model=dict)
async def get_agent_versions(
    agent_id: str,
    token_payload: dict = Depends(verify_okta_token),
    service: AgentApplicationService = Depends(get_agent_service)
):
    """Agent 버전 히스토리 조회 (전체 snapshot 포함)"""
    versions = await service.get_version_history(agent_id)
    return {
        "data": [
            {
                "id": v.id,
                "version": str(v.version),
                "change_log": v.change_log,
                "deployed_by": v.deployed_by,
                "deployed_at": v.deployed_at,
                # Include snapshot data for frontend
                "llm_model": v.snapshot.get("llm_model"),
                "instruction": v.snapshot.get("instruction"),
                "knowledge_bases": v.snapshot.get("knowledge_bases", []),
                "mcps": v.snapshot.get("mcps", []),
                "status": v.snapshot.get("status"),
            }
            for v in versions
        ],
        "status": 200
    }


@router.post("/generate-instruction")
async def generate_instruction(
    request: InstructionGenerateRequest,
    user: dict = Depends(verify_okta_token)
):
    """
    Generate optimized agent instructions using Claude haiku 4.5

    Uses Bedrock to analyze agent configuration and generate
    tailored instructions based on:
    - Agent name and description
    - Selected LLM model
    - Connected Knowledge Bases
    - Available MCP tools
    """
    try:
        print(f"📥 Received instruction generation request:")
        print(f"   Name: {request.name}")
        print(f"   Description: {request.description}")
        print(f"   Model: {request.model}")
        print(f"   KnowledgeBases: {request.knowledgeBases}")
        print(f"   MCPs count: {len(request.mcps)}")
        for i, mcp in enumerate(request.mcps):
            print(f"   MCP[{i}]: {mcp.name} - {mcp.description}")

        # Build context for Claude
        context_parts = [
            f"Agent Name: {request.name}",
        ]
        
        if request.description:
            context_parts.append(f"Description: {request.description}")
        
        context_parts.append(f"LLM Model: {request.model}")

        if request.knowledgeBases:
            kb_info = [f"- {kb.name}: {kb.description or 'No description'}" for kb in request.knowledgeBases]
            context_parts.append(f"Knowledge Bases:\n" + "\n".join(kb_info))

        if request.mcps:
            mcp_info = [f"- {mcp.name}: {mcp.description or 'No description'}" for mcp in request.mcps]
            context_parts.append(f"Available Tools (MCPs):\n" + "\n".join(mcp_info))

        context = "\n\n".join(context_parts)
        
        # Prompt for Claude (Korean)
        prompt = f"""당신은 AI 에이전트 설계 전문가입니다. 다음 에이전트 설정을 분석하여 최적화된 시스템 instruction을 생성하세요.

<agent_configuration>
{context}
</agent_configuration>

<task>
위 에이전트 설정을 바탕으로 다음 단계를 따라 전략적으로 instruction을 작성하세요:

1. **리소스 분석**
   - Knowledge Bases 목록을 확인하고, 각 KB의 용도와 활용 시나리오 파악
   - MCP Tools 목록을 확인하고, 각 도구의 기능과 사용 상황 분석
   - KB와 MCP를 언제, 어떻게 조합하여 사용할지 전략 수립

2. **역할 정의**
   - 에이전트의 핵심 역할과 목적을 명확히 정의
   - KB와 MCP를 활용한 구체적인 문제 해결 방식 명시

3. **리소스 활용 가이드라인**
   - 각 Knowledge Base를 언제 참조해야 하는지 명확히 지시
   - 각 MCP Tool을 언제 사용해야 하는지 구체적으로 설명
   - KB 검색 → MCP 실행 등 리소스 조합 전략 제시
   - 불필요한 KB, MCP 조회는 지양하며, KB툴과 MCP툴들은 의존성이 없는 이상 최대한 병렬 호출 하도록 가이드

4. **응답 품질 보장**
   - KB에서 찾은 정보를 어떻게 인용하고 활용할지 안내
   - MCP 실행 결과를 사용자에게 어떻게 전달할지 명시
   - 정보가 불확실하거나 없을 때의 대응 방안 설정
</task>

<example>
다음은 "AnyCompany 고객 서비스 에이전트"의 instruction 예시입니다:

<role>
당신은 AnyCompany의 공식 AI 고객 서비스 담당자입니다. 고객의 문의에 친절하고 정확하게 응답하며, AnyCompany의 서비스 품질을 대표합니다.

주요 책임:
- 항공권 예약, 변경, 환불 관련 문의 응대
- 마일리지 및 SKYPASS 프로그램 안내
- 수하물 규정 및 기내 서비스 정보 제공
- 출입국 요건 및 여행 준비사항 안내
</role>

<knowledge_bases>
## Homepage-FAQ Knowledge Base
- **용도**: AnyCompany 공식 FAQ 및 일반 고객 문의 답변
- **활용 시점**: 고객이 일반적인 서비스 정책, 수하물 규정, 마일리지 사용법 등을 문의할 때
- **검색 전략**: 고객 질문의 핵심 키워드를 추출하여 검색 (예: "환불", "수하물", "마일리지 적립")

## Tariff-Rules Knowledge Base
- **용도**: 항공권 운임 규정 및 변경/환불 수수료 정보
- **활용 시점**: 항공권 변경 수수료, 환불 조건, 운임 클래스별 규정 문의 시
- **검색 전략**: 운임 클래스(Y, C, F 등)와 함께 규정 유형으로 검색
</knowledge_bases>

<tools>
## Reservation-MCP
- **기능**: 예약 조회, 생성, 변경, 취소
- **사용 시점**: 고객이 예약 확인, 좌석 변경, 일정 변경을 요청할 때
- **주의사항**: 예약 변경 전 반드시 Tariff-Rules KB에서 수수료 정책 확인

## SKYPASS-MCP
- **기능**: 마일리지 조회, 적립 내역, 사용 가능 보너스 항공권 조회
- **사용 시점**: 마일리지 잔액 확인, 적립 예정 마일리지 계산, 보너스 항공권 가용성 확인 시
</tools>

<guidelines>
## 응답 원칙
1. 항상 존댓말을 사용하고 "고객님"으로 호칭
2. KB에서 찾은 정보는 출처와 함께 명확히 전달
3. 불확실한 정보는 "확인이 필요합니다"라고 안내하고 고객센터 연결 제안

## 리소스 활용 순서
1. 먼저 질문 유형 파악 (정보 조회 vs 예약 작업)
2. 정보 조회: 관련 KB 검색 → 결과 요약 → 추가 정보 필요시 MCP 호출
3. 예약 작업: KB에서 규정 확인 → MCP로 작업 수행 → 결과 안내

## 병렬 처리
- 독립적인 정보 조회는 병렬로 수행 (예: FAQ 검색 + 마일리지 조회)
- 의존성이 있는 작업은 순차 처리 (예: 규정 확인 후 예약 변경)
</guidelines>
</example>

<important>
- 반드시 한국어로 작성하세요
- 위 예시처럼 XML 태그 형식(<role>, <knowledge_bases>, <tools>, <guidelines>)을 사용하여 구조화하세요
- Knowledge Bases와 MCP Tools가 있다면 각각의 **이름을 명시**하고 활용 전략을 구체적으로 작성하세요
- 없는 Knowledge Bases / MCP는 절대로 가정하지 마세요. 없을 경우 응답에서 각 태그자체(<knowledge_bases>, <tools>를 없애세요. 
- 단순한 일반론이 아닌, 제공된 리소스 목록을 반영한 **맞춤형 instruction**을 작성하세요
- 최소 1500자 이상의 상세하고 구체적인 instruction을 작성하세요
- KB 참조 시 "KB에서", "FAQ에서" 등 출처를 명확히 언급하도록 가이드하세요
</important>

<output_format>
- instruction 텍스트만 직접 출력하세요
- 백틱(```)이나 코드 블록으로 감싸지 마세요
- "다음은 instruction입니다" 같은 서문이나 추가 설명 없이 instruction 내용만 바로 시작하세요
</output_format>"""

        # Call Claude Haiku 4.5 - 싱글톤 클라이언트 사용
        response = _bedrock_runtime.invoke_model(
            modelId='global.anthropic.claude-haiku-4-5-20251001-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8192,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        result = json.loads(response['body'].read())
        instruction = result['content'][0]['text']
        
        return {
            "data": {
                "instruction": instruction.strip()
            },
            "status": 200
        }
        
    except Exception as e:
        print(f"❌ Failed to generate instruction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate instruction: {str(e)}")


@router.post("/test/session")
async def create_test_session(
    request: TestChatRequest,
    user: dict = Depends(verify_okta_token)
):
    """Create temporary test session for Agent Create page"""
    try:
        session_id = f"test-{uuid.uuid4()}"
        user_id = user["sub"]
        
        # Create temporary session (not saved to DB)
        session_data = {
            "session_id": session_id,
            "agent_config": {
                "name": request.name,
                "instructions": request.instructions,
                "model": request.model,
                "knowledge_bases": request.knowledgeBases,
                "mcps": request.mcps,
            },
            "user_id": user_id,
        }
        
        # Store in memory (or cache) - for now just return session_id
        return {
            "data": {
                "sessionId": session_id,
                "config": session_data["agent_config"]
            },
            "status": 200
        }
        
    except Exception as e:
        print(f"❌ Failed to create test session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create test session: {str(e)}")


@router.post("/test/{session_id}/message")
async def send_test_message(
    session_id: str,
    request: TestMessageRequest,
    user: dict = Depends(verify_okta_token)
):
    """Send message to test session (simplified, no DB persistence)"""
    try:
        # TODO: Retrieve session config from cache/memory
        # For now, return mock response

        response_content = f"[Test Mode] Received: {request.message}"

        return {
            "data": {
                "content": response_content,
                "metadata": {
                    "tokens": {"input": 10, "output": 20},
                    "responseTime": 500
                }
            },
            "status": 200
        }

    except Exception as e:
        print(f"❌ Failed to send test message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send test message: {str(e)}")


@router.post("/draft/deploy", response_model=dict)
async def deploy_draft_agent(
    request: DeployDraftAgentRequest,
    user: dict = Depends(verify_okta_token)
):
    """Draft Agent 배포 (Agent Edit/Create 화면 테스트용)

    Agent를 저장하지 않고 임시로 AgentCore Runtime에 배포하여 테스트합니다.
    Playground의 배포 프로세스를 재사용합니다.
    """
    try:
        from app.playground.application.service import DeploymentService
        from app.playground.infrastructure.repositories.dynamodb_deployment_repository import DynamoDBDeploymentRepository
        from app.playground.infrastructure.repositories.dynamodb_conversation_repository import DynamoDBConversationRepository
        from app.playground.infrastructure.clients.agentcore_client import AgentCoreClient
        from app.playground.infrastructure.code_generator import AgentCodeGenerator
        from app.knowledge_bases.infrastructure.repositories.dynamodb_kb_repository import DynamoDBKBRepository

        user_id = user["sub"]

        # Deployment Service 초기화
        deployment_repository = DynamoDBDeploymentRepository()
        conversation_repository = DynamoDBConversationRepository()
        agent_repository = DynamoDBAgentRepository()
        kb_repository = DynamoDBKBRepository()
        agentcore_client = AgentCoreClient(
            region=settings.AWS_REGION,
            role_arn=settings.PLAYGROUND_RUNTIME_ROLE_ARN or settings.AGENTCORE_ROLE_ARN,
            ecr_repository=settings.PLAYGROUND_ECR_REPOSITORY,
            codebuild_project=settings.CODEBUILD_PROJECT_NAME,
            source_bucket=settings.AGENT_BUILD_SOURCE_BUCKET
        )
        code_generator = AgentCodeGenerator()

        deployment_service = DeploymentService(
            deployment_repository=deployment_repository,
            conversation_repository=conversation_repository,
            agent_repository=agent_repository,
            kb_repository=kb_repository,
            agentcore_client=agentcore_client,
            code_generator=code_generator
        )

        # Draft Agent ID 생성 (기존 agent_id가 있으면 사용, 없으면 "draft-{uuid}" 생성)
        draft_agent_id = request.agent_id or f"draft-{uuid.uuid4()}"
        draft_version = "draft"

        # Draft Agent 임시 저장 (배포를 위해 필요)
        from app.agent.domain.entities.agent import Agent
        from app.agent.domain.value_objects import (
            AgentId, LLMModel, Instruction, AgentStatus
        )

        # 기존 Agent가 있으면 업데이트, 없으면 새로 생성
        existing_agent = await agent_repository.find_by_id(draft_agent_id)
        if existing_agent:
            # Edit 모드: 기존 Agent 업데이트
            existing_agent.name = request.name
            existing_agent.description = request.description
            existing_agent.llm_model = LLMModel(
                model_id=request.llm_model_id,
                model_name=request.llm_model_name,
                provider=request.llm_provider
            )
            existing_agent.instruction = Instruction(
                system_prompt=request.system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            existing_agent.knowledge_bases = request.knowledge_bases
            existing_agent.mcps = request.mcps
            await agent_repository.save(existing_agent)
            logger.info(f"Updated existing draft agent: {draft_agent_id}")
        else:
            # Create 모드: 새 Draft Agent 생성
            draft_agent = Agent(
                id=AgentId(draft_agent_id),
                name=request.name,
                description=request.description,
                llm_model=LLMModel(
                    model_id=request.llm_model_id,
                    model_name=request.llm_model_name,
                    provider=request.llm_provider
                ),
                instruction=Instruction(
                    system_prompt=request.system_prompt,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                ),
                knowledge_bases=request.knowledge_bases,
                mcps=request.mcps,
                team_tags=[],
                status=AgentStatus.DRAFT,
                created_by=user_id
            )
            await agent_repository.save(draft_agent)
            logger.info(f"Created new draft agent: {draft_agent_id}")

        # 배포 실행 (Playground DeploymentService 재사용)
        deployment_response = await deployment_service.deploy_agent(
            user_id=user_id,
            agent_id=draft_agent_id,
            version=draft_version,
            conversation_id=None,  # Draft는 새 대화
            force_rebuild=request.force_rebuild
        )

        return {
            "data": {
                "id": deployment_response.id,
                "agent_id": draft_agent_id,
                "version": draft_version,
                "status": deployment_response.status,
                "runtime_id": deployment_response.runtime_id,
                "runtime_arn": deployment_response.runtime_arn,
                "endpoint_url": deployment_response.endpoint_url,
                "build_id": deployment_response.build_id,
                "build_phase": deployment_response.build_phase,
                "build_phase_message": deployment_response.build_phase_message,
                "idle_timeout": deployment_response.idle_timeout,
                "max_lifetime": deployment_response.max_lifetime,
                "created_at": deployment_response.created_at,
                "updated_at": deployment_response.updated_at,
                "expires_at": deployment_response.expires_at,
                "error_message": deployment_response.error_message
            },
            "status": 200
        }

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"❌ Failed to deploy draft agent: {str(e)}\n{error_details}")
        print(f"❌ Failed to deploy draft agent: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to deploy draft agent: {str(e)}")
