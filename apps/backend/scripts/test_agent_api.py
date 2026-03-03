"""Agent API 테스트 스크립트"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_create_agent():
    """Agent 생성 테스트"""
    print("\n=== 1. Agent 생성 테스트 ===")
    
    payload = {
        "name": "Test Agent",
        "description": "테스트용 Agent",
        "llm_model_id": "anthropic.claude-3-sonnet",
        "llm_model_name": "Claude 3 Sonnet",
        "llm_provider": "Anthropic",
        "system_prompt": "You are a helpful assistant.",
        "temperature": 0.7,
        "max_tokens": 2000,
        "knowledge_bases": [],
        "mcps": [],
        "team_tags": []
    }
    
    response = requests.post(f"{BASE_URL}/agents", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        data = response.json()
        agent_id = data["data"]["id"]
        print(f"✅ Agent 생성 성공: {agent_id}")
        print(f"   버전: {data['data']['current_version']}")
        return agent_id
    else:
        print(f"❌ Agent 생성 실패: {response.text}")
        return None

def test_get_agent(agent_id):
    """Agent 조회 테스트"""
    print(f"\n=== 2. Agent 조회 테스트 ===")
    
    response = requests.get(f"{BASE_URL}/agents/{agent_id}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Agent 조회 성공")
        print(f"   이름: {data['data']['name']}")
        print(f"   상태: {data['data']['status']}")
    else:
        print(f"❌ Agent 조회 실패: {response.text}")

def test_list_agents():
    """Agent 목록 조회 테스트"""
    print(f"\n=== 3. Agent 목록 조회 테스트 ===")
    
    response = requests.get(f"{BASE_URL}/agents?page=1&page_size=10")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Agent 목록 조회 성공")
        print(f"   총 개수: {data['pagination']['totalItems']}")
    else:
        print(f"❌ Agent 목록 조회 실패: {response.text}")

def test_update_agent(agent_id):
    """Agent 수정 테스트"""
    print(f"\n=== 4. Agent 수정 테스트 ===")
    
    payload = {
        "name": "Updated Test Agent",
        "description": "수정된 테스트용 Agent",
        "llm_model_id": "anthropic.claude-3-sonnet",
        "llm_model_name": "Claude 3 Sonnet",
        "llm_provider": "Anthropic",
        "system_prompt": "You are a very helpful assistant.",
        "temperature": 0.8,
        "max_tokens": 3000,
        "knowledge_bases": [],
        "mcps": [],
        "team_tags": []
    }
    
    response = requests.put(f"{BASE_URL}/agents/{agent_id}", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Agent 수정 성공")
        print(f"   새 버전: {data['data']['current_version']}")
    else:
        print(f"❌ Agent 수정 실패: {response.text}")

def test_get_versions(agent_id):
    """버전 히스토리 조회 테스트"""
    print(f"\n=== 5. 버전 히스토리 조회 테스트 ===")
    
    response = requests.get(f"{BASE_URL}/agents/{agent_id}/versions")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 버전 히스토리 조회 성공")
        print(f"   버전 개수: {len(data['data'])}")
        for v in data['data']:
            print(f"   - {v['version']}: {v['change_log']}")
    else:
        print(f"❌ 버전 히스토리 조회 실패: {response.text}")

def test_change_status(agent_id):
    """Agent 상태 변경 테스트"""
    print(f"\n=== 6. Agent 상태 변경 테스트 ===")
    
    payload = {"enabled": False}
    response = requests.patch(f"{BASE_URL}/agents/{agent_id}", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Agent 상태 변경 성공")
        print(f"   새 상태: {data['data']['status']}")
    else:
        print(f"❌ Agent 상태 변경 실패: {response.text}")

if __name__ == "__main__":
    print("🚀 Agent API 테스트 시작")
    print(f"Base URL: {BASE_URL}")
    
    try:
        # 1. Agent 생성
        agent_id = test_create_agent()
        
        if agent_id:
            # 2. Agent 조회
            test_get_agent(agent_id)
            
            # 3. Agent 목록 조회
            test_list_agents()
            
            # 4. Agent 수정
            test_update_agent(agent_id)
            
            # 5. 버전 히스토리 조회
            test_get_versions(agent_id)
            
            # 6. 상태 변경
            test_change_status(agent_id)
        
        print("\n✅ 모든 테스트 완료!")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 백엔드 서버에 연결할 수 없습니다.")
        print("   서버를 먼저 실행하세요: cd apps/backend && SKIP_AUTH=true python3 -m uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
