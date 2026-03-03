/**
 * useLocalChat - Local Agent 채팅을 위한 커스텀 훅
 *
 * SSE 스트리밍, 메시지 관리, 세션 cleanup을 통합 관리합니다.
 * AgentCreate, AgentEdit, Playground에서 공통으로 사용됩니다.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import type { Message } from '../types';
import api from '../utils/axios';

interface UseLocalChatOptions {
  agentId: string;
  onPrepareSuccess?: (sessionId: string) => void;
  onPrepareError?: (error: string) => void;
}

interface PrepareParams {
  system_prompt: string;
  model: string;
  mcp_ids: string[];
  kb_ids: string[];
}

interface UseLocalChatReturn {
  // State
  messages: Message[];
  inputMessage: string;
  sending: boolean;
  isPrepared: boolean;
  preparing: boolean;
  localSessionId: string | null;
  isDirty: boolean;

  // Actions
  setInputMessage: (msg: string) => void;
  setIsDirty: (dirty: boolean) => void;
  prepare: (params: PrepareParams) => Promise<void>;
  sendMessage: () => Promise<void>;
  clearMessages: () => void;
  cleanup: () => void;
}

export function useLocalChat({ agentId, onPrepareSuccess, onPrepareError }: UseLocalChatOptions): UseLocalChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [isPrepared, setIsPrepared] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [localSessionId, setLocalSessionId] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  const localSessionRef = useRef<string | null>(null);

  // Keep ref in sync with state
  useEffect(() => {
    localSessionRef.current = localSessionId;
  }, [localSessionId]);

  // Session cleanup function
  const cleanupLocalSession = useCallback(async (sessionId: string, agentIdParam: string) => {
    try {
      await api.delete(`/agents/local-chat/${agentIdParam}/session/${sessionId}`);
    } catch (error) {
      // Cleanup 실패는 조용히 무시
    }
  }, []);

  // Cleanup on page unload/close
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (localSessionRef.current && agentId) {
        const apiBaseUrl = import.meta.env.DEV ? 'http://localhost:8000' : '';

        navigator.sendBeacon(
          `${apiBaseUrl}/api/v1/agents/local-chat/${agentId}/session/${localSessionRef.current}/cleanup`,
          ''
        );
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      if (localSessionRef.current && agentId) {
        cleanupLocalSession(localSessionRef.current, agentId);
      }
    };
  }, [agentId, cleanupLocalSession]);

  // Prepare agent
  const prepare = useCallback(async (params: PrepareParams) => {
    setPreparing(true);
    setIsPrepared(false);

    try {
      // 기존 세션이 있고 설정이 변경되지 않았다면 재사용
      if (localSessionId && !isDirty) {
        setIsPrepared(true);
        setPreparing(false);
        return;
      }

      // 새로운 로컬 세션 준비 - 메시지 초기화
      setMessages([]);

      const response = await api.post(`/agents/local-chat/${agentId}/prepare`, params);

      const sessionId = response.data.session_id;
      setLocalSessionId(sessionId);
      setIsPrepared(true);
      setIsDirty(false);
      onPrepareSuccess?.(sessionId);
    } catch (error: any) {
      console.error('Failed to prepare local agent:', error);
      const errorMessage = error.response?.data?.detail || 'Local Agent 준비 실패';
      onPrepareError?.(errorMessage);
    } finally {
      setPreparing(false);
    }
  }, [agentId, localSessionId, isDirty, onPrepareSuccess, onPrepareError]);

  // Send message with SSE streaming
  const sendMessage = useCallback(async () => {
    if (!inputMessage.trim() || sending) return;

    if (!localSessionId) {
      alert('Agent가 준비되지 않았습니다. Prepare를 먼저 클릭하세요.');
      return;
    }

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    const messageContent = inputMessage;
    setInputMessage('');
    setSending(true);

    try {
      const apiBaseUrl = import.meta.env.DEV ? 'http://localhost:8000' : '';

      const response = await fetch(`${apiBaseUrl}/api/v1/agents/local-chat/${agentId}/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ session_id: localSessionId, message: messageContent }),
      });

      if (!response.ok || !response.body) {
        throw new Error('Stream failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';

      // Placeholder message
      const assistantMessage: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMessage]);

      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            if (!data) continue;

            try {
              const parsed = JSON.parse(data);

              if (parsed.type === 'progress') {
                // Progress 이벤트 (XML 태그 파싱 결과)
                const progressId = parsed.id;
                const progressStatus = parsed.status; // 'start' | 'done'
                const progressLabel = parsed.label || '처리 중...';

                if (progressStatus === 'start') {
                  // 새 progress 시작 - tools 배열에 추가
                  setMessages(prev => {
                    const updated = [...prev];
                    const lastMsg = updated[updated.length - 1];
                    if (lastMsg && lastMsg.role === 'assistant') {
                      lastMsg.tools = lastMsg.tools || [];

                      // 같은 id가 이미 있으면 추가하지 않음
                      const alreadyExists = lastMsg.tools.some(t => t.id === `progress-${progressId}`);
                      if (!alreadyExists) {
                        // 같은 label의 도구가 error 상태로 존재하면 재시도로 처리
                        const errorToolIndex = lastMsg.tools.findIndex(
                          t => t.name === progressLabel && t.status === 'error'
                        );

                        if (errorToolIndex !== -1) {
                          // 기존 error 도구를 재시도 중으로 변경
                          lastMsg.tools[errorToolIndex] = {
                            ...lastMsg.tools[errorToolIndex],
                            id: `progress-${progressId}`,  // 새 ID로 업데이트
                            name: `${progressLabel} (재시도)`,
                            status: 'loading'
                          };
                        } else {
                          // 새로운 도구 추가
                          lastMsg.tools.push({
                            id: `progress-${progressId}`,
                            name: progressLabel,
                            status: 'loading'
                          });
                        }
                      }
                    }
                    return updated;
                  });
                } else if (progressStatus === 'done') {
                  // Progress 완료 - 해당 id의 상태를 completed로
                  // 실제 도구 실패는 tool_result 이벤트에서 error로 처리됨
                  const progressContent = parsed.content;  // thinking 내용 (있는 경우)
                  setMessages(prev => {
                    const updated = [...prev];
                    const lastMsg = updated[updated.length - 1];
                    if (lastMsg && lastMsg.role === 'assistant' && lastMsg.tools) {
                      const targetIndex = lastMsg.tools.findIndex(t => t.id === `progress-${progressId}`);
                      if (targetIndex !== -1) {
                        lastMsg.tools[targetIndex] = {
                          ...lastMsg.tools[targetIndex],
                          name: progressLabel,
                          status: 'completed',
                          ...(progressContent && { content: progressContent })
                        };
                      }
                    }
                    return updated;
                  });
                }

              } else if (parsed.type === 'tool_use') {
                // 도구 사용 이벤트 (Bedrock API 형식 - 하위 호환)
                const toolName = parsed.tool_name || 'Unknown Tool';
                let displayName = toolName;
                if (toolName.startsWith('retrieve_from_')) {
                  const kbName = toolName.replace('retrieve_from_', '').replace(/_/g, '-');
                  displayName = `Knowledge Base "${kbName}" 조회`;
                } else {
                  displayName = `"${toolName}" 도구 사용`;
                }

                setMessages(prev => {
                  const updated = [...prev];
                  const lastMsg = updated[updated.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant') {
                    lastMsg.tools = lastMsg.tools || [];

                    // 같은 이름의 도구가 error 상태로 존재하면 재시도로 처리
                    const errorToolIndex = lastMsg.tools.findIndex(
                      t => t.name === displayName && t.status === 'error'
                    );

                    if (errorToolIndex !== -1) {
                      // 기존 error 도구를 재시도 중으로 변경
                      lastMsg.tools[errorToolIndex] = {
                        ...lastMsg.tools[errorToolIndex],
                        name: `${displayName} (재시도)`,
                        status: 'loading'
                      };
                    } else {
                      // 새로운 도구 추가 (이미 loading이나 completed 상태로 존재하지 않는 경우만)
                      const alreadyExists = lastMsg.tools.some(
                        t => t.name === displayName || t.name === `${displayName} (재시도)`
                      );
                      if (!alreadyExists) {
                        lastMsg.tools.push({
                          id: `tool-${Date.now()}-${Math.random()}`,
                          name: displayName,
                          status: 'loading'
                        });
                      }
                    }
                  }
                  return updated;
                });

              } else if (parsed.type === 'tool_result') {
                // 도구 사용 완료 이벤트 (Bedrock API 형식 - 하위 호환)
                const resultStatus = parsed.status === 'error' ? 'error' : 'completed';
                setMessages(prev => {
                  const updated = [...prev];
                  const lastMsg = updated[updated.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant' && lastMsg.tools) {
                    const lastLoadingIndex = lastMsg.tools.map(t => t.status).lastIndexOf('loading');
                    if (lastLoadingIndex !== -1) {
                      lastMsg.tools[lastLoadingIndex] = {
                        ...lastMsg.tools[lastLoadingIndex],
                        status: resultStatus as 'completed' | 'error'
                      };
                    }
                  }
                  return updated;
                });

              } else if (parsed.type === 'content' || parsed.type === 'text') {
                // 텍스트 이벤트
                const textContent = parsed.content || '';
                accumulatedContent += textContent;
                setMessages(prev => {
                  const updated = [...prev];
                  const lastMsg = updated[updated.length - 1];

                  if (lastMsg && lastMsg.role === 'assistant') {
                    // 도구 호출이 완료된 메시지에 새 텍스트가 오는 경우
                    // (도구가 있고, 모든 도구가 completed/error 상태)
                    const hasCompletedTools = lastMsg.tools &&
                      lastMsg.tools.length > 0 &&
                      lastMsg.tools.every(t => t.status === 'completed' || t.status === 'error');

                    if (hasCompletedTools) {
                      // 도구 완료 후 새 텍스트는 새 말풍선에서 시작
                      // 이전 말풍선의 텍스트는 그대로 유지
                      updated.push({
                        id: `msg-${Date.now()}`,
                        role: 'assistant',
                        content: textContent,
                        timestamp: new Date().toISOString()
                      });
                      // 새 말풍선부터 새로 누적 시작
                      accumulatedContent = textContent;
                    } else {
                      // 도구 호출 중이거나 도구가 없는 경우 - 텍스트 누적
                      lastMsg.content = accumulatedContent;
                    }
                  }
                  return updated;
                });

              } else if (parsed.type === 'done') {
                // 완료 이벤트 - 모든 loading 상태를 completed로
                setMessages(prev => prev.map(msg => {
                  if (msg.role === 'assistant' && msg.tools) {
                    return {
                      ...msg,
                      tools: msg.tools.map(tool =>
                        tool.status === 'loading' ? { ...tool, status: 'completed' as const } : tool
                      )
                    };
                  }
                  return msg;
                }));

              } else if (parsed.type === 'error') {
                const errorContent = parsed.content || parsed.message || parsed.error || '알 수 없는 오류가 발생했습니다';
                console.error('Stream error:', errorContent);
                setMessages(prev => {
                  const updated = [...prev];
                  updated[updated.length - 1].content = `오류: ${errorContent}`;
                  return updated;
                });
                break;
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', line);
            }
          }
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('메시지 전송 실패');
    } finally {
      setSending(false);
    }
  }, [agentId, inputMessage, localSessionId, sending]);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const cleanup = useCallback(() => {
    if (localSessionId && agentId) {
      cleanupLocalSession(localSessionId, agentId);
    }
    setLocalSessionId(null);
    setIsPrepared(false);
    setMessages([]);
  }, [localSessionId, agentId, cleanupLocalSession]);

  return {
    messages,
    inputMessage,
    sending,
    isPrepared,
    preparing,
    localSessionId,
    isDirty,
    setInputMessage,
    setIsDirty,
    prepare,
    sendMessage,
    clearMessages,
    cleanup,
  };
}
