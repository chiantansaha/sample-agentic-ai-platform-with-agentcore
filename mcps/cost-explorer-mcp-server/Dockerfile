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

# dependabot should continue to update this to the latest hash.
FROM public.ecr.aws/amazonlinux/amazonlinux@sha256:e27a70c006c68f0d194cc9b9624714d6ed8d979a94f60f7d31392f4c8294155b AS uv

# Install build dependencies needed for compiling packages
RUN dnf install -y shadow-utils python3 python3-devel gcc && \
    dnf clean all

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Prefer the system python
ENV UV_PYTHON_PREFERENCE=only-managed

# Run without updating the uv.lock file like running with `--frozen`
ENV UV_FROZEN=true

# Copy the required files first
COPY pyproject.toml uv.lock uv-requirements.txt ./

# Python optimization and uv configuration
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    python3 -m ensurepip && \
    python3 -m pip install --require-hashes --requirement uv-requirements.txt --no-cache-dir && \
    uv sync --python 3.13 --frozen --no-install-project --no-dev --no-editable

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --python 3.13 --frozen --no-dev --no-editable

# Make the directory just in case it doesn't exist
RUN mkdir -p /root/.local

FROM public.ecr.aws/amazonlinux/amazonlinux@sha256:e27a70c006c68f0d194cc9b9624714d6ed8d979a94f60f7d31392f4c8294155b

# Place executables in the environment at the front of the path and include other binaries
# Set streamable-http transport mode for AgentCore Runtime compatibility
# AWS_REGION is required for boto3 clients - default to us-east-1, can be overridden at runtime
# OpenTelemetry (ADOT) configuration for AgentCore observability
ENV PATH="/app/.venv/bin:$PATH:/usr/sbin" \
    PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=streamable-http \
    FASTMCP_HOST=0.0.0.0 \
    FASTMCP_PORT=8000 \
    AWS_REGION=us-east-1 \
    AWS_DEFAULT_REGION=us-east-1 \
    # ADOT (AWS Distro for OpenTelemetry) configuration
    AGENT_OBSERVABILITY_ENABLED=true \
    OTEL_PYTHON_DISTRO=aws_distro \
    OTEL_PYTHON_CONFIGURATOR=aws_configurator \
    OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
    OTEL_TRACES_EXPORTER=otlp

# Install other tools as needed for the MCP server
# Add non-root user and ability to change directory into /root
RUN dnf install -y shadow-utils procps && \
    dnf clean all && \
    groupadd --force --system app && \
    useradd app -g app -d /app && \
    chmod o+x /root

# Get the project from the uv layer
COPY --from=uv --chown=app:app /root/.local /root/.local
COPY --from=uv --chown=app:app /app/.venv /app/.venv

# Get healthcheck script
COPY ./docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh

# Run as non-root
USER app

# Expose SSE server port (FastMCP default)
EXPOSE 8000

# HTTP healthcheck for streamable-http mode
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -sf http://localhost:8000/mcp || exit 1

# Use opentelemetry-instrument for auto-instrumentation with ADOT
ENTRYPOINT ["opentelemetry-instrument", "awslabs.cost-explorer-mcp-server"]
