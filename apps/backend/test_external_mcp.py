#!/usr/bin/env python3
"""External MCP 생성 테스트 스크립트

Linear MCP를 생성하고 tool이 정상적으로 fetch되는지 테스트합니다.

Usage:
    cd apps/backend
    source venv/bin/activate
    python test_external_mcp.py
"""

import asyncio
import json
import sys

# Add app to path
sys.path.insert(0, '.')

from app.config import settings
from app.mcp.dto.request import CreateExternalMCPRequest
from app.mcp.presentation.dependencies import get_mcp_service


async def test_external_mcp():
    print("=" * 60)
    print("External MCP Creation Test - Linear")
    print("=" * 60)

    # 설정 확인
    print("\n[Config Check]")
    print(f"  AWS_REGION: {settings.AWS_REGION}")
    print(f"  TABLE_PREFIX: {settings.TABLE_PREFIX}")
    print(f"  ENVIRONMENT: {settings.ENVIRONMENT}")
    print(f"  MCP_PROXY_RUNTIME_NAME: {settings.MCP_PROXY_RUNTIME_NAME}")
    print(f"  MCP_PROXY_TARGET_NAME: {settings.MCP_PROXY_TARGET_NAME}")
    print(f"  MCP_PROXY_REPOSITORY: {settings.MCP_PROXY_REPOSITORY}")
    print(f"  MCP_PROXY_CONFIG_TABLE: {settings.MCP_PROXY_CONFIG_TABLE}")

    config_table_name = f"{settings.TABLE_PREFIX}-{settings.ENVIRONMENT}-{settings.MCP_PROXY_CONFIG_TABLE}"
    print(f"  Full config table name: {config_table_name}")

    # MCP 서비스 생성 (의존성 주입)
    print("\n[Creating MCP Service]")
    service = get_mcp_service()

    # External MCP 생성 요청
    request = CreateExternalMCPRequest(
        name="linear-mcp-test",
        description="Linear MCP Test",
        team_tags=["test"],
        server_name="linear",
        mcp_config={
            "command": "npx",
            "args": [
                "-y",
                "@smithery/cli@latest",
                "run",
                "linear",
                "--key",
                "77caa7c7-5f9d-4ec0-9705-5f0293aff2cf"
            ]
        }
    )

    print("\n[Creating External MCP]")
    print(f"  Name: {request.name}")
    print(f"  Server Name: {request.server_name}")
    print(f"  Command: {request.mcp_config.get('command')}")
    print(f"  Args: {request.mcp_config.get('args')}")

    try:
        response = await service.create_external_mcp(request)

        print("\n[Result]")
        print(f"  MCP ID: {response.id}")
        print(f"  Name: {response.name}")
        print(f"  Type: {response.type}")
        print(f"  Status: {response.status}")
        print(f"  Endpoint: {response.endpoint}")
        print(f"  Tools: {len(response.toolList or [])} tools")

        if response.toolList:
            print("\n[Tools]")
            for tool in response.toolList:
                print(f"  - {tool.name}: {tool.description[:50]}...")
        else:
            print("\n[WARNING] No tools fetched!")

        print("\n" + "=" * 60)
        print("Test completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_external_mcp())
    sys.exit(0 if success else 1)
