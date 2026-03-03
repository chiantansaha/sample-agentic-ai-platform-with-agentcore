"""Deployment Repository Interface"""
from abc import ABC, abstractmethod
from typing import Optional, List

from ..entities.deployment import Deployment


class DeploymentRepository(ABC):
    """Deployment Repository Interface"""

    @abstractmethod
    async def save(self, deployment: Deployment) -> Deployment:
        """배포 정보 저장"""
        pass

    @abstractmethod
    async def find_by_id(self, deployment_id: str) -> Optional[Deployment]:
        """ID로 배포 조회"""
        pass

    @abstractmethod
    async def find_by_user_agent_version(
        self,
        user_id: str,
        agent_id: str,
        agent_version: str
    ) -> Optional[Deployment]:
        """사용자/에이전트/버전으로 활성 배포 조회"""
        pass

    @abstractmethod
    async def find_active_by_user(self, user_id: str) -> List[Deployment]:
        """사용자의 활성 배포 목록 조회"""
        pass

    @abstractmethod
    async def delete(self, deployment_id: str) -> None:
        """배포 정보 삭제"""
        pass
