#!/usr/bin/env python3
"""Import API Catalog data from JSON file to DynamoDB"""

import sys
import os
import json
import asyncio

# Backend 경로 추가
backend_path = os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend')
sys.path.append(backend_path)

# 환경변수 로드
from dotenv import load_dotenv
env_file = os.path.join(backend_path, '.env.development')
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"📁 Loaded env from: {env_file}")

from app.api_catalog.dynamodb_repository import DynamoDBAPICatalogRepository
from app.mcp.domain.value_objects import APITarget


async def import_api_catalog(json_file: str):
    """Import API Catalog data from JSON file"""
    print(f"📥 Importing API Catalog data from: {json_file}")

    # JSON 파일 읽기
    with open(json_file, 'r', encoding='utf-8') as f:
        import_data = json.load(f)

    repository = DynamoDBAPICatalogRepository()

    success_count = 0
    for api_dict in import_data:
        try:
            api_target = APITarget(
                id=api_dict['id'],
                name=api_dict['name'],
                api_id=api_dict['api_id'],
                endpoint=api_dict['endpoint'],
                method=api_dict['method'],
                auth_type=api_dict['auth_type'],
                openapi_schema=api_dict['openapi_schema'],
                team_tag_ids=api_dict.get('team_tag_ids', [])
            )
            await repository.save(api_target)
            print(f"✅ Imported: {api_target.name}")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to import {api_dict.get('name', 'unknown')}: {e}")

    print(f"\n🎉 Successfully imported {success_count}/{len(import_data)} APIs")


def main():
    # 기본 파일 경로
    default_file = os.path.join(os.path.dirname(__file__), 'api_catalog_export.json')

    # 인자로 파일 경로 받기
    json_file = sys.argv[1] if len(sys.argv) > 1 else default_file

    if not os.path.exists(json_file):
        print(f"❌ File not found: {json_file}")
        print(f"Usage: python import_api_catalog.py [json_file_path]")
        sys.exit(1)

    try:
        asyncio.run(import_api_catalog(json_file))
    except Exception as e:
        print(f"❌ Error importing data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
