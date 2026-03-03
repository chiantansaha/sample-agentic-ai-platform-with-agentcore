import { X } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { ChatMessageList } from './ChatMessageList';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string | number;
  tools?: Array<{
    id: string;
    name: string;
    status: 'completed' | 'loading' | 'running' | 'error';
    content?: string;
  }>;
}

interface ChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  messages: Message[];
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  isLoading?: boolean;
  disabled?: boolean;
  placeholder?: string;
  agentName?: string;
}

export default function ChatModal({
  isOpen,
  onClose,
  title,
  messages,
  input,
  onInputChange,
  onSend,
  isLoading = false,
  disabled = false,
  placeholder = '메시지를 입력하세요...',
  agentName = 'Agent'
}: ChatModalProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && input.trim()) {
        onSend();
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full h-full max-w-7xl max-h-[95vh] m-4 bg-white rounded-lg shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="닫기"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.length === 0 && !isLoading ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              대화를 시작해보세요
            </div>
          ) : (
            <>
              <ChatMessageList
                messages={messages}
                isLoading={isLoading}
                agentName={agentName}
              />
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Area */}
        <div className="px-6 py-4 border-t border-gray-200">
          <div className="flex gap-3">
            <textarea
              value={input}
              onChange={(e) => onInputChange(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={placeholder}
              disabled={disabled}
              rows={3}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500"
            />
            <button
              onClick={onSend}
              disabled={disabled || !input.trim() || isLoading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:text-gray-700 transition-colors font-medium self-end"
            >
              {isLoading ? '전송 중...' : '전송'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
