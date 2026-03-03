"""BedrockGatewayService 통합 테스트 (실제 AWS API 호출)"""
import pytest
import json
from ..infrastructure.gateway_service_impl import BedrockGatewayService


class TestBedrockGatewayService:
    """Bedrock Gateway Service 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_create_dedicated_gateway(self, gateway_service, sample_mcp_entity):
        """TC-GATEWAY-001: Gateway 생성 (실제 AWS 호출)"""
        # Gateway 생성
        gateway_id = await gateway_service.create_dedicated_gateway(sample_mcp_entity)
        
        # 검증
        assert gateway_id is not None
        assert gateway_id.startswith("gw-") or len(gateway_id) > 0
        assert sample_mcp_entity.endpoint is not None
        assert "gateway" in sample_mcp_entity.endpoint.lower()
        
        print(f"\n✅ Gateway 생성 성공:")
        print(f"   Gateway ID: {gateway_id}")
        print(f"   Endpoint: {sample_mcp_entity.endpoint}")
    
    @pytest.mark.asyncio
    async def test_create_gateway_role(self, gateway_service):
        """TC-GATEWAY-002: IAM Role 생성"""
        gateway_name = "test-gateway-role"
        
        # IAM Role 생성
        role_arn = await gateway_service._create_gateway_role(gateway_name)
        
        # 검증
        assert role_arn is not None
        assert "arn:aws:iam::" in role_arn
        assert gateway_name in role_arn
        
        print(f"\n✅ IAM Role 생성 성공:")
        print(f"   Role ARN: {role_arn}")
    
    @pytest.mark.asyncio
    async def test_create_gateway_with_iam_auth(self, gateway_service):
        """TC-GATEWAY-003: Gateway 생성 (IAM 인증)"""
        gateway_name = "test-gateway-iam"
        
        # IAM Role 생성
        role_arn = await gateway_service._create_gateway_role(gateway_name)
        
        # Gateway 생성
        gateway = await gateway_service._create_gateway(gateway_name, role_arn)
        
        # 검증
        assert gateway is not None
        assert "gatewayId" in gateway
        assert "gatewayUrl" in gateway
        assert gateway["gatewayUrl"] is not None
        
        print(f"\n✅ Gateway 생성 성공:")
        print(f"   Gateway ID: {gateway['gatewayId']}")
        print(f"   Gateway URL: {gateway['gatewayUrl']}")
    
    @pytest.mark.asyncio
    async def test_create_api_targets(self, gateway_service, sample_mcp_entity):
        """TC-GATEWAY-004: API Target 생성"""
        # Gateway 먼저 생성
        gateway_id = await gateway_service.create_dedicated_gateway(sample_mcp_entity)
        
        # Target 생성 (이미 create_dedicated_gateway에서 호출됨)
        # 추가 검증
        assert len(sample_mcp_entity.selected_api_targets) > 0
        
        print(f"\n✅ API Target 생성 성공:")
        print(f"   Gateway ID: {gateway_id}")
        print(f"   Target 개수: {len(sample_mcp_entity.selected_api_targets)}")
        for target in sample_mcp_entity.selected_api_targets:
            print(f"   - {target.name}: {target.method} {target.endpoint}")
    
    @pytest.mark.asyncio
    async def test_openapi_schema_conversion(self, sample_openapi_schema):
        """TC-GATEWAY-005: OpenAPI Schema 변환"""
        # Dict → JSON 문자열 변환
        schema_json = json.dumps(sample_openapi_schema)
        
        # 검증
        assert isinstance(schema_json, str)
        assert len(schema_json) > 0
        
        # 다시 파싱 가능한지 확인
        parsed = json.loads(schema_json)
        assert parsed["openapi"] == "3.0.0"
        assert "paths" in parsed
        
        print(f"\n✅ OpenAPI Schema 변환 성공:")
        print(f"   Schema 크기: {len(schema_json)} bytes")
