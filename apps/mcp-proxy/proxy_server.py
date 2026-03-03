"""
Multi-MCP Proxy Server - FastMCP based proxy for multiple MCP servers

This server acts as a proxy between AWS AgentCore Runtime and multiple MCP servers.
It spawns multiple MCP server processes and exposes all their tools via a single FastMCP endpoint.

Environment Variables:
    MCP_SERVERS_CONFIG: JSON string or path to JSON file containing MCP server configurations
    MCP_CONFIG_DYNAMODB_TABLE: DynamoDB table name for config (alternative to MCP_SERVERS_CONFIG)
    MCP_CONFIG_AWS_REGION: AWS region for DynamoDB (default: us-east-1)

Configuration Format:
    {
      "mcpServers": {
        "googlecalendar": {
          "command": "npx",
          "args": ["-y", "@smithery/cli@latest", "run", "googlecalendar", "--key", "xxx"]
        },
        "github": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-github"],
          "env": {"GITHUB_TOKEN": "xxx"}
        }
      }
    }

Tool Naming:
    Tools are prefixed with server name: {server_name}__{tool_name}
    Example: googlecalendar__list_events, github__create_issue
"""

import json
import os
import subprocess
import sys
import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# ============================================================
# IMMEDIATE STARTUP LOGGING - This runs before any imports fail
# ============================================================
print("=" * 70, file=sys.stderr, flush=True)
print("[STARTUP] Multi-MCP Proxy Server Starting...", file=sys.stderr, flush=True)
print(f"[STARTUP] Python: {sys.version}", file=sys.stderr, flush=True)
print(f"[STARTUP] CWD: {os.getcwd()}", file=sys.stderr, flush=True)
print(f"[STARTUP] PID: {os.getpid()}", file=sys.stderr, flush=True)
print(f"[STARTUP] ENV MCP_SERVERS_CONFIG: {'SET' if os.environ.get('MCP_SERVERS_CONFIG') else 'NOT SET'}", file=sys.stderr, flush=True)
print(f"[STARTUP] ENV MCP_CONFIG_DYNAMODB_TABLE: {os.environ.get('MCP_CONFIG_DYNAMODB_TABLE', 'NOT SET')}", file=sys.stderr, flush=True)
print(f"[STARTUP] ENV MCP_CONFIG_AWS_REGION: {os.environ.get('MCP_CONFIG_AWS_REGION', 'us-east-1')}", file=sys.stderr, flush=True)
print("=" * 70, file=sys.stderr, flush=True)

try:
    from mcp.server.fastmcp import FastMCP
    print("[STARTUP] FastMCP import successful", file=sys.stderr, flush=True)
except ImportError as e:
    print(f"[STARTUP] FATAL: Failed to import FastMCP: {e}", file=sys.stderr, flush=True)
    sys.exit(1)


# ============================================================
# Configuration
# ============================================================

