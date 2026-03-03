import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Agent } from '../../types';
import { AgentCard } from '../../components/agent/AgentCard';
import { LoadingSpinner, Card } from '../../components/common';
import api from '../../utils/axios';
import { getTimestampValue } from '../../utils/date';

type SortOption = 'newest' | 'oldest' | 'name-asc' | 'name-desc' | 'updated';

export function AgentList() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'enabled' | 'disabled'>('all');
  const [showDraft, setShowDraft] = useState(false); // draft Agent 표시 여부
  const [sortBy, setSortBy] = useState<SortOption>('newest');

  useEffect(() => {
    fetchAgents();
  }, [searchQuery, statusFilter]);

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = {};
      if (searchQuery) params.search = searchQuery;
      if (statusFilter !== 'all') params.status = statusFilter;

      const response = await api.get('/agents', { params });
      setAgents(response.data.data || []);
    } catch (error) {
      console.error('Failed to fetch agents:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  // Client-side filtering (Playground Agent는 Agent 리스트 API에 포함되지 않음)
  let filteredAgents = agents
    // Draft 상태 필터링 (showDraft가 false면 draft 제외)
    .filter(agent => showDraft || agent.status?.toLowerCase() !== 'draft');

  // Sort agents
  filteredAgents = [...filteredAgents].sort((a, b) => {
    const aData = a as any;
    const bData = b as any;

    switch (sortBy) {
      case 'newest':
        return getTimestampValue(bData.created_at || bData.createdAt) - getTimestampValue(aData.created_at || aData.createdAt);
      case 'oldest':
        return getTimestampValue(aData.created_at || aData.createdAt) - getTimestampValue(bData.created_at || bData.createdAt);
      case 'name-asc':
        return a.name.localeCompare(b.name, 'ko-KR');
      case 'name-desc':
        return b.name.localeCompare(a.name, 'ko-KR');
      case 'updated':
        return getTimestampValue(bData.updated_at || bData.updatedAt) - getTimestampValue(aData.updated_at || aData.updatedAt);
      default:
        return 0;
    }
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Agents</h1>
          <p className="text-gray-600 mt-1">Manage your AI agents</p>
        </div>
        <Link
          to="/agents/create"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          + Create Agent
        </Link>
      </div>

      {/* Search and Filters */}
      <Card>
        <div className="flex flex-col sm:flex-row gap-4 mb-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Agent명, 설명, 태그로 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
            />
          </div>
          <div className="flex items-center gap-2">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
            >
              <option value="newest">최신순</option>
              <option value="oldest">오래된순</option>
              <option value="updated">최근 수정순</option>
              <option value="name-asc">이름순 (A-Z)</option>
              <option value="name-desc">이름역순 (Z-A)</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as 'all' | 'enabled' | 'disabled')}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
            >
              <option value="all">전체 상태</option>
              <option value="enabled">Enabled</option>
              <option value="disabled">Disabled</option>
            </select>
            <div className="text-sm text-gray-600 whitespace-nowrap">
              {filteredAgents.length}개
            </div>
          </div>
        </div>

        {/* Draft 표시 체크박스 - 카드 하단 오른쪽 */}
        <div className="flex justify-end pt-4 mt-4 border-t border-gray-200">
          <label htmlFor="showDraft" className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              id="showDraft"
              checked={showDraft}
              onChange={(e) => setShowDraft(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            />
            <span className="text-xs text-gray-600">
              Draft 상태 Agent 표시
            </span>
          </label>
        </div>
      </Card>

      {filteredAgents.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <p className="text-gray-500">
              {searchQuery || statusFilter !== 'all'
                ? '검색 결과가 없습니다.'
                : '등록된 Agent가 없습니다.'}
            </p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {filteredAgents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  );
}
