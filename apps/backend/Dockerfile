FROM python:3.11-slim

WORKDIR /app

# Environment mode (development/production)
ARG ENV_MODE=development
ENV ENV_MODE=$ENV_MODE

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Verify mcp-proxy-for-aws installation
RUN python -c "from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client; print('mcp-proxy-for-aws installed successfully')"

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 appuser \
    && chown -R appuser:appgroup /app

USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
