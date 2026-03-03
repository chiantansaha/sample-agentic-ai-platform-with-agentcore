import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import type { Agent, AgentVersion, Message, Status } from '../../types';
import { LoadingSpinner, Badge, StatusIndicator, Card, Button, Modal } from '../../components/common';
import { useToast } from '../../contexts/ToastContext';
import { useTrackPageVisit } from '../../hooks/useRecentActivity';
import { formatLocalDate, formatLocalDateTime } from '../../utils/date';
import api from '../../utils/axios';

export function AgentDetail() {
  const { id } = useParams<{ id: string }>();
  const { showToast } = useToast();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [versions, setVersions] = useState<AgentVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'versions'>('overview');
  const [showPlayground, setShowPlayground] = useState(false);
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [pendingStatus, setPendingStatus] = useState<Status | null>(null);

  // Playground state
  const [playgroundMessages, setPlaygroundMessages] = useState<Message[]>([]);
  const [playgroundInput, setPlaygroundInput] = useState('');
  const [playgroundSending, setPlaygroundSending] = useState(false);

  // Track page visit
  useTrackPageVisit('agent', id, agent?.name);

  useEffect(() => {
    if (id) {
      fetchAgent(id);
    }
  }, [id]);

  const fetchAgent = async (agentId: string) => {
    try {
      // Fetch agent and version history in parallel
      const [agentRes, versionsRes] = await Promise.all([
        api.get(`/agents/${agentId}`),
        api.get(`/agents/${agentId}/versions`)
      ]);

      const agentData = agentRes.data.data;
      setAgent(agentData);

      // Map version history from API
      const versionHistory = versionsRes.data.data || [];
      if (versionHistory.length > 0) {
        setVersions(versionHistory.map((v: any) => {
          const versionStr = typeof v.version === 'string'
            ? v.version
            : v.version && typeof v.version === 'object'
              ? `${v.version.major}.${v.version.minor}.${v.version.patch}`
              : 'Unknown';

          return {
            version: versionStr.startsWith('v') ? versionStr : `v${versionStr}`,
            description: v.change_log || 'Version update',
            changeLog: v.change_log || '',
            model: v.llm_model?.model_name || v.llm_model?.model_id || 'N/A',
            mcps: v.mcps || [],
            knowledgeBases: v.knowledge_bases || [],
            instructions: v.instruction?.system_prompt || '',
            status: v.status || agentData.status,
            deployedAt: v.deployed_at,
            deployedBy: v.deployed_by || 'system',
          };
        }));
      } else {
        // Fallback: create single version from current agent data
        const currentVersion = agentData.current_version || agentData.version || '1.0.0';
        const versionStr = typeof currentVersion === 'string'
          ? currentVersion
          : `${currentVersion.major}.${currentVersion.minor}.${currentVersion.patch}`;

        setVersions([
          {
            version: versionStr.startsWith('v') ? versionStr : `v${versionStr}`,
            description: 'Current version',
            changeLog: '',
            model: agentData.llm_model?.model_name || agentData.llm_model?.model_id || 'N/A',
            mcps: agentData.mcps || [],
            knowledgeBases: agentData.knowledge_bases || [],
            instructions: agentData.instruction?.system_prompt || '',
            status: agentData.status,
            deployedAt: agentData.updated_at || agentData.created_at,
            deployedBy: 'system',
          },
        ]);
      }
    } catch (error) {
      console.error('Failed to fetch agent:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusToggle = () => {
    if (!agent) return;

    const newStatus: Status = agent.status === 'enabled' ? 'disabled' : 'enabled';

    // Disable 시 확인 모달 표시
    if (newStatus === 'disabled') {
      setPendingStatus(newStatus);
      setShowDisableModal(true);
    } else {
      // Enable 시 바로 변경
      updateStatus(newStatus);
    }
  };

  const updateStatus = async (newStatus: Status) => {
    if (!agent) return;

    try {
      const response = await api.patch(`/agents/${agent.id}/status`, { enabled: newStatus === 'enabled' });

      if (response.status === 200) {
        setAgent({ ...agent, status: newStatus });
        showToast('상태가 성공적으로 변경되었습니다.', 'success');
      }
    } catch (error) {
      console.error('Failed to update status:', error);
      showToast('상태 변경 중 오류가 발생했습니다.', 'error');
    }
  };

  const confirmDisable = () => {
    if (pendingStatus) {
      updateStatus(pendingStatus);
    }
    setShowDisableModal(false);
    setPendingStatus(null);
  };

  const cancelDisable = () => {
    setShowDisableModal(false);
    setPendingStatus(null);
  };

  const handlePlaygroundSend = async () => {
    if (!playgroundInput.trim() || playgroundSending) return;

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: playgroundInput,
      timestamp: new Date().toISOString(),
    };

    setPlaygroundMessages((prev) => [...prev, userMessage]);
    setPlaygroundInput('');
    setPlaygroundSending(true);

    // Simulate AI response
    await new Promise((resolve) => setTimeout(resolve, 1500));

    const assistantMessage: Message = {
      id: `msg-${Date.now() + 1}`,
      role: 'assistant',
      content: `This is a test response from "${agent?.name}". In production, this would use the actual deployed agent.`,
      timestamp: new Date().toISOString(),
      metadata: {
        tokens: { input: 50, output: 120 },
        responseTime: 1500,
      },
    };

    setPlaygroundMessages((prev) => [...prev, assistantMessage]);
    setPlaygroundSending(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Agent not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/agents" className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
          ← Back to Agents
        </Link>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900">{agent.name}</h1>
            <p className="text-gray-600 mt-1">{agent.description}</p>
            <div className="flex items-center gap-3 mt-3">
              <StatusIndicator status={agent.status} />
              <Badge variant="gray">
                Current: {(() => {
                  const version = (agent as any).current_version || (agent as any).version;
                  if (!version) return 'N/A';
                  return version.toString().startsWith('v') ? version : `v${version}`;
                })()}
              </Badge>
              <span className="text-sm text-gray-500">{versions.length} versions</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Enable/Disable Toggle */}
            <button
              onClick={handleStatusToggle}
              className="relative inline-flex items-center gap-3 h-10 rounded-lg px-4 bg-white border-2 border-gray-200 hover:border-blue-400 transition-all font-medium text-gray-700 hover:shadow-md"
            >
              <span className="text-sm">{agent.status === 'enabled' ? 'Enabled' : 'Disabled'}</span>
              <div
                className={`relative w-11 h-6 rounded-full transition-all duration-300 ${
                  agent.status === 'enabled' ? 'bg-blue-600' : 'bg-gray-300'
                }`}
              >
                <div
                  className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-md transform transition-all duration-300 ease-in-out ${
                    agent.status === 'enabled' ? 'translate-x-5' : 'translate-x-0.5'
                  }`}
                />
              </div>
            </button>

            <Link
              to={`/playground?agent=${agent.id}&version=${(() => {
                const version = (agent as any).current_version || (agent as any).version;
                if (!version) return '';
                return version.toString().startsWith('v') ? version.substring(1) : version;
              })()}`}
              className="px-6 py-2 border border-purple-600 text-purple-600 rounded-lg hover:bg-purple-50 transition-colors font-medium"
            >
              Playground
            </Link>
            <Link
              to={`/agents/${agent.id}/edit`}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-sm"
            >
              Edit
            </Link>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          {(['overview', 'versions'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`
                py-2 px-1 border-b-2 font-medium text-sm capitalize transition-colors
                ${
                  activeTab === tab
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-2 gap-6">
          <Card>
            <h3 className="font-semibold text-gray-900 mb-4">Basic Information</h3>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-gray-500">Status</dt>
                <dd className="text-gray-900 font-medium capitalize">{(agent as any).status || 'N/A'}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Version</dt>
                <dd className="text-gray-900 font-medium">
                  {(() => {
                    const version = (agent as any).current_version || (agent as any).version;
                    if (!version) return 'N/A';
                    return version.toString().startsWith('v') ? version : `v${version}`;
                  })()}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Created</dt>
                <dd className="text-gray-900 font-medium">
                  {formatLocalDate((agent as any).created_at || (agent as any).createdAt)}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Last Updated</dt>
                <dd className="text-gray-900 font-medium">
                  {formatLocalDate((agent as any).updated_at || (agent as any).updatedAt)}
                </dd>
              </div>
            </dl>
          </Card>

          <Card>
            <h3 className="font-semibold text-gray-900 mb-4">LLM Configuration</h3>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-gray-500">Model</dt>
                <dd className="text-gray-900 font-medium break-all">
                  {(() => {
                    const agentData = agent as any;
                    const model = agentData.llm_model?.model_name || agentData.llm_model?.model_id || agentData.model;
                    return model || 'N/A';
                  })()}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Provider</dt>
                <dd className="text-gray-900 font-medium">
                  {(agent as any).llm_model?.provider || 'N/A'}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Temperature</dt>
                <dd className="text-gray-900 font-medium">
                  {(agent as any).instruction?.temperature ?? 'N/A'}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Max Tokens</dt>
                <dd className="text-gray-900 font-medium">
                  {(agent as any).instruction?.max_tokens?.toLocaleString() || 'N/A'}
                </dd>
              </div>
            </dl>
          </Card>

          <Card>
            <h3 className="font-semibold text-gray-900 mb-4">Resources</h3>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-gray-500 mb-2">MCPs</dt>
                <dd className="flex flex-wrap gap-1">
                  {(() => {
                    const mcps = (agent as any).mcps || [];
                    if (mcps.length === 0) {
                      return <span className="text-gray-400">No MCPs connected</span>;
                    }
                    return mcps.map((mcp: { id: string; name: string } | string, index: number) => {
                      // 백엔드에서 {id, name} 객체로 내려오거나, 레거시로 string ID만 내려올 수 있음
                      const mcpId = typeof mcp === 'string' ? mcp : mcp.id;
                      const mcpName = typeof mcp === 'string' ? mcp : mcp.name;
                      return (
                        <span key={mcpId || index} className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded font-medium">
                          {mcpName}
                        </span>
                      );
                    });
                  })()}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500 mb-2">Knowledge Bases</dt>
                <dd className="flex flex-wrap gap-1">
                  {(() => {
                    const kbs = (agent as any).knowledge_bases || (agent as any).knowledgeBases || [];
                    if (kbs.length === 0) {
                      return <span className="text-gray-400">No Knowledge Bases connected</span>;
                    }
                    return kbs.map((kb: { id: string; name: string } | string, index: number) => {
                      // 백엔드에서 {id, name} 객체로 내려오거나, 레거시로 string ID만 내려올 수 있음
                      const kbId = typeof kb === 'string' ? kb : kb.id;
                      const kbName = typeof kb === 'string' ? kb : kb.name;
                      return (
                        <span key={kbId || index} className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded font-medium">
                          {kbName}
                        </span>
                      );
                    });
                  })()}
                </dd>
              </div>
            </dl>
          </Card>

          <Card>
            <h3 className="font-semibold text-gray-900 mb-4">Instructions</h3>
            <div className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg max-h-60 overflow-y-auto whitespace-pre-wrap">
              {(agent as any).instruction?.system_prompt || (agent as any).instructions || 'No instructions provided'}
            </div>
          </Card>
        </div>
      )}

      {activeTab === 'versions' && (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900">
              <strong>Production Deployment History:</strong> Only production deployments are shown here. Each deployment creates a new version with its own configuration and endpoint.
            </p>
          </div>

          {versions.map((version) => (
            <Card key={version.version}>
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h4 className="font-semibold text-gray-900">{version.version}</h4>
                    {version.version === ((agent as any)?.current_version || (agent as any)?.version) && (
                      <Badge variant="success">Current</Badge>
                    )}
                    <StatusIndicator status={version.status} />
                  </div>
                  <p className="text-sm text-gray-600 mb-2">{version.description}</p>
                  <div className="text-xs text-gray-500 space-y-1">
                    {version.changeLog && (
                      <div>
                        <span className="font-medium">Change Log:</span> {version.changeLog}
                      </div>
                    )}
                    <div>
                      <span className="font-medium">Deployed:</span> {formatLocalDateTime(version.deployedAt)} by {version.deployedBy}
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-gray-200">
                <h5 className="font-medium text-gray-900 mb-2 text-sm">Configuration:</h5>
                <dl className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <dt className="text-gray-500">Model</dt>
                    <dd className="text-gray-900 font-medium">{version.model}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">MCPs</dt>
                    <dd className="text-gray-900">{(version.mcps || []).length} tool(s)</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Knowledge Bases</dt>
                    <dd className="text-gray-900">{(version.knowledgeBases || []).length} KB(s)</dd>
                  </div>
                  {version.deploymentConfig?.authentication && (
                    <div>
                      <dt className="text-gray-500">Authentication</dt>
                      <dd className="text-gray-900">{version.deploymentConfig.authentication.type}</dd>
                    </div>
                  )}
                </dl>

                {version.deploymentConfig?.network && (
                  <div className="mt-3">
                    <dt className="text-gray-500 text-xs mb-1">Network Configuration:</dt>
                    <dd className="text-xs bg-gray-50 p-2 rounded">
                      VPC: {version.deploymentConfig.network.vpcId} |
                      Subnets: {version.deploymentConfig.network.subnetIds?.join(', ')}
                    </dd>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}


      {/* Disable Confirmation Modal */}
      <Modal
        isOpen={showDisableModal}
        onClose={cancelDisable}
        title="Agent 비활성화 확인"
        maxWidth="md"
      >
        <div className="space-y-5">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center border-2 border-blue-200">
              <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-gray-900 mb-2 text-lg">정말 비활성화하시겠습니까?</h4>
              <div className="space-y-2 text-sm text-gray-600">
                <p className="flex items-start gap-2">
                  <span className="text-blue-600 mt-0.5">•</span>
                  <span><strong className="text-gray-700">기존 리소스 이용:</strong> 문제 없음</span>
                </p>
                <p className="flex items-start gap-2">
                  <span className="text-blue-600 mt-0.5">•</span>
                  <span><strong className="text-gray-700">신규 리소스 연동:</strong> 문제가 발생할 수 있습니다</span>
                </p>
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2 border-t border-gray-100">
            <button
              onClick={cancelDisable}
              className="px-5 py-2 border-2 border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 hover:border-gray-300 transition-all font-medium"
            >
              취소
            </button>
            <button
              onClick={confirmDisable}
              className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-sm"
            >
              비활성화
            </button>
          </div>
        </div>
      </Modal>

      {/* Playground Modal */}
      {showPlayground && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
            {/* Header */}
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">Playground</h2>
                  <p className="text-gray-600 mt-1">
                    {agent.name} - {(() => {
                      const version = (agent as any).current_version || (agent as any).version;
                      if (!version) return 'Draft';
                      return version.toString().startsWith('v') ? version : `v${version}`;
                    })()}
                  </p>
                </div>
                <button
                  onClick={() => {
                    setShowPlayground(false);
                    setPlaygroundMessages([]);
                    setPlaygroundInput('');
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 p-6 overflow-y-auto bg-gray-50">
              {playgroundMessages.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-400 mb-2">Start a conversation to test your agent</p>
                  <p className="text-sm text-gray-500">
                    Model: {(() => {
                      const agentData = agent as any;
                      return agentData.llm_model?.model_name || agentData.llm_model?.model_id || agentData.model || 'N/A';
                    })()}
                  </p>
                  <p className="text-sm text-gray-500">
                    MCPs: {((agent as any).mcps || []).length} | KBs: {((agent as any).knowledge_bases || (agent as any).knowledgeBases || []).length}
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {playgroundMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-lg px-4 py-2 ${
                          msg.role === 'user'
                            ? 'bg-blue-600 text-white'
                            : 'bg-white border border-gray-200 text-gray-900'
                        }`}
                      >
                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        {msg.metadata && (
                          <p className="text-xs mt-1 opacity-70">
                            {msg.metadata.responseTime}ms • {msg.metadata.tokens?.input}in / {msg.metadata.tokens?.output}out
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                  {playgroundSending && (
                    <div className="flex justify-start">
                      <div className="bg-white border border-gray-200 rounded-lg px-4 py-2">
                        <LoadingSpinner size="sm" />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Input Area */}
            <div className="p-6 border-t border-gray-200 bg-white">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={playgroundInput}
                  onChange={(e) => setPlaygroundInput(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handlePlaygroundSend();
                    }
                  }}
                  placeholder="Type a message..."
                  disabled={playgroundSending}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <Button
                  onClick={handlePlaygroundSend}
                  disabled={!playgroundInput.trim() || playgroundSending}
                  size="md"
                >
                  Send
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
