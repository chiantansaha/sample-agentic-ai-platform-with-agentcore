"""MCP Creation Progress DTOs for SSE streaming"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from enum import Enum
import json


class ProgressStatus(str, Enum):
    """Progress status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressStep:
    """Individual progress step"""
    step: int
    total_steps: int
    title: str
    description: str
    status: ProgressStatus = ProgressStatus.PENDING
    details: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "totalSteps": self.total_steps,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "details": self.details
        }

    def to_sse(self) -> str:
        """Convert to SSE format"""
        return f"data: {json.dumps(self.to_dict())}\n\n"


@dataclass
class DeployProgress:
    """Deploy MCP progress tracker with 8 steps"""

    STEPS = [
        ("Setting up OAuth", "Cognito OAuth 인프라 준비 중..."),
        ("Creating Runtime Role", "Runtime IAM 역할 생성 중..."),
        ("Creating Runtime", "AgentCore Runtime 생성 중... (약 1-2분 소요)"),
        ("Creating Gateway Role", "Gateway IAM 역할 생성 중..."),
        ("Creating Gateway", "AgentCore Gateway 생성 중..."),
        ("Waiting for Gateway", "Gateway 준비 대기 중..."),
        ("Creating Target", "MCP Server Target 생성 중..."),
        ("Fetching Tools", "MCP 서버에서 도구 목록 조회 중...")
    ]

    current_step: int = 0
    total_steps: int = 8
    mcp_name: str = ""
    error: Optional[str] = None
    mcp_id: Optional[str] = None
    completed: bool = False

    def get_current_progress(self) -> ProgressStep:
        """Get current step progress"""
        if self.current_step <= 0:
            return ProgressStep(
                step=0,
                total_steps=self.total_steps,
                title="Initializing",
                description="MCP 생성 준비 중...",
                status=ProgressStatus.IN_PROGRESS
            )

        if self.current_step > len(self.STEPS):
            return ProgressStep(
                step=self.total_steps,
                total_steps=self.total_steps,
                title="Completed",
                description="MCP 생성 완료!",
                status=ProgressStatus.COMPLETED,
                details=self.mcp_id
            )

        idx = self.current_step - 1
        title, description = self.STEPS[idx]

        return ProgressStep(
            step=self.current_step,
            total_steps=self.total_steps,
            title=title,
            description=description,
            status=ProgressStatus.IN_PROGRESS
        )

    def step_completed(self, step_num: int, details: Optional[str] = None) -> ProgressStep:
        """Mark a step as completed"""
        self.current_step = step_num + 1
        idx = step_num - 1
        if 0 <= idx < len(self.STEPS):
            title, description = self.STEPS[idx]
            return ProgressStep(
                step=step_num,
                total_steps=self.total_steps,
                title=title,
                description=f"{title} 완료",
                status=ProgressStatus.COMPLETED,
                details=details
            )
        return self.get_current_progress()

    def step_failed(self, error_msg: str) -> ProgressStep:
        """Mark current step as failed"""
        self.error = error_msg
        idx = max(0, self.current_step - 1)
        if idx < len(self.STEPS):
            title, _ = self.STEPS[idx]
        else:
            title = "Error"

        return ProgressStep(
            step=self.current_step,
            total_steps=self.total_steps,
            title=title,
            description="오류가 발생했습니다",
            status=ProgressStatus.FAILED,
            details=error_msg
        )

    def finish(self, mcp_id: str) -> ProgressStep:
        """Mark deployment as completed"""
        self.completed = True
        self.mcp_id = mcp_id
        return ProgressStep(
            step=self.total_steps,
            total_steps=self.total_steps,
            title="Completed",
            description="MCP가 성공적으로 생성되었습니다!",
            status=ProgressStatus.COMPLETED,
            details=mcp_id
        )


@dataclass
class FinalResult:
    """Final result sent at the end of SSE stream"""
    success: bool
    mcp_id: Optional[str] = None
    error: Optional[str] = None
    data: Optional[dict] = None

    def to_sse(self) -> str:
        """Convert to SSE format with event type"""
        result = {
            "success": self.success,
            "mcpId": self.mcp_id,
            "error": self.error,
            "data": self.data
        }
        return f"event: result\ndata: {json.dumps(result)}\n\n"
