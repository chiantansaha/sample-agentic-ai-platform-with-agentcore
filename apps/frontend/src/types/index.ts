// Common Types
export type Status = 'enabled' | 'disabled';
export type Health = 'healthy' | 'unhealthy' | 'unknown';
export type MCPType = 'external' | 'internal-deploy' | 'internal-create';

// MCP Health Check Response
export interface MCPHealthStatus {
  mcpId: string;
  mcpName: string;
  status: Status;
  health: {
    healthy: boolean | null;
    gatewayStatus: string;
    message: string;
    cached: boolean;
  } | null;
}

// Tool Endpoint (하나의 API에 여러 paths가 있을 때 각 endpoint 정보)
export interface ToolEndpoint {
  method: string;         // HTTP method (GET, POST, etc.)
  path: string;           // API path (/reference-data/locations)
  summary: string;        // Endpoint 요약 설명
  inputSchema: Record<string, unknown>;  // 해당 endpoint의 parameters (JSON Schema)
  responses?: Record<string, unknown>;   // OpenAPI responses schema
}

// Tool (MCP Protocol Standard)
export interface Tool {
  name: string;           // Unique identifier
  description: string;
  inputSchema: Record<string, unknown>;
  endpoints?: ToolEndpoint[];  // 여러 endpoint 정보 (하나의 API에 여러 paths가 있을 때)
  responses?: Record<string, unknown>;   // OpenAPI responses schema
  method?: string;        // HTTP method (첫 번째 endpoint 기준)
  endpoint?: string;      // API endpoint URL
  authType?: string;      // Authentication type (oauth, api_key, none)
}

// MCP (Model Context Protocol)
export interface MCP {
  id: string;
  name: string; // Immutable after creation
  description: string;
  type: MCPType;
  status: Status;
  version: string; // Current version (e.g., "v1", "v2")
  endpoint: string; // Gateway URL with version (e.g., "https://agentcore-gateway.com/flight-search-v1/mcp")
  toolList: Tool[];
  createdAt: number | string; // Unix timestamp (seconds) or ISO string
  updatedAt: number | string; // Unix timestamp (seconds) or ISO string
  // For external MCP
  endpointUrl?: string; // Original external MCP endpoint URL
  serverUrl?: string;
  authConfig?: {
    type: string;
    clientId?: string;
    tokenUrl?: string;
  };
  // For internal deploy MCP
  ecrRepository?: string;
  imageTag?: string;
  // For internal create MCP
  selectedApiTargets?: APITarget[];
  // For internal MCP (Deploy & Create) - Semantic Search
  enableSemanticSearch?: boolean;
}

// MCP Version History
export interface MCPVersion {
  version: string;
  endpoint: string;
  description: string;
  changeLog: string;
  status: Status;
  createdAt: number | string; // Unix timestamp (seconds) or ISO string
  createdBy: string;
  toolList: Tool[];
}

// API Target (for Internal MCP)
export interface APITarget {
  id: string;
  name: string;
  apiId: string; // Reference to API Catalog
  endpoint: string;
  method: string;
  authType?: 'none' | 'api_key' | 'oauth' | 'iam';
}

// Knowledge Base (v2.0 - 파일 기반 관리)
export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  knowledge_base_id: string; // Bedrock Knowledge Base ID
  status: Status;

  // Version & Sync
  current_version: number;
  file_count?: number;
  sync_status?: 'uploaded' | 'pending' | 'syncing' | 'completed' | 'failed';
  sync_started_at?: number | string; // Unix timestamp (seconds) or ISO string
  sync_completed_at?: number | string; // Unix timestamp (seconds) or ISO string

  // Audit
  created_at: number | string; // Unix timestamp (seconds) or ISO string
  updated_at: number | string; // Unix timestamp (seconds) or ISO string
  created_by?: string;
  updated_by?: string;

  // Legacy field for backward compatibility
  tags?: string[];
}

// KB Version Management
export interface KnowledgeBaseVersion {
  kb_id: string;
  version: number;
  files: KnowledgeBaseFile[];
  change_log: string;
  changes: VersionChanges;
  sync_status: 'uploaded' | 'pending' | 'syncing' | 'completed' | 'failed';
  sync_job_id: string;
  sync_started_at?: number | string; // Unix timestamp (seconds) or ISO string
  sync_completed_at?: number | string; // Unix timestamp (seconds) or ISO string
  created_at: number | string; // Unix timestamp (seconds) or ISO string
  created_by: string;
}

// KB File Information
export interface KnowledgeBaseFile {
  name: string;
  size: number; // bytes
  content_type: string; // MIME type
  s3_key: string; // S3 path
  checksum: string; // MD5
  uploaded_at?: number | string; // Unix timestamp (seconds) or ISO string
}

