"""Agent Code Generator - Agent 설정 기반 코드 동적 생성

Container Deploy (ECR) 방식을 사용하여 AgentCore Runtime에 배포합니다.
"""
import os
import logging
from datetime import datetime
from typing import Any
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# 템플릿 디렉토리
TEMPLATE_DIR = Path(__file__).parent / "templates"


class AgentCodeGenerator:
    """Agent 코드 생성기 (Container 방식)

    Agent 설정을 기반으로 AgentCore Runtime에 배포할 코드를 생성합니다.

    생성 파일:
    - agent.py: 메인 Agent 코드
    - kb_tools.py: Knowledge Base Retrieval 도구 (KB가 있는 경우)
    - requirements.txt: 의존성 목록
    - Dockerfile: Container 이미지 빌드용
    """

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=select_autoescape()
        )

    def generate(
        self,
        agent_config: dict,
        session_bucket: str = None,
        session_prefix: str = None,
        local_testing: bool = False,
        base_image_uri: str = None
    ) -> dict[str, str]:
        """Agent 코드 생성 (Container 방식)

        Args:
            agent_config: Agent 설정
                - agent_id: Agent ID
                - agent_name: Agent 이름
                - version: 버전
                - model_id: 모델 ID
                - system_prompt: 시스템 프롬프트
                - temperature: 온도 (기본값: 0.7)
                - max_tokens: 최대 토큰 (기본값: 2000)
                - knowledge_bases: KB 목록 [{"id": "kb-id", "name": "kb-name"}, ...]
                - tools: Strands 커뮤니티 도구 목록 ["file_read", "file_write", "editor", ...]
                - mcp_servers: MCP 서버 목록 [
                    {
                        "name": "server_name",      # MCP 서버 이름 (prefix로 사용)
                        "transport": "http",        # http, sse, stdio 중 선택
                        "url": "http://...",        # http/sse 방식일 때 URL
                        "headers": {...},           # http 방식일 때 인증 헤더 (선택)
                        "command": "uvx",           # stdio 방식일 때 명령어
                        "args": [...]               # stdio 방식일 때 인자
                    }, ...
                  ]
            session_bucket: 세션 저장용 S3 버킷
            session_prefix: 세션 저장용 S3 prefix
            local_testing: 로컬 테스트용 코드 생성 여부 (기본값: False)
                - True: OTel 워크어라운드 포함 (로컬에서 python agent.py 실행용)
                - False: 워크어라운드 제외 (AgentCore Runtime 배포용)
            base_image_uri: 커스텀 베이스 이미지 URI (선택)

        Returns:
            {filename: content} 딕셔너리
        """
        files = {}

        # 컨텍스트 준비
        context = self._prepare_context(
            agent_config, session_bucket, session_prefix, local_testing, base_image_uri
        )

        # agent.py 생성
        agent_template = self.env.get_template("agent_template.py.j2")
        files["agent.py"] = agent_template.render(**context)

        # KB가 있는 경우 kb_tools.py 생성
        if context.get("knowledge_bases"):
            kb_template = self.env.get_template("kb_tools_template.py.j2")
            files["kb_tools.py"] = kb_template.render(**context)

        # requirements.txt 생성
        req_template = self.env.get_template("requirements.txt.j2")
        files["requirements.txt"] = req_template.render(**context)

        # Dockerfile 생성
        dockerfile_template = self.env.get_template("Dockerfile.j2")
        files["Dockerfile"] = dockerfile_template.render(**context)

        # buildspec.yml 생성 (CodeBuild용)
        files["buildspec.yml"] = self._generate_buildspec(base_image_uri=base_image_uri)

        logger.info(f"Generated {len(files)} files for agent {agent_config.get('agent_name')} (container)")
        return files

    def _generate_buildspec(self, base_image_uri: str = None, include_runtime: bool = True) -> str:
        """buildspec.yml 생성 (ARM64 크로스 빌드 + Runtime 생성)

        Args:
            base_image_uri: 베이스 이미지 URI. 있으면 QEMU 설정 건너뛰기
            include_runtime: Runtime 생성 포함 여부 (기본값: True)
        """
        from textwrap import dedent

        # Runtime 생성 명령어 (post_build에 추가)
        # dedent() 후 post_build.commands 아래의 아이템은 6칸 들여쓰기
        runtime_commands = ""
        if include_runtime:
            # 첫 줄은 줄바꿈만, 6칸 들여쓰기로 시작
            runtime_commands = "\n" + """\
      # Runtime 생성이 필요한 경우에만 실행 (RUNTIME_NAME이 설정된 경우)
      - |
        if [ -n "$RUNTIME_NAME" ]; then
          echo "Creating AgentCore Runtime..."
          CONTAINER_URI="$ECR_REPOSITORY_URL:$IMAGE_TAG"
          RESPONSE=$(aws bedrock-agentcore-control create-agent-runtime \\
            --agent-runtime-name "$RUNTIME_NAME" \\
            --description "Playground Agent - $RUNTIME_NAME" \\
            --agent-runtime-artifact "{\\"containerConfiguration\\": {\\"containerUri\\": \\"$CONTAINER_URI\\"}}" \\
            --role-arn "$AGENTCORE_ROLE_ARN" \\
            --network-configuration '{"networkMode": "PUBLIC"}' \\
            --output json 2>&1) || {
              echo "Failed to create runtime: $RESPONSE"
              echo '{"status": "failed", "error": "'"$RESPONSE"'"}' > /tmp/runtime_result.json
              aws s3 cp /tmp/runtime_result.json "s3://$SOURCE_BUCKET/$S3_PREFIX/runtime_result.json"
              exit 1
            }
          echo "$RESPONSE"
          RUNTIME_ID=$(echo "$RESPONSE" | jq -r '.agentRuntimeId')
          RUNTIME_ARN=$(echo "$RESPONSE" | jq -r '.agentRuntimeArn')
          echo "Runtime ID: $RUNTIME_ID"
          echo "Runtime ARN: $RUNTIME_ARN"
          echo "Waiting for Runtime to be READY..."
          MAX_ATTEMPTS=60
          ATTEMPT=0
          while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
            STATUS=$(aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id "$RUNTIME_ID" --query 'status' --output text 2>/dev/null || echo "UNKNOWN")
            echo "Attempt $((ATTEMPT+1))/$MAX_ATTEMPTS - Status: $STATUS"
            if [ "$STATUS" = "READY" ]; then
              echo "Runtime is READY!"
              ENDPOINT_URL=$(aws bedrock-agentcore-control get-agent-runtime --agent-runtime-id "$RUNTIME_ID" --query 'agentRuntimeEndpoint.url' --output text 2>/dev/null || echo "")
              echo "Endpoint URL: $ENDPOINT_URL"
              echo "{\\\"status\\\": \\\"ready\\\", \\\"runtime_id\\\": \\\"$RUNTIME_ID\\\", \\\"runtime_arn\\\": \\\"$RUNTIME_ARN\\\", \\\"endpoint_url\\\": \\\"$ENDPOINT_URL\\\"}" > /tmp/runtime_result.json
              aws s3 cp /tmp/runtime_result.json "s3://$SOURCE_BUCKET/$S3_PREFIX/runtime_result.json"
              exit 0
            elif [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "DELETED" ]; then
              echo "Runtime creation failed with status: $STATUS"
              echo '{"status": "failed", "error": "Runtime status: '"$STATUS"'"}' > /tmp/runtime_result.json
              aws s3 cp /tmp/runtime_result.json "s3://$SOURCE_BUCKET/$S3_PREFIX/runtime_result.json"
              exit 1
            fi
            ATTEMPT=$((ATTEMPT+1))
            sleep 10
          done
          echo "Timeout waiting for Runtime to be READY"
          echo '{"status": "failed", "error": "Timeout waiting for READY status"}' > /tmp/runtime_result.json
          aws s3 cp /tmp/runtime_result.json "s3://$SOURCE_BUCKET/$S3_PREFIX/runtime_result.json"
          exit 1
        else
          echo "RUNTIME_NAME not set, skipping runtime creation"
        fi"""

        # 베이스 이미지 사용 시: QEMU 설정 불필요 (이미 ARM64로 빌드됨)
        if base_image_uri:
            return dedent("""\
                version: 0.2

                phases:
                  pre_build:
                    commands:
                      - echo "Logging in to Amazon ECR..."
                      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
                      - echo "Build started on $(date)"
                      - echo "Image Tag - $IMAGE_TAG"
                      - echo "Using base image - $BASE_IMAGE_URI"
                      - echo "Skipping QEMU setup (base image is already ARM64)"

                      # Buildx 빌더 생성 (QEMU 없이)
                      - docker buildx create --use --name arm64-builder --driver docker-container || true
                      - docker buildx inspect --bootstrap

                  build:
                    commands:
                      - echo "Building ARM64 Docker image with base image..."
                      - docker buildx build --platform linux/arm64 --load -t $ECR_REPOSITORY_URL:$IMAGE_TAG .
                      - echo "Build completed on $(date)"

                  post_build:
                    commands:
                      - echo "Pushing Docker image to ECR..."
                      - docker push $ECR_REPOSITORY_URL:$IMAGE_TAG
                      - echo "Push completed on $(date)"
                      - echo "Image URI - $ECR_REPOSITORY_URL:$IMAGE_TAG"
                """) + runtime_commands
        else:
            # 베이스 이미지 없을 때: QEMU 설정 필요 (처음부터 ARM64 빌드)
            return dedent("""\
                version: 0.2

                phases:
                  pre_build:
                    commands:
                      - echo "Logging in to Amazon ECR..."
                      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
                      - echo "Build started on $(date)"
                      - echo "Image Tag - $IMAGE_TAG"

                      # Docker Buildx 및 QEMU 설정 (ARM64 크로스 빌드)
                      - echo "Setting up Docker Buildx for ARM64..."
                      - docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
                      - docker buildx create --use --name arm64-builder --driver docker-container
                      - docker buildx inspect --bootstrap

                  build:
                    commands:
                      - echo "Building ARM64 Docker image with Buildx..."
                      - docker buildx build --platform linux/arm64 --load -t $ECR_REPOSITORY_URL:$IMAGE_TAG .
                      - echo "Build completed on $(date)"

                  post_build:
                    commands:
                      - echo "Pushing Docker image to ECR..."
                      - docker push $ECR_REPOSITORY_URL:$IMAGE_TAG
                      - echo "Push completed on $(date)"
                      - echo "Image URI - $ECR_REPOSITORY_URL:$IMAGE_TAG"
                """) + runtime_commands

    def _prepare_context(
        self,
        agent_config: dict,
        session_bucket: str = None,
        session_prefix: str = None,
        local_testing: bool = False,
        base_image_uri: str = None
    ) -> dict[str, Any]:
        """템플릿 컨텍스트 준비 (Container 방식)"""
        from app.config import settings

        knowledge_bases = agent_config.get("knowledge_bases", [])
        tools = agent_config.get("tools", [])
        mcp_servers = agent_config.get("mcp_servers", [])

        # KB 설정 정규화
        normalized_kbs = []
        for kb in knowledge_bases:
            if isinstance(kb, str):
                # Legacy: KB ID만 전달된 경우 (현재는 사용하지 않음)
                logger.warning(f"KB passed as string: {kb}. Should be dict with id, name, knowledge_base_id")
                normalized_kbs.append({
                    "id": kb,
                    "name": kb[:8],
                    "knowledge_base_id": kb
                })
            elif isinstance(kb, dict):
                normalized_kbs.append({
                    "id": kb.get("id"),
                    "name": kb.get("name"),
                    "knowledge_base_id": kb.get("knowledge_base_id")
                })

        # MCP 서버 설정 정규화
        normalized_mcp = []
        for server in mcp_servers:
            if isinstance(server, dict):
                normalized_mcp.append({
                    "name": server.get("name", "mcp_server"),
                    "transport": server.get("transport", "http"),
                    "url": server.get("url", ""),
                    "headers": server.get("headers"),
                    "command": server.get("command"),
                    "args": server.get("args", []),
                    "auth_type": server.get("auth_type", "no_auth"),
                    "aws_region": server.get("aws_region", settings.AWS_REGION)
                })

        # 이미지 이름 생성 (agent_id 기반)
        agent_id = agent_config.get("agent_id", "agent")
        agent_name = agent_config.get("agent_name", "Playground Agent")
        version = agent_config.get("version", "1.0.0")

        # 이미지 이름: 알파벳, 숫자, 하이픈만 허용
        safe_name = "".join(c if c.isalnum() or c == "-" else "-" for c in agent_name.lower())
        image_name = f"agentcore-{safe_name}"
        image_tag = version.replace(".", "-")

        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "agent_version": version,
            "model_id": agent_config.get("model_id", "anthropic.claude-3-sonnet-20240229-v1:0"),
            "system_prompt": agent_config.get("system_prompt", "You are a helpful assistant."),
            "temperature": agent_config.get("temperature", 0.7),
            "max_tokens": agent_config.get("max_tokens", 2000),
            "knowledge_bases": normalized_kbs,
            "tools": tools,
            "has_tools": bool(tools),
            "mcp_servers": normalized_mcp,
            "has_session_manager": bool(session_bucket),
            "session_bucket": session_bucket or "",
            "session_prefix": session_prefix or "",
            "generated_at": int(datetime.utcnow().timestamp()),
            "local_testing": local_testing,
            # Container deployment 관련
            "image_name": image_name,
            "image_tag": image_tag,
            "python_version": "3.13",
            "enable_otel": True,
            "additional_files": [],
            "environment_variables": {},
            "base_image_uri": base_image_uri or "",
            "aws_region": settings.AWS_REGION
        }

    def generate_s3_prefix(
        self,
        user_id: str,
        agent_id: str,
        version: str,
        deployment_id: str
    ) -> str:
        """S3 prefix 생성"""
        return f"agents/{user_id}/{agent_id}/{version}/{deployment_id}"