@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server"""
    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None


def load_config_from_dynamodb(table_name: str, region: str) -> Dict[str, Any]:
    """Load MCP server configurations from DynamoDB."""
    print(f"[DDB] Starting DynamoDB config load...", file=sys.stderr, flush=True)
    print(f"[DDB] Table: {table_name}", file=sys.stderr, flush=True)
    print(f"[DDB] Region: {region}", file=sys.stderr, flush=True)

    try:
        print(f"[DDB] Importing boto3...", file=sys.stderr, flush=True)
        import boto3
        print(f"[DDB] boto3 imported successfully", file=sys.stderr, flush=True)

        print(f"[DDB] Creating DynamoDB resource...", file=sys.stderr, flush=True)
        dynamodb = boto3.resource('dynamodb', region_name=region)
        print(f"[DDB] DynamoDB resource created", file=sys.stderr, flush=True)

        print(f"[DDB] Getting table reference...", file=sys.stderr, flush=True)
        table = dynamodb.Table(table_name)
        print(f"[DDB] Table reference obtained", file=sys.stderr, flush=True)

        print(f"[DDB] Executing scan (FilterExpression: enabled = true)...", file=sys.stderr, flush=True)
        response = table.scan(
            FilterExpression='enabled = :enabled',
            ExpressionAttributeValues={':enabled': True}
        )

        items = response.get('Items', [])
        print(f"[DDB] Scan completed. Found {len(items)} enabled items", file=sys.stderr, flush=True)

        mcp_servers = {}
        for idx, item in enumerate(items):
            server_name = item.get('id', item.get('name', ''))
            command = item.get('command', 'npx')
            args = item.get('args', [])
            env = item.get('env')

            print(f"[DDB] Item {idx + 1}: server_name={server_name}, command={command}", file=sys.stderr, flush=True)
            print(f"[DDB]   args={args[:3]}{'...' if len(args) > 3 else ''}", file=sys.stderr, flush=True)
            print(f"[DDB]   env_keys={list(env.keys()) if env else 'None'}", file=sys.stderr, flush=True)

            if server_name:
                mcp_servers[server_name] = {
                    'command': command,
                    'args': args,
                    'env': env
                }
                print(f"[DDB] Added server config: {server_name}", file=sys.stderr, flush=True)
            else:
                print(f"[DDB] WARNING: Skipping item with no server_name", file=sys.stderr, flush=True)

        print(f"[DDB] Total servers loaded: {len(mcp_servers)}", file=sys.stderr, flush=True)
        print(f"[DDB] Server names: {list(mcp_servers.keys())}", file=sys.stderr, flush=True)
        return {'mcpServers': mcp_servers}

    except Exception as e:
        print(f"[DDB] ERROR: Failed to load config from DynamoDB: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {'mcpServers': {}}


def load_config() -> Dict[str, MCPServerConfig]:
    """Load MCP server configurations from environment variable, file, or DynamoDB."""
    print(f"[CONFIG] Starting configuration load...", file=sys.stderr, flush=True)

    config_str = os.environ.get("MCP_SERVERS_CONFIG", "")
    dynamodb_table = os.environ.get("MCP_CONFIG_DYNAMODB_TABLE", "")
    aws_region = os.environ.get("MCP_CONFIG_AWS_REGION", "us-east-1")

    print(f"[CONFIG] MCP_SERVERS_CONFIG length: {len(config_str) if config_str else 0}", file=sys.stderr, flush=True)
    print(f"[CONFIG] MCP_CONFIG_DYNAMODB_TABLE: {dynamodb_table or 'NOT SET'}", file=sys.stderr, flush=True)
    print(f"[CONFIG] MCP_CONFIG_AWS_REGION: {aws_region}", file=sys.stderr, flush=True)

    config_data = None

    if config_str:
        if os.path.isfile(config_str):
            print(f"[CONFIG] Loading config from file: {config_str}", file=sys.stderr, flush=True)
            with open(config_str, 'r') as f:
                config_data = json.load(f)
            print(f"[CONFIG] File loaded successfully", file=sys.stderr, flush=True)
        else:
            try:
                print("[CONFIG] Loading config from environment variable (JSON)", file=sys.stderr, flush=True)
                config_data = json.loads(config_str)
                print(f"[CONFIG] JSON parsed successfully", file=sys.stderr, flush=True)
            except json.JSONDecodeError as e:
                print(f"[CONFIG] ERROR: Failed to parse MCP_SERVERS_CONFIG: {e}", file=sys.stderr, flush=True)

    elif dynamodb_table:
        print(f"[CONFIG] Loading config from DynamoDB table: {dynamodb_table}", file=sys.stderr, flush=True)
        config_data = load_config_from_dynamodb(dynamodb_table, aws_region)
    else:
        print(f"[CONFIG] WARNING: No config source specified (no env var, no DynamoDB)", file=sys.stderr, flush=True)

    if not config_data:
        print("[CONFIG] ERROR: No configuration data loaded", file=sys.stderr, flush=True)
        return {}

    servers = {}
    mcp_servers = config_data.get("mcpServers", {})
    print(f"[CONFIG] Found {len(mcp_servers)} server(s) in config", file=sys.stderr, flush=True)

    for name, config in mcp_servers.items():
        print(f"[CONFIG] Creating MCPServerConfig for: {name}", file=sys.stderr, flush=True)
        servers[name] = MCPServerConfig(
            name=name,
            command=config.get("command", ""),
            args=config.get("args", []),
            env=config.get("env")
        )

    print(f"[CONFIG] Total server configs created: {len(servers)}", file=sys.stderr, flush=True)
    return servers


# ============================================================
# MCP Process Manager
# ============================================================

class MCPProcess:
    """Manages a single MCP server subprocess"""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.is_initialized = False
        self.tools: List[Dict] = []
        self._lock = threading.Lock()
        self._request_id = 0

    def _next_request_id(self) -> str:
        self._request_id += 1
        return f"{self.config.name}-{self._request_id}"

    def _stderr_reader(self):
        """Background thread to read and print stderr"""
        try:
            for line in self.process.stderr:
                print(f"[{self.config.name}] STDERR: {line.rstrip()}", file=sys.stderr)
        except Exception as e:
            print(f"[{self.config.name}] stderr reader error: {e}", file=sys.stderr)

    def start(self) -> bool:
        """Start the MCP server subprocess"""
        if not self.config.command:
            return False

        cmd = [self.config.command] + self.config.args
        env = os.environ.copy()
        if self.config.env:
            env.update(self.config.env)

        # Mask sensitive args for logging
        safe_args = []
        for i, arg in enumerate(self.config.args):
            if i > 0 and self.config.args[i-1] in ["--key", "--token", "-k"]:
                safe_args.append("***")
            elif arg.startswith("ghp_") or arg.startswith("sk-"):
                safe_args.append("***")
            else:
                safe_args.append(arg)

        print(f"Starting [{self.config.name}]: {self.config.command} {' '.join(safe_args)}", file=sys.stderr)

        try:
            self.process = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1, env=env
            )
            print(f"[{self.config.name}] started (PID: {self.process.pid})", file=sys.stderr)

            # Start stderr reader thread
            stderr_thread = threading.Thread(target=self._stderr_reader, daemon=True)
            stderr_thread.start()

            return True
        except Exception as e:
            print(f"ERROR: Failed to start [{self.config.name}]: {e}", file=sys.stderr)
            return False

    def initialize(self) -> bool:
        """Initialize MCP protocol connection"""
        if self.is_initialized or not self.process:
            return self.is_initialized

        try:
            # Wait for process to start and check stderr for any startup messages
            print(f"[{self.config.name}] Waiting for process to start...", file=sys.stderr)
            time.sleep(3)

            # Check if process is still running
            if self.process.poll() is not None:
                # Process exited, read stderr
                stderr_output = self.process.stderr.read() if self.process.stderr else ""
                print(f"[{self.config.name}] Process exited early. stderr: {stderr_output}", file=sys.stderr)
                return False

            init_request = {
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "multi-mcp-proxy", "version": "1.0.0"}
                }
            }

            print(f"[{self.config.name}] Sending initialize request...", file=sys.stderr)
            response = self._send_request(init_request, timeout=30)
            print(f"[{self.config.name}] Initialize response: {response}", file=sys.stderr)

            if not response or "error" in response:
                print(f"[{self.config.name}] Initialize failed or error in response", file=sys.stderr)
                return False

            self._send_request({"jsonrpc": "2.0", "method": "notifications/initialized"}, expect_response=False)
            time.sleep(0.5)
            self.is_initialized = True
            print(f"[{self.config.name}] initialized successfully", file=sys.stderr)
            return True

        except Exception as e:
            print(f"ERROR: Failed to initialize [{self.config.name}]: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return False

    def fetch_tools(self) -> List[Dict]:
        """Fetch tool list from MCP server"""
        if not self.is_initialized:
            return []

        response = self._send_request({
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/list"
        })

        if response and "result" in response and "tools" in response["result"]:
            self.tools = response["result"]["tools"]
            return self.tools
        return []

    def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Call a tool on the MCP server"""
        if not self.is_initialized:
            return {"error": f"[{self.config.name}] not initialized"}

        response = self._send_request({
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        })

        if response and "result" in response:
            return response["result"]
        elif response and "error" in response:
            return {"error": response["error"]}
        return {"error": "No response"}

    def _send_request(self, request: Dict, expect_response: bool = True, timeout: int = 30) -> Optional[Dict]:
        """Send request to MCP server with timeout"""
        import select

        with self._lock:
            if not self.process or self.process.poll() is not None:
                print(f"[{self.config.name}] Process not running", file=sys.stderr)
                return None
            try:
                request_str = json.dumps(request)
                print(f"[{self.config.name}] Sending: {request_str[:200]}...", file=sys.stderr)
                self.process.stdin.write(request_str + "\n")
                self.process.stdin.flush()

                if not expect_response:
                    return {}

                # Use select for timeout on readline
                import selectors
                sel = selectors.DefaultSelector()
                sel.register(self.process.stdout, selectors.EVENT_READ)

                ready = sel.select(timeout=timeout)
                sel.close()

                if not ready:
                    print(f"[{self.config.name}] Timeout waiting for response ({timeout}s)", file=sys.stderr)
                    return None

                response_line = self.process.stdout.readline()
                print(f"[{self.config.name}] Received: {response_line[:200] if response_line else 'empty'}...", file=sys.stderr)
                return json.loads(response_line) if response_line else None
            except Exception as e:
                print(f"ERROR: Request failed [{self.config.name}]: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                return None

    def stop(self):
        """Stop the subprocess"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class MultiMCPManager:
    """Manages multiple MCP server processes"""

    TOOL_SEPARATOR = "__"

    def __init__(self, configs: Dict[str, MCPServerConfig]):
        self.configs = configs
        self.processes: Dict[str, MCPProcess] = {}
        self._all_tools: List[Dict] = []

    def start_all(self) -> bool:
        for name, config in self.configs.items():
            process = MCPProcess(config)
            if process.start():
                self.processes[name] = process
        return len(self.processes) > 0

    def initialize_all(self) -> bool:
        success = 0
        for name, process in self.processes.items():
            if process.initialize():
                success += 1
        print(f"Initialized {success}/{len(self.processes)} servers", file=sys.stderr)
        return success > 0

    def fetch_all_tools(self) -> List[Dict]:
        self._all_tools = []
        for name, process in self.processes.items():
            tools = process.fetch_tools()
            for tool in tools:
                prefixed_tool = tool.copy()
                prefixed_tool["name"] = f"{name}{self.TOOL_SEPARATOR}{tool['name']}"
                prefixed_tool["description"] = f"[{name}] {tool.get('description', '')}"
                self._all_tools.append(prefixed_tool)
        print(f"Total tools: {len(self._all_tools)}", file=sys.stderr)
        return self._all_tools

    def call_tool(self, prefixed_name: str, arguments: Dict) -> Any:
        if self.TOOL_SEPARATOR not in prefixed_name:
            return {"error": f"Invalid tool name: {prefixed_name}"}

        server_name, tool_name = prefixed_name.split(self.TOOL_SEPARATOR, 1)
        if server_name not in self.processes:
            return {"error": f"Unknown server: {server_name}"}

        return self.processes[server_name].call_tool(tool_name, arguments)

    def get_all_tools(self) -> List[Dict]:
        return self._all_tools


# ============================================================
# FastMCP Server
# ============================================================

manager: Optional[MultiMCPManager] = None

mcp = FastMCP(
    name="multi-mcp-proxy",
    host="0.0.0.0",
    port=8000,
    stateless_http=True
)


def create_tool_handler(tool_name: str):
    def handler(**kwargs) -> Any:
        if manager is None:
            return {"error": "Manager not initialized"}
        return manager.call_tool(tool_name, kwargs)
    return handler


def register_all_tools():
    if manager is None:
        return
    for tool in manager.fetch_all_tools():
        mcp._tool_manager.add_tool(
            fn=create_tool_handler(tool["name"]),
            name=tool["name"],
            description=tool.get("description", "")
        )


def initialize():
    global manager

    print("=" * 60, file=sys.stderr, flush=True)
    print("[INIT] Multi-MCP Proxy Server v1.1 (with debug logging)", file=sys.stderr, flush=True)
    print("=" * 60, file=sys.stderr, flush=True)

    print("[INIT] Loading configurations...", file=sys.stderr, flush=True)
    configs = load_config()
    if not configs:
        print("[INIT] ERROR: No MCP server configurations found", file=sys.stderr, flush=True)
        return False

    print(f"[INIT] Loaded {len(configs)} server configuration(s)", file=sys.stderr, flush=True)
    for name in configs.keys():
        print(f"[INIT]   - {name}", file=sys.stderr, flush=True)

    print("[INIT] Creating MultiMCPManager...", file=sys.stderr, flush=True)
    manager = MultiMCPManager(configs)

    print("[INIT] Starting all MCP server processes...", file=sys.stderr, flush=True)
    if not manager.start_all():
        print("[INIT] ERROR: Failed to start any MCP server processes", file=sys.stderr, flush=True)
        return False

    print("[INIT] Initializing all MCP connections...", file=sys.stderr, flush=True)
    if not manager.initialize_all():
        print("[INIT] ERROR: Failed to initialize any MCP connections", file=sys.stderr, flush=True)
        return False

    print("[INIT] Registering tools with FastMCP...", file=sys.stderr, flush=True)
    register_all_tools()

    tool_count = len(manager.get_all_tools())
    print(f"[INIT] SUCCESS: Registered {tool_count} tools", file=sys.stderr, flush=True)
    print("=" * 60, file=sys.stderr, flush=True)
    return True


print("[MAIN] Running initialization...", file=sys.stderr, flush=True)
if not initialize():
    print("[MAIN] WARNING: Initialization failed or no servers available", file=sys.stderr, flush=True)
else:
    print("[MAIN] Initialization complete", file=sys.stderr, flush=True)


if __name__ == "__main__":
    print("[MAIN] Starting FastMCP server on 0.0.0.0:8000...", file=sys.stderr, flush=True)
    print("[MAIN] Transport: streamable-http", file=sys.stderr, flush=True)
    print("[MAIN] Ready for connections", file=sys.stderr, flush=True)
    mcp.run(transport="streamable-http")
