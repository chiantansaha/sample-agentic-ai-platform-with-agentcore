"""Mock Data for Demo Mode

DynamoDB 미설정 시 데모용 mock 데이터를 제공합니다.
"""
from datetime import datetime
from typing import List, Dict, Any

# Current timestamp for mock data (seconds, not milliseconds)
MOCK_TIMESTAMP = int(datetime.now().timestamp())


# =============================================================================
# MCP Mock Data
# =============================================================================
MOCK_MCPS: List[Dict[str, Any]] = [
    {
        "id": "mcp-001",
        "name": "git-repo-research-mcp",
        "description": "Git 레포지토리를 분석하고 코드 구조, 커밋 히스토리, 브랜치 정보 등을 조사하는 MCP 서버입니다.",
        "type": "external",
        "sub_type": "endpoint",
        "status": "enabled",
        "version": "v2",
        "endpoint": "https://git-repo-research-mcp-gateway-prod-x7k2m9pqrs.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
        "endpoint_url": "https://api.github.com",
        "auth_type": "oauth",
        "team_tag_ids": [],
        "tool_list": [
            {
                "name": "analyze_repository",
                "description": "Analyze repository structure and code patterns",
                "input_schema": {"type": "object", "properties": {"repo_url": {"type": "string"}, "branch": {"type": "string"}}},
            },
            {
                "name": "get_commit_history",
                "description": "Get commit history with detailed analysis",
                "input_schema": {"type": "object", "properties": {"repo": {"type": "string"}, "limit": {"type": "integer"}}},
            },
            {
                "name": "search_code",
                "description": "Search code across repository files",
                "input_schema": {"type": "object", "properties": {"repo": {"type": "string"}, "query": {"type": "string"}}},
            },
            {
                "name": "list_branches",
                "description": "List all branches in a repository",
                "input_schema": {"type": "object", "properties": {"repo": {"type": "string"}}},
            },
            {
                "name": "get_file_content",
                "description": "Get content of a specific file",
                "input_schema": {"type": "object", "properties": {"repo": {"type": "string"}, "path": {"type": "string"}, "branch": {"type": "string"}}},
            },
            {
                "name": "compare_branches",
                "description": "Compare two branches and show differences",
                "input_schema": {"type": "object", "properties": {"repo": {"type": "string"}, "base": {"type": "string"}, "head": {"type": "string"}}},
            },
            {
                "name": "get_contributors",
                "description": "Get list of repository contributors",
                "input_schema": {"type": "object", "properties": {"repo": {"type": "string"}}},
            },
        ],
        "created_at": MOCK_TIMESTAMP - 86400 * 7,  # 7 days ago
        "updated_at": MOCK_TIMESTAMP - 86400 * 2,  # 2 days ago
    },
    {
        "id": "mcp-002",
        "name": "mysql-mcp",
        "description": "MySQL 데이터베이스에 연결하여 쿼리 실행, 스키마 조회, 데이터 관리를 수행하는 MCP 서버입니다.",
        "type": "external",
        "sub_type": "endpoint",
        "status": "enabled",
        "version": "v3",
        "endpoint": "https://mysql-mcp-gateway-prod-a3b5c7d9ef.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
        "endpoint_url": "mysql://localhost:3306",
        "auth_type": "no_auth",
        "team_tag_ids": [],
        "tool_list": [
            {
                "name": "execute_query",
                "description": "Execute a SQL query on MySQL database",
                "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "database": {"type": "string"}}},
            },
            {
                "name": "list_databases",
                "description": "List all databases on the server",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "list_tables",
                "description": "List all tables in a database",
                "input_schema": {"type": "object", "properties": {"database": {"type": "string"}}},
            },
            {
                "name": "describe_table",
                "description": "Get table schema and column information",
                "input_schema": {"type": "object", "properties": {"database": {"type": "string"}, "table": {"type": "string"}}},
            },
            {
                "name": "get_table_indexes",
                "description": "Get indexes defined on a table",
                "input_schema": {"type": "object", "properties": {"database": {"type": "string"}, "table": {"type": "string"}}},
            },
            {
                "name": "explain_query",
                "description": "Get execution plan for a query",
                "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "database": {"type": "string"}}},
            },
            {
                "name": "get_table_stats",
                "description": "Get table statistics and row count",
                "input_schema": {"type": "object", "properties": {"database": {"type": "string"}, "table": {"type": "string"}}},
            },
            {
                "name": "backup_table",
                "description": "Create a backup of a table",
                "input_schema": {"type": "object", "properties": {"database": {"type": "string"}, "table": {"type": "string"}, "destination": {"type": "string"}}},
            },
        ],
        "created_at": MOCK_TIMESTAMP - 86400 * 14,  # 14 days ago
        "updated_at": MOCK_TIMESTAMP - 86400 * 1,  # 1 day ago
    },
    {
        "id": "mcp-003",
        "name": "dataprocessing-mcp",
        "description": "데이터 변환, ETL 파이프라인 실행, 데이터 정제 및 분석 작업을 수행하는 MCP 서버입니다.",
        "type": "external",
        "sub_type": "endpoint",
        "status": "enabled",
        "version": "v1",
        "endpoint": "https://dataprocessing-mcp-gateway-prod-h8j2k4l6mn.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
        "endpoint_url": "https://dataprocessing.internal.example.com",
        "auth_type": "no_auth",
        "team_tag_ids": [],
        "tool_list": [
            {
                "name": "transform_data",
                "description": "Transform data using specified operations",
                "input_schema": {"type": "object", "properties": {"source": {"type": "string"}, "transformations": {"type": "array"}}},
            },
            {
                "name": "run_etl_job",
                "description": "Run an ETL pipeline job",
                "input_schema": {"type": "object", "properties": {"job_id": {"type": "string"}, "parameters": {"type": "object"}}},
            },
            {
                "name": "validate_data",
                "description": "Validate data against schema",
                "input_schema": {"type": "object", "properties": {"data": {"type": "object"}, "schema": {"type": "object"}}},
            },
            {
                "name": "aggregate_data",
                "description": "Aggregate data with grouping and metrics",
                "input_schema": {"type": "object", "properties": {"source": {"type": "string"}, "group_by": {"type": "array"}, "metrics": {"type": "array"}}},
            },
            {
                "name": "filter_data",
                "description": "Filter data based on conditions",
                "input_schema": {"type": "object", "properties": {"source": {"type": "string"}, "conditions": {"type": "array"}}},
            },
            {
                "name": "join_datasets",
                "description": "Join multiple datasets together",
                "input_schema": {"type": "object", "properties": {"left": {"type": "string"}, "right": {"type": "string"}, "join_key": {"type": "string"}}},
            },
        ],
        "created_at": MOCK_TIMESTAMP - 86400 * 30,  # 30 days ago
        "updated_at": MOCK_TIMESTAMP - 86400 * 5,  # 5 days ago
    },
    {
        "id": "mcp-004",
        "name": "eks-mcp",
        "description": "Amazon EKS 클러스터를 관리하고 Pod, Service, Deployment 등 Kubernetes 리소스를 조회/관리하는 MCP 서버입니다.",
        "type": "internal-deploy",
        "status": "enabled",
        "version": "v2",
        "endpoint": "https://eks-mcp-gateway-prod-p1q3r5s7tu.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
        "ecr_repository": "agentic-ai/eks-mcp",
        "image_tag": "v2",
        "team_tag_ids": [],
        "tool_list": [
            {
                "name": "list_clusters",
                "description": "List all EKS clusters in a region",
                "input_schema": {"type": "object", "properties": {"region": {"type": "string"}}},
            },
            {
                "name": "get_cluster_info",
                "description": "Get detailed cluster information",
                "input_schema": {"type": "object", "properties": {"cluster": {"type": "string"}}},
            },
            {
                "name": "list_namespaces",
                "description": "List all namespaces in a cluster",
                "input_schema": {"type": "object", "properties": {"cluster": {"type": "string"}}},
            },
            {
                "name": "get_pods",
                "description": "Get pods in a namespace",
                "input_schema": {"type": "object", "properties": {"cluster": {"type": "string"}, "namespace": {"type": "string"}}},
            },
            {
                "name": "get_pod_logs",
                "description": "Get logs from a specific pod",
                "input_schema": {"type": "object", "properties": {"cluster": {"type": "string"}, "namespace": {"type": "string"}, "pod": {"type": "string"}, "lines": {"type": "integer"}}},
            },
            {
                "name": "describe_deployment",
                "description": "Describe a Kubernetes deployment",
                "input_schema": {"type": "object", "properties": {"cluster": {"type": "string"}, "namespace": {"type": "string"}, "deployment": {"type": "string"}}},
            },
            {
                "name": "list_services",
                "description": "List services in a namespace",
                "input_schema": {"type": "object", "properties": {"cluster": {"type": "string"}, "namespace": {"type": "string"}}},
            },
            {
                "name": "get_node_status",
                "description": "Get status of cluster nodes",
                "input_schema": {"type": "object", "properties": {"cluster": {"type": "string"}}},
            },
            {
                "name": "scale_deployment",
                "description": "Scale a deployment to specified replicas",
                "input_schema": {"type": "object", "properties": {"cluster": {"type": "string"}, "namespace": {"type": "string"}, "deployment": {"type": "string"}, "replicas": {"type": "integer"}}},
            },
        ],
        "created_at": MOCK_TIMESTAMP - 86400 * 21,  # 21 days ago
        "updated_at": MOCK_TIMESTAMP - 86400 * 3,  # 3 days ago
    },
    {
        "id": "mcp-005",
        "name": "cloudwatch-appsignals-mcp",
        "description": "Amazon CloudWatch Application Signals를 통해 애플리케이션 성능 모니터링, 트레이스 분석, 메트릭 조회를 수행하는 MCP 서버입니다.",
        "type": "internal-deploy",
        "status": "disabled",
        "version": "v1",
        "endpoint": "https://cloudwatch-appsignals-mcp-gateway-prod-v2w4x6y8za.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
        "ecr_repository": "agentic-ai/cloudwatch-appsignals-mcp",
        "image_tag": "v1",
        "team_tag_ids": [],
        "tool_list": [
            {
                "name": "get_service_metrics",
                "description": "Get application performance metrics",
                "input_schema": {"type": "object", "properties": {"service_name": {"type": "string"}, "time_range": {"type": "string"}}},
            },
            {
                "name": "list_services",
                "description": "List all monitored services",
                "input_schema": {"type": "object", "properties": {"environment": {"type": "string"}}},
            },
            {
                "name": "list_traces",
                "description": "List distributed traces for a service",
                "input_schema": {"type": "object", "properties": {"service_name": {"type": "string"}, "filter": {"type": "object"}}},
            },
            {
                "name": "get_trace_details",
                "description": "Get detailed trace information",
                "input_schema": {"type": "object", "properties": {"trace_id": {"type": "string"}}},
            },
            {
                "name": "get_slo_status",
                "description": "Get SLO status and compliance",
                "input_schema": {"type": "object", "properties": {"slo_id": {"type": "string"}}},
            },
            {
                "name": "list_slos",
                "description": "List all defined SLOs",
                "input_schema": {"type": "object", "properties": {"service_name": {"type": "string"}}},
            },
            {
                "name": "get_error_rate",
                "description": "Get error rate metrics for a service",
                "input_schema": {"type": "object", "properties": {"service_name": {"type": "string"}, "time_range": {"type": "string"}}},
            },
            {
                "name": "get_latency_percentiles",
                "description": "Get latency percentile metrics (p50, p90, p99)",
                "input_schema": {"type": "object", "properties": {"service_name": {"type": "string"}, "operation": {"type": "string"}, "time_range": {"type": "string"}}},
            },
            {
                "name": "create_alarm",
                "description": "Create a CloudWatch alarm for a metric",
                "input_schema": {"type": "object", "properties": {"service_name": {"type": "string"}, "metric": {"type": "string"}, "threshold": {"type": "number"}}},
            },
            {
                "name": "get_service_map",
                "description": "Get service dependency map",
                "input_schema": {"type": "object", "properties": {"service_name": {"type": "string"}}},
            },
        ],
        "created_at": MOCK_TIMESTAMP - 86400 * 10,  # 10 days ago
        "updated_at": MOCK_TIMESTAMP - 86400 * 10,  # 10 days ago
    },
]


