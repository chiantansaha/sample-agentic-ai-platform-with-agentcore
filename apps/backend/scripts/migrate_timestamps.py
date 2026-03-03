"""
DynamoDB Timestamp Migration Script

이 스크립트는 기존 ISO 문자열 형식의 timestamp 값들을
Unix timestamp (초 단위 정수)로 마이그레이션합니다.

사용법:
    # Dry run (실제 업데이트 없이 확인만)
    AWS_PROFILE=default python scripts/migrate_timestamps.py --dry-run

    # 실제 마이그레이션 실행
    AWS_PROFILE=default python scripts/migrate_timestamps.py

    # 특정 테이블만 마이그레이션
    AWS_PROFILE=default python scripts/migrate_timestamps.py --table agent-management

환경변수:
    AWS_PROFILE: AWS 프로파일 (기본값: default)
    AWS_REGION: AWS 리전 (기본값: us-east-1)
"""

import argparse
import boto3
from datetime import datetime, timezone
from decimal import Decimal
import os
import sys

# 마이그레이션 대상 테이블 및 필드 정의
MIGRATION_CONFIG = {
    "agentic-ai-dev-agent-management-dev": {
        "timestamp_fields": ["CreatedAt", "UpdatedAt", "DeployedAt"],
        "description": "Agent 관리 테이블"
    },
    "agentic-ai-dev-kb-management-dev": {
        "timestamp_fields": ["CreatedAt", "UpdatedAt"],
        "description": "Knowledge Base 관리 테이블"
    },
    "agentic-ai-dev-kb-versions-dev": {
        "timestamp_fields": ["created_at", "sync_started_at", "sync_completed_at"],
        "description": "KB 버전 테이블"
    },
    "agentic-ai-dev-playground-conversations-dev": {
        "timestamp_fields": ["CreatedAt", "UpdatedAt"],
        "description": "Playground 대화 테이블"
    },
    "agentic-ai-dev-playground-management-dev": {
        "timestamp_fields": ["CreatedAt", "UpdatedAt", "ExpiresAt", "Timestamp"],
        "description": "Playground 관리 테이블"
    },
    "agentic-ai-dev-team-tag-management-dev": {
        "timestamp_fields": ["CreatedAt", "SyncedAt"],
        "description": "팀 태그 관리 테이블"
    },
    "agentic-ai-dev-mcp": {
        "timestamp_fields": ["created_at", "updated_at"],
        "description": "MCP 테이블"
    },
    "agentic-ai-dev-mcp-versions": {
        "timestamp_fields": ["created_at"],
        "description": "MCP 버전 테이블"
    }
}


def parse_iso_to_timestamp(iso_string: str) -> int:
    """ISO 문자열을 Unix timestamp로 변환"""
    if not iso_string:
        return None

    # Z를 +00:00으로 변환
    iso_string = iso_string.replace('Z', '+00:00')

    # timezone 정보가 없으면 추가
    if '+' not in iso_string and '-' not in iso_string[-6:]:
        iso_string = iso_string + '+00:00'

    try:
        dt = datetime.fromisoformat(iso_string)
        return int(dt.timestamp())
    except ValueError:
        # 마이크로초 없는 형식 처리
        try:
            dt = datetime.strptime(iso_string[:19], '%Y-%m-%dT%H:%M:%S')
            dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            print(f"  ⚠️  Cannot parse: {iso_string}")
            return None


def is_iso_string(value) -> bool:
    """값이 ISO 문자열인지 확인"""
    if not isinstance(value, str):
        return False
    # ISO 문자열 패턴 확인 (YYYY-MM-DD로 시작)
    return len(value) >= 10 and value[4] == '-' and value[7] == '-'


def get_primary_key_schema(table):
    """테이블의 Primary Key 스키마 가져오기"""
    key_schema = table.key_schema
    key_names = {}
    for key in key_schema:
        key_names[key['KeyType']] = key['AttributeName']
    return key_names