// Version Changes Tracking
export interface VersionChanges {
  added: string[]; // Files added
  deleted: string[]; // Files deleted
  modified: string[]; // Files modified
}

// Agent
export interface Agent {
  id: string;
  name: string;
  description: string;
  status: Status;
  model: string; // e.g., 'claude-3-sonnet', 'claude-3-opus'
  mcps: MCP[];
  knowledgeBases: KnowledgeBase[];
  instructions: string;
  version?: string; // e.g., "v1.0.0", "v1.1.0" (deprecated, use currentVersion)
  currentVersion?: string | { major: number; minor: number; patch: number }; // Current version from backend (can be string or object)
  deploymentType?: string; // e.g., "runtime"
  stats: {
    requestCount: number;
    avgResponseTime: number;
    successRate: number;
  };
  createdAt: number | string; // Unix timestamp (seconds) or ISO string
  updatedAt: number | string; // Unix timestamp (seconds) or ISO string
}

// Agent Version History (Production deployments only)
export interface AgentVersion {
  id: string;
  version: string | { major: number; minor: number; patch: number };
  change_log: string;
  deployed_by: string;
  deployed_at: number | string; // Unix timestamp (seconds) or ISO string
  // Snapshot fields (from backend)
  llm_model?: {
    model_id: string;
    model_name: string;
    provider: string;
  };
  instruction?: {
    system_prompt: string;
    temperature: number;
    max_tokens: number;
  };
  knowledge_bases?: string[];
  mcps?: string[];
  snapshot?: {
    llm_model?: {
      model_id: string;
      model_name: string;
      provider: string;
    };
    instruction?: {
      system_prompt: string;
      temperature: number;
      max_tokens: number;
    };
    knowledge_bases?: string[];
    mcps?: string[];
    status?: string;
  };
}

// Playground
export interface PlaygroundSession {
  id: string;
  agentId: string;
  messages: Message[];
  createdAt: number | string; // Unix timestamp (seconds) or ISO string
  updatedAt: number | string; // Unix timestamp (seconds) or ISO string
}

// AgentCore Runtime Types
export type DeploymentStatus = 'pending' | 'building' | 'uploading' | 'creating' | 'ready' | 'deleting' | 'deleted' | 'failed';

export interface Deployment {
  id: string;
  agent_id: string;
  version: string;
  status: DeploymentStatus;
  runtime_id?: string;
  runtime_arn?: string;
  endpoint_url?: string;
  conversation_id?: string;
  is_resumed: boolean;
  message_count: number;
  build_id?: string;
  build_phase?: string;
  build_phase_message?: string;
  idle_timeout: number;
  max_lifetime: number;
  created_at: number | string; // Unix timestamp (seconds) or ISO string
  updated_at: number | string; // Unix timestamp (seconds) or ISO string
  expires_at?: number | string; // Unix timestamp (seconds) or ISO string
  error_message?: string;
}

export interface Conversation {
  id: string;
  agent_id: string;
  agent_version: string;
  agent_name?: string;
  title: string;
  message_count: number;
  last_message_preview?: string;
  created_at: number | string; // Unix timestamp (seconds) or ISO string
  updated_at: number | string; // Unix timestamp (seconds) or ISO string
}

export interface ConversationList {
  conversations: Conversation[];
  total: number;
  max_allowed: number;
}

export interface ToolUse {
  id: string;
  name: string;
  status: 'loading' | 'completed' | 'error';
  content?: string;  // thinking 등 태그 내용
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number | string; // Unix timestamp (seconds) or ISO string
  tools?: ToolUse[];  // Tool usage within this message
  metadata?: {
    toolCalls?: ToolCall[];
    tokens?: {
      input: number;
      output: number;
    };
    responseTime?: number;
    toolStatus?: 'loading' | 'completed';
    toolName?: string;
  };
}

export interface ToolCall {
  toolId: string;
  toolName: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  duration: number;
}

// Settings
export interface Settings {
  general: GeneralSettings;
  security: SecuritySettings;
  notifications: NotificationSettings;
}

export interface GeneralSettings {
  organizationName: string;
  defaultRegion: string;
  timezone: string;
}

export interface SecuritySettings {
  mfaEnabled: boolean;
  sessionTimeout: number; // in minutes
  allowedIPs: string[];
}

export interface NotificationSettings {
  email: boolean;
  slack: boolean;
  webhookUrl?: string;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
  };
}

export interface ApiError {
  message: string;
  code: string;
  details?: Record<string, unknown>;
}