# =============================================================================
# Agent Mock Data
# =============================================================================
MOCK_AGENTS: List[Dict[str, Any]] = [
    {
        "id": "agent-001",
        "name": "DevOps Assistant",
        "description": "CI/CD 파이프라인 관리, 인프라 모니터링, 배포 자동화를 지원하는 AI 에이전트입니다.",
        "llm_model": {
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "model_name": "Claude 3 Sonnet",
            "provider": "Anthropic"
        },
        "instruction": {
            "system_prompt": "You are a DevOps assistant that helps with CI/CD pipelines, infrastructure monitoring, and deployment automation.",
            "temperature": 0.7,
            "max_tokens": 4096
        },
        "knowledge_bases": ["kb-001"],
        "mcps": ["mcp-001", "mcp-004"],
        "status": "enabled",
        "current_version": "1.0.0",
        "team_tags": [],
        "created_at": MOCK_TIMESTAMP - 86400 * 14,
        "updated_at": MOCK_TIMESTAMP - 86400 * 2,
        "created_by": "demo-user",
        "updated_by": "demo-user"
    },
    {
        "id": "agent-002",
        "name": "Customer Support Bot",
        "description": "고객 문의 응대, FAQ 검색, 티켓 생성 등을 자동화하는 고객 지원 에이전트입니다.",
        "llm_model": {
            "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
            "model_name": "Claude 3 Haiku",
            "provider": "Anthropic"
        },
        "instruction": {
            "system_prompt": "You are a friendly customer support agent. Help customers with their inquiries and create support tickets when needed.",
            "temperature": 0.5,
            "max_tokens": 2048
        },
        "knowledge_bases": ["kb-002"],
        "mcps": ["mcp-002", "mcp-003"],
        "status": "enabled",
        "current_version": "2.1.0",
        "team_tags": [],
        "created_at": MOCK_TIMESTAMP - 86400 * 30,
        "updated_at": MOCK_TIMESTAMP - 86400 * 1,
        "created_by": "demo-user",
        "updated_by": "demo-user"
    },
    {
        "id": "agent-003",
        "name": "Code Review Assistant",
        "description": "코드 리뷰, 버그 탐지, 코딩 표준 검사를 수행하는 개발 지원 에이전트입니다.",
        "llm_model": {
            "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "model_name": "Claude 3.5 Sonnet v2",
            "provider": "Anthropic"
        },
        "instruction": {
            "system_prompt": "You are an expert code reviewer. Analyze code for bugs, security issues, and adherence to best practices.",
            "temperature": 0.3,
            "max_tokens": 8192
        },
        "knowledge_bases": [],
        "mcps": ["mcp-001"],
        "status": "enabled",
        "current_version": "1.5.0",
        "team_tags": [],
        "created_at": MOCK_TIMESTAMP - 86400 * 7,
        "updated_at": MOCK_TIMESTAMP - 86400 * 7,
        "created_by": "demo-user",
        "updated_by": "demo-user"
    },
    {
        "id": "agent-004",
        "name": "Data Analyst",
        "description": "데이터 분석, 리포트 생성, 인사이트 도출을 수행하는 분석 에이전트입니다.",
        "llm_model": {
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "model_name": "Claude 3 Sonnet",
            "provider": "Anthropic"
        },
        "instruction": {
            "system_prompt": "You are a data analyst assistant. Help users analyze data, generate reports, and derive insights.",
            "temperature": 0.4,
            "max_tokens": 4096
        },
        "knowledge_bases": ["kb-003"],
        "mcps": ["mcp-005"],
        "status": "disabled",
        "current_version": "0.8.0",
        "team_tags": [],
        "created_at": MOCK_TIMESTAMP - 86400 * 5,
        "updated_at": MOCK_TIMESTAMP - 86400 * 5,
        "created_by": "demo-user",
        "updated_by": "demo-user"
    },
]


