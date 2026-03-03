"""API 엔드포인트 End-to-End 테스트"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """인증 헤더 (테스트용)"""
    # SKIP_AUTH=true 환경에서는 불필요하지만, 실제 환경 대비
    return {
        "Authorization": "Bearer test-token"
    }


class TestMCPAPI:
    """MCP API 엔드포인트 테스트"""
    
    def test_create_internal_create_mcp(self, client, auth_headers, api_create_request_payload):
        """TC-API-001: POST /api/v1/mcpss (Internal Create)"""
        response = client.post(
            "/api/v1/mcpss",
            json=api_create_request_payload,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["name"] == api_create_request_payload["name"]
        assert data["data"]["type"] == "internal-create"
        assert data["data"]["endpoint"] is not None
        
        print(f"\n✅ MCP 생성 성공:")
        print(f"   ID: {data['data']['id']}")
        print(f"   Name: {data['data']['name']}")
        print(f"   Endpoint: {data['data']['endpoint']}")
    
    def test_create_mcp_duplicate_name(self, client, auth_headers, api_create_request_payload):
        """TC-API-002: POST /api/v1/mcps (중복 이름)"""
        # 첫 번째 생성
        client.post("/api/v1/mcps", json=api_create_request_payload, headers=auth_headers)
        
        # 중복 생성 시도
        response = client.post("/api/v1/mcps", json=api_create_request_payload, headers=auth_headers)
        
        assert response.status_code == 409  # Conflict
    
    def test_create_mcp_invalid_type(self, client, auth_headers, api_create_request_payload):
        """TC-API-003: POST /api/v1/mcps (잘못된 타입)"""
        invalid_payload = api_create_request_payload.copy()
        invalid_payload["type"] = "invalid-type"
        
        response = client.post("/api/v1/mcps", json=invalid_payload, headers=auth_headers)
        
        assert response.status_code == 400  # Bad Request
    
    def test_list_mcps(self, client, auth_headers, api_create_request_payload):
        """TC-API-004: GET /api/v1/mcps"""
        # MCP 생성
        client.post("/api/v1/mcps", json=api_create_request_payload, headers=auth_headers)
        
        # 목록 조회
        response = client.get("/api/v1/mcps", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert len(data["data"]) > 0
        assert "pagination" in data
    
    def test_get_mcp_detail(self, client, auth_headers, api_create_request_payload):
        """TC-API-005: GET /api/v1/mcps/{mcp_id}"""
        # MCP 생성
        create_response = client.post(
            "/api/v1/mcps",
            json=api_create_request_payload,
            headers=auth_headers
        )
        mcp_id = create_response.json()["data"]["id"]
        
        # 상세 조회
        response = client.get(f"/api/v1/mcps/{mcp_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == mcp_id
        assert data["data"]["name"] == api_create_request_payload["name"]
    
    def test_get_mcp_not_found(self, client, auth_headers):
        """TC-API-006: GET /api/v1/mcps/{mcp_id} (존재하지 않음)"""
        response = client.get("/api/v1/mcps/mcp-nonexistent", headers=auth_headers)
        
        assert response.status_code == 404  # Not Found
    
    def test_toggle_mcp_status_enable(self, client, auth_headers, api_create_request_payload):
        """TC-API-007: PATCH /api/v1/mcps/{mcp_id} (Enable)"""
        # MCP 생성
        create_response = client.post(
            "/api/v1/mcps",
            json=api_create_request_payload,
            headers=auth_headers
        )
        mcp_id = create_response.json()["data"]["id"]
        
        # Enable
        response = client.patch(
            f"/api/v1/mcps/{mcp_id}",
            json={"status": "enabled"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "enabled"
    
    def test_toggle_mcp_status_disable(self, client, auth_headers, api_create_request_payload):
        """TC-API-008: PATCH /api/v1/mcps/{mcp_id} (Disable)"""
        # MCP 생성 및 Enable
        create_response = client.post(
            "/api/v1/mcps",
            json=api_create_request_payload,
            headers=auth_headers
        )
        mcp_id = create_response.json()["data"]["id"]
        client.patch(f"/api/v1/mcps/{mcp_id}", json={"status": "enabled"}, headers=auth_headers)
        
        # Disable
        response = client.patch(
            f"/api/v1/mcps/{mcp_id}",
            json={"status": "disabled"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "disabled"
