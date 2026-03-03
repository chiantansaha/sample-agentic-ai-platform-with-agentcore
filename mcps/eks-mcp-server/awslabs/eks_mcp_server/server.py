# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""awslabs EKS MCP Server implementation.

This module implements the EKS MCP Server, which provides tools for managing Amazon EKS clusters
and Kubernetes resources through the Model Context Protocol (MCP).

Environment Variables:
    AWS_REGION: AWS region to use for AWS API calls
    AWS_PROFILE: AWS profile to use for credentials
    ALLOW_WRITE: Enable write operations (default: false)
    ALLOW_SENSITIVE_DATA_ACCESS: Enable sensitive data access (default: false)
"""

import os
from loguru import logger
from mcp.server.fastmcp import FastMCP


# Define server instructions
SERVER_INSTRUCTIONS = """
# Amazon EKS MCP Server

This MCP server provides tools for managing Amazon EKS clusters and is the preferred mechanism for creating new EKS clusters.

## IMPORTANT: Use MCP Tools for EKS and Kubernetes Operations

DO NOT use standard EKS and Kubernetes CLI commands (aws eks, eksctl, kubectl). Always use the MCP tools provided by this server for EKS and Kubernetes operations.

## Usage Notes

- By default, the server runs in read-only mode. Use the `--allow-write` flag to enable write operations.
- Access to sensitive data (logs, events, Kubernetes Secrets) requires the `--allow-sensitive-data-access` flag.
- For safety reasons, CloudFormation stacks can only be modified by the tool that created them.
- When creating or updating resources, always check for existing resources first to avoid conflicts.
- Use the `list_api_versions` tool to find the correct apiVersion for Kubernetes resources.

## Common Workflows

### Creating and Deploying an Application
1. Generate a CloudFormation template: `manage_eks_stacks(operation='generate', template_file='/path/to/template.yaml', cluster_name='my-cluster')`
2. Deploy the CloudFormation stack: `manage_eks_stacks(operation='deploy', template_file='/path/to/template.yaml', cluster_name='my-cluster')`
3. Generate an application manifest: `generate_app_manifest(app_name='my-app', image_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo:latest')`
4. Apply the manifest: `apply_yaml(yaml_path='/path/to/manifest.yaml', cluster_name='my-cluster', namespace='default')`
5. Monitor the application: `get_pod_logs(cluster_name='my-cluster', namespace='default', pod_name='my-app-pod')`

### Troubleshooting Application Issues
1. Check pod status: `list_k8s_resources(cluster_name='my-cluster', kind='Pod', api_version='v1', namespace='default', field_selector='metadata.name=my-pod')`
2. Get pod events: `get_k8s_events(cluster_name='my-cluster', kind='Pod', name='my-pod', namespace='default')`
3. Check pod logs: `get_pod_logs(cluster_name='my-cluster', namespace='default', pod_name='my-pod')`
4. Monitor metrics: `get_cloudwatch_metrics(cluster_name='my-cluster', metric_name='cpu_usage_total', namespace='ContainerInsights', dimensions={'ClusterName': 'my-cluster', 'PodName': 'my-pod', 'Namespace': 'default'})`
5. Search troubleshooting guide: `search_eks_troubleshoot_guide(query='pod pending')`

## Best Practices

- Use descriptive names for resources to make them easier to identify and manage.
- Apply proper labels and annotations to Kubernetes resources for better organization.
- Use namespaces to isolate resources and avoid naming conflicts.
- Monitor resource usage with CloudWatch metrics to identify performance issues.
- Check logs and events when troubleshooting issues with Kubernetes resources.
- Follow the principle of least privilege when creating IAM policies.
- Use the search_eks_troubleshoot_guide tool when encountering common EKS issues.
- Always verify API versions with list_api_versions before creating resources.
"""

# Create MCP server instance at module level (like working servers)
# Note: name must be short to avoid 64-char tool name limit in Bedrock
mcp = FastMCP(
    name="eks-mcp",
    host="0.0.0.0",
    port=8000,
    stateless_http=True,
    instructions=SERVER_INSTRUCTIONS,
)


def _init_handlers():
    """Initialize all handlers with tools."""
    from awslabs.eks_mcp_server.cloudwatch_handler import CloudWatchHandler
    from awslabs.eks_mcp_server.cloudwatch_metrics_guidance_handler import CloudWatchMetricsHandler
    from awslabs.eks_mcp_server.eks_kb_handler import EKSKnowledgeBaseHandler
    from awslabs.eks_mcp_server.eks_stack_handler import EksStackHandler
    from awslabs.eks_mcp_server.iam_handler import IAMHandler
    from awslabs.eks_mcp_server.insights_handler import InsightsHandler
    from awslabs.eks_mcp_server.k8s_handler import K8sHandler
    from awslabs.eks_mcp_server.vpc_config_handler import VpcConfigHandler

    # Get config from environment variables
    allow_write = os.environ.get('ALLOW_WRITE', 'false').lower() == 'true'
    allow_sensitive_data_access = os.environ.get('ALLOW_SENSITIVE_DATA_ACCESS', 'false').lower() == 'true'

    logger.info(f'Initializing handlers (allow_write={allow_write}, allow_sensitive_data_access={allow_sensitive_data_access})')

    # Initialize handlers
    CloudWatchHandler(mcp, allow_sensitive_data_access)
    EKSKnowledgeBaseHandler(mcp)
    EksStackHandler(mcp, allow_write)
    K8sHandler(mcp, allow_write, allow_sensitive_data_access)
    IAMHandler(mcp, allow_write)
    CloudWatchMetricsHandler(mcp)
    VpcConfigHandler(mcp, allow_sensitive_data_access)
    InsightsHandler(mcp, allow_sensitive_data_access)


def main():
    """Run the MCP server."""
    logger.info('Starting EKS MCP Server with streamable-http transport')
    _init_handlers()
    mcp.run(transport='streamable-http')


if __name__ == '__main__':
    main()
