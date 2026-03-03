import { useState, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Card, LoadingSpinner } from '../../components/common';
import api from '../../utils/axios';

export function KBCreate() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const nameInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  // Files
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [showProcessGuide, setShowProcessGuide] = useState(false);

  const [formData, setFormData] = useState({
    name: '',
    description: '',
  });

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files);
      setSelectedFiles(prev => [...prev, ...newFiles]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setSelectedFiles(prev => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const validateKBName = (name: string): string | null => {
    if (!name || name.length === 0) {
      return 'Knowledge Base 이름을 입력해주세요.';
    }
    if (name.length > 100) {
      return '이름은 최대 100자까지 입력 가능합니다.';
    }
    // AWS Bedrock pattern: ([0-9a-zA-Z][_-]?){1,100}
    // 영문자, 숫자, 언더스코어, 하이픈만 허용
    const validPattern = /^[0-9a-zA-Z_-]+$/;
    if (!validPattern.test(name)) {
      return '이름은 영문자, 숫자, 언더스코어(_), 하이픈(-)만 사용 가능합니다. (한글/특수문자/공백 불가)';
    }
    return null;
  };

  const handleSubmit = async () => {
    setError('');

    // Validate KB name
    const nameError = validateKBName(formData.name);
    if (nameError) {
      setError(nameError);
      return;
    }

    if (selectedFiles.length === 0) {
      setError('최소 1개 이상의 파일을 업로드해주세요.');
      return;
    }

    setSubmitting(true);

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('name', formData.name);
      formDataToSend.append('description', formData.description || '');

      // Append all files
      selectedFiles.forEach(file => {
        formDataToSend.append('files', file);
      });

      await api.post('/knowledge-bases', formDataToSend, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      navigate('/knowledge-bases');
    } catch (err) {
      console.error('KB creation error:', err);
      setError('Knowledge Base 생성 중 오류가 발생했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <Link to="/knowledge-bases" className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
          ← Back to Knowledge Bases
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Create Knowledge Base</h1>
        <p className="text-gray-600 mt-1">
          파일을 업로드하면 자동으로 인덱싱되어 Knowledge Base가 생성됩니다
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
              Knowledge Base 이름 <span className="text-red-500">*</span>
            </label>
            <input
              ref={nameInputRef}
              type="text"
              required
              value={formData.name}
              onKeyDown={(e) => {
                // 허용된 키: 영문, 숫자, _, -, 특수키
                const allowedKeys = ['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Tab', 'Home', 'End', 'Enter'];
                if (allowedKeys.includes(e.key)) return;
                if (e.ctrlKey || e.metaKey) return;

                // 한글 입력 시도 차단 (IME)
                if (e.key === 'Process' || e.keyCode === 229) {
                  e.preventDefault();
                  return;
                }

                // 유효한 문자만 허용
                if (!/^[a-zA-Z0-9_-]$/.test(e.key)) {
                  e.preventDefault();
                }
              }}
              onInput={(e) => {
                // IME 입력이 통과된 경우 제거
                const input = e.target as HTMLInputElement;
                const cursorPos = input.selectionStart || 0;
                const rawValue = input.value;
                const sanitized = rawValue.replace(/[^0-9a-zA-Z_-]/g, '');

                if (rawValue !== sanitized) {
                  const beforeCursor = rawValue.slice(0, cursorPos);
                  const sanitizedBeforeCursor = beforeCursor.replace(/[^0-9a-zA-Z_-]/g, '');

                  input.value = sanitized;
                  input.setSelectionRange(sanitizedBeforeCursor.length, sanitizedBeforeCursor.length);

                  if (sanitized.length <= 100) {
                    setFormData({ ...formData, name: sanitized });
                  }
                }
              }}
              onChange={(e) => {
                const sanitized = e.target.value.replace(/[^0-9a-zA-Z_-]/g, '');
                if (sanitized.length <= 100 && sanitized !== formData.name) {
                  setFormData({ ...formData, name: sanitized });
                }
              }}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
              placeholder="my-knowledge-base"
              maxLength={100}
            />
            <p className="text-xs text-gray-500 mt-1">
              {formData.name.length}/100자 · 영문자, 숫자, _, - 만 사용 가능
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              설명
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
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

      {/* File Upload */}
      <Card>
        <div className="flex items-start justify-between mb-6">
          <h3 className="font-semibold text-gray-900">파일 업로드 <span className="text-red-500">*</span></h3>
          <button
            type="button"
            onClick={() => setShowProcessGuide(!showProcessGuide)}
            className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 hover:bg-blue-100 text-gray-600 hover:text-blue-600 transition-all hover:scale-110"
            title="처리 프로세스 가이드"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
            </svg>
          </button>
        </div>

        {/* Guide Popover */}
        {showProcessGuide && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg relative">
            <button
              type="button"
              onClick={() => setShowProcessGuide(false)}
              className="absolute top-2 right-2 text-blue-400 hover:text-blue-600 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <h4 className="text-sm font-semibold text-blue-900 mb-3">처리 프로세스</h4>
            <ol className="text-sm text-blue-800 space-y-2">
              <li className="flex items-start gap-2">
                <span className="font-medium text-blue-900 flex-shrink-0">1.</span>
                <span>파일이 S3 버킷에 업로드됩니다</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="font-medium text-blue-900 flex-shrink-0">2.</span>
                <span>SQS 큐를 통해 Lambda 함수가 트리거됩니다</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="font-medium text-blue-900 flex-shrink-0">3.</span>
                <span>OpenSearch 인덱스가 자동으로 생성됩니다</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="font-medium text-blue-900 flex-shrink-0">4.</span>
                <span>Bedrock Knowledge Base와 Data Source가 생성됩니다</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="font-medium text-blue-900 flex-shrink-0">5.</span>
                <span>Ingestion Job이 실행되어 문서 인덱싱이 시작됩니다</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="font-medium text-blue-900 flex-shrink-0">6.</span>
                <span>완료되면 상태가 "uploaded" → "syncing" → "completed"로 변경됩니다</span>
              </li>
            </ol>
            <p className="mt-3 text-xs text-blue-700">
              💡 인덱싱은 백그라운드에서 처리되며, KB 목록에서 상태를 확인할 수 있습니다.
            </p>
          </div>
        )}

        {/* Drag & Drop Area */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            dragActive
              ? 'border-blue-600 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileChange}
            className="hidden"
            accept=".pdf,.txt,.md,.doc,.docx"
          />
          <div className="space-y-2">
            <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
              <path
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <div className="text-gray-600">
              <span className="font-medium text-blue-600">파일을 선택</span>하거나 여기에 드래그하세요
            </div>
            <p className="text-xs text-gray-500">
              지원 형식: PDF, TXT, MD, DOC, DOCX
            </p>
          </div>
        </div>

        {/* Selected Files List */}
        {selectedFiles.length > 0 && (
          <div className="mt-4 space-y-2">
            <h4 className="text-sm font-medium text-gray-700">선택된 파일 ({selectedFiles.length})</h4>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {selectedFiles.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <svg className="h-5 w-5 text-gray-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
                      <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(index);
                    }}
                    className="ml-4 text-red-600 hover:text-red-800 transition-colors"
                  >
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
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
          to="/knowledge-bases"
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
              업로드 중...
            </>
          ) : (
            '생성'
          )}
        </button>
      </div>
    </div>
  );
}
