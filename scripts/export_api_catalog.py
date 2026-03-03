#!/usr/bin/env python3
"""Export API Catalog data from DynamoDB to JSON file"""

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


async def export_api_catalog():
    """Export all API Catalog data to JSON"""
    print("📤 Exporting API Catalog data...")

    repository = DynamoDBAPICatalogRepository()
    apis = await repository.find_all()

    # APITarget 객체를 dict로 변환
    export_data = []
    for api in apis:
        api_dict = {
            "id": api.id,
            "name": api.name,
            "api_id": api.api_id,
            "endpoint": api.endpoint,
            "method": api.method,
            "auth_type": api.auth_type,
            "openapi_schema": api.openapi_schema,
            "team_tag_ids": api.team_tag_ids or []
        }
        export_data.append(api_dict)

    # JSON 파일로 저장
    output_file = os.path.join(os.path.dirname(__file__), 'api_catalog_export.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Exported {len(export_data)} APIs to: {output_file}")
    return output_file


def main():
    try:
        asyncio.run(export_api_catalog())
    except Exception as e:
        print(f"❌ Error exporting data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