def migrate_table(dynamodb, table_name: str, config: dict, dry_run: bool = True):
    """단일 테이블 마이그레이션"""
    print(f"\n{'='*60}")
    print(f"테이블: {table_name}")
    print(f"설명: {config['description']}")
    print(f"대상 필드: {', '.join(config['timestamp_fields'])}")
    print(f"{'='*60}")

    table = dynamodb.Table(table_name)

    # Primary Key 스키마 가져오기
    pk_schema = get_primary_key_schema(table)
    pk_name = pk_schema.get('HASH')
    sk_name = pk_schema.get('RANGE')

    print(f"Primary Key: {pk_name}" + (f", Sort Key: {sk_name}" if sk_name else ""))

    # 전체 스캔
    scan_kwargs = {}
    items_scanned = 0
    items_updated = 0
    items_skipped = 0

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])

        for item in items:
            items_scanned += 1
            updates_needed = {}

            # timestamp 필드 확인
            for field in config['timestamp_fields']:
                if field in item:
                    value = item[field]
                    if is_iso_string(value):
                        new_value = parse_iso_to_timestamp(value)
                        if new_value is not None:
                            updates_needed[field] = new_value

            if updates_needed:
                # Primary Key 추출
                key = {pk_name: item[pk_name]}
                if sk_name and sk_name in item:
                    key[sk_name] = item[sk_name]

                if dry_run:
                    print(f"  [DRY RUN] Item {key}:")
                    for field, new_value in updates_needed.items():
                        print(f"    {field}: {item[field]} -> {new_value}")
                else:
                    # 실제 업데이트 수행
                    update_expression_parts = []
                    expression_attribute_names = {}
                    expression_attribute_values = {}

                    for i, (field, new_value) in enumerate(updates_needed.items()):
                        placeholder_name = f"#f{i}"
                        placeholder_value = f":v{i}"
                        update_expression_parts.append(f"{placeholder_name} = {placeholder_value}")
                        expression_attribute_names[placeholder_name] = field
                        expression_attribute_values[placeholder_value] = new_value

                    update_expression = "SET " + ", ".join(update_expression_parts)

                    try:
                        table.update_item(
                            Key=key,
                            UpdateExpression=update_expression,
                            ExpressionAttributeNames=expression_attribute_names,
                            ExpressionAttributeValues=expression_attribute_values
                        )
                        print(f"  ✅ Updated {key}: {list(updates_needed.keys())}")
                        items_updated += 1
                    except Exception as e:
                        print(f"  ❌ Failed to update {key}: {e}")
            else:
                items_skipped += 1

        # 페이지네이션
        if 'LastEvaluatedKey' in response:
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        else:
            break

    print(f"\n📊 결과:")
    print(f"   스캔된 아이템: {items_scanned}")
    print(f"   업데이트 {'예정' if dry_run else '완료'}: {items_updated}")
    print(f"   건너뜀 (이미 timestamp): {items_skipped}")


def main():
    parser = argparse.ArgumentParser(description='DynamoDB Timestamp Migration Script')
    parser.add_argument('--dry-run', action='store_true', help='실제 업데이트 없이 확인만')
    parser.add_argument('--table', type=str, help='특정 테이블만 마이그레이션 (테이블 이름 일부)')
    parser.add_argument('--profile', type=str, default=os.environ.get('AWS_PROFILE', 'default'),
                        help='AWS 프로파일 (기본값: default)')
    parser.add_argument('--region', type=str, default=os.environ.get('AWS_REGION', 'us-east-1'),
                        help='AWS 리전 (기본값: us-east-1)')

    args = parser.parse_args()

    print("=" * 70)
    print("DynamoDB Timestamp Migration Script")
    print("=" * 70)
    print(f"AWS 프로파일: {args.profile}")
    print(f"AWS 리전: {args.region}")
    print(f"모드: {'DRY RUN (확인만)' if args.dry_run else '실제 마이그레이션'}")

    if not args.dry_run:
        confirm = input("\n⚠️  실제 데이터를 수정합니다. 계속하시겠습니까? (yes/no): ")
        if confirm.lower() != 'yes':
            print("취소되었습니다.")
            sys.exit(0)

    # DynamoDB 연결
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    dynamodb = session.resource('dynamodb')

    # 마이그레이션 실행
    for table_name, config in MIGRATION_CONFIG.items():
        # 특정 테이블 필터링
        if args.table and args.table not in table_name:
            continue

        try:
            migrate_table(dynamodb, table_name, config, dry_run=args.dry_run)
        except Exception as e:
            print(f"\n❌ 테이블 {table_name} 마이그레이션 실패: {e}")
            continue

    print("\n" + "=" * 70)
    print("마이그레이션 완료!")
    print("=" * 70)


if __name__ == "__main__":
    main()
