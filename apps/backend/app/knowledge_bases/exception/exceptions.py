"""KB Domain Exceptions"""


class KBException(Exception):
    """KB 도메인 예외 기본 클래스"""
    pass


class KBNotFoundException(KBException):
    """KB를 찾을 수 없음"""
    def __init__(self, kb_id: str):
        self.kb_id = kb_id
        super().__init__(f"Knowledge Base not found: {kb_id}")


class DataSourceException(KBException):
    """DataSource 예외"""
    pass
