import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { MCP, Status } from '../../types';
import { LoadingSpinner, Modal } from '../../components/common';
import { MCPCard } from '../../components/mcp';
import { useToast } from '../../contexts/ToastContext';
import api from '../../utils/axios';

export function MCPList() {
  const { showToast } = useToast();
  const [allMcps, setAllMcps] = useState<MCP[]>([]); // 전체 MCP 목록
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | 'external' | 'internal'>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'enabled' | 'disabled'>('all');
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [pendingStatusChange, setPendingStatusChange] = useState<{ mcpId: string; status: 'enabled' | 'disabled' } | null>(null);

  useEffect(() => {
    fetchMCPs();
  }, [searchQuery, typeFilter, statusFilter]);

  const fetchMCPs = async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = {};
      if (searchQuery) params.search = searchQuery;
      if (typeFilter !== 'all') params.type = typeFilter;
      if (statusFilter !== 'all') params.status = statusFilter;

      const response = await api.get('/mcps/', { params });
      setAllMcps(response.data.data);
    } catch (error) {
      console.error('Failed to fetch MCPs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusToggle = (mcpId: string, currentStatus: Status) => {
    const newStatus: Status = currentStatus === 'enabled' ? 'disabled' : 'enabled';
    if (newStatus === 'disabled') {
      setPendingStatusChange({mcpId, status: newStatus});
      setShowDisableModal(true);
    } else {
      updateStatus(mcpId, newStatus);
    }
  };

  const updateStatus = async (mcpId: string, newStatus: Status) => {
    try {
      await api.patch(`/mcps/${mcpId}`, { status: newStatus });
      setAllMcps(allMcps.map(m => m.id === mcpId ? {...m, status: newStatus} : m));
      showToast(`MCP가 성공적으로 ${newStatus === 'enabled' ? '활성화' : '비활성화'}되었습니다.`, 'success');
    } catch (error) {
      console.error('Failed to update MCP status:', error);
      showToast('상태 변경 중 오류가 발생했습니다.', 'error');
    }
  };

  const confirmDisable = () => {
    if (pendingStatusChange) {
      updateStatus(pendingStatusChange.mcpId, pendingStatusChange.status);
    }
    setShowDisableModal(false);
    setPendingStatusChange(null);
  };

  const cancelDisable = () => {
    setShowDisableModal(false);
    setPendingStatusChange(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">MCPs</h1>
          <p className="text-gray-600 mt-1">
            Manage your Model Context Protocol integrations
          </p>
        </div>
        <Link
          to="/mcps/create"
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-sm"
        >
          + Create MCP
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm p-4">
        <div className="grid grid-cols-4 gap-4 mb-4">
          {/* Search */}
          <div className="col-span-2">
            <input
              type="text"
              placeholder="Search MCPs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
            />
          </div>

          {/* Type Filter */}
          <div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as any)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
            >
              <option value="all">All Types</option>
              <option value="external">External</option>
              <option value="internal">Internal</option>
            </select>
          </div>

          {/* Status Filter */}
          <div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
            >
              <option value="all">All Status</option>
              <option value="enabled">Enabled</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>
        </div>

      </div>

      {/* Results Count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          Showing {allMcps.length} MCP{allMcps.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* MCP Grid */}
      {allMcps.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No MCPs found</p>
          <p className="text-sm text-gray-400 mt-2">
            Try adjusting your filters or create a new MCP
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {allMcps.map((mcp) => (
            <MCPCard
              key={mcp.id}
              mcp={mcp}
              onStatusToggle={handleStatusToggle}
            />
          ))}
        </div>
      )}

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
    </div>
  );
}
