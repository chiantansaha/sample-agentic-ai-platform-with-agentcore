import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import type { MCP, MCPVersion, Status, MCPHealthStatus, Health, Tool, ToolEndpoint } from '../../types';
import { LoadingSpinner, Badge, StatusIndicator, Card, Modal } from '../../components/common';
import { useToast } from '../../contexts/ToastContext';
import { useTrackPageVisit } from '../../hooks/useRecentActivity';
import { formatLocalDateTime } from '../../utils/date';
import api from '../../utils/axios';

export function MCPDetail() {
  const { id } = useParams<{ id: string }>();
  const { showToast } = useToast();
  const [mcp, setMcp] = useState<MCP | null>(null);
  const [versions, setVersions] = useState<MCPVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'tools' | 'versions'>('overview');
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [pendingStatus, setPendingStatus] = useState<Status | null>(null);
  const [expandedToolIndex, setExpandedToolIndex] = useState<number | null>(null);
  const [healthStatus, setHealthStatus] = useState<MCPHealthStatus | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);

  // Track page visit
  useTrackPageVisit('mcp', id, mcp?.name);

  useEffect(() => {
    if (id) {
      fetchMCP(id);
      fetchHealth(id);
    }
  }, [id]);

  const fetchMCP = async (mcpId: string) => {
    try {
      // Fetch MCP details
      const mcpResponse = await api.get(`/mcps/${mcpId}`);
      const mcpData = mcpResponse.data;
      setMcp(mcpData.data);

      // Fetch version history
      try {
        const versionsResponse = await api.get(`/mcps/${mcpId}/versions`);
        const versionsData = versionsResponse.data;

        if (versionsData.success && versionsData.data) {
          setVersions(versionsData.data);
        } else {
          // Fallback: create single version from current MCP data
          setVersions([
            {
              version: mcpData.data.version,
              endpoint: mcpData.data.endpoint,
              description: mcpData.data.description,
              changeLog: 'Current version',
              status: mcpData.data.status,
              createdAt: mcpData.data.updatedAt,
              createdBy: 'admin',
              toolList: mcpData.data.toolList || [],
            },
          ]);
        }
      } catch (versionError) {
        console.error('Failed to fetch version history:', versionError);
        // Fallback: create single version from current MCP data
        setVersions([
          {
            version: mcpData.data.version,
            endpoint: mcpData.data.endpoint,
            description: mcpData.data.description,
            changeLog: 'Current version',
            status: mcpData.data.status,
            createdAt: mcpData.data.updatedAt,
            createdBy: 'admin',
            toolList: mcpData.data.toolList || [],
          },
        ]);
      }
    } catch (error) {
      console.error('Failed to fetch MCP:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchHealth = async (mcpId: string) => {
    setHealthLoading(true);
    try {
      const response = await api.get(`/mcps/${mcpId}/health`);
      if (response.data.success) {
        setHealthStatus(response.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch health status:', error);
    } finally {
      setHealthLoading(false);
    }
  };

  // Convert health status to Health type
  const getHealthValue = (): Health | undefined => {
    if (!healthStatus?.health) return undefined;
    if (healthStatus.health.healthy === true) return 'healthy';
    if (healthStatus.health.healthy === false) return 'unhealthy';
    return 'unknown';
  };

  const handleStatusToggle = () => {
    if (!mcp) return;

    const newStatus: Status = mcp.status === 'enabled' ? 'disabled' : 'enabled';

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
    if (!mcp) return;

    try {
      const response = await api.patch(`/mcps/${mcp.id}`, { status: newStatus });

      if (response.status === 200) {
        setMcp({ ...mcp, status: newStatus });
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!mcp) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">MCP not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/mcps" className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
          ← Back to MCPs
        </Link>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900">{mcp.name}</h1>
            <p className="text-gray-600 mt-1">{mcp.description}</p>
            <div className="flex items-center gap-3 mt-3">
              <Badge variant={mcp.type === 'external' ? 'primary' : 'success'}>
                {mcp.type === 'external' ? 'External' : 'Internal'}
              </Badge>
              <Badge variant="gray">Current: {mcp.version}</Badge>
              <StatusIndicator status={mcp.status} />
              {healthLoading ? (
                <span className="text-xs text-gray-400">Checking health...</span>
              ) : (
                <StatusIndicator health={getHealthValue()} />
              )}
              <span className="text-sm text-gray-500">{versions.length} versions</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Enable/Disable Toggle */}
            <button
              onClick={handleStatusToggle}
              className="relative inline-flex items-center gap-3 h-10 rounded-lg px-4 bg-white border-2 border-gray-200 hover:border-blue-400 transition-all font-medium text-gray-700 hover:shadow-md"
            >
              <span className="text-sm">{mcp.status === 'enabled' ? 'Enabled' : 'Disabled'}</span>
              <div
                className={`relative w-11 h-6 rounded-full transition-all duration-300 ${
                  mcp.status === 'enabled' ? 'bg-blue-600' : 'bg-gray-300'
                }`}
              >
                <div
                  className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-md transform transition-all duration-300 ease-in-out ${
                    mcp.status === 'enabled' ? 'translate-x-5' : 'translate-x-0.5'
                  }`}
                />
              </div>
            </button>

            <Link
              to={`/mcps/${mcp.id}/edit`}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-sm"
            >
              Edit
            </Link>
          </div>
        </div>
      </div>

      {/* Disable Confirmation Modal */}
      <Modal
        isOpen={showDisableModal}
        onClose={cancelDisable}
        title="MCP 비활성화 확인"
        maxWidth="xl"
      >
        <div className="space-y-4">
          <p className="text-gray-700">
            정말로 이 MCP를 비활성화하시겠습니까?
          </p>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h4 className="font-medium text-yellow-900 mb-2">영향 범위:</h4>
            <ul className="space-y-2 text-sm text-yellow-800">
              <li className="flex items-start gap-2">
                <span className="text-yellow-600 mt-0.5">•</span>
                <span>이미 연결된 에이전트: 이 MCP를 더 이상 사용할 수 없습니다</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-yellow-600 mt-0.5">•</span>
                <span>새로운 에이전트 연결: 비활성화된 MCP는 선택할 수 없습니다</span>
              </li>
            </ul>
          </div>

          <div className="flex gap-3 justify-end pt-4">
            <button
              onClick={cancelDisable}
              className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              취소
            </button>
            <button
              onClick={confirmDisable}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              비활성화
            </button>
          </div>
        </div>
      </Modal>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          {(['overview', 'tools', 'versions'] as const).map((tab) => (
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
        <div className="space-y-6">
          {/* Statistics Cards */}
          <div className="grid grid-cols-3 gap-6">
            <Card>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center">
                  <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Tools</p>
                  <p className="text-2xl font-bold text-gray-900">{mcp.toolList?.length || 0}</p>
                </div>
              </div>
            </Card>

            <Card>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-purple-50 flex items-center justify-center">
                  <svg className="w-6 h-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Type</p>
                  <p className="text-lg font-semibold text-gray-900 capitalize">
                    {mcp.type === 'external' && 'External'}
                    {mcp.type === 'internal-deploy' && 'Container'}
                    {mcp.type === 'internal-create' && 'API'}
                  </p>
                </div>
              </div>
            </Card>

            <Card>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-green-50 flex items-center justify-center">
                  <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Version</p>
                  <p className="text-lg font-semibold text-gray-900">{mcp.version}</p>
                </div>
              </div>
            </Card>
          </div>

          {/* MCP Endpoint */}
          <Card>
            <div className="flex items-center gap-2 mb-3">
              <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              <h3 className="font-semibold text-gray-900">MCP Endpoint</h3>
            </div>
            <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm break-all">
              {mcp.endpoint}
            </div>
          </Card>

          {/* External MCP Original Endpoint */}
          {mcp.type === 'external' && mcp.endpointUrl && (
            <Card>
              <div className="flex items-center gap-2 mb-3">
                <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                <h3 className="font-semibold text-gray-900">External MCP Endpoint</h3>
              </div>
              <div className="bg-blue-50 text-blue-900 p-4 rounded-lg font-mono text-sm break-all border border-blue-200">
                {mcp.endpointUrl}
              </div>
            </Card>
          )}

          {/* Details Grid */}
          <div className="grid grid-cols-2 gap-6">
            <Card>
              <div className="flex items-center gap-2 mb-4">
                <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="font-semibold text-gray-900">Details</h3>
              </div>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <dt className="text-gray-500">MCP Name</dt>
                  <dd className="text-gray-900 font-medium">{mcp.name}</dd>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <dt className="text-gray-500">Status</dt>
                  <dd><StatusIndicator status={mcp.status} /></dd>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <dt className="text-gray-500">Health</dt>
                  <dd>
                    {healthLoading ? (
                      <span className="text-xs text-gray-400">Checking...</span>
                    ) : (
                      <StatusIndicator health={getHealthValue()} />
                    )}
                  </dd>
                </div>
                {(mcp.type === 'internal-deploy' || mcp.type === 'internal-create') && (
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <dt className="text-gray-500">Semantic Search</dt>
                    <dd>
                      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
                        mcp.enableSemanticSearch
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          mcp.enableSemanticSearch ? 'bg-green-500' : 'bg-gray-400'
                        }`} />
                        {mcp.enableSemanticSearch ? 'Enabled' : 'Disabled'}
                      </span>
                    </dd>
                  </div>
                )}
                <div className="flex justify-between items-start py-2">
                  <dt className="text-gray-500">Description</dt>
                  <dd className="text-gray-900 font-medium text-right max-w-xs">{mcp.description || 'N/A'}</dd>
                </div>
              </dl>
            </Card>

            <Card>
              <div className="flex items-center gap-2 mb-4">
                <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="font-semibold text-gray-900">Timeline</h3>
              </div>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <dt className="text-gray-500">Created</dt>
                  <dd className="text-gray-900 font-medium">
                    {formatLocalDateTime(mcp.createdAt)}
                  </dd>
                </div>
                <div className="flex justify-between items-center py-2">
                  <dt className="text-gray-500">Last Updated</dt>
                  <dd className="text-gray-900 font-medium">
                    {formatLocalDateTime(mcp.updatedAt)}
                  </dd>
                </div>
              </dl>
            </Card>
          </div>

          {/* Gateway Info */}
          {mcp.gateway && (
            <Card>
              <div className="flex items-center gap-2 mb-4">
                <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                </svg>
                <h3 className="font-semibold text-gray-900">Gateway Information</h3>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <dt className="text-gray-500">Name</dt>
                    <dd className="text-gray-900 font-medium">{mcp.gateway.name}</dd>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <dt className="text-gray-500">Type</dt>
                    <dd className="text-gray-900 font-medium capitalize">{mcp.gateway.type}</dd>
                  </div>
                  <div className="flex justify-between items-center py-2">
                    <dt className="text-gray-500">Status</dt>
                    <dd><StatusIndicator health={mcp.gateway.health} /></dd>
                  </div>
                </div>
                <div>
                  <dt className="text-gray-500 text-sm mb-2">Endpoint</dt>
                  <dd className="bg-gray-50 p-3 rounded border border-gray-200 text-gray-900 font-mono text-xs break-all">
                    {mcp.gateway.endpoint}
                  </dd>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {activeTab === 'tools' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">Tools ({mcp.toolList?.length || 0})</h3>
          </div>
          <div className="grid gap-4">
            {mcp.toolList?.map((tool, index) => (
              <Card key={index} className="cursor-pointer" onClick={() => setExpandedToolIndex(expandedToolIndex === index ? null : index)}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      {/* Method Badge - show first endpoint method or tool.method */}
                      {((tool as Tool).endpoints?.[0]?.method || (tool as any).method) && (
                        <span className={`px-2 py-0.5 rounded text-white font-medium text-xs ${
                          ((tool as Tool).endpoints?.[0]?.method || (tool as any).method) === 'GET' ? 'bg-blue-500' :
                          ((tool as Tool).endpoints?.[0]?.method || (tool as any).method) === 'POST' ? 'bg-green-500' :
                          ((tool as Tool).endpoints?.[0]?.method || (tool as any).method) === 'PUT' ? 'bg-orange-500' :
                          ((tool as Tool).endpoints?.[0]?.method || (tool as any).method) === 'PATCH' ? 'bg-orange-400' :
                          ((tool as Tool).endpoints?.[0]?.method || (tool as any).method) === 'DELETE' ? 'bg-red-500' :
                          'bg-gray-500'
                        }`}>
                          {(tool as Tool).endpoints?.[0]?.method || (tool as any).method}
                        </span>
                      )}
                      <h4 className="font-medium text-gray-900">{tool.name}</h4>
                      {/* Endpoint count badge */}
                      {(tool as Tool).endpoints && (tool as Tool).endpoints!.length > 1 && (
                        <span className="px-2 py-0.5 rounded bg-gray-200 text-gray-700 text-xs">
                          {(tool as Tool).endpoints!.length} endpoints
                        </span>
                      )}
                      <svg
                        className={`w-5 h-5 text-gray-400 transition-transform ${expandedToolIndex === index ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">
                      {/* Show first sentence only */}
                      {tool.description.split(/[.!?]/)[0]}
                      {tool.description.includes('.') || tool.description.includes('!') || tool.description.includes('?') ? '.' : ''}
                    </p>

                    {/* Expanded Details */}
                    {expandedToolIndex === index && (
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <div className="text-sm space-y-4">
                          {/* Base Endpoint and Auth Info */}
                          {((tool as any).endpoint || (tool as any).authType) && (
                            <div className="bg-gray-50 p-3 rounded border border-gray-200 space-y-2">
                              {(tool as any).endpoint && (
                                <div>
                                  <span className="text-xs font-medium text-gray-500">Base URL:</span>
                                  <div className="text-xs font-mono text-gray-900 mt-1 break-all">{(tool as any).endpoint}</div>
                                </div>
                              )}
                              {(tool as any).authType && (
                                <div>
                                  <span className="text-xs font-medium text-gray-500">Auth:</span>
                                  <div className="text-xs text-gray-900 mt-1 capitalize">{(tool as any).authType}</div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Endpoints Details (New - similar to MCPCreate's View Schema Details) */}
                          {(tool as Tool).endpoints && (tool as Tool).endpoints!.length > 0 ? (
                            <div>
                              <div className="text-xs font-medium text-gray-500 mb-2">Endpoints:</div>
                              <div className="space-y-3">
                                {(tool as Tool).endpoints!.map((endpoint: ToolEndpoint, epIndex: number) => (
                                  <div key={epIndex} className="bg-gray-50 p-3 rounded border border-gray-200">
                                    {/* Method + Path */}
                                    <div className="flex items-center gap-2 mb-2">
                                      <span className={`px-2 py-0.5 rounded text-white font-medium text-xs ${
                                        endpoint.method === 'GET' ? 'bg-blue-500' :
                                        endpoint.method === 'POST' ? 'bg-green-500' :
                                        endpoint.method === 'PUT' ? 'bg-orange-500' :
                                        endpoint.method === 'PATCH' ? 'bg-orange-400' :
                                        endpoint.method === 'DELETE' ? 'bg-red-500' :
                                        'bg-gray-500'
                                      }`}>
                                        {endpoint.method}
                                      </span>
                                      <span className="font-mono text-gray-900 font-semibold text-xs">{endpoint.path}</span>
                                    </div>

                                    {/* Summary */}
                                    {endpoint.summary && (
                                      <p className="text-xs text-gray-600 mb-3">{endpoint.summary}</p>
                                    )}

                                    {/* Parameters from inputSchema */}
                                    {endpoint.inputSchema?.properties && Object.keys(endpoint.inputSchema.properties).length > 0 && (
                                      <div className="mb-3">
                                        <div className="text-xs font-medium text-gray-700 mb-1">Parameters:</div>
                                        <div className="ml-2 space-y-1">
                                          {Object.entries(endpoint.inputSchema.properties as Record<string, any>).map(([paramName, paramSchema]: [string, any]) => {
                                            // Handle body object with nested properties
                                            if (paramName === 'body' && paramSchema.properties) {
                                              return (
                                                <div key={paramName} className="space-y-1">
                                                  <div className="text-xs font-medium text-gray-700 mt-2">Request Body:</div>
                                                  {Object.entries(paramSchema.properties as Record<string, any>).map(([nestedName, nestedSchema]: [string, any]) => (
                                                    <div key={nestedName} className="text-xs ml-2">
                                                      <span className="font-mono text-blue-600">{nestedName}</span>
                                                      {(paramSchema.required as string[] | undefined)?.includes(nestedName) && <span className="text-red-500">*</span>}
                                                      <span className="text-gray-600"> - {nestedSchema.type || 'any'}</span>
                                                      {nestedSchema.description && (
                                                        <div className="ml-4 text-gray-500">{nestedSchema.description}</div>
                                                      )}
                                                    </div>
                                                  ))}
                                                </div>
                                              );
                                            }

                                            // Regular parameters
                                            return (
                                              <div key={paramName} className="text-xs">
                                                <span className="font-mono text-blue-600">{paramName}</span>
                                                {(endpoint.inputSchema.required as string[] | undefined)?.includes(paramName) && <span className="text-red-500">*</span>}
                                                <span className="text-gray-600"> - {paramSchema.type || 'any'}</span>
                                                {paramSchema.enum && (
                                                  <span className="text-gray-500"> ({paramSchema.enum.join(', ')})</span>
                                                )}
                                                {paramSchema.description && (
                                                  <div className="ml-4 text-gray-500">{paramSchema.description}</div>
                                                )}
                                              </div>
                                            );
                                          })}
                                        </div>
                                      </div>
                                    )}

                                    {/* Responses */}
                                    {endpoint.responses && Object.keys(endpoint.responses).length > 0 && (
                                      <div>
                                        <div className="text-xs font-medium text-gray-700 mb-1">Responses:</div>
                                        <div className="ml-2 space-y-2">
                                          {Object.entries(endpoint.responses as Record<string, any>).map(([statusCode, response]: [string, any]) => (
                                            <div key={statusCode} className="text-xs">
                                              <div>
                                                <span className={`font-mono font-semibold ${
                                                  statusCode.startsWith('2') ? 'text-green-600' :
                                                  statusCode.startsWith('4') ? 'text-yellow-600' :
                                                  statusCode.startsWith('5') ? 'text-red-600' :
                                                  'text-gray-600'
                                                }`}>{statusCode}</span>
                                                <span className="text-gray-600"> - {response.description || 'Response'}</span>
                                              </div>
                                              {response.content?.['application/json']?.schema?.properties && (
                                                <div className="ml-4 mt-1 space-y-0.5">
                                                  {Object.entries(response.content['application/json'].schema.properties as Record<string, any>).map(([propName, propSchema]: [string, any]) => (
                                                    <div key={propName}>
                                                      <span className="font-mono text-blue-600">{propName}</span>
                                                      <span className="text-gray-600"> - {propSchema.type || 'any'}</span>
                                                      {propSchema.description && <span className="text-gray-500"> : {propSchema.description}</span>}
                                                    </div>
                                                  ))}
                                                </div>
                                              )}
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : (
                            /* Fallback: Legacy parameters display when no endpoints array */
                            <>
                              {/* Parameters */}
                              {tool.inputSchema?.properties && Object.keys(tool.inputSchema.properties).length > 0 && (
                                <div>
                                  <div className="text-xs font-medium text-gray-500 mb-2">Parameters:</div>
                                  <div className="text-xs bg-gray-50 p-3 rounded border border-gray-200 space-y-1">
                                    {Object.entries(tool.inputSchema.properties as Record<string, any>).map(([propName, propSchema]: [string, any]) => {
                                      // Handle body object with nested properties
                                      if (propName === 'body' && propSchema.properties) {
                                        return (
                                          <div key={propName} className="space-y-1">
                                            <div className="font-medium text-gray-700">Request Body:</div>
                                            {Object.entries(propSchema.properties as Record<string, any>).map(([nestedName, nestedSchema]: [string, any]) => (
                                              <div key={nestedName} className="ml-2">
                                                <span className="font-mono text-blue-600">{nestedName}</span>
                                                {(propSchema.required as string[] | undefined)?.includes(nestedName) && <span className="text-red-500">*</span>}
                                                <span className="text-gray-600"> - {nestedSchema.type || 'any'}</span>
                                                {nestedSchema.description && <span className="text-gray-500"> : {nestedSchema.description}</span>}
                                              </div>
                                            ))}
                                          </div>
                                        );
                                      }

                                      // Regular parameters
                                      return (
                                        <div key={propName}>
                                          <span className="font-mono text-blue-600">{propName}</span>
                                          {(tool.inputSchema.required as string[] | undefined)?.includes(propName) && <span className="text-red-500">*</span>}
                                          <span className="text-gray-600"> - {propSchema.type || 'any'}</span>
                                          {propSchema.enum && (
                                            <span className="text-gray-500"> ({propSchema.enum.join(', ')})</span>
                                          )}
                                          {propSchema.description && <span className="text-gray-500"> : {propSchema.description}</span>}
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {/* Responses */}
                              {(tool as any).responses && (
                                <div>
                                  <div className="text-xs font-medium text-gray-500 mb-2">Responses:</div>
                                  <div className="text-xs bg-gray-50 p-3 rounded border border-gray-200 space-y-2">
                                    {Object.entries((tool as any).responses as Record<string, any>).map(([statusCode, response]: [string, any]) => (
                                      <div key={statusCode}>
                                        <div>
                                          <span className="font-mono text-green-600">{statusCode}</span>
                                          <span className="text-gray-600"> - {response.description || 'Success'}</span>
                                        </div>
                                        {response.content?.['application/json']?.schema?.properties && (
                                          <div className="ml-4 space-y-0.5 mt-1">
                                            {Object.entries(response.content['application/json'].schema.properties as Record<string, any>).map(([propName, propSchema]: [string, any]) => (
                                              <div key={propName}>
                                                <span className="font-mono text-blue-600">{propName}</span>
                                                <span className="text-gray-600"> - {propSchema.type || 'any'}</span>
                                                {propSchema.description && <span className="text-gray-500"> : {propSchema.description}</span>}
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'versions' && (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900">
              <strong>Note:</strong> MCP name cannot be changed after creation. Editing an MCP creates a new version with an updated endpoint URL.
            </p>
          </div>

          {versions.map((version) => (
            <Card key={version.version}>
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h4 className="font-semibold text-gray-900">{version.version}</h4>
                    {version.version === mcp.version && (
                      <Badge variant="success">Current</Badge>
                    )}
                    <StatusIndicator status={version.status} />
                  </div>
                  <p className="text-sm text-gray-600 mb-2">{version.description}</p>
                  <div className="text-xs text-gray-500 space-y-1">
                    <div>
                      <span className="font-medium">Endpoint:</span>{' '}
                      <code className="bg-gray-100 px-2 py-0.5 rounded">{version.endpoint}</code>
                    </div>
                    <div>
                      <span className="font-medium">Change Log:</span> {version.changeLog}
                    </div>
                    <div>
                      <span className="font-medium">Created:</span> {formatLocalDateTime(version.createdAt)} by {version.createdBy}
                    </div>
                    <div>
                      <span className="font-medium">Tools:</span> {version.toolList?.length || 0} tool(s)
                    </div>
                  </div>
                </div>
              </div>

              {version.toolList && version.toolList.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <h5 className="font-medium text-gray-900 mb-2 text-sm">Tools in this version:</h5>
                  <div className="space-y-2">
                    {version.toolList.map((tool, idx) => (
                      <div key={tool.name || idx} className="text-xs bg-gray-50 px-3 py-2 rounded">
                        <span className="font-medium">{tool.name}</span>: {tool.description}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

    </div>
  );
}
