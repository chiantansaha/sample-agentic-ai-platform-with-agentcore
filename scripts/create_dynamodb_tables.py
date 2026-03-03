#!/usr/bin/env python3
"""Create DynamoDB tables for MCP Management"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend'))

from app.config import settings
from app.mcp.infrastructure.dynamodb_client import dynamodb_client


def create_mcp_table():
    """Create MCP main table"""
    table_name = f"{settings.table_name_prefix}-mcp"
    
    if dynamodb_client.table_exists(table_name):
        print(f"✅ Table {table_name} already exists")
        return
    
    table = dynamodb_client.client.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'team_tags',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'created_at',
                'AttributeType': 'S'
            }
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'team-tags-index',
                'KeySchema': [
                    {
                        'AttributeName': 'team_tags',
                        'KeyType': 'HASH'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            },
            {
                'IndexName': 'created-at-index',
                'KeySchema': [
                    {
                        'AttributeName': 'created_at',
                        'KeyType': 'HASH'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            }
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    print(f"🚀 Creating table {table_name}...")
    
    # Wait for table to be created
    waiter = dynamodb_client.client.get_waiter('table_exists')
    waiter.wait(TableName=table_name)
    
    print(f"✅ Table {table_name} created successfully")


def create_mcp_versions_table():
    """Create MCP versions table"""
    table_name = f"{settings.table_name_prefix}-mcp-versions"
    
    if dynamodb_client.table_exists(table_name):
        print(f"✅ Table {table_name} already exists")
        return
    
    table = dynamodb_client.client.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'mcp_id',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'version',
                'KeyType': 'RANGE'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'mcp_id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'version',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'created_at',
                'AttributeType': 'S'
            }
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'created-at-index',
                'KeySchema': [
                    {
                        'AttributeName': 'created_at',
                        'KeyType': 'HASH'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            }
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    print(f"🚀 Creating table {table_name}...")
    
    # Wait for table to be created
    waiter = dynamodb_client.client.get_waiter('table_exists')
    waiter.wait(TableName=table_name)
    
    print(f"✅ Table {table_name} created successfully")


def create_api_catalog_table():
    """Create API Catalog table"""
    table_name = f"{settings.table_name_prefix}-api-catalog"

    if dynamodb_client.table_exists(table_name):
        print(f"✅ Table {table_name} already exists")
        return

    table = dynamodb_client.client.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            }
        ],
        BillingMode='PAY_PER_REQUEST'
    )

    print(f"🚀 Creating table {table_name}...")

    # Wait for table to be created
    waiter = dynamodb_client.client.get_waiter('table_exists')
    waiter.wait(TableName=table_name)

    print(f"✅ Table {table_name} created successfully")


def create_mcp_proxy_config_table():
    """Create MCP Proxy Config table for External MCP servers

    This table stores MCP server configurations that the Multi-MCP Proxy
    Runtime reads on startup to spawn MCP server subprocesses.

    Schema:
    - id: Server name (used as tool prefix, e.g., "youtube")
    - mcp_id: Reference to MCP entity ID
    - command: Command to run (e.g., "npx")
    - args: Command arguments (e.g., ["-y", "@smithery/cli@latest", "run", "youtube", "--key", "xxx"])
    - env: Environment variables (optional)
    - enabled: Whether to spawn this server on startup
    """
    table_name = f"{settings.table_name_prefix}-{settings.MCP_PROXY_CONFIG_TABLE}"

    if dynamodb_client.table_exists(table_name):
        print(f"✅ Table {table_name} already exists")
        return

    table = dynamodb_client.client.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            }
        ],
        BillingMode='PAY_PER_REQUEST'
    )

    print(f"🚀 Creating table {table_name}...")

    # Wait for table to be created
    waiter = dynamodb_client.client.get_waiter('table_exists')
    waiter.wait(TableName=table_name)

    print(f"✅ Table {table_name} created successfully")


def main():
    """Create all DynamoDB tables"""
    print(f"🔧 Creating DynamoDB tables with prefix: {settings.table_name_prefix}")
    print(f"📍 Region: {settings.AWS_REGION}")

    try:
        create_mcp_table()
        create_mcp_versions_table()
        create_api_catalog_table()
        create_mcp_proxy_config_table()
        print("\n🎉 All tables created successfully!")

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
