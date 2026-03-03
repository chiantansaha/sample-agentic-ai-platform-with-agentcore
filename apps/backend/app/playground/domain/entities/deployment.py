"""Deployment Entity for AgentCore Runtime (Container 방식)"""
from dataclasses import dataclass, field
from typing import Optional

from ..value_objects import DeploymentId, DeploymentStatus
from app.shared.utils.timestamp import now_timestamp


@dataclass
class Deployment:
    """AgentCore Runtime Deployment Aggregate Root (Container 방식)"""
    id: DeploymentId
    user_id: str
    agent_id: str
    agent_version: str
    status: DeploymentStatus = DeploymentStatus.PENDING
    runtime_id: Optional[str] = None
    runtime_arn: Optional[str] = None
    endpoint_url: Optional[str] = None
    container_uri: Optional[str] = None  # ECR 이미지 URI
    conversation_id: Optional[str] = None  # 대화 이어하기용
    error_message: Optional[str] = None
    idle_timeout: int = 300  # 5분
    max_lifetime: int = 3600  # 1시간
    build_id: Optional[str] = None  # CodeBuild 빌드 ID
    build_phase: Optional[str] = None  # 현재 빌드 Phase (SUBMITTED, PROVISIONING, BUILD 등)
    build_phase_message: Optional[str] = None  # Phase별 한글 메시지
    s3_prefix: Optional[str] = None  # S3 빌드 소스 경로 (Runtime 결과 읽기용)
    created_at: int = field(default_factory=now_timestamp)
    updated_at: int = field(default_factory=now_timestamp)
    expires_at: Optional[int] = None  # Unix timestamp (seconds)

    def mark_building(self, container_uri: str = None, build_id: str = None):
        """Docker 빌드 중 상태로 변경"""
        self.status = DeploymentStatus.BUILDING
        if container_uri:
            self.container_uri = container_uri
        if build_id:
            self.build_id = build_id
        self.updated_at = now_timestamp()

    def update_build_phase(self, phase: str, message: str = None):
        """빌드 Phase 업데이트"""
        self.build_phase = phase
        self.build_phase_message = message
        self.updated_at = now_timestamp()

    def mark_creating(self, runtime_id: str):
        """Runtime 생성 중 상태로 변경"""
        self.status = DeploymentStatus.CREATING
        self.runtime_id = runtime_id
        self.updated_at = now_timestamp()

    def mark_ready(self, runtime_arn: str, endpoint_url: str, expires_at: int):
        """배포 완료 상태로 변경"""
        self.status = DeploymentStatus.READY
        self.runtime_arn = runtime_arn
        self.endpoint_url = endpoint_url
        self.expires_at = expires_at
        self.updated_at = now_timestamp()

    def mark_failed(self, error_message: str):
        """배포 실패 상태로 변경"""
        self.status = DeploymentStatus.FAILED
        self.error_message = error_message
        self.updated_at = now_timestamp()

    def mark_deleting(self):
        """삭제 중 상태로 변경"""
        self.status = DeploymentStatus.DELETING
        self.updated_at = now_timestamp()

    def mark_deleted(self):
        """삭제 완료 상태로 변경"""
        self.status = DeploymentStatus.DELETED
        self.updated_at = now_timestamp()

    def is_active(self) -> bool:
        """활성 상태인지 확인"""
        return self.status == DeploymentStatus.READY

    def is_terminal(self) -> bool:
        """종료 상태인지 확인"""
        return self.status in [DeploymentStatus.FAILED, DeploymentStatus.DELETED]