# =============================================================================
# Knowledge Base Mock Data
# =============================================================================
MOCK_KNOWLEDGE_BASES: List[Dict[str, Any]] = [
    {
        "id": "kb-001",
        "name": "DevOps Documentation",
        "description": "CI/CD, 쿠버네티스, AWS 인프라 관련 내부 문서 모음입니다.",
        "status": "ready",
        "current_version": "1.0.0",
        "bedrock_kb_id": "MOCK-KB-001",
        "data_source_id": "MOCK-DS-001",
        "team_tags": [],
        "file_count": 45,
        "total_size_bytes": 15728640,  # 15 MB
        "created_at": MOCK_TIMESTAMP - 86400 * 30,
        "updated_at": MOCK_TIMESTAMP - 86400 * 3,
        "created_by": "demo-user",
        "updated_by": "demo-user"
    },
    {
        "id": "kb-002",
        "name": "Customer Support FAQ",
        "description": "고객 지원 FAQ, 제품 매뉴얼, 문제 해결 가이드를 포함합니다.",
        "status": "ready",
        "current_version": "2.0.0",
        "bedrock_kb_id": "MOCK-KB-002",
        "data_source_id": "MOCK-DS-002",
        "team_tags": [],
        "file_count": 128,
        "total_size_bytes": 52428800,  # 50 MB
        "created_at": MOCK_TIMESTAMP - 86400 * 60,
        "updated_at": MOCK_TIMESTAMP - 86400 * 1,
        "created_by": "demo-user",
        "updated_by": "demo-user"
    },
    {
        "id": "kb-003",
        "name": "Analytics Reports Archive",
        "description": "과거 분석 리포트 및 데이터 분석 방법론 문서입니다.",
        "status": "syncing",
        "current_version": "0.5.0",
        "bedrock_kb_id": "MOCK-KB-003",
        "data_source_id": "MOCK-DS-003",
        "team_tags": [],
        "file_count": 23,
        "total_size_bytes": 8388608,  # 8 MB
        "created_at": MOCK_TIMESTAMP - 86400 * 14,
        "updated_at": MOCK_TIMESTAMP - 86400 * 0,  # today
        "created_by": "demo-user",
        "updated_by": "demo-user"
    },
    {
        "id": "kb-004",
        "name": "API Documentation",
        "description": "내부 API 문서 및 통합 가이드입니다.",
        "status": "failed",
        "current_version": "1.0.0",
        "bedrock_kb_id": None,
        "data_source_id": None,
        "team_tags": [],
        "file_count": 0,
        "total_size_bytes": 0,
        "error_message": "Failed to create Bedrock Knowledge Base: Access Denied",
        "created_at": MOCK_TIMESTAMP - 86400 * 2,
        "updated_at": MOCK_TIMESTAMP - 86400 * 2,
        "created_by": "demo-user",
        "updated_by": "demo-user"
    },
]


