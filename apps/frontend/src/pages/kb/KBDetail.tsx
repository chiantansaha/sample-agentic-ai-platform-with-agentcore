import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import type { KnowledgeBase, KnowledgeBaseVersion, KnowledgeBaseFile, Status } from '../../types';
import { LoadingSpinner, StatusIndicator, Card, Modal } from '../../components/common';
import { VersionHistory } from '../../components/kb';
import { useToast } from '../../contexts/ToastContext';
import { useTrackPageVisit } from '../../hooks/useRecentActivity';
import { formatLocalDate } from '../../utils/date';
import api from '../../utils/axios';

export function KBDetail() {
  const { id } = useParams<{ id: string }>();
  const { showToast } = useToast();
  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'versions'>('overview');
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [pendingStatus, setPendingStatus] = useState<Status | null>(null);
  const [versions, setVersions] = useState<KnowledgeBaseVersion[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [files, setFiles] = useState<KnowledgeBaseFile[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);

  // Track page visit
  useTrackPageVisit('kb', id, kb?.name);

  useEffect(() => {
    if (id) {
      api.get(`/knowledge-bases/${id}`)
        .then(res => {
          setKb(res.data.data);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    }
  }, [id]);

  useEffect(() => {
    if (id && activeTab === 'versions') {
      fetchVersions();
      fetchFiles();
    }
  }, [id, activeTab]);

  const fetchVersions = async () => {
    if (!id) return;
    setVersionsLoading(true);
    try {
      const response = await api.get(`/knowledge-bases/${id}/versions`);
      setVersions(response.data.data?.versions || []);
    } catch (error) {
      console.error('Failed to fetch versions:', error);
    } finally {
      setVersionsLoading(false);
    }
  };

  const fetchFiles = async () => {
    if (!id) return;
    setFilesLoading(true);
    try {
      const response = await api.get(`/knowledge-bases/${id}/files`);
      setFiles(response.data.data?.files || []);
    } catch (error) {
      console.error('Failed to fetch files:', error);
    } finally {
      setFilesLoading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const handleStatusToggle = () => {
    if (!kb) return;

    const newStatus: Status = kb.status === 'enabled' ? 'disabled' : 'enabled';

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
    if (!kb) return;

    try {
      const response = await api.patch(`/knowledge-bases/${kb.id}/status`, { enabled: newStatus === 'enabled' });

      if (response.status === 200) {
        setKb({ ...kb, status: newStatus });
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

  if (!kb) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Knowledge Base not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/knowledge-bases" className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
          ← Back to Knowledge Bases
        </Link>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900">{kb.name}</h1>
            <p className="text-gray-600 mt-1">{kb.description}</p>
            <div className="flex items-center gap-3 mt-3">
              <StatusIndicator status={kb.status} />
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Enable/Disable Toggle */}
            <button
              onClick={handleStatusToggle}
              className="relative inline-flex items-center gap-3 h-10 rounded-lg px-4 bg-white border-2 border-gray-200 hover:border-blue-400 transition-all font-medium text-gray-700 hover:shadow-md"
            >
              <span className="text-sm">{kb.status === 'enabled' ? 'Enabled' : 'Disabled'}</span>
              <div
                className={`relative w-11 h-6 rounded-full transition-all duration-300 ${
                  kb.status === 'enabled' ? 'bg-blue-600' : 'bg-gray-300'
                }`}
              >
                <div
                  className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-md transform transition-all duration-300 ease-in-out ${
                    kb.status === 'enabled' ? 'translate-x-5' : 'translate-x-0.5'
                  }`}
                />
              </div>
            </button>

            <Link
              to={`/knowledge-bases/${kb.id}/edit`}
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
        title="Knowledge Base 비활성화 확인"
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
                <dt className="text-gray-500">Created</dt>
                <dd className="text-gray-900 font-medium">
                  {formatLocalDate(kb.created_at)}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Last Updated</dt>
                <dd className="text-gray-900 font-medium">
                  {formatLocalDate(kb.updated_at)}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Version</dt>
                <dd className="text-gray-900 font-medium">
                  v{kb.current_version}
                </dd>
              </div>
              {kb.sync_status && (
                <div>
                  <dt className="text-gray-500">Sync Status</dt>
                  <dd className={`font-medium ${
                    kb.sync_status === 'completed' ? 'text-green-600' :
                    kb.sync_status === 'syncing' ? 'text-blue-600' :
                    kb.sync_status === 'uploaded' || kb.sync_status === 'pending' ? 'text-yellow-600' :
                    kb.sync_status === 'failed' ? 'text-red-600' : 'text-gray-600'
                  }`}>
                    {kb.sync_status}
                  </dd>
                </div>
              )}
            </dl>
          </Card>

          <Card>
            <h3 className="font-semibold text-gray-900 mb-4">Bedrock Configuration</h3>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-gray-500">Bedrock KB ID</dt>
                <dd className="font-medium text-gray-900 font-mono text-xs mt-1">
                  {kb.knowledge_base_id || <span className="text-gray-400">Not yet created</span>}
                </dd>
              </div>
              {kb.file_count !== undefined && (
                <div>
                  <dt className="text-gray-500">File Count</dt>
                  <dd className="text-gray-900 font-medium">
                    {kb.file_count} files
                  </dd>
                </div>
              )}
            </dl>
          </Card>
        </div>
      )}

      {activeTab === 'versions' && (
        <div className="space-y-6">
          {/* Current Files */}
          <Card>
            <h3 className="font-semibold text-gray-900 mb-4">Current Files</h3>
            {filesLoading ? (
              <div className="flex items-center justify-center py-8">
                <LoadingSpinner size="md" />
              </div>
            ) : files.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">No files uploaded yet</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-4 py-2 text-left text-gray-700 font-medium">File Name</th>
                      <th className="px-4 py-2 text-left text-gray-700 font-medium">Size</th>
                      <th className="px-4 py-2 text-left text-gray-700 font-medium">Type</th>
                      <th className="px-4 py-2 text-left text-gray-700 font-medium">Uploaded</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {files.map((file, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-gray-900">{file.name}</td>
                        <td className="px-4 py-3 text-gray-600">{formatFileSize(file.size)}</td>
                        <td className="px-4 py-3 text-gray-600">{file.content_type}</td>
                        <td className="px-4 py-3 text-gray-600">
                          {file.uploaded_at ? formatLocalDate(file.uploaded_at) : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {/* Version History */}
          <VersionHistory
            versions={versions}
            currentVersion={kb.current_version}
            loading={versionsLoading}
          />
        </div>
      )}
    </div>
  );
}
