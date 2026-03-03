"""External MCP 생성 및 Tools 조회 테스트

테스트 시나리오:
1. External MCP 생성 (memory MCP 설정 사용)
2. sync_external_mcp_runtime 호출하여 tools 조회
"""
import asyncio
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.mcp.application.service import MCPApplicationService
from app.mcp.infrastructure.mcp_repository_impl import DynamoDBMCPRepository
from app.mcp.infrastructure.mcp_version_repository_impl import DynamoDBMCPVersionRepository
from app.mcp.infrastructure.gateway_service_impl import BedrockGatewayService
from app.mcp.domain.services import ECRService, KEISService
from app.mcp.dto.request import CreateExternalMCPRequest


async def test_external_mcp_creation():
    """External MCP 생성 및 tools 조회 테스트"""
    print("=" * 60)
    print("External MCP Creation Test")
    print("=" * 60)
    print(f"AWS Region: {settings.AWS_REGION}")
    print(f"Table Prefix: {settings.TABLE_PREFIX}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print()

    # 서비스 초기화
    mcp_repository = DynamoDBMCPRepository()
    version_repository = DynamoDBMCPVersionRepository()
    gateway_service = BedrockGatewayService()
    ecr_service = ECRService()
    keis_service = KEISService()

    mcp_service = MCPApplicationService(
        mcp_repository=mcp_repository,
        version_repository=version_repository,
        gateway_service=gateway_service,
        ecr_service=ecr_service,
        keis_service=keis_service
    )

    # External MCP 생성 요청 (memory MCP)
    request = CreateExternalMCPRequest(
        name="test-memory-mcp",
        description="Test Memory MCP Server",
        team_tags=[],
        server_name="memory",  # Tool prefix
        mcp_config={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"]
        }
    )

    print("📋 Creating External MCP...")
    print(f"   Name: {request.name}")
    print(f"   Server Name: {request.server_name}")
    print(f"   Config: {request.mcp_config}")
    print()

    try:
        # 1. External MCP 생성
        response = await mcp_service.create_external_mcp(request)
        print(f"✅ MCP Created: {response.id}")
        print(f"   Gateway ID: {response.gateway_id}")
        print(f"   Endpoint: {response.endpoint}")
        print(f"   Tools count: {len(response.tools)}")
        print()

        if response.tools:
            print("📋 Tools:")
            for tool in response.tools:
                print(f"   - {tool.get('name')}: {tool.get('description', '')[:50]}...")
        else:
            print("⚠️ No tools yet. Need to sync Runtime.")
            print()

        # 2. Sync External MCP Runtime (Tools 조회)
        print("=" * 60)
        print("📋 Syncing External MCP Runtime...")
        print("   This will restart Runtime and fetch tools.")
        print("   This may take several minutes...")
        print()

        sync_result = await gateway_service.sync_external_mcp_runtime()

        print(f"✅ Sync completed")
        print(f"   Runtime ID: {sync_result.get('runtime_id')}")
        print(f"   Runtime Endpoint: {sync_result.get('runtime_endpoint')}")
        print()

        servers = sync_result.get('servers', {})
        for server_name, tools in servers.items():
            print(f"📋 Server: {server_name}")
            print(f"   Tools count: {len(tools)}")
            for tool in tools[:5]:  # 처음 5개만 출력
                print(f"   - {tool.get('name')}")
            if len(tools) > 5:
                print(f"   ... and {len(tools) - 5} more")

        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_tools_only():
    """기존 External MCP의 tools만 조회 테스트 (sync 없이)"""
    print("=" * 60)
    print("Tools Fetch Test (without sync)")
    print("=" * 60)

    gateway_service = BedrockGatewayService()

    # DynamoDB에서 모든 MCP 설정 조회
    configs = await gateway_service._get_all_mcp_configs_from_dynamodb()
    print(f"📋 Found {len(configs)} MCP configs in DynamoDB")

    for config in configs:
        print(f"   - {config.get('id')}: command={config.get('command')}")

    print()
    print("⚠️ To fetch tools, call sync_external_mcp_runtime()")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync", action="store_true", help="Run full sync test")
    parser.add_argument("--tools-only", action="store_true", help="Check tools without sync")
    args = parser.parse_args()

    if args.sync:
        asyncio.run(test_external_mcp_creation())
    elif args.tools_only:
        asyncio.run(test_tools_only())
    else:
        print("Usage:")
        print("  python test_external_mcp_flow.py --sync        # Full creation + sync test")
        print("  python test_external_mcp_flow.py --tools-only  # Check existing configs")
