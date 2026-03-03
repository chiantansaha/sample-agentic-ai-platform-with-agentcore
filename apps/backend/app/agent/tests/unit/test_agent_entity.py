"""Agent Entity 단위 테스트"""
import pytest
from datetime import datetime

from ...domain.entities import Agent
from ...domain.value_objects import AgentId, LLMModel, Instruction, Version, AgentStatus


def test_agent_creation():
    """Agent 생성 테스트"""
    agent = Agent(
        id=AgentId.generate(),
        name="Test Agent",
        description="Test Description",
        llm_model=LLMModel(
            model_id="claude-3",
            model_name="Claude 3",
            provider="Anthropic"
        ),
        instruction=Instruction(
            system_prompt="You are helpful",
            temperature=0.7,
            max_tokens=2000
        )
    )
    
    assert agent.name == "Test Agent"
    assert agent.status == AgentStatus.ENABLED
    assert str(agent.current_version) == "v1.0.0"


def test_agent_update():
    """Agent 업데이트 테스트"""
    agent = Agent(
        id=AgentId.generate(),
        name="Test Agent",
        description="Test Description",
        llm_model=LLMModel("claude-3", "Claude 3", "Anthropic"),
        instruction=Instruction("You are helpful")
    )
    
    new_llm = LLMModel("gpt-4", "GPT-4", "OpenAI")
    new_instruction = Instruction("You are very helpful")
    
    agent.update(
        name="Updated Agent",
        description="Updated Description",
        llm_model=new_llm,
        instruction=new_instruction,
        knowledge_bases=[],
        mcps=[],
        team_tags=[],
        updated_by="user-123"
    )
    
    assert agent.name == "Updated Agent"
    assert agent.llm_model.model_id == "gpt-4"
    assert agent.updated_by == "user-123"


def test_agent_enable_disable():
    """Agent 활성화/비활성화 테스트"""
    agent = Agent(
        id=AgentId.generate(),
        name="Test Agent",
        description="Test",
        llm_model=LLMModel("claude-3", "Claude 3", "Anthropic"),
        instruction=Instruction("You are helpful")
    )
    
    # 초기 상태는 enabled
    assert agent.status == AgentStatus.ENABLED
    
    # Disable
    agent.disable()
    assert agent.status == AgentStatus.DISABLED
    
    # Enable
    agent.enable()
    assert agent.status == AgentStatus.ENABLED


def test_agent_version_increment():
    """Agent 버전 증가 테스트"""
    agent = Agent(
        id=AgentId.generate(),
        name="Test Agent",
        description="Test",
        llm_model=LLMModel("claude-3", "Claude 3", "Anthropic"),
        instruction=Instruction("You are helpful")
    )
    
    assert str(agent.current_version) == "v1.0.0"
    
    new_version = agent.current_version.increment_minor()
    agent.increment_version(new_version)
    
    assert str(agent.current_version) == "v1.1.0"
