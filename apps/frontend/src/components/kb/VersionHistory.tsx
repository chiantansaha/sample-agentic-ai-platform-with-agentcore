import React, { useState } from 'react';
import type { KnowledgeBaseVersion, KnowledgeBaseFile } from '../../types';
import { Card, Modal, LoadingSpinner } from '../common';
import { formatLocalDateTime } from '../../utils/date';

interface VersionHistoryProps {
  versions: KnowledgeBaseVersion[];
  currentVersion: number;
  onVersionRestore?: (version: number) => Promise<void>;
  loading?: boolean;
}

export function VersionHistory({
  versions,
  currentVersion,
  onVersionRestore,
  loading = false
}: VersionHistoryProps) {
  const [selectedVersion, setSelectedVersion] = useState<KnowledgeBaseVersion | null>(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [restoring, setRestoring] = useState(false);

  const handleViewDetails = (version: KnowledgeBaseVersion) => {
    setSelectedVersion(version);
    setShowDetailsModal(true);
  };

  const handleRestore = async (version: number) => {
    if (!onVersionRestore) return;

    setRestoring(true);
    try {
      await onVersionRestore(version);
    } finally {
      setRestoring(false);
      setShowDetailsModal(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getSyncStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'syncing': return 'text-blue-600';
      case 'uploaded': return 'text-yellow-600';
      case 'pending': return 'text-yellow-600';
      case 'failed': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getSyncStatusIcon = (status: string) => {
    return '';
  };

  if (loading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner size="md" />
        </div>
      </Card>
    );
  }

  if (versions.length === 0) {
    return (
      <Card>
        <h3 className="font-semibold text-gray-900 mb-4">Version History</h3>
        <div className="text-center py-8">
          <p className="text-sm text-gray-500">
            버전 히스토리가 없습니다.
          </p>
          <p className="text-xs text-gray-400 mt-2">
            현재 버전: v{currentVersion}
          </p>
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <h3 className="font-semibold text-gray-900 mb-4">Version History</h3>

        <div className="space-y-4">
          {versions.map((version) => (
            <div
              key={version.version}
              className={`border-l-4 pl-4 py-3 ${
                version.version === currentVersion
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h4 className="font-medium text-gray-900">
                      Version {version.version}
                      {version.version === currentVersion && (
                        <span className="ml-2 px-2 py-0.5 bg-blue-600 text-white text-xs rounded-full">
                          Current
                        </span>
                      )}
                    </h4>
                    <span className={`text-sm ${getSyncStatusColor(version.sync_status)}`}>
                      {version.sync_status}
                    </span>
                  </div>

                  <p className="text-sm text-gray-600 mt-1">{version.change_log}</p>

                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                    <span>{version.files.length} files</span>
                    {version.changes.added.length > 0 && (
                      <span className="text-green-600">
                        +{version.changes.added.length} added
                      </span>
                    )}
                    {version.changes.modified.length > 0 && (
                      <span className="text-blue-600">
                        {version.changes.modified.length} modified
                      </span>
                    )}
                    {version.changes.deleted.length > 0 && (
                      <span className="text-red-600">
                        -{version.changes.deleted.length} deleted
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 mt-2 text-xs text-gray-400">
                    <span>Created by {version.created_by}</span>
                    <span>•</span>
                    <span>{formatLocalDateTime(version.created_at)}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleViewDetails(version)}
                    className="px-3 py-1 text-sm text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    View Details
                  </button>
                  {onVersionRestore && version.version !== currentVersion && (
                    <button
                      onClick={() => handleRestore(version.version)}
                      disabled={restoring}
                      className="px-3 py-1 text-sm text-gray-600 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                    >
                      Restore
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Version Details Modal */}
      <Modal
        isOpen={showDetailsModal}
        onClose={() => setShowDetailsModal(false)}
        title={`Version ${selectedVersion?.version} Details`}
        maxWidth="2xl"
      >
        {selectedVersion && (
          <div className="space-y-6">
            {/* Overview */}
            <div>
              <h4 className="font-semibold text-gray-900 mb-3">Overview</h4>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">Version:</dt>
                  <dd className="font-medium">v{selectedVersion.version}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Change Log:</dt>
                  <dd className="font-medium">{selectedVersion.change_log}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Sync Status:</dt>
                  <dd className={`font-medium ${getSyncStatusColor(selectedVersion.sync_status)}`}>
                    {selectedVersion.sync_status}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Created By:</dt>
                  <dd className="font-medium">{selectedVersion.created_by}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Created At:</dt>
                  <dd className="font-medium">{formatLocalDateTime(selectedVersion.created_at)}</dd>
                </div>
                {selectedVersion.sync_completed_at && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Synced At:</dt>
                    <dd className="font-medium">
                      {formatLocalDateTime(selectedVersion.sync_completed_at)}
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            {/* File Changes */}
            <div>
              <h4 className="font-semibold text-gray-900 mb-3">File Changes</h4>

              {/* Added Files */}
              {selectedVersion.changes.added.length > 0 && (
                <div className="mb-4">
                  <h5 className="text-sm font-medium text-green-600 mb-2">
                    Added Files ({selectedVersion.changes.added.length})
                  </h5>
                  <div className="space-y-1">
                    {selectedVersion.changes.added.map((fileName) => (
                      <div key={fileName} className="flex items-center gap-2 text-sm">
                        <span className="text-green-500">+</span>
                        <span className="text-gray-700">{fileName}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Modified Files */}
              {selectedVersion.changes.modified.length > 0 && (
                <div className="mb-4">
                  <h5 className="text-sm font-medium text-blue-600 mb-2">
                    Modified Files ({selectedVersion.changes.modified.length})
                  </h5>
                  <div className="space-y-1">
                    {selectedVersion.changes.modified.map((fileName) => (
                      <div key={fileName} className="flex items-center gap-2 text-sm">
                        <span className="text-blue-500">~</span>
                        <span className="text-gray-700">{fileName}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Deleted Files */}
              {selectedVersion.changes.deleted.length > 0 && (
                <div className="mb-4">
                  <h5 className="text-sm font-medium text-red-600 mb-2">
                    Deleted Files ({selectedVersion.changes.deleted.length})
                  </h5>
                  <div className="space-y-1">
                    {selectedVersion.changes.deleted.map((fileName) => (
                      <div key={fileName} className="flex items-center gap-2 text-sm">
                        <span className="text-red-500">-</span>
                        <span className="text-gray-700 line-through">{fileName}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* All Files in Version */}
            <div>
              <h4 className="font-semibold text-gray-900 mb-3">
                All Files ({selectedVersion.files.length})
              </h4>
              <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-4 py-2 text-left text-gray-700">File Name</th>
                      <th className="px-4 py-2 text-left text-gray-700">Size</th>
                      <th className="px-4 py-2 text-left text-gray-700">Type</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {selectedVersion.files.map((file, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-2 text-gray-900">{file.name}</td>
                        <td className="px-4 py-2 text-gray-600">
                          {formatFileSize(file.size)}
                        </td>
                        <td className="px-4 py-2 text-gray-600">
                          {file.content_type}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
              <button
                onClick={() => setShowDetailsModal(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
              >
                Close
              </button>
              {onVersionRestore && selectedVersion.version !== currentVersion && (
                <button
                  onClick={() => handleRestore(selectedVersion.version)}
                  disabled={restoring}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 flex items-center gap-2"
                >
                  {restoring ? (
                    <>
                      <LoadingSpinner size="sm" />
                      Restoring...
                    </>
                  ) : (
                    'Restore This Version'
                  )}
                </button>
              )}
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}