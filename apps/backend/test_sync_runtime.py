"""Runtime Sync 테스트 - Runtime 재시작 및 Tools 조회"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.mcp.infrastructure.gateway_service_impl import BedrockGatewayService


async def sync_runtime():
    """External MCP Runtime sync"""
    print("=" * 60)
    print("Syncing External MCP Runtime")
    print("=" * 60)
    print()

    gateway_service = BedrockGatewayService()

    print("📋 Starting sync...")
    print("   This will:")
    print("   1. Delete existing Runtime")
    print("   2. Create new Runtime")
    print("   3. Wait for MCP servers to initialize (60s)")
    print("   4. Fetch tools from each server")
    print()

    try:
        # Cognito 인프라 초기화 먼저
        print("🔐 Initializing Cognito infrastructure...")
        await gateway_service.cognito_service.get_or_create_shared_infrastructure()
        print("✅ Cognito ready")
        print()

        result = await gateway_service.sync_external_mcp_runtime()

        print()
        print("=" * 60)
        print("✅ Sync Result")
        print("=" * 60)
        print(f"Runtime ID: {result.get('runtime_id')}")
        print(f"Runtime Endpoint: {result.get('runtime_endpoint')}")
        print()

        servers = result.get('servers', {})
        total_tools = 0
        for server_name, tools in servers.items():
            tool_count = len(tools)
            total_tools += tool_count
            print(f"📋 {server_name}: {tool_count} tools")
            for tool in tools[:3]:
                print(f"   - {tool.get('name')}")
            if tool_count > 3:
                print(f"   ... and {tool_count - 3} more")

        print()
        print(f"🎉 Total: {len(servers)} servers, {total_tools} tools")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(sync_runtime())
