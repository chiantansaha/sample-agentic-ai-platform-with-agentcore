"""MCP Domain Exceptions"""


class MCPDomainException(Exception):
    """MCP 도메인 기본 예외"""
    pass


class MCPNotFoundException(MCPDomainException):
    """MCP를 찾을 수 없음"""
    def __init__(self, mcp_id: str):
        super().__init__(f"MCP not found: {mcp_id}")
        self.mcp_id = mcp_id


class MCPAlreadyExistsException(MCPDomainException):
    """MCP가 이미 존재함"""
    def __init__(self, name: str):
        super().__init__(f"MCP already exists: {name}")
        self.name = name


class MCPValidationException(MCPDomainException):
    """MCP 검증 실패"""
    def __init__(self, message: str):
        super().__init__(f"MCP validation failed: {message}")


class MCPStatusException(MCPDomainException):
    """MCP 상태 변경 실패"""
    def __init__(self, message: str):
        super().__init__(f"MCP status change failed: {message}")


class GatewayCreationException(MCPDomainException):
    """Gateway 생성 실패"""
    def __init__(self, message: str):
        super().__init__(f"Gateway creation failed: {message}")


class ECRValidationException(MCPDomainException):
    """ECR 검증 실패"""
    def __init__(self, repository: str, tag: str):
        super().__init__(f"ECR image not found: {repository}:{tag}")
        self.repository = repository
        self.tag = tag
