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

"""Cost Explorer MCP server implementation.

This server provides tools for analyzing AWS costs and usage data through the AWS Cost Explorer API.

Note: This file uses wrapper functions to resolve Field() defaults properly.
The original handlers use Field() as default values which doesn't work with FastMCP's
direct function calls. Wrappers use Annotated types with proper Python defaults.
"""

import os
import sys
from typing import Annotated, Any, Dict, Optional, Union

from awslabs.cost_explorer_mcp_server.comparison_handler import (
    get_cost_and_usage_comparisons as _get_cost_and_usage_comparisons,
    get_cost_comparison_drivers as _get_cost_comparison_drivers,
)
from awslabs.cost_explorer_mcp_server.cost_usage_handler import get_cost_and_usage as _get_cost_and_usage
from awslabs.cost_explorer_mcp_server.forecasting_handler import get_cost_forecast as _get_cost_forecast
from awslabs.cost_explorer_mcp_server.metadata_handler import (
    get_dimension_values,
    get_tag_values,
)
from awslabs.cost_explorer_mcp_server.models import DateRange
from awslabs.cost_explorer_mcp_server.utility_handler import get_today_date
from awslabs.cost_explorer_mcp_server.constants import VALID_COST_METRICS, VALID_GRANULARITIES
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field


# Configure Loguru logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))


# =============================================================================
# Wrapper Functions
# =============================================================================
# These wrappers resolve Field() defaults that don't work with FastMCP's
# direct function invocation. Using Annotated[type, Field()] with proper defaults.

async def get_cost_and_usage(
    ctx: Context,
    date_range: DateRange,
    granularity: Annotated[str, Field(
        description=f'The granularity at which cost data is aggregated. Valid values are {", ".join(VALID_GRANULARITIES)}.'
    )] = 'MONTHLY',
    group_by: Annotated[Optional[Union[Dict[str, str], str]], Field(
        description="Either a dictionary with Type and Key for grouping costs, or simply a string key to group by. Example: 'SERVICE' or {'Type': 'DIMENSION', 'Key': 'SERVICE'}."
    )] = 'SERVICE',
    filter_expression: Annotated[Optional[Dict[str, Any]], Field(
        description="Filter criteria as a Python dictionary to narrow down AWS costs."
    )] = None,
    metric: Annotated[str, Field(
        description=f'The metric to return. Valid values are {", ".join(VALID_COST_METRICS)}.'
    )] = 'UnblendedCost',
) -> Dict[str, Any]:
    """Retrieve AWS cost and usage data."""
    return await _get_cost_and_usage(
        ctx=ctx,
        date_range=date_range,
        granularity=granularity,
        group_by=group_by,
        filter_expression=filter_expression,
        metric=metric,
    )


async def get_cost_and_usage_comparisons(
    ctx: Context,
    baseline_date_range: DateRange,
    comparison_date_range: DateRange,
    metric_for_comparison: Annotated[str, Field(
        description=f'The cost metric to compare. Valid values are {", ".join(VALID_COST_METRICS)}.'
    )] = 'UnblendedCost',
    group_by: Annotated[Optional[Union[Dict[str, str], str]], Field(
        description="Group by dimension. Example: 'SERVICE' or {'Type': 'DIMENSION', 'Key': 'SERVICE'}."
    )] = 'SERVICE',
    filter_expression: Annotated[Optional[Dict[str, Any]], Field(
        description="Filter criteria as a Python dictionary."
    )] = None,
) -> Dict[str, Any]:
    """Compare AWS costs between two time periods."""
    return await _get_cost_and_usage_comparisons(
        ctx=ctx,
        baseline_date_range=baseline_date_range,
        comparison_date_range=comparison_date_range,
        metric_for_comparison=metric_for_comparison,
        group_by=group_by,
        filter_expression=filter_expression,
    )


