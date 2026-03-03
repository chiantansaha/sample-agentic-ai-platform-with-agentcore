# Multi-MCP Proxy - FastMCP based proxy for multiple MCP servers
#
# Environment Variables:
#   - MCP_SERVERS_CONFIG: JSON string or path to config file
#   - MCP_CONFIG_DYNAMODB_TABLE: DynamoDB table name (alternative)
#   - MCP_CONFIG_AWS_REGION: AWS region for DynamoDB
#
# Build: docker build --platform linux/arm64 -t mcp-proxy .

FROM python:3.11-slim

# Disable Python output buffering for proper logging
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install Node.js for npx/CLI tools
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pre-install common MCP CLI tools
RUN npm install -g @smithery/cli

# Install uv for Python-based MCP servers (uvx)
RUN pip install --no-cache-dir uv

WORKDIR /app

COPY proxy_server.py .

RUN pip install --no-cache-dir mcp uvicorn boto3

EXPOSE 8000

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 appuser \
    && chown -R appuser:appgroup /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "proxy_server.py"]
