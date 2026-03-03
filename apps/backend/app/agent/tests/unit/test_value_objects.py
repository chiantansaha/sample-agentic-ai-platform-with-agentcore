"""Value Objects 단위 테스트"""
import pytest

from ...domain.value_objects import AgentId, Version, LLMModel, Instruction, AgentStatus


def test_agent_id_generation():
    """AgentId 생성 테스트"""
    agent_id = AgentId.generate()
    assert agent_id.value is not None
    assert len(agent_id.value) == 36  # UUID 길이


def test_version_string_conversion():
    """Version 문자열 변환 테스트"""
    version = Version(1, 2, 3)
    assert str(version) == "v1.2.3"


def test_version_from_string():
    """Version 문자열 파싱 테스트"""
    version = Version.from_string("v1.2.3")
    assert version.major == 1
    assert version.minor == 2
    assert version.patch == 3


def test_version_increment_minor():
    """Version 마이너 증가 테스트"""
    version = Version(1, 2, 3)
    new_version = version.increment_minor()
    assert str(new_version) == "v1.3.0"


def test_version_increment_major():
    """Version 메이저 증가 테스트"""
    version = Version(1, 2, 3)
    new_version = version.increment_major()
    assert str(new_version) == "v2.0.0"


def test_llm_model_immutability():
    """LLMModel 불변성 테스트"""
    model = LLMModel("claude-3", "Claude 3", "Anthropic")
    
    with pytest.raises(Exception):  # dataclass frozen=True
        model.model_id = "gpt-4"


def test_instruction_defaults():
    """Instruction 기본값 테스트"""
    instruction = Instruction("You are helpful")
    assert instruction.temperature == 0.7
    assert instruction.max_tokens == 2000


def test_agent_status_enum():
    """AgentStatus Enum 테스트"""
    assert AgentStatus.ENABLED.value == "enabled"
    assert AgentStatus.DISABLED.value == "disabled"
