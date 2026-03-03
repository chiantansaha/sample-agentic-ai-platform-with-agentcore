import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Button } from './Button';

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentPage: string;
}

function FeedbackModal({ isOpen, onClose, currentPage }: FeedbackModalProps) {
  const [feedback, setFeedback] = useState('');
  const [sent, setSent] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = () => {
    if (!feedback.trim()) return;

    const recipients = 'yejinkm@amazon.com;ssminji@amazon.com';
    const subject = encodeURIComponent(`[AWS Platform] 피드백 - ${currentPage}`);
    const body = encodeURIComponent(`페이지: ${currentPage}
작성 시간: ${new Date().toLocaleString('ko-KR')}

피드백 내용:
${feedback.trim()}

---
이 메일은 AWS Agentic AI Platform에서 전송되었습니다.`);

    // Open Outlook Web App with pre-filled email
    const outlookUrl = `https://outlook.office.com/mail/deeplink/compose?to=${recipients}&subject=${subject}&body=${body}`;
    window.open(outlookUrl, '_blank');

    // Show success message
    setSent(true);
    setTimeout(() => {
      onClose();
      setFeedback('');
      setSent(false);
    }, 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-lg w-full mx-4 shadow-xl">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">피드백 보내기</h2>
          <p className="text-sm text-gray-600 mt-1">
            현재 페이지: <span className="font-medium text-gray-900">{currentPage}</span>
          </p>
        </div>

        <div className="p-6">
          {sent ? (
            <div className="text-center py-8">
              <div className="text-green-600 text-5xl mb-4">✓</div>
              <p className="text-lg font-medium text-gray-900">Outlook이 열렸습니다!</p>
              <p className="text-sm text-gray-600 mt-2">
                새 탭에서 Outlook을 확인하고 전송 버튼을 눌러주세요.
              </p>
            </div>
          ) : (
            <>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                기능 제안 또는 의견
              </label>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={8}
                placeholder="개선 사항, 버그, 새로운 기능 제안 등 자유롭게 작성해주세요..."
              />
              <p className="text-xs text-gray-500 mt-2">
                버튼을 클릭하면 Outlook이 열립니다. 페이지 정보가 자동으로 포함됩니다.
              </p>
            </>
          )}
        </div>

        {!sent && (
          <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
            <Button onClick={onClose} variant="outline">
              취소
            </Button>
            <Button onClick={handleSubmit} disabled={!feedback.trim()}>
              Outlook으로 보내기
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export function FeedbackButton() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const location = useLocation();

  // Get current page name from route
  const getPageName = () => {
    const path = location.pathname;
    if (path === '/') return 'Dashboard';
    if (path.startsWith('/agents/create')) return 'Agent Create';
    if (path.startsWith('/agents/') && path.endsWith('/edit')) return 'Agent Edit';
    if (path.startsWith('/agents/')) return 'Agent Detail';
    if (path.startsWith('/agents')) return 'Agent List';
    if (path.startsWith('/mcps/create')) return 'MCP Create';
    if (path.startsWith('/mcps/') && path.endsWith('/edit')) return 'MCP Edit';
    if (path.startsWith('/mcps/')) return 'MCP Detail';
    if (path.startsWith('/mcps')) return 'MCP List';
    if (path.startsWith('/knowledge-bases/create')) return 'Knowledge Base Create';
    if (path.startsWith('/knowledge-bases/') && path.endsWith('/edit')) return 'Knowledge Base Edit';
    if (path.startsWith('/knowledge-bases/')) return 'Knowledge Base Detail';
    if (path.startsWith('/knowledge-bases')) return 'Knowledge Base List';
    if (path.startsWith('/gateways/create')) return 'Gateway Create';
    if (path.startsWith('/gateways/') && path.endsWith('/edit')) return 'Gateway Edit';
    if (path.startsWith('/gateways/')) return 'Gateway Detail';
    if (path.startsWith('/gateways')) return 'Gateway List';
    if (path.startsWith('/blueprints/')) return 'Blueprint Detail';
    if (path.startsWith('/blueprints')) return 'Blueprint List';
    if (path === '/playground') return 'Playground';
    if (path === '/settings') return 'Settings';
    return path;
  };

  return (
    <>
      <button
        onClick={() => setIsModalOpen(true)}
        className="fixed bottom-6 right-6 bg-blue-600 text-white rounded-full p-4 shadow-lg hover:bg-blue-700 transition-all hover:scale-110 z-40 flex items-center gap-2"
        aria-label="피드백 보내기"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={2}
          stroke="currentColor"
          className="w-6 h-6"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"
          />
        </svg>
        <span className="text-sm font-medium">피드백</span>
      </button>

      <FeedbackModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        currentPage={getPageName()}
      />
    </>
  );
}