async def get_cost_comparison_drivers(
    ctx: Context,
    baseline_date_range: DateRange,
    comparison_date_range: DateRange,
    metric_for_comparison: Annotated[str, Field(
        description=f'The cost metric to analyze. Valid values are {", ".join(VALID_COST_METRICS)}.'
    )] = 'UnblendedCost',
    group_by: Annotated[Optional[Union[Dict[str, str], str]], Field(
        description="Group by dimension. Example: 'SERVICE' or {'Type': 'DIMENSION', 'Key': 'SERVICE'}."
    )] = 'SERVICE',
    filter_expression: Annotated[Optional[Dict[str, Any]], Field(
        description="Filter criteria as a Python dictionary."
    )] = None,
) -> Dict[str, Any]:
    """Analyze what drove cost changes between two periods. Returns top 10 drivers."""
    return await _get_cost_comparison_drivers(
        ctx=ctx,
        baseline_date_range=baseline_date_range,
        comparison_date_range=comparison_date_range,
        metric_for_comparison=metric_for_comparison,
        group_by=group_by,
        filter_expression=filter_expression,
    )


async def get_cost_forecast(
    ctx: Context,
    date_range: DateRange,
    granularity: Annotated[str, Field(
        description='Forecast granularity. Valid values are DAILY and MONTHLY.'
    )] = 'MONTHLY',
    filter_expression: Annotated[Optional[Dict[str, Any]], Field(
        description="Filter criteria as a Python dictionary."
    )] = None,
    metric: Annotated[str, Field(
        description='The metric to forecast. Valid values are UNBLENDED_COST, BLENDED_COST, AMORTIZED_COST, NET_UNBLENDED_COST, NET_AMORTIZED_COST.'
    )] = 'UNBLENDED_COST',
    prediction_interval_level: Annotated[int, Field(
        description='Prediction confidence interval (51-99). Default is 80.'
    )] = 80,
) -> Dict[str, Any]:
    """Get cost forecast for a future period."""
    return await _get_cost_forecast(
        ctx=ctx,
        date_range=date_range,
        granularity=granularity,
        filter_expression=filter_expression,
        metric=metric,
        prediction_interval_level=prediction_interval_level,
    )


# Define server instructions
SERVER_INSTRUCTIONS = """
# AWS Cost Explorer MCP Server

## IMPORTANT: Each API call costs $0.01 - use filters and specific date ranges to minimize charges.

## Critical Rules
- Comparison periods: exactly 1 month, start on day 1 (e.g., "2025-04-01" to "2025-05-01")
- UsageQuantity: Recommended to filter by USAGE_TYPE, USAGE_TYPE_GROUP or results are meaningless
- When user says "last X months": Use complete calendar months, not partial periods
- get_cost_comparison_drivers: returns only top 10 most significant drivers

## Query Pattern Mapping

| User Query Pattern | Recommended Tool | Notes |
|-------------------|-----------------|-------|
| "What were my costs for..." | get_cost_and_usage | Use for historical cost analysis |
| "How much did I spend on..." | get_cost_and_usage | Filter by service/region as needed |
| "Show me costs by..." | get_cost_and_usage | Set group_by parameter accordingly |
| "Compare costs between..." | get_cost_and_usage_comparisons | Ensure exactly 1 month periods |
| "Why did my costs change..." | get_cost_comparison_drivers | Returns top 10 drivers only |
| "What caused my bill to..." | get_cost_comparison_drivers | Good for root cause analysis |
| "Predict/forecast my costs..." | get_cost_forecast | Works best with specific services |
| "What will I spend on..." | get_cost_forecast | Can filter by dimension |

## Cost Optimization Tips
- Always use specific date ranges rather than broad periods
- Filter by specific services when possible to reduce data processed
- For usage metrics, always filter by USAGE_TYPE or USAGE_TYPE_GROUP to get meaningful results
- Combine related questions into a single query where possible
"""

# Create FastMCP server with instructions
# Configure for AgentCore Runtime with streamable-http transport
# Note: name must be short to avoid 64-char tool name limit in Bedrock
app = FastMCP(
    name='ce-mcp',
    instructions=SERVER_INSTRUCTIONS,
    host='0.0.0.0',
    port=8000,
    stateless_http=True,
)

# Register all tools with the app
# Note: Use app.tool()(func) pattern - the function name becomes the tool name
app.tool()(get_today_date)
app.tool()(get_dimension_values)
app.tool()(get_tag_values)
app.tool()(get_cost_forecast)
app.tool()(get_cost_and_usage_comparisons)
app.tool()(get_cost_comparison_drivers)
app.tool()(get_cost_and_usage)


def main():
    """Run the MCP server with streamable-http transport for AgentCore Runtime."""
    logger.info('Starting Cost Explorer MCP Server with streamable-http transport')
    app.run(transport='streamable-http')


if __name__ == '__main__':
    main()
