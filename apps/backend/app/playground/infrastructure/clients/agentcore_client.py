"""AgentCore Runtime Client - AgentCore Runtime API 클라이언트

Container 배포 방식 (ECR)을 사용합니다.
AWS CodeBuild를 사용하여 Docker 이미지를 빌드합니다. (로컬 Docker 미지원)
"""
import json
import logging
import asyncio
from typing import AsyncIterator, Optional
from datetime import datetime, timedelta
import tempfile
from pathlib import Path

import boto3
from botocore.config import Config

from app.config import settings

logger = logging.getLogger(__name__)


class AgentCoreClient:
    """AgentCore Runtime API 클라이언트

    Container 배포 방식 (ECR)을 사용합니다.
    AWS CodeBuild를 통해 Docker 이미지를 빌드합니다.

    Features:
    - CodeBuild를 통한 Docker 이미지 빌드
    - ECR에 이미지 푸시
    - AgentCore Runtime 생성/조회/삭제
    - Runtime 호출 (스트리밍)
    """

    def __init__(
        self,
        region: str = None,
        role_arn: str = None,
        ecr_repository: str = None,
        codebuild_project: str = None,
        source_bucket: str = None
    ):
        self.region = region or settings.AWS_REGION
        self.role_arn = role_arn or settings.PLAYGROUND_RUNTIME_ROLE_ARN
        self.ecr_repository = ecr_repository or settings.PLAYGROUND_ECR_REPOSITORY
        self.codebuild_project = codebuild_project or settings.CODEBUILD_PROJECT_NAME
        self.source_bucket = source_bucket or settings.AGENT_BUILD_SOURCE_BUCKET
        self.aws_profile = settings.AWS_PROFILE

        # CodeBuild 설정 검증 (로컬 개발 모드에서는 경고만 출력)
        if not self.codebuild_project or not self.source_bucket:
            if settings.ENVIRONMENT == "dev" or settings.ENVIRONMENT == "development":
                logger.warning(
                    "⚠️ CodeBuild configuration not set. "
                    "Playground deployment features will be unavailable. "
                    "Set CODEBUILD_PROJECT_NAME and AGENT_BUILD_SOURCE_BUCKET for full functionality."
                )
            else:
                raise ValueError(
                    "CodeBuild configuration required. "
                    "Set CODEBUILD_PROJECT_NAME and AGENT_BUILD_SOURCE_BUCKET environment variables."
                )

        self._config = Config(
            region_name=self.region,
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )

        # Lazy initialization - clients created on first access
        self._s3_client = None
        self._codebuild_client = None
        self._ecr_client = None
        self._sts_client = None
        self._agentcore_control = None
        self._agentcore = None

        # AWS Account ID (lazy)
        self._account_id = None

    @property
    def s3_client(self):
        """S3 클라이언트 (lazy initialization)"""
        if self._s3_client is None:
            if self.aws_profile:
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.region)
                self._s3_client = session.client('s3', config=self._config)
                logger.info(f"🔑 [S3] Using AWS Profile: {self.aws_profile}")
            else:
                self._s3_client = boto3.client('s3', config=self._config)
                logger.info("🔑 [S3] Using default AWS credentials (no profile)")

            # Log caller identity
            try:
                sts = session.client('sts') if self.aws_profile else boto3.client('sts')
                identity = sts.get_caller_identity()
                logger.info(f"🔑 [S3] Caller Identity: {identity['Arn']}")
            except Exception as e:
                logger.warning(f"⚠️ [S3] Failed to get caller identity: {e}")
        return self._s3_client

    @property
    def codebuild_client(self):
        """CodeBuild 클라이언트 (lazy initialization)"""
        if self._codebuild_client is None:
            if self.aws_profile:
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.region)
                self._codebuild_client = session.client('codebuild', config=self._config)
                logger.info(f"🔑 [CodeBuild] Using AWS Profile: {self.aws_profile}")
            else:
                self._codebuild_client = boto3.client('codebuild', config=self._config)
                logger.info("🔑 [CodeBuild] Using default AWS credentials (no profile)")

            # Log caller identity
            try:
                sts = session.client('sts') if self.aws_profile else boto3.client('sts')
                identity = sts.get_caller_identity()
                logger.info(f"🔑 [CodeBuild] Caller Identity: {identity['Arn']}")
            except Exception as e:
                logger.warning(f"⚠️ [CodeBuild] Failed to get caller identity: {e}")
        return self._codebuild_client

    @property
    def ecr_client(self):
        """ECR 클라이언트 (lazy initialization)"""
        if self._ecr_client is None:
            if self.aws_profile:
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.region)
                self._ecr_client = session.client('ecr', config=self._config)
                logger.info(f"🔑 [ECR] Using AWS Profile: {self.aws_profile}")
            else:
                self._ecr_client = boto3.client('ecr', config=self._config)
                logger.info("🔑 [ECR] Using default AWS credentials (no profile)")

            # Log caller identity
            try:
                sts = session.client('sts') if self.aws_profile else boto3.client('sts')
                identity = sts.get_caller_identity()
                logger.info(f"🔑 [ECR] Caller Identity: {identity['Arn']}")
            except Exception as e:
                logger.warning(f"⚠️ [ECR] Failed to get caller identity: {e}")
        return self._ecr_client

    @property
    def sts_client(self):
        """STS 클라이언트 (lazy initialization)"""
        if self._sts_client is None:
            if self.aws_profile:
                session = boto3.Session(profile_name=self.aws_profile, region_name=self.region)
                self._sts_client = session.client('sts', config=self._config)
                logger.info(f"🔑 [STS] Using AWS Profile: {self.aws_profile}")
            else:
                self._sts_client = boto3.client('sts', config=self._config)
                logger.info("🔑 [STS] Using default AWS credentials (no profile)")

            # Log caller identity
            try:
                identity = self._sts_client.get_caller_identity()
                logger.info(f"🔑 [STS] Caller Identity: {identity['Arn']}")
            except Exception as e:
                logger.warning(f"⚠️ [STS] Failed to get caller identity: {e}")
        return self._sts_client

    @property
    def account_id(self) -> str:
        """AWS Account ID"""
        if self._account_id is None:
            self._account_id = self.sts_client.get_caller_identity()['Account']
        return self._account_id

    @property
    def agentcore_control(self):
        """AgentCore Control Plane 클라이언트 (lazy initialization)"""
        if self._agentcore_control is None:
            try:
                if self.aws_profile:
                    session = boto3.Session(profile_name=self.aws_profile, region_name=self.region)
                    self._agentcore_control = session.client(
                        'bedrock-agentcore-control',
                        config=self._config
                    )
                    logger.info(f"🔑 [AgentCore Control] Using AWS Profile: {self.aws_profile}")
                else:
                    self._agentcore_control = boto3.client(
                        'bedrock-agentcore-control',
                        config=self._config
                    )
                    logger.info("🔑 [AgentCore Control] Using default AWS credentials (no profile)")

                # Log caller identity
                try:
                    sts = session.client('sts') if self.aws_profile else boto3.client('sts')
                    identity = sts.get_caller_identity()
                    logger.info(f"🔑 [AgentCore Control] Caller Identity: {identity['Arn']}")
                except Exception as e:
                    logger.warning(f"⚠️ [AgentCore Control] Failed to get caller identity: {e}")
            except Exception as e:
                logger.warning(f"Failed to create agentcore-control client: {e}")
                raise RuntimeError(
                    "AgentCore service not available. "
                    "Please ensure you have the latest AWS SDK with AgentCore support."
                )
        return self._agentcore_control

    @property
    def agentcore(self):
        """AgentCore Data Plane 클라이언트 (lazy initialization)"""
        if self._agentcore is None:
            try:
                if self.aws_profile:
                    session = boto3.Session(profile_name=self.aws_profile, region_name=self.region)
                    self._agentcore = session.client(
                        'bedrock-agentcore',
                        config=self._config
                    )
                    logger.info(f"🔑 [AgentCore Data] Using AWS Profile: {self.aws_profile}")
                else:
                    self._agentcore = boto3.client(
                        'bedrock-agentcore',
                        config=self._config
                    )
                    logger.info("🔑 [AgentCore Data] Using default AWS credentials (no profile)")

                # Log caller identity
                try:
                    sts = session.client('sts') if self.aws_profile else boto3.client('sts')
                    identity = sts.get_caller_identity()
                    logger.info(f"🔑 [AgentCore Data] Caller Identity: {identity['Arn']}")
                except Exception as e:
                    logger.warning(f"⚠️ [AgentCore Data] Failed to get caller identity: {e}")
            except Exception as e:
                logger.warning(f"Failed to create agentcore client: {e}")
                raise RuntimeError(
                    "AgentCore service not available. "
                    "Please ensure you have the latest AWS SDK with AgentCore support."
                )
        return self._agentcore

    async def build_and_push_container(
        self,
        files: dict[str, str],
        image_tag: str,
        user_id: str,
        agent_id: str,
        version: str,
        deployment_id: str,
        repository_name: str = None,
        force_rebuild: bool = False,
        runtime_name: str = None
    ) -> tuple[str, Optional[str], Optional[str]]:
        """Docker 이미지 빌드 및 ECR 푸시 (Runtime 생성 포함 가능)

        Args:
            files: {filename: content} - Dockerfile 포함
            image_tag: 이미지 태그 (예: "v1.0.0", "latest")
            user_id: 사용자 ID (S3 경로 구분용)
            agent_id: Agent ID (S3 경로 구분용)
            version: Agent 버전 (S3 경로 구분용)
            deployment_id: Deployment ID (S3 경로 구분용)
            repository_name: ECR 리포지토리 이름 (없으면 기본값 사용)
            force_rebuild: True면 기존 이미지 무시하고 강제 재빌드
            runtime_name: Runtime 이름 (지정하면 CodeBuild에서 Runtime까지 생성)

        Returns:
            (ECR 이미지 URI, CodeBuild ID, S3 prefix) 튜플
            - 이미지가 재사용된 경우 build_id와 s3_prefix는 None
        """
        repo_name = repository_name or self.ecr_repository
        if not repo_name:
            raise ValueError(
                "ECR repository not configured. "
                "Set PLAYGROUND_ECR_REPOSITORY environment variable."
            )

        # ECR 리포지토리 생성 (없으면)
        await self._ensure_ecr_repository(repo_name)

        # ECR 이미지 URI
        ecr_uri = f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/{repo_name}:{image_tag}"

        # 기존 이미지 확인 (캐싱) - force_rebuild가 아닌 경우만
        if not force_rebuild:
            existing_image = await self.check_image_exists(image_tag, repo_name)
            if existing_image:
                logger.info(f"Found existing image: {existing_image}")
                return (existing_image, None, None)  # build_id와 s3_prefix는 None

        # CodeBuild로 빌드 (runtime_name이 있으면 Runtime 생성까지)
        logger.info(f"Using CodeBuild for Docker build: {image_tag}" + (f" with Runtime: {runtime_name}" if runtime_name else ""))
        return await self._build_with_codebuild(
            files, image_tag, repo_name, ecr_uri,
            user_id, agent_id, version, deployment_id,
            runtime_name=runtime_name
        )

    async def _build_with_codebuild(
        self,
        files: dict[str, str],
        image_tag: str,
        repo_name: str,
        ecr_uri: str,
        user_id: str,
        agent_id: str,
        version: str,
        deployment_id: str,
        runtime_name: str = None
    ) -> tuple[str, str, str]:
        """CodeBuild로 빌드 (Runtime 생성 포함)

        S3 경로: agent-builds/{user_id}/{agent_id}/{version}/{deployment_id}/

        Args:
            runtime_name: Runtime 이름 (지정하면 CodeBuild에서 Runtime까지 생성)

        Returns:
            (ECR URI, build_id, s3_prefix) 튜플
        """
        if not self.codebuild_project:
            raise ValueError(
                "CodeBuild project not configured. "
                "Set CODEBUILD_PROJECT_NAME environment variable."
            )

        if not self.source_bucket:
            raise ValueError(
                "S3 source bucket not configured. "
                "Set AGENT_BUILD_SOURCE_BUCKET environment variable."
            )

        loop = asyncio.get_event_loop()

        # 1. 임시 디렉토리에 파일 작성
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 파일 작성
            for filename, content in files.items():
                file_path = temp_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                logger.debug(f"Written: {filename}")

            # 2. S3에 개별 파일 업로드 (사용자별 구분)
            s3_prefix = f"agent-builds/{user_id}/{agent_id}/{version}/{deployment_id}/"
            logger.info(f"Uploading {len(files)} files to S3: s3://{self.source_bucket}/{s3_prefix}")

            for filename, content in files.items():
                s3_key = f"{s3_prefix}{filename}"
                file_path = temp_path / filename

                await loop.run_in_executor(
                    None,
                    lambda fp=str(file_path), key=s3_key: self.s3_client.upload_file(
                        fp,
                        self.source_bucket,
                        key
                    )
                )
                logger.debug(f"Uploaded: {filename}")

            logger.info(f"All files uploaded to S3")

        # 3. CodeBuild 트리거
        logger.info(f"Starting CodeBuild project: {self.codebuild_project}")

        # buildspec.yml 내용 (동적 생성)
        buildspec_content = files.get('buildspec.yml', '')

        # 환경변수 설정
        env_vars = [
            {'name': 'IMAGE_TAG', 'value': image_tag, 'type': 'PLAINTEXT'},
            {'name': 'ECR_REPOSITORY_URL', 'value': f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/{repo_name}", 'type': 'PLAINTEXT'},
            {'name': 'SOURCE_BUCKET', 'value': self.source_bucket, 'type': 'PLAINTEXT'},
            {'name': 'S3_PREFIX', 'value': s3_prefix.rstrip('/'), 'type': 'PLAINTEXT'},
        ]

        # Runtime 생성 옵션이 있으면 추가 환경변수 설정
        if runtime_name:
            env_vars.extend([
                {'name': 'RUNTIME_NAME', 'value': runtime_name, 'type': 'PLAINTEXT'},
                {'name': 'AGENTCORE_ROLE_ARN', 'value': self.role_arn, 'type': 'PLAINTEXT'},
            ])
            logger.info(f"Runtime creation enabled: {runtime_name}")

        build_response = await loop.run_in_executor(
            None,
            lambda: self.codebuild_client.start_build(
                projectName=self.codebuild_project,
                sourceTypeOverride='S3',
                sourceLocationOverride=f"{self.source_bucket}/{s3_prefix}",
                buildspecOverride=buildspec_content,
                environmentVariablesOverride=env_vars
            )
        )

        build_id = build_response['build']['id']
        logger.info(f"CodeBuild started: {build_id}")

        # CodeBuild 시작 직후 즉시 반환 (UI가 building 상태로 전환할 수 있도록)
        # 빌드 완료는 wait_for_build_completion()으로 별도 대기
        return (ecr_uri, build_id, s3_prefix)

    async def wait_for_build_completion(
        self,
        build_id: str,
        s3_prefix: str,
        max_wait_time: int = 1200,
        poll_interval: int = 10
    ) -> None:
        """CodeBuild 완료 대기

        Args:
            build_id: CodeBuild 빌드 ID
            s3_prefix: S3 소스 경로 (참조용 - cleanup은 별도 호출 필요)
            max_wait_time: 최대 대기 시간 (초)
            poll_interval: 폴링 간격 (초)

        Raises:
            RuntimeError: 빌드 실패 시
            TimeoutError: 타임아웃 시

        Note:
            S3 소스 파일 정리는 이 함수에서 하지 않습니다.
            runtime_result.json을 읽은 후 cleanup_s3_source()를 호출하세요.
        """
        loop = asyncio.get_event_loop()
        start_time = datetime.utcnow()

        while (datetime.utcnow() - start_time).total_seconds() < max_wait_time:
            build_info = await loop.run_in_executor(
                None,
                lambda: self.codebuild_client.batch_get_builds(ids=[build_id])
            )

            build = build_info['builds'][0]
            build_status = build['buildStatus']

            logger.debug(f"CodeBuild status: {build_status}")

            if build_status == 'SUCCEEDED':
                logger.info(f"CodeBuild completed successfully: {build_id}")
                # S3 정리는 여기서 하지 않음 - runtime_result.json을 먼저 읽어야 함
                return
            elif build_status in ['FAILED', 'FAULT', 'TIMED_OUT', 'STOPPED']:
                error_msg = f"CodeBuild failed with status: {build_status}"
                if 'phases' in build:
                    for phase in build['phases']:
                        if phase.get('phaseStatus') == 'FAILED':
                            error_msg += f"\nFailed phase: {phase['phaseType']}"
                            if 'contexts' in phase:
                                for context in phase['contexts']:
                                    error_msg += f"\n  {context.get('message', '')}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"CodeBuild did not complete within {max_wait_time} seconds")

    async def _ensure_ecr_repository(self, repository_name: str) -> None:
        """ECR 리포지토리가 없으면 생성"""
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(
                None,
                lambda: self.ecr_client.describe_repositories(
                    repositoryNames=[repository_name]
                )
            )
            logger.debug(f"ECR repository exists: {repository_name}")
        except self.ecr_client.exceptions.RepositoryNotFoundException:
            logger.info(f"Creating ECR repository: {repository_name}")
            await loop.run_in_executor(
                None,
                lambda: self.ecr_client.create_repository(
                    repositoryName=repository_name,
                    imageScanningConfiguration={'scanOnPush': True},
                    imageTagMutability='MUTABLE'
                )
            )
            logger.info(f"ECR repository created: {repository_name}")

    async def check_image_exists(
        self,
        image_tag: str,
        repository_name: str = None
    ) -> Optional[str]:
        """ECR에 이미지가 존재하는지 확인

        Args:
            image_tag: 이미지 태그
            repository_name: ECR 리포지토리 이름

        Returns:
            이미지 URI (존재하면) 또는 None
        """
        repo_name = repository_name or self.ecr_repository
        if not repo_name:
            return None

        loop = asyncio.get_event_loop()

        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.ecr_client.describe_images(
                    repositoryName=repo_name,
                    imageIds=[{"imageTag": image_tag}]
                )
            )

            if response.get("imageDetails"):
                ecr_uri = f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/{repo_name}:{image_tag}"
                logger.info(f"Found existing ECR image: {ecr_uri}")
                return ecr_uri

        except self.ecr_client.exceptions.ImageNotFoundException:
            logger.debug(f"Image not found: {repo_name}:{image_tag}")
        except Exception as e:
            logger.debug(f"Error checking image: {e}")

        return None

    def generate_image_tag(self, agent_id: str, version: str) -> str:
        """Agent ID와 Version으로 일관된 이미지 태그 생성

        Args:
            agent_id: Agent ID
            version: Agent version (예: "1.4.0" 또는 "v1.4.0")

        Returns:
            이미지 태그 (예: "b80431b9-v1-4-0")
        """
        # agent_id 앞 8자리 + version (점을 대시로 변환)
        agent_short = agent_id[:8]
        # version에서 v 접두사 제거 후 통일된 형식으로 생성
        version_clean = version.lstrip("v")
        version_tag = version_clean.replace(".", "-")
        return f"{agent_short}-v{version_tag}"

    async def create_runtime_with_container(
        self,
        name: str,
        container_uri: str,
        description: str = None
    ) -> dict:
        """컨테이너 기반 AgentCore Runtime 생성

        Args:
            name: Runtime 이름
            container_uri: ECR 이미지 URI
            description: 설명

        Returns:
            {runtime_id, runtime_arn, status}
        """
        if not self.role_arn:
            raise ValueError(
                "IAM Role ARN not configured. "
                "Set AGENTCORE_ROLE_ARN or PLAYGROUND_RUNTIME_ROLE_ARN environment variable."
            )

        loop = asyncio.get_event_loop()

        try:
            logger.info(f"Creating container-based runtime: {name}")
            logger.info(f"Container URI: {container_uri}")

            response = await loop.run_in_executor(
                None,
                lambda: self.agentcore_control.create_agent_runtime(
                    agentRuntimeName=name,
                    description=description or f"Playground Runtime (Container): {name}",
                    agentRuntimeArtifact={
                        'containerConfiguration': {
                            'containerUri': container_uri
                        }
                    },
                    roleArn=self.role_arn,
                    networkConfiguration={
                        'networkMode': 'PUBLIC'
                    }
                )
            )

            logger.info(f"Runtime created: {response.get('agentRuntimeId')}")

            return {
                "runtime_id": response.get("agentRuntimeId"),
                "runtime_arn": response.get("agentRuntimeArn"),
                "status": response.get("status"),
                "deployment_type": "container"
            }

        except Exception as e:
            import traceback
            logger.error(f"Failed to create container runtime: {e}")
            logger.error(f"Error details: {traceback.format_exc()}")
            logger.error(f"Request parameters - Name: {name}, Role: {self.role_arn}, Container: {container_uri}")
            raise

    async def update_runtime_container(
        self,
        runtime_id: str,
        container_uri: str
    ) -> dict:
        """기존 Runtime의 컨테이너 이미지 업데이트

        Args:
            runtime_id: Runtime ID
            container_uri: 새 ECR 이미지 URI

        Returns:
            {runtime_id, runtime_arn, status}
        """
        loop = asyncio.get_event_loop()

        try:
            logger.info(f"Updating runtime {runtime_id} with new container: {container_uri}")

            response = await loop.run_in_executor(
                None,
                lambda: self.agentcore_control.update_agent_runtime(
                    agentRuntimeId=runtime_id,
                    agentRuntimeArtifact={
                        'containerConfiguration': {
                            'containerUri': container_uri
                        }
                    },
                    networkConfiguration={
                        'networkMode': 'PUBLIC'
                    },
                    roleArn=self.role_arn
                )
            )

            return {
                "runtime_id": response.get("agentRuntimeId"),
                "runtime_arn": response.get("agentRuntimeArn"),
                "status": response.get("status")
            }

        except Exception as e:
            logger.error(f"Failed to update runtime container: {e}")
            raise

    async def get_runtime(self, runtime_id: str) -> dict:
        """Runtime 상태 조회

        Returns:
            {runtime_id, runtime_arn, status, endpoint_url}
        """
        loop = asyncio.get_event_loop()

        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.agentcore_control.get_agent_runtime(
                    agentRuntimeId=runtime_id
                )
            )

            return {
                "runtime_id": response.get("agentRuntimeId"),
                "runtime_arn": response.get("agentRuntimeArn"),
                "status": response.get("status"),
                "endpoint_url": response.get("agentRuntimeEndpoint", {}).get("url")
            }

        except Exception as e:
            logger.error(f"Failed to get runtime {runtime_id}: {e}")
            raise

    async def wait_for_ready(
        self,
        runtime_id: str,
        max_wait: int = 300,
        poll_interval: int = 5
    ) -> dict:
        """Runtime이 Ready 상태가 될 때까지 대기

        Args:
            runtime_id: Runtime ID
            max_wait: 최대 대기 시간 (초)
            poll_interval: 폴링 간격 (초)

        Returns:
            Runtime 정보 (Ready 상태)

        Raises:
            TimeoutError: 시간 초과
            RuntimeError: 생성 실패
        """
        start_time = datetime.utcnow()
        timeout_at = start_time + timedelta(seconds=max_wait)

        while datetime.utcnow() < timeout_at:
            runtime = await self.get_runtime(runtime_id)
            status = runtime.get("status")

            if status == "READY":
                logger.info(f"Runtime {runtime_id} is ready")
                return runtime
            elif status in ["FAILED", "DELETED"]:
                raise RuntimeError(f"Runtime creation failed with status: {status}")

            logger.debug(f"Runtime {runtime_id} status: {status}, waiting...")
            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Runtime {runtime_id} did not become ready within {max_wait} seconds")

    async def invoke(
        self,
        runtime_arn: str,
        payload: dict,
        session_id: str = None
    ) -> AsyncIterator[dict]:
        """Runtime 호출 (스트리밍)"""
        loop = asyncio.get_event_loop()

        try:
            # 요청 파라미터
            invoke_params = {
                "agentRuntimeArn": runtime_arn,
                "payload": json.dumps(payload).encode('utf-8')
            }

            if session_id:
                invoke_params["runtimeSessionId"] = session_id

            # 동기 호출을 비동기로 래핑
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: self.agentcore.invoke_agent_runtime(**invoke_params)
                )
            except Exception as invoke_error:
                logger.error(f"Runtime invoke failed: {invoke_error}")
                yield {"type": "error", "content": f"Runtime 호출 실패: {str(invoke_error)}"}
                return

            # 스트리밍 응답 처리
            event_stream = response.get("response")

            if event_stream and hasattr(event_stream, 'iter_lines'):
                # StreamingBody with iter_lines - 실시간 줄 단위 읽기
                for line in event_stream.iter_lines():
                    if isinstance(line, bytes):
                        line = line.decode('utf-8')

                    line = line.strip()
                    if not line or not line.startswith('data: '):
                        continue

                    raw_text = line[6:]  # "data: " 제거
                    if not raw_text:
                        continue

                    try:
                        data = json.loads(raw_text)

                        # 이중 JSON 인코딩 처리 (string이 반환되면 다시 파싱)
                        if isinstance(data, str):
                            data = json.loads(data)

                        parsed = self._parse_stream_event(data)

                        if parsed.get("type") != "skip":
                            yield parsed
                    except json.JSONDecodeError:
                        pass

            elif event_stream and hasattr(event_stream, 'read'):
                # StreamingBody without iter_lines - 청크 단위로 읽기
                buffer = ""
                chunk_size = 1024  # 1KB씩 읽기

                while True:
                    chunk = event_stream.read(chunk_size)
                    if not chunk:
                        break

                    if isinstance(chunk, bytes):
                        chunk = chunk.decode('utf-8')

                    buffer += chunk
                    lines = buffer.split('\n')
                    buffer = lines.pop()  # 마지막 불완전한 줄은 버퍼에 보관

                    for line in lines:
                        line = line.strip()
                        if not line or not line.startswith('data: '):
                            continue

                        raw_text = line[6:]
                        if not raw_text:
                            continue

                        try:
                            data = json.loads(raw_text)
                            if isinstance(data, str):
                                data = json.loads(data)

                            parsed = self._parse_stream_event(data)
                            if parsed.get("type") != "skip":
                                yield parsed
                        except json.JSONDecodeError:
                            pass

            elif hasattr(event_stream, '__iter__'):
                # Event stream
                for event in event_stream:
                    if isinstance(event, dict) and "chunk" in event:
                        chunk_data = event["chunk"].get("bytes", b"")
                        if chunk_data:
                            raw_text = chunk_data.decode('utf-8')

                            # Python repr 형태 메시지 필터링 (큰따옴표로 시작하는 경우)
                            if raw_text.startswith("'") or raw_text.startswith('"'):
                                continue

                            try:
                                data = json.loads(raw_text)
                                parsed = self._parse_stream_event(data)

                                # skip 타입 이벤트는 전송하지 않음
                                if parsed.get("type") != "skip":
                                    yield parsed
                            except json.JSONDecodeError:
                                pass
            else:
                logger.error("Unknown response format")
                yield {"type": "error", "content": "Unknown response format"}

            yield {"type": "done", "session_id": session_id}

        except Exception as e:
            logger.error(f"Runtime invoke exception: {e}", exc_info=True)
            yield {"type": "error", "content": f"예상치 못한 오류: {str(e)}"}

    async def delete_runtime(self, runtime_id: str) -> None:
        """Runtime 삭제"""
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(
                None,
                lambda: self.agentcore_control.delete_agent_runtime(
                    agentRuntimeId=runtime_id
                )
            )
            logger.info(f"Deleted runtime {runtime_id}")

        except self.agentcore_control.exceptions.ResourceNotFoundException:
            logger.warning(f"Runtime {runtime_id} already deleted or not found")
        except Exception as e:
            logger.error(f"Failed to delete runtime {runtime_id}: {e}")
            raise

    def _is_tool_call_xml(self, text: str) -> bool:
        """Agent 내부 도구 호출 XML 패턴인지 확인

        필터링 대상 패턴:
        - <function_calls>, </function_calls>
        - <invoke name="...">, </invoke>
        - <parameter name="...">, </parameter>
        - <function_result>, </function_result>
        """
        if not text:
            return False

        stripped = text.strip()

        # 시작 태그로 시작하는 경우
        if stripped.startswith(("<function_calls>", "</function", "<invoke", "</invoke>",
                                "<parameter", "</parameter>", "<function_result", "</function_result")):
            return True

        # 텍스트 내에 XML 태그 포함
        xml_patterns = [
            "<function_calls>", "</function_calls>",
            "<invoke name=", "</invoke>",
            "<parameter name=", "</parameter>",
            "<function_result>", "</function_result>",
        ]

        return any(pattern in text for pattern in xml_patterns)

    def _parse_stream_event(self, data: dict) -> dict:
        """스트리밍 이벤트 파싱

        Strands Agent 형식 (stream_async):
        - {"data": "text..."}: 텍스트 스트리밍
        - {"current_tool_use": {"name": "tool_name", ...}}: 도구 사용 시작
        - {"reasoningContent": {"text": "..."}}: thinking/reasoning
        - {"complete": true}: 완료

        Bedrock ConversationAPI 형식 (하위 호환):
        - {"event": {"contentBlockDelta": {"delta": {"text": "..."}}}}
        - {"event": {"contentBlockStart": {"start": {"toolUse": {"name": "..."}}}}}
        """
        # 1. Strands Agent 형식 - data 필드 (텍스트 스트리밍)
        if "data" in data:
            text = data["data"]
            if text and isinstance(text, str):
                # Agent 내부 도구 호출 XML 패턴 필터링
                if self._is_tool_call_xml(text):
                    return {"type": "skip"}
                return {"type": "text", "content": text}

        # 2. Strands Agent 형식 - current_tool_use (도구 사용)
        if "current_tool_use" in data:
            tool_info = data["current_tool_use"]
            if isinstance(tool_info, dict):
                tool_name = tool_info.get("name", "")
                tool_id = tool_info.get("toolUseId", "")
                if tool_name:
                    return {"type": "tool_use", "tool_name": tool_name, "tool_id": tool_id}

        # 3. Strands Agent 형식 - reasoningContent (thinking)
        if "reasoningContent" in data:
            reasoning = data["reasoningContent"]
            if isinstance(reasoning, dict):
                text = reasoning.get("text", "")
                if text:
                    return {"type": "thinking", "content": text}

        # 4. Bedrock ConversationAPI 형식
        if "event" in data:
            event = data["event"]

            # contentBlockDelta - 텍스트 스트리밍
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                text = delta.get("text", "")
                if text:
                    return {"type": "text", "content": text}
                # reasoning delta
                reasoning = delta.get("reasoningContent", {})
                if reasoning:
                    return {"type": "thinking", "content": reasoning.get("text", "")}

            # contentBlockStart - 도구 사용 시작
            if "contentBlockStart" in event:
                start = event["contentBlockStart"].get("start", {})
                if "toolUse" in start:
                    tool_name = start["toolUse"].get("name", "")
                    tool_id = start["toolUse"].get("toolUseId", "")
                    return {"type": "tool_use", "tool_name": tool_name, "tool_id": tool_id}

            # contentBlockStop - 블록 종료 (tool result)
            if "contentBlockStop" in event:
                return {"type": "tool_result"}

            # messageStop - 메시지 종료
            if "messageStop" in event:
                stop_reason = event["messageStop"].get("stopReason", "end_turn")
                return {"type": "done", "stop_reason": stop_reason}

            # metadata - 토큰 사용량 등
            if "metadata" in event:
                metadata = event["metadata"]
                return {
                    "type": "done",
                    "metadata": {
                        "input_tokens": metadata.get("usage", {}).get("inputTokens", 0),
                        "output_tokens": metadata.get("usage", {}).get("outputTokens", 0)
                    }
                }

        # 5. text 필드 (하위 호환)
        if "text" in data and isinstance(data.get("text"), str):
            text = data["text"]
            if text:
                if self._is_tool_call_xml(text):
                    return {"type": "skip"}
                return {"type": "text", "content": text}

        # 6. Delta 안에 text가 있는 경우
        if "delta" in data:
            delta = data["delta"]
            if isinstance(delta, dict):
                text = delta.get("text", "")
                if text:
                    if self._is_tool_call_xml(text):
                        return {"type": "skip"}
                    return {"type": "text", "content": text}
                # toolUse in delta
                if "toolUse" in delta:
                    tool_name = delta["toolUse"].get("name", "")
                    return {"type": "tool_use", "tool_name": tool_name}

        # 7. content 필드 (일반적인 형식)
        if "content" in data and data["content"]:
            content = data["content"]
            if isinstance(content, str) and self._is_tool_call_xml(content):
                return {"type": "skip"}
            return {"type": "text", "content": content}

        # 8. Stop reason (완료)
        if "stop_reason" in data:
            return {"type": "done", "stop_reason": data["stop_reason"]}

        # 9. complete 이벤트 (Strands Agent)
        if data.get("complete"):
            return {"type": "done"}

        # 10. 명시적 type 필드
        event_type = data.get("type")
        if event_type == "done":
            return data
        if event_type == "error":
            return {"type": "error", "content": data.get("content", data.get("message", "Unknown error"))}

        # 11. 무시 가능한 이벤트 (messageStart, init_event_loop 등)
        if any(key in data for key in ["init_event_loop", "start", "start_event_loop", "message"]):
            return {"type": "skip"}

        # 12. 기타 이벤트 - 디버그 로그만 출력
        logger.debug(f"Unhandled event: {list(data.keys())}")
        return {"type": "skip"}

    async def get_build_phases(self, build_id: str) -> Optional[dict]:
        """CodeBuild의 현재 phase 정보 조회

        Args:
            build_id: CodeBuild 빌드 ID

        Returns:
            {
                'status': 'IN_PROGRESS' | 'SUCCEEDED' | 'FAILED' | ...,
                'current_phase': 'PROVISIONING' | 'BUILD' | ...,
                'phase_message': '한글 메시지',
                'phases': [...]  # 전체 phase 목록
            }
        """
        loop = asyncio.get_event_loop()

        try:
            build_info = await loop.run_in_executor(
                None,
                lambda: self.codebuild_client.batch_get_builds(ids=[build_id])
            )

            if not build_info.get('builds'):
                return None

            build = build_info['builds'][0]
            build_status = build['buildStatus']
            phases = build.get('phases', [])

            # 현재 실행 중인 phase 찾기
            current_phase = None
            for phase in phases:
                if phase.get('phaseStatus') == 'IN_PROGRESS':
                    current_phase = phase['phaseType']
                    break

            # 현재 phase가 없으면 마지막 완료된 phase 사용
            if not current_phase and phases:
                current_phase = phases[-1]['phaseType']

            # Phase별 한글 메시지 매핑
            phase_messages = {
                'SUBMITTED': '빌드 요청 접수',
                'QUEUED': '빌드 대기 중',
                'PROVISIONING': '빌드 환경 준비 중',
                'DOWNLOAD_SOURCE': '소스 코드 다운로드 중',
                'INSTALL': '의존성 설치 중',
                'PRE_BUILD': '빌드 준비 중',
                'BUILD': 'Docker 이미지 빌드 중',
                'POST_BUILD': '빌드 후처리 중',
                'UPLOAD_ARTIFACTS': 'ECR에 이미지 업로드 중',
                'FINALIZING': '빌드 완료 처리 중'
            }

            phase_message = phase_messages.get(current_phase, '빌드 진행 중')

            return {
                'status': build_status,
                'current_phase': current_phase,
                'phase_message': phase_message,
                'phases': phases
            }

        except Exception as e:
            logger.error(f"Failed to get build phases for {build_id}: {e}")
            return None

    async def get_runtime_result_from_s3(self, s3_prefix: str) -> Optional[dict]:
        """S3에서 Runtime 생성 결과 조회

        CodeBuild에서 Runtime 생성 후 저장한 결과 파일을 읽습니다.

        Args:
            s3_prefix: S3 prefix (예: "agent-builds/{user_id}/{agent_id}/{version}/{deployment_id}")

        Returns:
            {
                'status': 'ready' | 'failed',
                'runtime_id': '...',
                'runtime_arn': '...',
                'endpoint_url': '...',
                'error': '...'  # 실패 시
            }
            또는 파일이 없으면 None
        """
        loop = asyncio.get_event_loop()
        s3_key = f"{s3_prefix.rstrip('/')}/runtime_result.json"

        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.s3_client.get_object(
                    Bucket=self.source_bucket,
                    Key=s3_key
                )
            )

            content = response['Body'].read().decode('utf-8')
            result = json.loads(content)
            logger.info(f"Runtime result from S3: {result}")
            return result

        except self.s3_client.exceptions.NoSuchKey:
            logger.debug(f"Runtime result not found at: {s3_key}")
            return None
        except Exception as e:
            logger.error(f"Failed to read runtime result from S3: {e}")
            return None

    async def cleanup_s3_source(self, s3_prefix: str) -> None:
        """S3 소스 파일 삭제 (빌드 완료 후 정리)

        runtime_result.json을 읽은 후 호출해야 합니다.

        Args:
            s3_prefix: S3 prefix (예: "agent-builds/{user_id}/{agent_id}/{version}/{deployment_id}/")
        """
        loop = asyncio.get_event_loop()

        try:
            # S3 객체 목록 조회
            response = await loop.run_in_executor(
                None,
                lambda: self.s3_client.list_objects_v2(
                    Bucket=self.source_bucket,
                    Prefix=s3_prefix
                )
            )

            # 객체가 있으면 삭제
            if 'Contents' in response and len(response['Contents']) > 0:
                objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]

                await loop.run_in_executor(
                    None,
                    lambda: self.s3_client.delete_objects(
                        Bucket=self.source_bucket,
                        Delete={'Objects': objects_to_delete}
                    )
                )

                logger.info(f"Deleted {len(objects_to_delete)} files from S3: {s3_prefix}")
            else:
                logger.debug(f"No files to delete at: {s3_prefix}")

        except Exception as e:
            logger.error(f"Failed to cleanup S3 source at {s3_prefix}: {e}")
            raise