# =============================================================================
# Dashboard Stats (computed from mock data)
# =============================================================================
def get_mock_mcp_stats() -> Dict[str, int]:
    """MCP 통계 계산"""
    total = len(MOCK_MCPS)
    enabled = sum(1 for m in MOCK_MCPS if m["status"] == "enabled")
    return {
        "total": total,
        "enabled": enabled,
        "disabled": total - enabled,
        "healthy": enabled,  # Assume all enabled are healthy for demo
        "unhealthy": 0
    }


def get_mock_agent_stats() -> Dict[str, int]:
    """Agent 통계 계산"""
    total = len(MOCK_AGENTS)
    enabled = sum(1 for a in MOCK_AGENTS if a["status"] == "enabled")
    return {
        "total": total,
        "enabled": enabled,
        "disabled": total - enabled,
        "healthy": enabled,
        "unhealthy": 0
    }


def get_mock_kb_stats() -> Dict[str, int]:
    """Knowledge Base 통계 계산"""
    total = len(MOCK_KNOWLEDGE_BASES)
    ready = sum(1 for kb in MOCK_KNOWLEDGE_BASES if kb["status"] == "ready")
    syncing = sum(1 for kb in MOCK_KNOWLEDGE_BASES if kb["status"] == "syncing")
    failed = sum(1 for kb in MOCK_KNOWLEDGE_BASES if kb["status"] == "failed")
    return {
        "total": total,
        "enabled": ready,  # 'ready' is considered enabled
        "disabled": failed,
        "healthy": ready + syncing,
        "unhealthy": failed
    }
