"""Agent Domain Exceptions"""


class AgentException(Exception):
    """Agent 도메인 예외 기본 클래스"""
    pass


class AgentNotFoundException(AgentException):
    """Agent를 찾을 수 없음"""
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        super().__init__(f"Agent not found: {agent_id}")


class AgentValidationException(AgentException):
    """Agent 검증 실패"""
    def __init__(self, message: str):
        super().__init__(f"Agent validation failed: {message}")
