import { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { Card, LoadingSpinner } from '../../components/common';
import type { KnowledgeBase, KnowledgeBaseFile } from '../../types';
import api from '../../utils/axios';

export function KBEdit() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    bedrockKbId: '',
  });

  // File management states
  const [currentFiles, setCurrentFiles] = useState<KnowledgeBaseFile[]>([]);
  const [deletedFileNames, setDeletedFileNames] = useState<string[]>([]);
  const [newFiles, setNewFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    if (id) {
      fetchKB(id);
      fetchKBFiles(id);
    }
  }, [id]);

  const fetchKB = async (kbId: string) => {
    try {
      const response = await api.get(`/knowledge-bases/${kbId}`);
      const data = response.data;
      const kb: KnowledgeBase = data.data;

      setFormData({
        name: kb.name,
        description: kb.description || '',
        bedrockKbId: kb.knowledge_base_id || '',
      });
    } catch (error) {
      console.error('Failed to fetch KB:', error);
      setError('Failed to load knowledge base');
    } finally {
      setLoading(false);
    }
  };

  const fetchKBFiles = async (kbId: string) => {
    try {
      const response = await api.get(`/knowledge-bases/${kbId}/files`);
      const data = response.data.data;
      setCurrentFiles(data.files || []);
    } catch (error) {
      console.error('Failed to fetch KB files:', error);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    setNewFiles(prev => [...prev, ...droppedFiles]);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      setNewFiles(prev => [...prev, ...selectedFiles]);
    }
  };

  const markFileForDeletion = (fileName: string) => {
    setDeletedFileNames(prev => [...prev, fileName]);
    setCurrentFiles(prev => prev.filter(f => f.name !== fileName));
  };

  const removeNewFile = (index: number) => {
    setNewFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    setError('');
    setSubmitting(true);

    try {
      // 1. 메타정보 업데이트 (이름, 설명)
      await api.put(`/knowledge-bases/${id}`, {
        name: formData.name,
        description: formData.description,
        bedrock_kb_id: formData.bedrockKbId,
      });

      // 2. 파일 업데이트 (새 파일 추가 또는 파일 삭제가 있는 경우에만)
      if (newFiles.length > 0 || deletedFileNames.length > 0) {
        const fileFormData = new FormData();

        // 새 파일 추가
        newFiles.forEach(file => {
          fileFormData.append('files', file);
        });

        // 삭제할 파일 이름 추가 (JSON string)
        fileFormData.append('deleted_files', JSON.stringify(deletedFileNames));

        await api.put(`/knowledge-bases/${id}/files`, fileFormData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      }

      navigate(`/knowledge-bases/${id}`);
    } catch (err: any) {
      console.error('Failed to update KB:', err);
      setError(err.response?.data?.detail || 'Knowledge Base 수정 중 오류가 발생했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <Link to={`/knowledge-bases/${id}`} className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
          ← Back to Knowledge Base
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Edit Knowledge Base</h1>
        <p className="text-gray-600 mt-1">
          Knowledge Base 메타정보 및 파일을 수정합니다
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Basic Information */}
      <Card>
        <h3 className="font-semibold text-gray-900 mb-6">기본 정보</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Knowledge Base 이름
            </label>
            <input
              type="text"
              disabled
              value={formData.name}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-500 cursor-not-allowed"
              placeholder="My Knowledge Base"
            />
            <p className="text-xs text-gray-500 mt-1">
              Knowledge Base 이름은 수정할 수 없습니다.
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              설명
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => {
                if (e.target.value.length <= 200) {
                  setFormData({ ...formData, description: e.target.value });
                }
              }}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
              rows={3}
              placeholder="Knowledge Base에 대한 설명..."
              maxLength={200}
            />
            <p className="text-xs text-gray-500 mt-1">
              {formData.description.length}/200자
            </p>
          </div>
        </div>
      </Card>

      {/* Current Files */}
      {currentFiles.length > 0 && (
        <Card>
          <h3 className="font-semibold text-gray-900 mb-6">현재 파일</h3>
          <div className="border border-gray-200 rounded-lg divide-y divide-gray-200">
            {currentFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <svg
                    className="w-5 h-5 text-green-600 flex-shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {(file.size / 1024).toFixed(2)} KB
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => markFileForDeletion(file.name)}
                  className="ml-4 p-1 text-gray-400 hover:text-red-600 transition-colors"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* New File Upload */}
      <Card>
        <h3 className="font-semibold text-gray-900 mb-6">새 파일 추가</h3>

        {/* Drag & Drop Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            isDragging
              ? 'border-blue-600 bg-blue-50'
              : 'border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50/50'
          }`}
        >
          <div className="flex flex-col items-center gap-4">
            <svg
              className={`w-12 h-12 ${isDragging ? 'text-blue-600' : 'text-gray-400'}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <div>
              <p className="text-gray-700 font-medium mb-1">
                파일을 여기에 드래그하거나 클릭하여 선택하세요
              </p>
              <p className="text-sm text-gray-500">
                TXT, MD, PDF 파일 등 (여러 파일 선택 가능)
              </p>
            </div>
            <label className="px-6 py-2 bg-white border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 hover:border-blue-400 transition-colors font-medium cursor-pointer">
              파일 선택
              <input
                type="file"
                multiple
                accept=".txt,.md,.pdf,.doc,.docx"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>
          </div>
        </div>

        {/* New Files List */}
        {newFiles.length > 0 && (
          <div className="mt-6 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-gray-700">
                추가할 파일 ({newFiles.length}개)
              </p>
              <button
                type="button"
                onClick={() => setNewFiles([])}
                className="text-sm text-red-600 hover:text-red-700 font-medium"
              >
                전체 삭제
              </button>
            </div>
            <div className="border border-gray-200 rounded-lg divide-y divide-gray-200">
              {newFiles.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <svg
                      className="w-5 h-5 text-blue-600 flex-shrink-0"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 4v16m8-8H4"
                      />
                    </svg>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(file.size / 1024).toFixed(2)} KB
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeNewFile(index)}
                    className="ml-4 p-1 text-gray-400 hover:text-red-600 transition-colors"
                  >
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Actions */}
      <div className="flex items-center justify-between pt-6 border-t border-gray-200">
        <Link
          to={`/knowledge-bases/${id}`}
          className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
        >
          취소
        </Link>

        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {submitting ? (
            <>
              <LoadingSpinner size="sm" />
              저장 중...
            </>
          ) : (
            '저장'
          )}
        </button>
      </div>
    </div>
  );
}
