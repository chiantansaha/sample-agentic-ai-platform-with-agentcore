import { useState, useEffect, useRef } from 'react';
import { flushSync } from 'react-dom';
import { useSearchParams } from 'react-router-dom';
import { Maximize2 } from 'lucide-react';
import { Card, Badge, ChatMessageList } from '../../components/common';
import ChatModal from '../../components/common/ChatModal';
import type { Agent, AgentVersion, Message, KnowledgeBase, MCP, Deployment, Conversation, ConversationList } from '../../types';
import api from '../../utils/axios';
import { formatLocalTime, formatLocalDate, formatLocalDateTime } from '../../utils/date';

export function Playground() {
  const [searchParams] = useSearchParams();
  const [productionAgents, setProductionAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [selectedVersion, setSelectedVersion] = useState<string>('');
  const [availableVersions, setAvailableVersions] = useState<AgentVersion[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // AgentCore Runtime state
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [deploying, setDeploying] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [showConversations, setShowConversations] = useState(false);
  const [forceRebuild, setForceRebuild] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [showGuideModal, setShowGuideModal] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Resource lookup maps
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [mcps, setMcps] = useState<MCP[]>([]);

  // 메시지 영역 자동 스크롤
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Fetch resources on mount
  useEffect(() => {
    const fetchResources = async () => {
      try {
        const [agentsRes, kbsRes, mcpsRes] = await Promise.all([
          api.get('/playground/agents'),
          api.get('/knowledge-bases'),
          api.get('/mcps/'),
        ]);
        setProductionAgents(agentsRes.data.data || []);
        setKnowledgeBases(kbsRes.data.data || []);
        setMcps(mcpsRes.data.data || []);
      } catch (error) {
        console.error('Failed to fetch resources:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchResources();
  }, []);

  // URL 파라미터로 agent와 version 자동 선택
  useEffect(() => {
    const agentParam = searchParams.get('agent');
    const versionParam = searchParams.get('version');

    if (agentParam && productionAgents.length > 0) {
      // Agent가 목록에 있는지 확인
      const agentExists = productionAgents.find(a => a.id === agentParam);
      if (agentExists) {
        setSelectedAgentId(agentParam);

        // Version이 URL에 있으면 설정 (버전 목록 로드 후 useEffect에서 자동 선택됨)
        if (versionParam) {
          setSelectedVersion(versionParam);
        }
      }
    }
  }, [searchParams, productionAgents]);

  // Load versions when agent is selected
  useEffect(() => {
    if (selectedAgentId) {
      const fetchVersions = async () => {
        try {
          const response = await api.get(`/playground/agents/${selectedAgentId}/versions`);
          const versions = response.data.data || [];
          setAvailableVersions(versions);

          // URL에서 버전이 지정된 경우 해당 버전 선택, 아니면 최신 버전 선택
          const versionParam = searchParams.get('version');

          if (versionParam && versions.some(v => {
            const vStr = typeof v.version === 'string'
              ? v.version
              : v.version && typeof v.version === 'object' && 'major' in v.version
                ? `${v.version.major}.${v.version.minor}.${v.version.patch}`
                : '';
            return vStr === versionParam;
          })) {
            // URL 파라미터의 버전이 존재하면 선택
            setSelectedVersion(versionParam);
          } else if (versions.length > 0) {
            // 그렇지 않으면 최신 버전 (첫 번째) 선택
            const firstVersion = versions[0].version;
            const versionStr = typeof firstVersion === 'string'
              ? firstVersion
              : firstVersion && typeof firstVersion === 'object' && 'major' in firstVersion
                ? `${firstVersion.major}.${firstVersion.minor}.${firstVersion.patch}`
                : '';
            setSelectedVersion(versionStr);
          } else {
            setSelectedVersion('');
          }
        } catch (error) {
          console.error('Failed to fetch agent versions:', error);
          setAvailableVersions([]);
          setSelectedVersion('');
        }
      };

      fetchVersions();
      // Clear state when changing agent
      setMessages([]);
      setDeployment(null);
      setConversations([]);
      setSelectedConversationId(null);
    } else {
      setAvailableVersions([]);
      setSelectedVersion('');
      setMessages([]);
      setDeployment(null);
      setConversations([]);
    }
  }, [selectedAgentId, searchParams]);

  // Clear messages when version changes
  useEffect(() => {
    setMessages([]);
    setDeployment(null);
    setConversations([]);
    setSelectedConversationId(null);
  }, [selectedVersion]);

  // Load conversations when version is selected
  useEffect(() => {
    if (selectedAgentId && selectedVersion) {
      fetchConversations();
    }
  }, [selectedAgentId, selectedVersion]);

  // Fetch conversations
  const fetchConversations = async () => {
    if (!selectedAgentId || !selectedVersion) return;
    setLoadingConversations(true);
    try {
      const response = await api.get(`/playground/conversations`, {
        params: { agent_id: selectedAgentId, version: selectedVersion }
      });
      const data: ConversationList = response.data.data;
      setConversations(data.conversations || []);
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
      setConversations([]);
    } finally {
      setLoadingConversations(false);
    }
  };

  // Deploy agent to AgentCore Runtime
  const deployRuntime = async (conversationId?: string) => {
    if (!selectedAgentId || !selectedVersion) return;

    // 이전 대화 이어하기: 기존 deployment 재사용 (메모리에 있는 경우)
    if (conversationId && deployment) {
      const isCompatible =
        deployment.agent_id === selectedAgentId &&
        deployment.version === selectedVersion;
      const isReady = deployment.status === 'ready';

      if (isCompatible && isReady) {
        // 같은 agent/version의 ready 상태 deployment가 있으면 즉시 재사용
        setSelectedConversationId(conversationId);
        setShowConversations(false);

        // Load previous conversation messages
        setLoadingMessages(true);
        try {
          const response = await api.get(`/playground/conversations/${conversationId}/messages`);
          const previousMessages = response.data.data || [];
          setMessages(previousMessages);
        } catch (error) {
          console.error('Failed to load previous messages:', error);
          alert('이전 대화 내역을 불러오는데 실패했습니다.');
          setMessages([]);
        } finally {
          setLoadingMessages(false);
        }
        return;
      }
    }

    // 페이지 새로고침 후 이전 대화 선택: 서버에서 기존 배포 조회
    if (conversationId && !deployment) {
      try {
        const activeResponse = await api.get('/playground/runtime/deployments/active', {
          params: { agent_id: selectedAgentId, version: selectedVersion }
        });
        const activeDeployment = activeResponse.data.data;

        if (activeDeployment && activeDeployment.status === 'ready') {
          // 기존 ready 배포가 있으면 즉시 재사용
          console.log('Reusing existing deployment from server:', activeDeployment.deployment_id);
          setDeployment(activeDeployment);
          setSelectedConversationId(conversationId);
          setShowConversations(false);

          // Load previous conversation messages
          setLoadingMessages(true);
          try {
            const response = await api.get(`/playground/conversations/${conversationId}/messages`);
            const previousMessages = response.data.data || [];
            setMessages(previousMessages);
          } catch (error) {
            console.error('Failed to load previous messages:', error);
            alert('이전 대화 내역을 불러오는데 실패했습니다.');
            setMessages([]);
          } finally {
            setLoadingMessages(false);
          }
          return;
        }
      } catch (error) {
        console.warn('Failed to check for existing deployment:', error);
        // 실패해도 새 배포로 진행
      }
    }

    // 새 배포 시작 (기존 배포가 없는 경우)
    setDeploying(true);
    setDeployment(null);
    setSelectedConversationId(conversationId || null);

    // 이전 대화를 불러오는 경우 먼저 메시지 로드
    if (conversationId) {
      setLoadingMessages(true);
      try {
        const response = await api.get(`/playground/conversations/${conversationId}/messages`);
        const previousMessages = response.data.data || [];
        setMessages(previousMessages);
      } catch (error) {
        console.error('❌ Failed to load previous messages:', error);
        alert('이전 대화 내역을 불러오는데 실패했습니다.');
        setMessages([]);
      } finally {
        setLoadingMessages(false);
      }
    }

    try {
      const response = await api.post('/playground/runtime/deploy', {
        agent_id: selectedAgentId,
        version: selectedVersion,
        conversation_id: conversationId,
        force_rebuild: forceRebuild
      });

      const deploymentData: Deployment = response.data.data;
      setDeployment(deploymentData);

      // Poll for ready status if not already ready
      if (deploymentData.status !== 'ready') {
        pollDeploymentStatus(deploymentData.id);
      }
    } catch (error: any) {
      console.error('Failed to deploy runtime:', error);
      const errorMessage = error.response?.data?.detail || 'Runtime 배포 실패';
      alert(errorMessage);
    } finally {
      setDeploying(false);
    }
  };

  // Poll deployment status
  const pollDeploymentStatus = async (deploymentId: string) => {
    const maxAttempts = 100; // 3초 * 100 = 5분
    let attempts = 0;

    const poll = async () => {
      try {
        const response = await api.get(`/playground/runtime/deployments/${deploymentId}/status`);
        const status = response.data.data;

        setDeployment(prev => prev ? { ...prev, ...status } : null);

        if (status.status === 'ready') {
          return;
        } else if (status.status === 'failed') {
          alert('Runtime 배포 실패: ' + (status.error_message || 'Unknown error'));
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 3000); // 3초마다 폴링 (5초 → 3초)
        } else {
          alert('Runtime 배포 시간 초과 (5분)');
        }
      } catch (error) {
        console.error('Failed to poll deployment status:', error);
        // 에러 발생 시 재시도
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 3000);
        }
      }
    };

    poll();
  };

  // Destroy runtime
  const destroyRuntime = async () => {
    if (!deployment) return;

    try {
      await api.delete(`/playground/runtime/deployments/${deployment.id}`);
      setDeployment(null);
      setMessages([]);
    } catch (error) {
      console.error('Failed to destroy runtime:', error);
    }
  };

  // Delete conversation
  const deleteConversation = async (conversationId: string) => {
    try {
      await api.delete(`/playground/conversations/${conversationId}`);
      fetchConversations();
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  // AgentCore Runtime 메시지 전송
  const sendMessage = async () => {
    if (!input.trim() || sending) return;
    if (!deployment || deployment.status !== 'ready') {
      alert('Runtime이 준비되지 않았습니다.');
      return;
    }

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    const messageContent = input;
    setInput('');
    setSending(true);

    // Note: Conversation은 Backend에서 자동 생성됨 (첫 메시지 시)
    // 프론트엔드는 별도 생성 불필요

    const assistantMessageId = `msg-${Date.now() + 1}`;
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, assistantMessage]);

    try {
      const endpoint = `/playground/runtime/deployments/${deployment.id}/chat/stream`;
      abortControllerRef.current = new AbortController();
      let metadata: Message['metadata'] | undefined;

      // SSE는 Vite 프록시를 우회 (개발 환경)
      // 프록시가 스트리밍을 버퍼링하는 것을 방지
      const apiBaseUrl = import.meta.env.DEV
        ? 'http://localhost:8000'
        : '';

      // fetch로 SSE 스트리밍
      const response = await fetch(`${apiBaseUrl}/api/v1${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ message: messageContent }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            if (!data) continue;

            try {
              const parsed = JSON.parse(data);
              handleStreamEvent(parsed, assistantMessageId, (m) => { metadata = m; });
            } catch (e) {
              // Parse error - skip
            }
          }
        }
      }

      if (metadata) {
        setMessages(prev => prev.map(msg =>
          msg.id === assistantMessageId ? { ...msg, metadata } : msg
        ));
      }

      // 첫 메시지였다면 Conversation 목록 새로고침 (Backend가 자동 생성)
      if (!selectedConversationId) {
        fetchConversations();
      }
    } catch (error) {
      handleStreamError(error, assistantMessageId);
    } finally {
      setSending(false);
      abortControllerRef.current = null;
    }
  };

  // Handle stream events
  const handleStreamEvent = (
    parsed: any,
    assistantMessageId: string,
    setMetadata: (m: Message['metadata']) => void
  ): boolean => {
    // 처리할 수 없는 이벤트는 무시
    if (!parsed || !parsed.type) {
      return false;
    }

    // thinking 이벤트 (reasoning)
    if (parsed.type === 'thinking') {
      setMessages(prev => {
        const updated = [...prev];
        const lastMsg = updated[updated.length - 1];

        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.tools = lastMsg.tools || [];

          // thinking이 이미 있는지 확인
          const existingThinking = lastMsg.tools.find(t => t.name === 'Thinking...');
          if (!existingThinking) {
            lastMsg.tools.push({
              id: `thinking-${Date.now()}`,
              name: 'Thinking...',
              status: 'loading'
            });
          }
        }

        return updated;
      });

      return true;
    }

    // 도구 사용 이벤트 (KB/MCP 조회)
    if (parsed.type === 'tool_use') {
      const toolName = parsed.tool_name || 'Unknown Tool';
      let displayName = toolName;

      // KB 도구인지 확인 (retrieve_from_xxx 형태)
      if (toolName.startsWith('retrieve_from_')) {
        const kbName = toolName.replace('retrieve_from_', '').replace(/_/g, '-');
        displayName = `Knowledge Base "${kbName}" 조회`;
      } else if (toolName.includes('_')) {
        // MCP 도구 (prefix_toolname 형태)
        const parts = toolName.split('_');
        const prefix = parts[0];
        const action = parts.slice(1).join('_');
        displayName = `${prefix}: ${action}`;
      } else {
        displayName = `${toolName}`;
      }

      // 현재 assistant 메시지의 tools 배열에 추가 (중복 체크)
      setMessages(prev => {
        const updated = [...prev];
        const lastMsg = updated[updated.length - 1];

        // 마지막 메시지가 assistant면 tools 배열에 추가
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.tools = lastMsg.tools || [];

          // Thinking이 있으면 completed로 변경
          const thinkingTool = lastMsg.tools.find(t => t.name === 'Thinking...' && t.status === 'loading');
          if (thinkingTool) {
            thinkingTool.status = 'completed';
          }

          // 같은 이름의 도구가 이미 있는지 확인 (중복 방지)
          const alreadyExists = lastMsg.tools.some(t => t.name === displayName);
          if (!alreadyExists) {
            lastMsg.tools.push({
              id: `tool-${Date.now()}-${Math.random()}`,
              name: displayName,
              status: 'loading'
            });
          }
        }

        return updated;
      });

      return true;
    }

    // 도구 사용 완료 이벤트 (tool_result)
    if (parsed.type === 'tool_result') {
      // 마지막 loading 상태의 tool만 completed로 변경
      // 새 메시지는 생성하지 않음 (모든 도구가 같은 메시지에 표시됨)
      setMessages(prev => {
        const updated = [...prev];
        const lastMsg = updated[updated.length - 1];

        // 마지막 메시지가 assistant이고 tools가 있으면 마지막 loading tool을 completed로 변경
        if (lastMsg && lastMsg.role === 'assistant' && lastMsg.tools) {
          // 마지막 loading 상태의 tool 찾기
          const lastLoadingIndex = lastMsg.tools.map(t => t.status).lastIndexOf('loading');
          if (lastLoadingIndex !== -1) {
            lastMsg.tools[lastLoadingIndex] = {
              ...lastMsg.tools[lastLoadingIndex],
              status: 'completed' as const
            };
          }
        }

        return updated;
      });

      return true;
    }

    // 텍스트 델타 이벤트 - 실시간으로 메시지에 추가
    if (parsed.type === 'text') {
      const textContent = parsed.content ?? '';

      // XML 태그 필터링 (Agent 내부 function call 태그)
      const xmlPatterns = [
        '<function_calls>', '</function_calls>',
        '<invoke', '</invoke>',
        '<parameter', '</parameter>',
        '<function_result>', '</function_result>'
      ];
      const hasXmlTag = xmlPatterns.some(pattern => textContent.includes(pattern));
      if (hasXmlTag) {
        return true; // XML 태그가 포함된 텍스트는 건너뛰기
      }

      if (textContent) {
        // 텍스트 추가 - 마지막 assistant 메시지에 추가
        flushSync(() => {
          setMessages(prev => {
            const updated = [...prev];
            const lastMsg = updated[updated.length - 1];

            // 마지막 메시지가 assistant이고, tools가 있고, content도 이미 있으면 새 메시지 생성
            // (텍스트 → 도구 → 텍스트 패턴에서 메시지 분리)
            if (lastMsg && lastMsg.role === 'assistant' && lastMsg.tools && lastMsg.tools.length > 0 && lastMsg.content) {
              // 새로운 assistant 메시지 생성
              updated.push({
                id: `msg-${Date.now()}`,
                role: 'assistant',
                content: textContent,
                timestamp: new Date().toISOString()
              });
            } else {
              // 마지막 assistant 메시지에 텍스트 추가
              for (let i = updated.length - 1; i >= 0; i--) {
                if (updated[i].role === 'assistant') {
                  updated[i] = {
                    ...updated[i],
                    content: updated[i].content + textContent
                  };
                  break;
                }
              }
            }
            return updated;
          });
        });
        return true;
      }
      return false;
    }

    // 메시지 완료 이벤트
    if (parsed.type === 'done') {
      // 모든 assistant 메시지의 loading 상태 tools를 completed로 변경
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
      return true;
    }

    // 최종 완성된 메시지 (선택적으로 사용)
    if (parsed.type === 'complete') {
      // 이미 델타로 조합된 메시지가 있으므로 무시하거나
      // 필요시 최종 검증용으로 사용 가능
      return true;
    }

    // 에러 이벤트
    if (parsed.type === 'error') {
      const errorContent = parsed.content || parsed.message || parsed.error || '알 수 없는 오류가 발생했습니다';
      setMessages(prev => prev.map(msg =>
        msg.id === assistantMessageId
          ? { ...msg, content: `오류: ${errorContent}` }
          : msg
      ));
      return true;
    }

    return false;
  };

  // Handle stream errors
  const handleStreamError = (error: any, assistantMessageId: string) => {
    if ((error as Error).name === 'CanceledError') {
      // Request cancelled by user - no action needed
    } else {
      console.error('Failed to stream message:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || '알 수 없는 오류가 발생했습니다.';
      setMessages(prev => prev.map(msg =>
        msg.id === assistantMessageId
          ? { ...msg, content: `죄송합니다. 메시지를 전송하는 중 오류가 발생했습니다.\n\n오류 내용: ${errorMessage}` }
          : msg
      ));
    }
  };

  // 전송 취소
  const cancelSending = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  // 대화 초기화
  const resetChat = () => {
    setMessages([]);
    setSelectedConversationId(null);
    if (deployment) {
      destroyRuntime();
    }
  };

  const selectedAgent = productionAgents.find(a => a.id === selectedAgentId);
  const selectedVersionData = availableVersions.find(v => {
    const versionStr = typeof v.version === 'string'
      ? v.version
      : v.version && typeof v.version === 'object' && 'major' in v.version
        ? `${v.version.major}.${v.version.minor}.${v.version.patch}`
        : '';
    return versionStr === selectedVersion;
  });
  const canChat = selectedAgentId && selectedVersion && deployment?.status === 'ready';

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Playground</h1>
          <p className="text-gray-600 mt-1">에이전트와 버전을 선택하여 테스트하세요</p>
        </div>
        <Card className="p-12">
          <div className="flex items-center justify-center">
            <div className="text-gray-500">로딩 중...</div>
          </div>
        </Card>

        {/* Floating Guide Button - 로딩 중에도 표시 */}
        <button
          onClick={() => setShowGuideModal(true)}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all duration-200 hover:shadow-xl"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="font-medium">Playground란?</span>
        </button>

        {/* Guide Modal - 로딩 중에도 표시 */}
        {showGuideModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setShowGuideModal(false)}>
            <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4" onClick={(e) => e.stopPropagation()}>
              <div className="p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex-shrink-0 w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-gray-900">Playground</h3>
                    <p className="text-sm text-gray-600">Agent 테스트 환경</p>
                  </div>
                  <button
                    onClick={() => setShowGuideModal(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <p className="text-gray-600 mb-4">
                  Agent를 선택하고 AgentCore Runtime에 배포하여 실시간으로 테스트할 수 있습니다.
                </p>
                <div className="space-y-2 text-sm text-gray-600">
                  <p>배포 프로세스: Pending → Building (2-3분) → Creating → Ready</p>
                  <p>최대 5개 대화 저장, Runtime 유휴 시간 30분</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Playground</h1>
        <p className="text-gray-600 mt-1">에이전트와 버전을 선택하여 테스트하세요</p>
      </div>

      {/* Floating Guide Button */}
      <button
        onClick={() => setShowGuideModal(true)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all duration-200 hover:shadow-xl"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="font-medium">Playground란?</span>
      </button>

      {/* Guide Modal */}
      {showGuideModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setShowGuideModal(false)}>
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0 w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">Playground 가이드</h3>
                  <p className="text-sm text-gray-600">Agent를 AgentCore Runtime에 배포하여 실시간으로 테스트할 수 있습니다</p>
                </div>
              </div>
              <button
                onClick={() => setShowGuideModal(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Deployment 개념 */}
                <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg p-5 border border-purple-100">
                  <div className="flex items-center gap-2 mb-4">
                    <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                    </svg>
                    <h4 className="font-semibold text-gray-900 text-lg">배포 프로세스</h4>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-start gap-3 bg-white rounded-lg p-3 shadow-sm">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center text-sm font-bold mt-0.5">1</span>
                      <div>
                        <p className="font-medium text-gray-900">Pending</p>
                        <p className="text-sm text-gray-600">Agent 코드 및 Dockerfile 생성 중</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3 bg-white rounded-lg p-3 shadow-sm">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center text-sm font-bold mt-0.5">2</span>
                      <div>
                        <p className="font-medium text-gray-900">Building</p>
                        <p className="text-sm text-gray-600">ARM64 컨테이너 이미지 빌드 및 ECR 푸시</p>
                        <p className="text-xs text-gray-500 mt-1">S3 소스 업로드, CodeBuild 트리거, Docker 빌드, ECR 푸시 (약 2-3분 소요)</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3 bg-white rounded-lg p-3 shadow-sm">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center text-sm font-bold mt-0.5">3</span>
                      <div>
                        <p className="font-medium text-gray-900">Creating</p>
                        <p className="text-sm text-gray-600">AgentCore Runtime 생성 중 (약 30초-1분 소요)</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3 bg-white rounded-lg p-3 shadow-sm">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-sm font-bold mt-0.5">4</span>
                      <div>
                        <p className="font-medium text-gray-900">Ready</p>
                        <p className="text-sm text-gray-600">배포 완료, 채팅 시작 가능</p>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t border-purple-200 space-y-2">
                    <div className="bg-white rounded-lg p-3">
                      <p className="text-sm text-gray-600 flex items-center gap-2">
                        <svg className="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="font-medium">예상 소요 시간: 약 3-4분 (ECR 이미지 캐싱 시 30초-1분)</span>
                      </p>
                    </div>
                    <div className="bg-blue-50 rounded-lg p-3 border border-blue-100">
                      <p className="text-xs font-medium text-blue-900 mb-1">빌드 환경</p>
                      <ul className="space-y-1 text-xs text-blue-800">
                        <li>AWS CodeBuild 기반 빌드 (로컬 Docker 미사용)</li>
                        <li>ECS Fargate 배포 환경과 일관된 빌드</li>
                        <li>환경변수: CODEBUILD_PROJECT_NAME, AGENT_BUILD_SOURCE_BUCKET</li>
                      </ul>
                    </div>
                  </div>
                </div>

                {/* Conversation 개념 */}
                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-5 border border-blue-100">
                  <div className="flex items-center gap-2 mb-4">
                    <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    <h4 className="font-semibold text-gray-900 text-lg">대화 관리</h4>
                  </div>
                  <div className="space-y-4">
                    <div className="bg-white rounded-lg p-4 shadow-sm">
                      <p className="font-medium text-gray-900 mb-2">저장 정책</p>
                      <ul className="space-y-2 text-sm text-gray-600">
                        <li className="flex items-start gap-2">
                          <span className="text-blue-600 mt-1">-</span>
                          <span>Agent/Version별 최대 5개 대화 저장</span>
                        </li>
                        <li className="flex items-start gap-2">
                          <span className="text-blue-600 mt-1">-</span>
                          <span>대화 이력은 S3에 자동 저장 (30일 보관)</span>
                        </li>
                        <li className="flex items-start gap-2">
                          <span className="text-blue-600 mt-1">-</span>
                          <span>5개 초과 시 가장 오래된 대화 자동 삭제</span>
                        </li>
                      </ul>
                    </div>
                    <div className="bg-white rounded-lg p-4 shadow-sm">
                      <p className="font-medium text-gray-900 mb-2">이전 대화 이어하기</p>
                      <ul className="space-y-2 text-sm text-gray-600">
                        <li className="flex items-start gap-2">
                          <span className="text-green-600 mt-1">-</span>
                          <span>기존 Runtime 재사용 가능 (대기 시간 없음)</span>
                        </li>
                        <li className="flex items-start gap-2">
                          <span className="text-green-600 mt-1">-</span>
                          <span>이전 대화 맥락 자동 복원</span>
                        </li>
                        <li className="flex items-start gap-2">
                          <span className="text-green-600 mt-1">-</span>
                          <span>첫 메시지부터 전체 이력 확인 가능</span>
                        </li>
                      </ul>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t border-blue-200 bg-white rounded-lg p-3">
                    <p className="text-sm text-gray-600 flex items-center gap-2">
                      <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span>Runtime 유휴 시간: 최대 30분, 전체 수명: 최대 3시간</span>
                    </p>
                  </div>
                </div>
              </div>

              {/* 기술 아키텍처 */}
              <div className="mt-6 bg-gradient-to-br from-gray-50 to-slate-50 rounded-lg p-5 border border-gray-200">
                <div className="flex items-center gap-2 mb-4">
                  <svg className="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                  <h4 className="font-semibold text-gray-900 text-lg">기술 아키텍처</h4>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-white rounded-lg p-4 shadow-sm">
                    <p className="font-medium text-gray-900 mb-2 flex items-center gap-2">
                      <span className="text-purple-600">1.</span>
                      코드 생성
                    </p>
                    <ul className="space-y-1 text-xs text-gray-600">
                      <li>Agent 코드 (Jinja2 템플릿)</li>
                      <li>Dockerfile (ARM64 지원)</li>
                      <li>buildspec.yml (CodeBuild)</li>
                      <li>requirements.txt</li>
                    </ul>
                  </div>
                  <div className="bg-white rounded-lg p-4 shadow-sm">
                    <p className="font-medium text-gray-900 mb-2 flex items-center gap-2">
                      <span className="text-blue-600">2.</span>
                      빌드 및 배포
                    </p>
                    <ul className="space-y-1 text-xs text-gray-600">
                      <li>S3 소스 업로드</li>
                      <li>CodeBuild 트리거</li>
                      <li>Docker 빌드 (linux/arm64)</li>
                      <li>ECR 이미지 푸시</li>
                      <li>AgentCore Runtime 생성</li>
                    </ul>
                  </div>
                  <div className="bg-white rounded-lg p-4 shadow-sm">
                    <p className="font-medium text-gray-900 mb-2 flex items-center gap-2">
                      <span className="text-green-600">3.</span>
                      세션 관리
                    </p>
                    <ul className="space-y-1 text-xs text-gray-600">
                      <li>DynamoDB 메타데이터</li>
                      <li>S3 대화 히스토리</li>
                      <li>Strands S3SessionManager</li>
                      <li>Runtime 재사용 (동일 Agent/Version)</li>
                    </ul>
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
                    <p className="text-xs font-medium text-amber-900 mb-1 flex items-center gap-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      중요 사항
                    </p>
                    <ul className="space-y-1 text-xs text-amber-800">
                      <li>CodeBuild 빌드는 로컬 Docker를 사용하지 않습니다 (ECS Fargate 배포 환경)</li>
                      <li>buildspecOverride로 동적 생성된 buildspec.yml 전달 (Terraform inline buildspec 대신)</li>
                      <li>ECR 이미지가 이미 존재하면 빌드를 건너뛰고 재사용합니다</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Agent Selection */}
      <Card className="p-6">
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Agent 선택
            </label>
            <select
              value={selectedAgentId}
              onChange={(e) => setSelectedAgentId(e.target.value)}
              disabled={loading || deploying}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              <option value="">Agent를 선택하세요</option>
              {productionAgents.map(agent => {
                const versionStr = typeof agent.currentVersion === 'string'
                  ? agent.currentVersion
                  : agent.currentVersion && typeof agent.currentVersion === 'object' && 'major' in agent.currentVersion
                    ? `${agent.currentVersion.major}.${agent.currentVersion.minor}.${agent.currentVersion.patch}`
                    : null;

                return (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}{versionStr ? ` (v${versionStr})` : ''}
                  </option>
                );
              })}
            </select>
            {selectedAgent && (
              <div className="mt-2 text-sm text-gray-600">
                <p>{selectedAgent.description}</p>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Version 선택
            </label>
            <select
              value={selectedVersion}
              onChange={(e) => setSelectedVersion(e.target.value)}
              disabled={!selectedAgentId || availableVersions.length === 0 || deploying}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              <option value="">Version을 선택하세요</option>
              {availableVersions.map(version => {
                const versionStr = typeof version.version === 'string'
                  ? version.version
                  : version.version && typeof version.version === 'object' && 'major' in version.version
                    ? `${version.version.major}.${version.version.minor}.${version.version.patch}`
                    : '';

                const description = version.change_log || '';

                return (
                  <option key={versionStr} value={versionStr}>
                    {versionStr ? `v${versionStr}` : 'Unknown'}{description ? ` - ${description}` : ''}
                  </option>
                );
              })}
            </select>
          </div>
        </div>

        {/* AgentCore Runtime Controls */}
        {selectedAgentId && selectedVersion && (
          <div className="mt-6 pt-6 border-t">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-medium text-gray-900">AgentCore Runtime</h4>
              {deployment && (
                <Badge
                  variant={deployment.status === 'ready' ? 'success' : deployment.status === 'failed' ? 'error' : 'warning'}
                >
                  {deployment.status}
                </Badge>
              )}
            </div>

            {!deployment ? (
              <div className="space-y-3">
                <div className="flex gap-4 items-center">
                  <button
                    onClick={() => deployRuntime()}
                    disabled={deploying}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:text-gray-700"
                  >
                    {deploying ? '배포 중...' : '새 세션 시작'}
                  </button>
                  <button
                    onClick={() => setShowConversations(!showConversations)}
                    disabled={loadingConversations}
                    className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {loadingConversations ? (
                      <>
                        <svg className="animate-spin h-4 w-4 text-gray-700" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        <span className="text-gray-700">로딩 중...</span>
                      </>
                    ) : (
                      <span>이전 대화 ({conversations.length})</span>
                    )}
                  </button>
                </div>
                <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={forceRebuild}
                    onChange={(e) => setForceRebuild(e.target.checked)}
                    className="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                  />
                  <span>에이전트 재배포 (ECR 이미지 다시 빌드)</span>
                </label>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex gap-4 items-center flex-wrap">
                  <span className="text-sm text-gray-600">
                    Runtime: <code className="bg-gray-100 px-1 rounded text-xs">{deployment.runtime_id}</code>
                  </span>
                  {selectedConversationId && (
                    <span className="text-sm text-gray-600">
                      Session: <code className="bg-blue-50 px-1 rounded text-blue-700 text-xs">{selectedConversationId}</code>
                    </span>
                  )}
                  {deployment.expires_at && (
                    <span className="text-sm text-gray-500">
                      만료: {formatLocalTime(deployment.expires_at)}
                    </span>
                  )}
                  <button
                    onClick={destroyRuntime}
                    className="px-3 py-1 text-red-600 border border-red-300 rounded hover:bg-red-50"
                  >
                    종료
                  </button>
                </div>
                {messages.length > 0 && (
                  <div className="text-xs text-gray-500">
                    현재 대화: {messages.length}개 메시지
                    {messages.length > 0 && messages[0].content && (
                      <span className="ml-2 text-gray-400">
                        "{messages[0].content.slice(0, 30)}{messages[0].content.length > 30 ? '...' : ''}"
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Conversation List */}
            {showConversations && conversations.length > 0 && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                <h5 className="font-medium mb-3">이전 대화</h5>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {conversations.map(conv => (
                    <div key={conv.id} className="flex items-center justify-between p-2 bg-white rounded border">
                      <div className="flex-1">
                        <p className="font-medium text-sm">{conv.title}</p>
                        <p className="text-xs text-gray-500">
                          {formatLocalDate(conv.updated_at)}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            deployRuntime(conv.id);
                            setShowConversations(false);
                          }}
                          disabled={deploying}
                          className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200 disabled:bg-gray-300 disabled:text-gray-600"
                        >
                          이어하기
                        </button>
                        <button
                          onClick={() => deleteConversation(conv.id)}
                          className="px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded"
                        >
                          삭제
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Reset Button */}
        {messages.length > 0 && (
          <div className="mt-4 pt-4 border-t flex justify-end">
            <button
              onClick={resetChat}
              className="text-sm text-red-600 hover:text-red-700"
            >
              대화 초기화
            </button>
          </div>
        )}
      </Card>

      {/* Chat Interface */}
      <div className="grid grid-cols-3 gap-6">
        <Card className="col-span-2 h-[600px] flex flex-col">
          <div className="flex items-center justify-between mb-4 pb-4 border-b">
            <h3 className="font-semibold">Chat</h3>
            <div className="flex items-center gap-3">
              {canChat && (
                <span className="text-sm text-gray-600">
                  {selectedAgent?.name} • {selectedVersion}
                </span>
              )}
              <button
                onClick={() => setIsModalOpen(true)}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                title="확대"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {!selectedAgentId || !selectedVersion ? (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <p className="text-lg mb-2">Agent와 Version을 선택하세요</p>
                <p className="text-sm">선택 후 채팅을 시작할 수 있습니다</p>
              </div>
            </div>
          ) : !deployment ? (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <p className="text-lg mb-2">AgentCore Runtime을 시작하세요</p>
                <p className="text-sm">위의 '새 세션 시작' 버튼을 클릭하세요</p>
              </div>
            </div>
          ) : deployment?.status !== 'ready' ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="w-full max-w-md px-8">
                {/* Progress Steps */}
                <div className="flex items-center justify-between mb-8">
                  {[
                    { key: 'pending', label: '준비', num: 1 },
                    { key: 'building', label: '빌드', num: 2 },
                    { key: 'creating', label: '배포', num: 3 },
                    { key: 'ready', label: '완료', num: 4 },
                  ].map((step, idx, arr) => {
                    const statusOrder = ['pending', 'building', 'creating', 'ready'];
                    const currentIdx = statusOrder.indexOf(deployment?.status || 'pending');
                    const stepIdx = statusOrder.indexOf(step.key);
                    const isActive = stepIdx === currentIdx;
                    const isComplete = stepIdx < currentIdx;

                    return (
                      <div key={step.key} className="flex items-center">
                        <div className="flex flex-col items-center">
                          <div className={`
                            w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold
                            transition-all duration-500
                            ${isComplete ? 'bg-green-500 text-white' : ''}
                            ${isActive ? 'bg-purple-600 text-white ring-4 ring-purple-200 animate-pulse' : ''}
                            ${!isComplete && !isActive ? 'bg-gray-200 text-gray-500' : ''}
                          `}>
                            {isComplete ? (
                              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            ) : step.num}
                          </div>
                          <span className={`text-xs mt-2 font-medium ${isActive ? 'text-purple-600' : isComplete ? 'text-green-600' : 'text-gray-400'}`}>
                            {step.label}
                          </span>
                        </div>
                        {idx < arr.length - 1 && (
                          <div className={`w-12 h-1 mx-2 rounded transition-all duration-500 ${isComplete ? 'bg-green-400' : 'bg-gray-200'}`} />
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Progress Bar */}
                <div className="relative mb-6">
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-purple-500 via-blue-500 to-indigo-500 rounded-full transition-all duration-1000 animate-pulse"
                      style={{
                        width: !deployment ? '5%'
                          : deployment.status === 'pending' ? '15%'
                          : deployment.status === 'building' ? '50%'
                          : deployment.status === 'creating' ? '85%'
                          : '100%'
                      }}
                    />
                  </div>
                  {/* Shimmer Effect */}
                  <div className="absolute inset-0 h-2 rounded-full overflow-hidden">
                    <div className="h-full w-1/3 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-[shimmer_2s_infinite]" />
                  </div>
                </div>

                {/* Status Message */}
                <div className="text-center space-y-3">
                  <p className="text-lg font-medium text-gray-900">
                    {deployment?.status === 'pending' && '배포 준비 중...'}
                    {deployment?.status === 'building' && (deployment.build_phase_message || 'Docker 이미지 빌드 중...')}
                    {deployment?.status === 'creating' && 'AgentCore Runtime 생성 중...'}
                  </p>
                  <p className="text-sm text-gray-600">
                    {deployment?.status === 'pending' && 'Agent 코드 및 Dockerfile을 생성하고 있습니다'}
                    {deployment?.status === 'building' && !deployment.build_phase_message && 'ARM64 컨테이너 이미지를 빌드하여 ECR에 푸시하고 있습니다 (약 1~2분 소요)'}
                    {deployment?.status === 'building' && deployment.build_phase_message && `현재 단계: ${deployment.build_phase || 'BUILD'}`}
                    {deployment?.status === 'creating' && 'AgentCore Runtime을 시작하고 있습니다 (약 30초~1분 소요)'}
                  </p>
                  {deployment?.id && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <p className="text-xs text-gray-500 mb-2">배포 ID</p>
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded text-gray-700">
                        {deployment.id.slice(0, 8)}...{deployment.id.slice(-8)}
                      </code>
                    </div>
                  )}
                  <p className="text-xs text-gray-400 mt-4">
                    전체 예상 소요 시간: 2~3분
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <>
              <div className="flex-1 overflow-y-auto space-y-4 mb-4">
                {loadingMessages ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center space-y-3">
                      <div className="animate-spin h-8 w-8 border-4 border-purple-500 border-t-transparent rounded-full mx-auto" />
                      <p className="text-gray-600">이전 대화 내역을 불러오는 중...</p>
                    </div>
                  </div>
                ) : messages.length === 0 && !sending ? (
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <p>메시지를 입력하여 대화를 시작하세요</p>
                  </div>
                ) : (
                  <ChatMessageList
                    messages={messages}
                    isLoading={sending}
                    agentName={selectedAgent?.name}
                    showMetadata={true}
                  />
                )}
                <div ref={messagesEndRef} />
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                  placeholder="메시지를 입력하세요..."
                  disabled={sending || !canChat}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                />
                {sending ? (
                  <button
                    onClick={cancelSending}
                    className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                  >
                    취소
                  </button>
                ) : (
                  <button
                    onClick={sendMessage}
                    disabled={!input.trim() || !canChat}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:text-gray-700 disabled:cursor-not-allowed"
                  >
                    전송
                  </button>
                )}
              </div>
            </>
          )}
        </Card>

        {/* Info Panel */}
        <Card className="h-[600px] flex flex-col">
          <h3 className="font-semibold mb-4 flex-shrink-0">정보</h3>

          {selectedVersionData ? (
            <div className="space-y-4 text-sm overflow-y-auto flex-1">
              <div>
                <p className="font-medium text-gray-700 mb-1">Agent</p>
                <p className="text-gray-900">{selectedAgent?.name}</p>
              </div>

              <div>
                <p className="font-medium text-gray-700 mb-1">Version</p>
                <p className="text-gray-900">
                  {typeof selectedVersionData.version === 'string'
                    ? selectedVersionData.version
                    : selectedVersionData.version && typeof selectedVersionData.version === 'object' && 'major' in selectedVersionData.version
                      ? `v${selectedVersionData.version.major}.${selectedVersionData.version.minor}.${selectedVersionData.version.patch}`
                      : 'N/A'}
                </p>
              </div>

              <div>
                <p className="font-medium text-gray-700 mb-1">LLM Model</p>
                {(() => {
                  const llmModel = selectedVersionData.snapshot?.llm_model || selectedVersionData.llm_model;
                  if (!llmModel) {
                    return <span className="text-sm text-gray-500">N/A</span>;
                  }
                  return (
                    <div className="space-y-1 text-xs">
                      <p className="text-gray-900 font-medium">{llmModel.model_name || llmModel.model_id}</p>
                      {llmModel.provider && (
                        <p className="text-gray-600">Provider: {llmModel.provider}</p>
                      )}
                      {llmModel.model_id && llmModel.model_name && (
                        <p className="text-gray-500 text-xs break-all">ID: {llmModel.model_id}</p>
                      )}
                    </div>
                  );
                })()}
              </div>

              {deployment && (
                <div>
                  <p className="font-medium text-gray-700 mb-1">Runtime 상태</p>
                  <div className="space-y-1 text-xs">
                    <p>상태: <Badge variant={deployment.status === 'ready' ? 'success' : 'warning'}>{deployment.status}</Badge></p>
                    {deployment.expires_at && (
                      <p>만료: {formatLocalDateTime(deployment.expires_at)}</p>
                    )}
                    <p>Idle Timeout: {deployment.idle_timeout}초</p>
                    <p>Max Lifetime: {deployment.max_lifetime}초</p>
                  </div>
                </div>
              )}

              <div>
                <p className="font-medium text-gray-700 mb-1">Tools (MCPs)</p>
                <div className="flex flex-wrap gap-1">
                  {(() => {
                    const mcpIds = selectedVersionData.snapshot?.mcps || selectedVersionData.mcps || [];
                    if (mcpIds.length === 0) {
                      return <span className="text-sm text-gray-500">없음</span>;
                    }
                    return mcpIds.map((mcpIdOrObj: any) => {
                      const mcpId = typeof mcpIdOrObj === 'string' ? mcpIdOrObj : mcpIdOrObj.id;
                      const mcpData = mcps.find(m => m.id === mcpId);
                      const displayName = mcpData?.name || (typeof mcpIdOrObj === 'object' ? mcpIdOrObj.name : mcpId);

                      return (
                        <Badge key={mcpId} variant="primary">
                          {displayName}
                        </Badge>
                      );
                    });
                  })()}
                </div>
              </div>

              <div>
                <p className="font-medium text-gray-700 mb-1">Knowledge Bases</p>
                <div className="flex flex-wrap gap-1">
                  {(() => {
                    const kbIds = selectedVersionData.snapshot?.knowledge_bases || selectedVersionData.knowledge_bases || [];
                    if (kbIds.length === 0) {
                      return <span className="text-sm text-gray-500">없음</span>;
                    }
                    return kbIds.map((kbIdOrObj: any) => {
                      const kbId = typeof kbIdOrObj === 'string' ? kbIdOrObj : kbIdOrObj.id;
                      const kbData = knowledgeBases.find(k => k.id === kbId);
                      const displayName = kbData?.name || (typeof kbIdOrObj === 'object' ? kbIdOrObj.name : `KB-${kbId.slice(-8)}`);

                      return (
                        <Badge key={kbId} variant="gray">
                          {displayName}
                        </Badge>
                      );
                    });
                  })()}
                </div>
              </div>

              {/* Instruction */}
              <div>
                <p className="font-medium text-gray-700 mb-1">Instruction</p>
                <div className="text-xs text-gray-800 space-y-2">
                  {(() => {
                    const instruction = selectedVersionData.snapshot?.instruction || selectedVersionData.instruction;
                    if (!instruction) {
                      return <span className="text-sm text-gray-500">없음</span>;
                    }
                    return (
                      <>
                        <div className="max-h-32 overflow-y-auto bg-gray-50 p-2 rounded border border-gray-200">
                          <p className="whitespace-pre-wrap break-words">
                            {instruction.system_prompt || '시스템 프롬프트 없음'}
                          </p>
                        </div>
                        <div className="flex gap-4 text-xs text-gray-600">
                          <span>Temperature: {instruction.temperature ?? 'N/A'}</span>
                          <span>Max Tokens: {instruction.max_tokens ?? 'N/A'}</span>
                        </div>
                      </>
                    );
                  })()}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
              <p>Agent를 선택하면 정보가 표시됩니다</p>
            </div>
          )}
        </Card>
      </div>

      {/* Chat Modal */}
      <ChatModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={selectedAgent ? `${selectedAgent.name} • ${selectedVersion}` : 'Chat'}
        messages={messages}
        input={input}
        onInputChange={setInput}
        onSend={sendMessage}
        isLoading={sending}
        disabled={!canChat}
        placeholder={canChat ? '메시지를 입력하세요...' : '먼저 Runtime을 배포하세요'}
      />
    </div>
  );
}
