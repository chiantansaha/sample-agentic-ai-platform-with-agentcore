/**
 * ChatMessageList - 공통 메시지 목록 렌더링 컴포넌트
 *
 * AgentCreate, AgentEdit, Playground, ChatModal에서 공통으로 사용됩니다.
 * Tool 사용 표시 (expand/collapse), "생각" 특별 처리 등을 포함합니다.
 */
import { useState } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';
import { MarkdownContent } from './MarkdownContent';
import { formatLocalTime } from '../../utils/date';

interface ToolUse {
  id: string;
  name: string;
  status: 'loading' | 'completed' | 'error' | 'running';
  content?: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string | number;
  tools?: ToolUse[];
  metadata?: {
    toolCalls?: any[];
    tokens?: {
      input: number;
      output: number;
    };
    responseTime?: number;
    toolStatus?: 'loading' | 'completed';
    toolName?: string;
  };
}

interface ChatMessageListProps {
  messages: Message[];
  isLoading?: boolean;
  agentName?: string;
  showMetadata?: boolean;
}

/**
 * 개별 Tool 사용 표시 컴포넌트
 */
function ToolUsageItem({
  tool,
  isExpanded,
  onToggle
}: {
  tool: ToolUse;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const isToolLoading = tool.status === 'loading' || tool.status === 'running';
  const isError = tool.status === 'error';
  const isThinking = tool.name === '생각';
  const hasContent = !!tool.content;

  // thinking인 경우 "생각 중" / "생각 완료", 다른 경우 tool 이름만 표시하고 상태는 아이콘으로
  const statusText = isThinking
    ? (isToolLoading ? ' 중' : isError ? ' 실패' : ' 완료')
    : ''; // tool은 이름만 표시, 상태는 아이콘으로 표현

  return (
    <div>
      <div className={`flex items-center gap-2 text-xs pl-3 border-l-2 ${isError ? 'text-red-500 border-red-300' : 'text-gray-500 border-gray-300'}`}>
        {isToolLoading ? (
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
        <span>{tool.name}{statusText}</span>
        {hasContent && (
          <button
            onClick={onToggle}
            className="p-0.5 hover:bg-gray-200 rounded transition-colors"
            title={isExpanded ? '접기' : '펼치기'}
          >
            {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          </button>
        )}
      </div>
      {hasContent && isExpanded && (
        <div className="ml-5 mt-1 p-2 bg-gray-100 rounded text-xs text-gray-600 whitespace-pre-wrap max-h-48 overflow-y-auto">
          {tool.content}
        </div>
      )}
    </div>
  );
}

/**
 * Typing Indicator 컴포넌트
 */
function TypingIndicator({ agentName }: { agentName?: string }) {
  return (
    <div className="p-4 rounded-lg bg-gray-50 mr-12">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-semibold text-gray-900">{agentName || 'Agent'}</p>
      </div>
      <div className="flex items-center gap-1">
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  );
}

/**
 * 메시지 목록 렌더링 컴포넌트
 */
export function ChatMessageList({
  messages,
  isLoading = false,
  agentName = 'Agent',
  showMetadata = false,
}: ChatMessageListProps) {
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

  const toggleToolExpand = (toolId: string) => {
    setExpandedTools(prev => {
      const next = new Set(prev);
      if (next.has(toolId)) {
        next.delete(toolId);
      } else {
        next.add(toolId);
      }
      return next;
    });
  };

  // Typing indicator 표시 여부 계산
  const showTypingIndicator = isLoading && (() => {
    const lastMsg = messages[messages.length - 1];
    const hasContent = lastMsg?.role === 'assistant' && (lastMsg.content || (lastMsg.tools && lastMsg.tools.length > 0));
    return !hasContent;
  })();

  return (
    <>
      {messages.map(msg => {
        // 시스템 메시지 스킵
        if (msg.role === 'system') {
          return null;
        }

        // 빈 content의 assistant 메시지 스킵 (스트리밍 시작 전)
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
                {msg.tools.map(tool => (
                  <ToolUsageItem
                    key={tool.id}
                    tool={tool}
                    isExpanded={expandedTools.has(tool.id)}
                    onToggle={() => toggleToolExpand(tool.id)}
                  />
                ))}
              </div>
            )}

            {/* 메타데이터 표시 (옵션) */}
            {showMetadata && msg.metadata && (
              <div className="mt-2 pt-2 border-t border-gray-200 flex gap-4 text-xs text-gray-500">
                {msg.metadata.tokens?.input !== undefined && (
                  <span>입력: {msg.metadata.tokens.input} tokens</span>
                )}
                {msg.metadata.tokens?.output !== undefined && (
                  <span>출력: {msg.metadata.tokens.output} tokens</span>
                )}
                {msg.metadata.responseTime !== undefined && (
                  <span>응답시간: {msg.metadata.responseTime}ms</span>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Typing Indicator */}
      {showTypingIndicator && <TypingIndicator agentName={agentName} />}
    </>
  );
}

export default ChatMessageList;
