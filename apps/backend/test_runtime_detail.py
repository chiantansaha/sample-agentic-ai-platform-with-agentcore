"""Runtime 상세 정보 확인"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.mcp.infrastructure.gateway_service_impl import BedrockGatewayService


async def check_runtime_detail():
    """Runtime 상세 정보 확인"""
    gateway_service = BedrockGatewayService()
    runtime_name = settings.MCP_PROXY_RUNTIME_NAME

    print(f"Checking Runtime: {runtime_name}")
    print()

    try:
        runtimes = gateway_service.gateway_client.list_agent_runtimes()
        runtime_list = runtimes.get('runtimeSummaries', []) or runtimes.get('agentRuntimes', [])

        for rt in runtime_list:
            rt_name = rt.get('agentRuntimeName') or rt.get('name')
            rt_id = rt.get('agentRuntimeId')

            if rt_name == runtime_name:
                print(f"Found Runtime: {rt_id}")
                print()

                # 상세 정보 조회
                details = gateway_service.gateway_client.get_agent_runtime(agentRuntimeId=rt_id)

                print("=== Full Runtime Details ===")
                print(json.dumps(details, indent=2, default=str))
                return

        print(f"Runtime not found: {runtime_name}")

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_runtime_detail())
