"""Playground Exceptions"""


class SessionNotFoundException(Exception):
    """세션을 찾을 수 없음"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class AgentNotFoundException(Exception):
    """Agent를 찾을 수 없음"""
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        super().__init__(f"Agent not found: {agent_id}")


# ==================== AgentCore Runtime Exceptions ====================

class DeploymentNotFoundException(Exception):
    """Deployment를 찾을 수 없음"""
    def __init__(self, deployment_id: str):
        self.deployment_id = deployment_id
        super().__init__(f"Deployment not found: {deployment_id}")


class DeploymentAlreadyExistsException(Exception):
    """이미 활성화된 Deployment가 존재함"""
    def __init__(self, deployment_id: str):
        self.deployment_id = deployment_id
        super().__init__(f"Active deployment already exists: {deployment_id}")


class ConversationNotFoundException(Exception):
    """Conversation을 찾을 수 없음"""
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        super().__init__(f"Conversation not found: {conversation_id}")


class MaxConversationsExceededException(Exception):
    """최대 대화 수 초과"""
    def __init__(self, max_count: int = 5):
        self.max_count = max_count
        super().__init__(f"Maximum conversations exceeded: {max_count}")


class RuntimeNotActiveException(Exception):
    """Runtime이 활성 상태가 아님"""
    def __init__(self, deployment_id: str, status: str):
        self.deployment_id = deployment_id
        self.status = status
        super().__init__(f"Runtime is not active. Deployment: {deployment_id}, Status: {status}")


class RuntimeCreationException(Exception):
    """Runtime 생성 실패"""
    def __init__(self, message: str):
        super().__init__(f"Runtime creation failed: {message}")
