import { Link } from 'react-router-dom';
import type { Agent } from '../../types';
import { StatusIndicator, Card } from '../common';
import { formatLocalDateTime } from '../../utils/date';

interface AgentCardProps {
  agent: Agent;
}

export function AgentCard({ agent }: AgentCardProps) {
  // API 응답 필드명 처리 (snake_case)
  const agentData = agent as any;
  const modelName = agentData.llm_model?.model_name || agentData.llm_model?.model_id || agentData.model || 'N/A';
  const kbCount = agentData.knowledge_bases?.length || agentData.knowledgeBases?.length || 0;
  const mcpCount = agentData.mcps?.length || 0;
  const currentVersion = agentData.current_version || agentData.version;
  const description = agentData.description || '설명 없음';

  // Additional fields
  const provider = agentData.llm_model?.provider || 'N/A';
  const createdAt = agentData.created_at || agentData.createdAt;
  const updatedAt = agentData.updated_at || agentData.updatedAt;

  // Version formatting - avoid duplicate 'v'
  const versionDisplay = currentVersion?.toString().startsWith('v')
    ? currentVersion
    : `v${currentVersion}`;

  return (
    <Card className="flex flex-col h-full">
      <Link to={`/agents/${agent.id}`} className="flex-1">
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-semibold text-gray-900 flex-1">{agent.name}</h3>
          <StatusIndicator status={agent.status} />
        </div>

        {description && description !== '설명 없음' && (
          <p className="text-sm text-gray-600 mb-3 line-clamp-2">
            {description}
          </p>
        )}

        <div className="text-xs space-y-1.5 border-t pt-3">
          <div className="flex justify-between gap-2">
            <span className="text-gray-500 flex-shrink-0">Model</span>
            <span className="font-medium text-gray-900 text-right break-all">
              {modelName}
            </span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-500">Provider</span>
            <span className="font-medium text-gray-900">{provider}</span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-500">Version</span>
            <span className="font-medium text-gray-900">{versionDisplay}</span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-500">MCPs</span>
            <span className="font-medium text-gray-900">{mcpCount} tools</span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-500">Knowledge Bases</span>
            <span className="font-medium text-gray-900">{kbCount} KBs</span>
          </div>

          {createdAt && (
            <div className="flex justify-between pt-1.5 border-t">
              <span className="text-gray-500">Created</span>
              <span className="font-medium text-gray-900 text-xs">
                {formatLocalDateTime(createdAt)}
              </span>
            </div>
          )}

          {updatedAt && (
            <div className="flex justify-between">
              <span className="text-gray-500">Updated</span>
              <span className="font-medium text-gray-900 text-xs">
                {formatLocalDateTime(updatedAt)}
              </span>
            </div>
          )}
        </div>
      </Link>
    </Card>
  );
}
