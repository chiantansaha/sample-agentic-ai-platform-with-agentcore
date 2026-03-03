"""Runtime 상태 및 Tools 조회 테스트"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.mcp.infrastructure.gateway_service_impl import BedrockGatewayService


async def check_runtime_status():
    """Runtime 상태 확인"""
    print("=" * 60)
    print("Runtime Status Check")
    print("=" * 60)

    gateway_service = BedrockGatewayService()
    runtime_name = settings.MCP_PROXY_RUNTIME_NAME

    print(f"Looking for Runtime: {runtime_name}")
    print()

    try:
        runtimes = gateway_service.gateway_client.list_agent_runtimes()
        runtime_list = runtimes.get('runtimeSummaries', []) or runtimes.get('agentRuntimes', [])

        print(f"📋 Found {len(runtime_list)} runtimes")
        print()

        for rt in runtime_list:
            rt_name = rt.get('agentRuntimeName') or rt.get('name')
            rt_id = rt.get('agentRuntimeId')
            status = rt.get('status', 'UNKNOWN')

            print(f"Runtime: {rt_name}")
            print(f"   ID: {rt_id}")
            print(f"   Status: {status}")

            if rt_name == runtime_name:
                print("   ⭐ This is the Multi-MCP Proxy Runtime")

                # 상세 정보 조회
                details = gateway_service.gateway_client.get_agent_runtime(agentRuntimeId=rt_id)
                runtime_arn = details.get('agentRuntimeArn')

                # ARN에서 endpoint URL 생성 (코드에서 하는 방식)
                import urllib.parse
                encoded_arn = urllib.parse.quote(runtime_arn, safe='')
                runtime_url = f"https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"

                print(f"   ARN: {runtime_arn}")
                print(f"   Endpoint: {runtime_url}")

                if status == 'READY':
                    print()
                    print("🔍 Attempting to fetch tools from Runtime...")
                    await fetch_tools_from_runtime(gateway_service, runtime_url)

            print()

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


async def fetch_tools_from_runtime(gateway_service, runtime_url: str):
    """Runtime에서 직접 tools 조회"""
    import json
    import requests

    try:
        # Cognito 토큰 획득
        client_id, client_secret = await gateway_service.cognito_service.get_or_create_m2m_client(
            client_name="mcp-gateway-oauth-client"
        )
        token_response = await gateway_service.cognito_service.get_access_token(
            client_id=client_id,
            client_secret=client_secret
        )
        access_token = token_response.get('access_token')

        if not access_token:
            print("❌ Failed to get access token")
            return

        print(f"✅ Got access token")

        # tools/list 요청
        payload = {
            "jsonrpc": "2.0",
            "id": "list-tools",
            "method": "tools/list"
        }

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream',
            'Authorization': f'Bearer {access_token}'
        }

        print(f"📤 Sending tools/list to: {runtime_url}")

        response = requests.post(
            runtime_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=60
        )

        print(f"📥 Response status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")

        content_type = response.headers.get('Content-Type', '')
        if 'text/event-stream' in content_type:
            # SSE 응답 파싱
            for line in response.text.strip().split('\n'):
                if line.startswith('data: '):
                    result = json.loads(line[6:])
                    break
            else:
                result = json.loads(response.text)
        else:
            result = response.json()

        if 'result' in result and 'tools' in result['result']:
            tools = result['result']['tools']
            print(f"✅ Found {len(tools)} tools")
            print()

            # 서버별로 그룹핑
            servers = {}
            for tool in tools:
                name = tool['name']
                if '__' in name:
                    server, tool_name = name.split('__', 1)
                    if server not in servers:
                        servers[server] = []
                    servers[server].append(tool_name)
                else:
                    if 'unknown' not in servers:
                        servers['unknown'] = []
                    servers['unknown'].append(name)

            for server, tool_list in servers.items():
                print(f"📋 Server: {server} ({len(tool_list)} tools)")
                for t in tool_list[:3]:
                    print(f"   - {t}")
                if len(tool_list) > 3:
                    print(f"   ... and {len(tool_list) - 3} more")
        else:
            print(f"⚠️ No tools in response: {result}")

    except Exception as e:
        print(f"❌ Error fetching tools: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_runtime_status())
