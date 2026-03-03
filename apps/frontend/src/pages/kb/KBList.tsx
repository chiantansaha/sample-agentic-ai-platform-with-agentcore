import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { KnowledgeBase } from '../../types';
import { Card, LoadingSpinner, StatusIndicator } from '../../components/common';
import { formatLocalDateTime, getTimestampValue } from '../../utils/date';
import api from '../../utils/axios';

type SortOption = 'newest' | 'oldest' | 'name-asc' | 'name-desc' | 'updated';

type SyncStatus = 'uploaded' | 'pending' | 'syncing' | 'completed' | 'failed';

const SYNC_STATUS_OPTIONS: { value: SyncStatus; label: string }[] = [
  { value: 'uploaded', label: 'Uploaded' },
  { value: 'pending', label: 'Pending' },
  { value: 'syncing', label: 'Syncing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
];

export function KBList() {
  const [kbs, setKBs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'enabled' | 'disabled'>('all');
  const [selectedSyncStatuses, setSelectedSyncStatuses] = useState<SyncStatus[]>([]);
  const [sortBy, setSortBy] = useState<SortOption>('newest');

  useEffect(() => {
    fetchKBs();
  }, [searchQuery, statusFilter]);

  const fetchKBs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (statusFilter !== 'all') params.append('status', statusFilter);

      const response = await api.get(`/knowledge-bases?${params}`);
      setKBs(response.data.data || []);
    } catch (error) {
      console.error('Failed to fetch KBs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSyncStatusToggle = (status: SyncStatus) => {
    setSelectedSyncStatuses(prev =>
      prev.includes(status)
        ? prev.filter(s => s !== status)
        : [...prev, status]
    );
  };

  if (loading) return <div className="flex items-center justify-center h-64"><LoadingSpinner size="lg" /></div>;

  // Client-side filtering by sync status
  let filteredKBs = kbs;

  // Filter by sync status
  if (selectedSyncStatuses.length > 0) {
    filteredKBs = filteredKBs.filter(kb =>
      kb.sync_status && selectedSyncStatuses.includes(kb.sync_status)
    );
  }

  // Sort KBs
  filteredKBs = [...filteredKBs].sort((a, b) => {
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
          <h1 className="text-3xl font-bold text-gray-900">Knowledge Bases</h1>
          <p className="text-gray-600 mt-1">Manage your knowledge bases</p>
        </div>
        <Link
          to="/knowledge-bases/create"
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-sm"
        >
          + Create Knowledge Base
        </Link>
      </div>

      {/* Search and Filters */}
      <Card>
        <div className="flex flex-col sm:flex-row gap-4 mb-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="KB명 또는 설명으로 검색..."
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
              {kbs.length}개
            </div>
          </div>
        </div>

        {/* Filters Row */}
        <div className="flex flex-col gap-4">
          {/* Sync Status Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Sync Status
            </label>
            <div className="flex flex-wrap gap-3">
              {SYNC_STATUS_OPTIONS.map(option => (
                <label
                  key={option.value}
                  className="flex items-center gap-2 px-3 py-2 border rounded-lg cursor-pointer transition-all hover:bg-gray-50"
                  style={{
                    borderColor: selectedSyncStatuses.includes(option.value) ? '#3b82f6' : '#e5e7eb',
                    backgroundColor: selectedSyncStatuses.includes(option.value) ? '#eff6ff' : 'white',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedSyncStatuses.includes(option.value)}
                    onChange={() => handleSyncStatusToggle(option.value)}
                    className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                  />
                  <span className="text-sm font-medium text-gray-700">{option.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      </Card>

      {filteredKBs.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <p className="text-gray-500">
              {searchQuery || statusFilter !== 'all' || selectedSyncStatuses.length > 0
                ? '검색 결과가 없습니다.'
                : '등록된 Knowledge Base가 없습니다.'}
            </p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {filteredKBs.map(kb => {
            return (
              <Link key={kb.id} to={`/knowledge-bases/${kb.id}`}>
                <Card>
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-gray-900 flex-1">{kb.name}</h3>
                    <StatusIndicator status={kb.status} />
                  </div>

                  {kb.description && (
                    <p className="text-sm text-gray-600 mb-3 line-clamp-2">{kb.description}</p>
                  )}

                  <div className="text-xs space-y-1.5 border-t pt-3">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Bedrock KB ID</span>
                      <span className="font-medium font-mono text-gray-900 text-right break-all">{kb.knowledge_base_id}</span>
                    </div>

                    <div className="flex justify-between">
                      <span className="text-gray-500">Version</span>
                      <span className="font-medium text-gray-900">v{kb.current_version}</span>
                    </div>

                    {kb.file_count !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Files</span>
                        <span className="font-medium text-gray-900">{kb.file_count} files</span>
                      </div>
                    )}

                    {kb.sync_status && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Sync Status</span>
                        <span className={`font-medium ${
                          kb.sync_status === 'completed' ? 'text-green-600' :
                          kb.sync_status === 'syncing' ? 'text-blue-600' :
                          kb.sync_status === 'uploaded' || kb.sync_status === 'pending' ? 'text-yellow-600' :
                          kb.sync_status === 'failed' ? 'text-red-600' : 'text-gray-600'
                        }`}>
                          {kb.sync_status}
                        </span>
                      </div>
                    )}

                    <div className="flex justify-between pt-1.5 border-t">
                      <span className="text-gray-500">Created</span>
                      <span className="font-medium text-gray-900 text-xs">
                        {formatLocalDateTime(kb.created_at)}
                      </span>
                    </div>

                    <div className="flex justify-between">
                      <span className="text-gray-500">Updated</span>
                      <span className="font-medium text-gray-900 text-xs">
                        {formatLocalDateTime(kb.updated_at)}
                      </span>
                    </div>

                    {kb.created_by && (
                      <div className="flex justify-between gap-2">
                        <span className="text-gray-500 flex-shrink-0">Created By</span>
                        <span className="font-medium text-gray-900 text-right break-all">
                          {kb.created_by.split('@')[0]}
                        </span>
                      </div>
                    )}
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
