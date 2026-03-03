/**
 * ChatPanel - Agent 테스트 채팅 패널
 *
 * 로컬 Agent 테스트를 위한 채팅 UI 컴포넌트입니다.
 * useLocalChat 훅과 함께 사용됩니다.
 */
import { Maximize2, RotateCcw } from 'lucide-react';
import type { Message } from '../../types';
import { Card, Button, LoadingSpinner, Badge, MarkdownContent } from '../common';
import ChatModal from '../common/ChatModal';
import { formatLocalTime } from '../../utils/date';

interface ChatPanelProps {
  // Chat state
  messages: Message[];
  inputMessage: string;
  sending: boolean;
  isPrepared: boolean;
  preparing: boolean;
  isDirty: boolean;

  // Actions
  onInputChange: (value: string) => void;
  onSend: () => void;
  onPrepare: () => void;
  onReset?: () => void;

  // UI options
  agentName?: string;
  prepareDisabled?: boolean;
  className?: string;

  // Modal
  isModalOpen: boolean;
  onModalOpen: () => void;
  onModalClose: () => void;
}

export function ChatPanel({
  messages,
  inputMessage,
  sending,
  isPrepared,
  preparing,
  isDirty,
  onInputChange,
  onSend,
  onPrepare,
  onReset,
  agentName = 'Agent',
  prepareDisabled = false,
  className = '',
  isModalOpen,
  onModalOpen,
  onModalClose,
}: ChatPanelProps) {

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      onSend();
    }
  };

  return (
    <>
      <Card className={`p-6 h-[calc(100vh-250px)] flex flex-col ${className}`}>
        {/* Header */}
        <div className="flex items-center justify-between mb-4 pb-4 border-b">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold">Test Chat</h3>
            <Badge variant="info" className="text-xs">Local</Badge>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onModalOpen}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              title="확대"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
            {isPrepared && onReset && (
              <button
                onClick={onReset}
                className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="세션 종료"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            )}
            <Button
              onClick={onPrepare}
              disabled={preparing || prepareDisabled}
              size="sm"
              variant={isPrepared && !isDirty ? 'outline' : 'primary'}
            >
              {preparing ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2" />
                  Preparing...
                </>
              ) : isPrepared && !isDirty ? (
                'Ready'
              ) : (
                'Prepare'
              )}
            </Button>
          </div>
        </div>

        {/* Chat Content */}
        {!isPrepared && !preparing ? (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <p className="text-lg mb-2">Click "Prepare" to test your agent</p>
              <p className="text-sm">로컬에서 바로 테스트합니다 (배포 없음)</p>
            </div>
          </div>
        ) : preparing ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center space-y-4">
              <LoadingSpinner size="lg" />
              <p className="text-lg font-medium text-gray-900">Agent 준비 중...</p>
              <p className="text-sm text-gray-600">로컬에서 Agent를 초기화하고 있습니다</p>
            </div>
          </div>
        ) : (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-4 mb-4">
              {messages.length === 0 && !sending ? (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <p>메시지를 입력하여 테스트를 시작하세요</p>
                </div>
              ) : (
                <>
                  {messages.map(msg => {
                    // 시스템 메시지 스킵
                    if (msg.role === 'system') return null;

                    // 빈 content의 assistant 메시지 스킵
                    if (msg.role === 'assistant' && !msg.content && (!msg.tools || msg.tools.length === 0)) {
                      return null;
                    }

                    return (
                      <div
                        key={msg.id}
                        className={`p-4 rounded-lg ${
                          msg.role === 'user' ? 'bg-blue-50 ml-12' : 'bg-gray-50 mr-12'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <p className="text-sm font-semibold text-gray-900">
                            {msg.role === 'user' ? '사용자' : agentName}
                          </p>
                          <p className="text-xs text-gray-500">
                            {formatLocalTime(msg.timestamp)}
                          </p>
                        </div>

                        <MarkdownContent content={msg.content} />

                        {/* Tool 사용 표시 */}
                        {msg.role === 'assistant' && msg.tools && msg.tools.length > 0 && (
                          <div className="mt-3 space-y-1">
                            {msg.tools.map((tool) => {
                              const isLoading = tool.status === 'loading';
                              const isError = tool.status === 'error';
                              return (
                                <div
                                  key={tool.id}
                                  className={`flex items-center gap-2 text-xs pl-3 border-l-2 ${
                                    isError ? 'text-red-500 border-red-300' : 'text-gray-500 border-gray-300'
                                  }`}
                                >
                                  {isLoading ? (
                                    <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                  ) : isError ? (
                                    <svg className="h-3 w-3 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                                    </svg>
                                  ) : (
                                    <svg className="h-3 w-3 text-green-600" viewBox="0 0 20 20" fill="currentColor">
                                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                    </svg>
                                  )}
                                  <span>{tool.name} {isLoading ? '호출 중' : isError ? '실패' : '호출 완료'}</span>
                                </div>
                              );
                            })}
                          </div>
                        )}

                        {msg.metadata && (
                          <div className="mt-2 pt-2 border-t border-gray-200 flex gap-4 text-xs text-gray-500">
                            <span>입력: {msg.metadata.tokens?.input} tokens</span>
                            <span>출력: {msg.metadata.tokens?.output} tokens</span>
                            <span>응답시간: {msg.metadata.responseTime}ms</span>
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {/* Typing indicator */}
                  {sending && (() => {
                    const lastMsg = messages[messages.length - 1];
                    const hasContent = lastMsg?.role === 'assistant' && (lastMsg.content || (lastMsg.tools && lastMsg.tools.length > 0));
                    return !hasContent;
                  })() && (
                    <div className="p-4 rounded-lg bg-gray-50 mr-12">
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-sm font-semibold text-gray-900">{agentName}</p>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Input */}
            <div className="flex gap-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => onInputChange(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="메시지를 입력하세요..."
                disabled={sending || isDirty}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
              />
              <Button
                onClick={onSend}
                disabled={sending || !inputMessage.trim() || isDirty}
              >
                {sending ? '전송 중...' : '전송'}
              </Button>
            </div>

            {isDirty && (
              <p className="text-xs text-orange-600 mt-2">
                설정을 변경했습니다. 다시 Prepare를 클릭하여 테스트 환경을 업데이트하세요.
              </p>
            )}
          </>
        )}
      </Card>

      {/* Modal */}
      <ChatModal
        isOpen={isModalOpen}
        onClose={onModalClose}
        title={`Test Chat - ${agentName}`}
        messages={messages}
        input={inputMessage}
        onInputChange={onInputChange}
        onSend={onSend}
        isLoading={sending}
        disabled={!isPrepared || preparing}
        placeholder={isPrepared ? '메시지를 입력하세요...' : 'Prepare 버튼을 먼저 클릭하세요'}
      />
    </>
  );
}
