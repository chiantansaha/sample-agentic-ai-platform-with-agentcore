import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { Maximize2, RotateCcw } from 'lucide-react';
import type { Agent, MCP, KnowledgeBase, Message, Deployment } from '../../types';
import { Card, Button, LoadingSpinner, Badge, Modal, ChatMessageList } from '../../components/common';
import ChatModal from '../../components/common/ChatModal';
import api from '../../utils/axios';

type Tab = 'basic' | 'llm' | 'kb' | 'mcp' | 'prompt';

const TABS: { id: Tab; label: string }[] = [
  { id: 'basic', label: 'Basic Info' },
  { id: 'llm', label: 'LLM Model' },
  { id: 'kb', label: 'Knowledge Base' },
  { id: 'mcp', label: 'Tools (MCP)' },
  { id: 'prompt', label: 'Instructions' },
];

interface LLMModel {
  id: string;
  name: string;
  description?: string;
  provider: string;
  maxTokens: number;
}

interface FormData {
  description: string;
  model: string;
  knowledgeBases: string[];
  mcps: string[];
  instructions: string;
}

export function AgentEdit() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('basic');

  const [agent, setAgent] = useState<Agent | null>(null);
  const [formData, setFormData] = useState<FormData>({
    description: '',
    model: 'claude-sonnet-4',
    knowledgeBases: [],
    mcps: [],
    instructions: '',
  });
  const [isDirty, setIsDirty] = useState(false);

  // Local test chat state
  const [isPrepared, setIsPrepared] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [localSessionId, setLocalSessionId] = useState<string | null>(null);
  const localSessionRef = useRef<string | null>(null); // for cleanup on unmount
  const [isTestChatModalOpen, setIsTestChatModalOpen] = useState(false);

  // Deployment state (for auto-deploy after save)
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [deployError, setDeployError] = useState<string | null>(null);

  const [availableKBs, setAvailableKBs] = useState<KnowledgeBase[]>([]);
  const [availableMCPs, setAvailableMCPs] = useState<MCP[]>([]);
  const [availableModels, setAvailableModels] = useState<LLMModel[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [loadingKBs, setLoadingKBs] = useState(false);
  const [loadingMCPs, setLoadingMCPs] = useState(false);

  // AI Instruction Generation
  const [generatingInstruction, setGeneratingInstruction] = useState(false);
  const [showInstructionModal, setShowInstructionModal] = useState(false);
  const [suggestedInstruction, setSuggestedInstruction] = useState('');

  // LLM search
  const [llmSearchQuery, setLlmSearchQuery] = useState('');

  // KB search
  const [kbSearchQuery, setKbSearchQuery] = useState('');

  // MCP search
  const [mcpSearchQuery, setMcpSearchQuery] = useState('');


  // Session cleanup function
  const cleanupLocalSession = useCallback(async (sessionId: string, agentId: string) => {
    try {
      await api.delete(`/agents/local-chat/${agentId}/session/${sessionId}`);
    } catch (error) {
      // Cleanup 실패는 조용히 무시
    }
  }, []);

  // Cleanup on page unload/close
  useEffect(() => {
    const handleBeforeUnload = () => {
      // Use sendBeacon for reliable cleanup on page close
      if (localSessionRef.current && id) {
        const apiBaseUrl = import.meta.env.DEV ? 'http://localhost:8000' : '';

        // sendBeacon doesn't support DELETE, so we use POST with _method override
        // Backend should handle this or we use a dedicated cleanup endpoint
        navigator.sendBeacon(
          `${apiBaseUrl}/api/v1/agents/local-chat/${id}/session/${localSessionRef.current}/cleanup`,
          JSON.stringify({})
        );
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      // Cleanup on component unmount
      if (localSessionRef.current && id) {
        cleanupLocalSession(localSessionRef.current, id);
      }
    };
  }, [id, cleanupLocalSession]);

  // Keep ref in sync with state
  useEffect(() => {
    localSessionRef.current = localSessionId;
  }, [localSessionId]);

  useEffect(() => {
    if (id) {
      loadAgent(id);
      loadResources();
    }
  }, [id]);

  const loadAgent = async (agentId: string) => {
    try {
      const response = await api.get(`/agents/${agentId}`);
      const data = response.data;
      const agentData = data.data;

      setAgent(agentData);

      // Extract model ID from llm_model object or various possible field names
      let modelId = '';
      if (agentData.llm_model && typeof agentData.llm_model === 'object') {
        modelId = agentData.llm_model.model_id || '';
      } else if (agentData.llmModel && typeof agentData.llmModel === 'object') {
        modelId = agentData.llmModel.modelId || agentData.llmModel.model_id || '';
      } else {
        modelId = agentData.model || agentData.llm_model_id || agentData.llmModelId || '';
      }

      // Extract instructions from instruction object or direct field
      let instructions = '';
      if (agentData.instruction && typeof agentData.instruction === 'object') {
        instructions = agentData.instruction.system_prompt || '';
      } else {
        instructions = agentData.instructions || agentData.system_prompt || '';
      }

      setFormData({
        description: agentData.description || '',
        model: modelId,
        knowledgeBases: Array.isArray(agentData.knowledgeBases)
          ? agentData.knowledgeBases.map((kb: any) => typeof kb === 'string' ? kb : kb.id)
          : Array.isArray(agentData.knowledge_bases)
            ? agentData.knowledge_bases.map((kb: any) => typeof kb === 'string' ? kb : kb.id)
            : [],
        mcps: Array.isArray(agentData.mcps)
          ? agentData.mcps.map((mcp: any) => typeof mcp === 'string' ? mcp : mcp.id)
          : [],
        instructions: instructions,
      });

      // Reset dirty state on load (ensures fresh state after refresh)
      setIsDirty(false);
      setIsPrepared(false);
    } catch (error) {
      console.error('Failed to load agent:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadResources = async () => {
    // Load KBs
    setLoadingKBs(true);
    api.get('/knowledge-bases')
      .then((res) => setAvailableKBs(res.data.data || []))
      .catch((error) => console.error('Failed to load KBs:', error))
      .finally(() => setLoadingKBs(false));

    // Load MCPs
    setLoadingMCPs(true);
    api.get('/mcps/')
      .then((res) => setAvailableMCPs(res.data.data || []))
      .catch((error) => console.error('Failed to load MCPs:', error))
      .finally(() => setLoadingMCPs(false));

    // Load LLMs
    setLoadingModels(true);
    api.get('/agents/llms')
      .then((res) => setAvailableModels(res.data.data || []))
      .catch((error) => console.error('Failed to load LLMs:', error))
      .finally(() => setLoadingModels(false));
  };

  const handleFormChange = (updates: Partial<FormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
    setIsDirty(true);
    setIsPrepared(false);
  };

  const toggleKB = (kbId: string) => {
    handleFormChange({
      knowledgeBases: formData.knowledgeBases.includes(kbId)
        ? formData.knowledgeBases.filter((id) => id !== kbId)
        : [...formData.knowledgeBases, kbId],
    });
  };

  const toggleMCP = (mcpId: string) => {
    handleFormChange({
      mcps: formData.mcps.includes(mcpId)
        ? formData.mcps.filter((id) => id !== mcpId)
        : [...formData.mcps, mcpId],
    });
  };

  // AI Instruction Generation
  const handleGenerateInstruction = async () => {
    if (!agent) return;

    setGeneratingInstruction(true);
    try {
      const kbInfos = formData.knowledgeBases
        .map(kbId => {
          const kb = availableKBs.find(k => k.id === kbId);
          return kb ? { id: kb.id, name: kb.name, description: kb.description || '' } : null;
        })
        .filter(Boolean);

      const mcpInfos = formData.mcps
        .map(mcpId => {
          const mcp = availableMCPs.find(m => m.id === mcpId);
          return mcp ? { name: mcp.name, description: mcp.description || '' } : null;
        })
        .filter(Boolean);

      const response = await api.post('/agents/generate-instruction', {
        name: agent.name,
        description: formData.description,
        model: formData.model,
        knowledgeBases: kbInfos,
        mcps: mcpInfos,
      });

      if (response.data?.data?.instruction) {
        setSuggestedInstruction(response.data.data.instruction);
        setShowInstructionModal(true);
      }
    } catch (error) {
      console.error('Failed to generate instruction:', error);
      alert('AI 추천 생성에 실패했습니다.');
    } finally {
      setGeneratingInstruction(false);
    }
  };

  const applyAIInstruction = () => {
    handleFormChange({ instructions: suggestedInstruction });
    setShowInstructionModal(false);
  };

  // Poll deployment status
  const pollDeploymentStatus = useCallback(async (deploymentId: string) => {
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
          setDeployError(status.error_message || 'Unknown error');
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 3000); // 3초마다 폴링
        } else {
          setDeployError('배포 시간 초과 (5분)');
        }
      } catch (error) {
        console.error('Failed to poll deployment status:', error);
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 3000);
        }
      }
    };

    poll();
  }, []);

  // Start deployment
  const startDeployment = useCallback(async (newVersion?: string) => {
    if (!agent || !id) return;

    setDeployError(null);
    setDeployment(null);
    setShowDeployModal(true);

    try {
      // Get version for deployment (use newVersion if provided, otherwise use agent's current version)
      let versionStr: string;
      if (newVersion) {
        versionStr = typeof newVersion === 'string'
          ? newVersion
          : (newVersion as any).major !== undefined
            ? `${(newVersion as any).major}.${(newVersion as any).minor}.${(newVersion as any).patch}`
            : '1.0.0';
      } else {
        const agentAny = agent as any;
        const currentVersion = agentAny.current_version || agentAny.currentVersion;
        versionStr = typeof currentVersion === 'string'
          ? currentVersion
          : currentVersion && typeof currentVersion === 'object' && 'major' in currentVersion
            ? `${currentVersion.major}.${currentVersion.minor}.${currentVersion.patch}`
            : '1.0.0';
      }

      const response = await api.post('/playground/runtime/deploy', {
        agent_id: id,
        version: versionStr,
        force_rebuild: true // 항상 새로 빌드
      });

      const deploymentData: Deployment = response.data.data;
      setDeployment(deploymentData);

      // Poll for ready status if not already ready
      if (deploymentData.status !== 'ready') {
        pollDeploymentStatus(deploymentData.id);
      }
    } catch (error: any) {
      console.error('Failed to deploy runtime:', error);
      let errorMessage = error.response?.data?.detail || 'Runtime 배포 실패';

      // 로컬 환경에서 CodeBuild 미설정 에러 처리
      if (errorMessage.includes('CODEBUILD_PROJECT_NAME') ||
          errorMessage.includes('source_bucket') ||
          errorMessage.includes('CodeBuild')) {
        errorMessage = '로컬 환경에서는 배포가 지원되지 않습니다. AWS 환경에서 테스트하거나, Prepare 버튼으로 로컬 테스트를 사용하세요.';
      }

      setDeployError(errorMessage);
    }
  }, [agent, id, pollDeploymentStatus]);

  const handleSave = async () => {
    if (!agent) return;

    // 선택된 KB 중 disabled 상태인 것이 있는지 확인
    const disabledKBs = formData.knowledgeBases.filter(kbId => {
      const kb = availableKBs.find(k => k.id === kbId);
      return kb && kb.status !== 'enabled';
    });

    if (disabledKBs.length > 0) {
      const disabledKBNames = disabledKBs.map(kbId => {
        const kb = availableKBs.find(k => k.id === kbId);
        return kb?.name || kbId;
      }).join(', ');
      alert(`Disabled Knowledge Base가 선택되어 있습니다: ${disabledKBNames}\n저장하려면 먼저 해제해주세요.`);
      return;
    }

    // 선택된 MCP 중 disabled 상태인 것이 있는지 확인
    const disabledMCPs = formData.mcps.filter(mcpId => {
      const mcp = availableMCPs.find(m => m.id === mcpId);
      return mcp && mcp.status !== 'enabled';
    });

    if (disabledMCPs.length > 0) {
      const disabledMCPNames = disabledMCPs.map(mcpId => {
        const mcp = availableMCPs.find(m => m.id === mcpId);
        return mcp?.name || mcpId;
      }).join(', ');
      alert(`Disabled MCP가 선택되어 있습니다: ${disabledMCPNames}\n저장하려면 먼저 해제해주세요.`);
      return;
    }

    setSaving(true);

    try {
      // Find selected model info
      const selectedModel = availableModels.find(m => m.id === formData.model);

      // Get existing LLM info from agent (API returns snake_case)
      const agentAny = agent as any;
      const existingLlm = agentAny.llm_model || {};

      // Transform formData to match backend UpdateAgentRequest
      const updatePayload = {
        name: agent.name,
        description: formData.description,
        llm_model_id: formData.model,
        llm_model_name: selectedModel?.name || existingLlm.model_name || '',
        llm_provider: selectedModel?.provider || existingLlm.provider || '',
        system_prompt: formData.instructions,
        temperature: existingLlm.temperature ?? 0.7,
        max_tokens: existingLlm.max_tokens ?? 2000,
        knowledge_bases: formData.knowledgeBases,
        mcps: formData.mcps,
      };

      const response = await api.put(`/agents/${id}`, updatePayload);

      if (response.status === 200) {
        setIsDirty(false);
        // 저장 응답에서 새 버전 가져오기
        const savedAgent = response.data.data;
        const newVersion = savedAgent.current_version || savedAgent.currentVersion;
        // agent 상태 업데이트 (UI에 새 버전 반영)
        setAgent(savedAgent);
        // 저장 성공 후 자동 배포 시작 (새 버전으로)
        startDeployment(newVersion);
      }
    } catch (error) {
      console.error('Failed to save agent:', error);
      alert('Agent 저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const handlePrepare = async () => {
    if (!agent || !id) return;

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

      // 로컬 Agent 준비 API 호출
      const response = await api.post(`/agents/local-chat/${id}/prepare`, {
        system_prompt: formData.instructions,
        model: formData.model,
        mcp_ids: formData.mcps,
        kb_ids: formData.knowledgeBases,
      });

      const sessionId = response.data.session_id;
      setLocalSessionId(sessionId);
      setIsPrepared(true);
      setIsDirty(false);
    } catch (error: any) {
      console.error('Failed to prepare local agent:', error);
      const errorMessage = error.response?.data?.detail || 'Local Agent 준비 실패';
      alert(errorMessage);
    } finally {
      setPreparing(false);
    }
  };

  const handleResetSession = async () => {
    if (!localSessionId || !id) return;

    try {
      // 기존 세션 cleanup
      await cleanupLocalSession(localSessionId, id);

      // 상태 초기화
      setLocalSessionId(null);
      setIsPrepared(false);
      setMessages([]);
      setInputMessage('');
    } catch (error) {
      console.error('Failed to reset session:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || sending || !id) return;

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

    setMessages((prev) => [...prev, userMessage]);
    const messageContent = inputMessage;
    setInputMessage('');
    setSending(true);

    try {
      // SSE 스트리밍 (로컬 채팅 API)
      const apiBaseUrl = import.meta.env.DEV ? 'http://localhost:8000' : '';

      const response = await fetch(`${apiBaseUrl}/api/v1/agents/local-chat/${id}/stream`, {
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
      setMessages((prev) => [...prev, assistantMessage]);

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
              // console.log('📩 SSE Event:', parsed);
              if (parsed.type === 'progress') {
                // progress 이벤트 - "생각" 등 처리
                const label = parsed.label || '';
                const progressId = parsed.id || `progress-${Date.now()}`;
                const isStart = parsed.status === 'start';
                const isDone = parsed.status === 'done';

                setMessages(prev => {
                  const updated = [...prev];
                  const lastMsg = updated[updated.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant') {
                    lastMsg.tools = lastMsg.tools || [];

                    if (isStart) {
                      // 시작 이벤트 - tool 추가
                      const alreadyExists = lastMsg.tools.some(t => t.id === `progress-${progressId}`);
                      if (!alreadyExists) {
                        lastMsg.tools.push({
                          id: `progress-${progressId}`,
                          name: label,
                          status: 'loading'
                        });
                      }
                    } else if (isDone) {
                      // 완료 이벤트 - 해당 tool 상태 변경
                      const toolIndex = lastMsg.tools.findIndex(t => t.id === `progress-${progressId}`);
                      if (toolIndex !== -1) {
                        lastMsg.tools[toolIndex] = {
                          ...lastMsg.tools[toolIndex],
                          status: 'completed',
                          content: parsed.content // thinking의 경우 content 포함
                        };
                      }
                    }
                  }
                  return updated;
                });
              } else if (parsed.type === 'tool_use') {
                // 도구 사용 이벤트 - assistant 메시지의 tools 배열에 추가
                const toolName = parsed.tool_name || 'Unknown Tool';
                let displayName = toolName;
                if (toolName.startsWith('retrieve_from_')) {
                  const kbName = toolName.replace('retrieve_from_', '').replace(/_/g, '-');
                  displayName = `KB "${kbName}" 조회`;
                } else {
                  // MCP prefix가 있으면 제거하고 표시
                  displayName = toolName;
                }

                setMessages(prev => {
                  const updated = [...prev];
                  const lastMsg = updated[updated.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant') {
                    lastMsg.tools = lastMsg.tools || [];

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
              } else if (parsed.type === 'tool_result') {
                // 도구 사용 완료 이벤트 - 마지막 loading 상태의 tool만 상태 변경
                // status가 'error'이면 실패로 표시
                const resultStatus = parsed.status === 'error' ? 'error' : 'completed';
                setMessages(prev => {
                  const updated = [...prev];
                  const lastMsg = updated[updated.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant' && lastMsg.tools) {
                    // 마지막 loading 상태의 tool 찾기
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
                // 'content'는 로컬 채팅 API, 'text'는 Playground API
                const textContent = parsed.content || '';
                accumulatedContent += textContent;
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
                    // 새 메시지 시작이므로 accumulatedContent 리셋
                    accumulatedContent = textContent;
                  } else if (lastMsg && lastMsg.role === 'assistant') {
                    // 기존 assistant 메시지에 텍스트 추가
                    lastMsg.content = accumulatedContent;
                  }
                  return updated;
                });
              } else if (parsed.type === 'done') {
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
              } else if (parsed.type === 'error') {
                const errorContent = parsed.content || parsed.message || parsed.error || '알 수 없는 오류가 발생했습니다';
                console.error('Stream error:', errorContent);
                setMessages((prev) => {
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
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Agent not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link to={`/agents/${id}`} className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
            ← Back to Agent
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Edit Agent</h1>
          <p className="text-gray-600 mt-1">{agent.name}</p>
        </div>
        <div className="flex items-center gap-3">
          <Link to={`/agents/${id}`}>
            <Button variant="outline">Cancel</Button>
          </Link>
          <Button onClick={handleSave} disabled={saving || !isDirty || !formData.model || !formData.instructions}>
            {saving ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                Deploying...
              </>
            ) : (
              'Deploy Changes'
            )}
          </Button>
        </div>
      </div>

      {/* Main Content: Left Panel + Right Chat */}
      <div className="grid grid-cols-2 gap-6">
        {/* Left Panel: Tabs */}
        <div className="space-y-4">
          {/* Tab Navigation */}
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex gap-4">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <Card className="p-6 min-h-[600px]">
            {activeTab === 'basic' && (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h2>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Agent Name
                  </label>
                  <input
                    type="text"
                    disabled
                    value={agent.name}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500 cursor-not-allowed"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Agent name cannot be changed after creation
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    required
                    value={formData.description}
                    onChange={(e) => {
                      if (e.target.value.length <= 500) {
                        handleFormChange({ description: e.target.value });
                      }
                    }}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={4}
                    placeholder="What does this agent do?"
                    maxLength={500}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {formData.description.length}/500자
                  </p>
                </div>

              </div>
            )}

            {activeTab === 'llm' && (
              <div className="space-y-4 h-full flex flex-col overflow-hidden">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Select LLM Model <span className="text-red-500">*</span></h2>
                  <p className="text-sm text-gray-600 mb-4">Choose an LLM model for your agent</p>
                </div>

                {/* Currently Selected Model - Always Visible */}
                {formData.model && availableModels.find(m => m.id === formData.model) && (
                  <div className="bg-blue-50 border-2 border-blue-600 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-sm font-semibold text-blue-900">Currently Selected</span>
                    </div>
                    {(() => {
                      const selectedModel = availableModels.find(m => m.id === formData.model);
                      if (!selectedModel) return null;
                      return (
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <div className="font-semibold text-gray-900">{selectedModel.name}</div>
                            <Badge color="blue" size="sm">{selectedModel.provider}</Badge>
                          </div>
                          <div className="text-xs text-gray-700 font-mono bg-white px-2 py-1 rounded border border-blue-200">
                            {selectedModel.id}
                          </div>
                          {selectedModel.description && (
                            <div className="text-sm text-gray-700 mt-2">{selectedModel.description}</div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                )}

                {/* Search Box */}
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search models by name or provider..."
                    value={llmSearchQuery}
                    onChange={(e) => setLlmSearchQuery(e.target.value)}
                    className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
                  />
                  <svg className="w-5 h-5 text-gray-400 absolute left-3 top-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>

                {/* Model List with Scroll */}
                <div className="flex-1 overflow-y-auto space-y-3 pr-2 max-h-[500px]">
                  {loadingModels ? (
                    <div className="flex flex-col items-center justify-center py-12 space-y-3">
                      <LoadingSpinner size="lg" />
                      <p className="text-gray-500 text-sm">모델 목록을 불러오는 중...</p>
                    </div>
                  ) : (
                    (() => {
                      // Deduplicate by ID
                      const uniqueModels = availableModels.filter((model, index, self) =>
                        index === self.findIndex(m => m.id === model.id)
                      );

                      // Apply search filter
                      const filteredModels = uniqueModels.filter(model =>
                        llmSearchQuery === '' ||
                        model.name.toLowerCase().includes(llmSearchQuery.toLowerCase()) ||
                        model.provider.toLowerCase().includes(llmSearchQuery.toLowerCase()) ||
                        model.id.toLowerCase().includes(llmSearchQuery.toLowerCase())
                      );

                      // Sort - selected first, then by name
                      const sortedModels = filteredModels.sort((a, b) => {
                        if (a.id === formData.model) return -1;
                        if (b.id === formData.model) return 1;
                        return a.name.localeCompare(b.name);
                      });

                      if (sortedModels.length === 0) {
                        return (
                          <div className="text-center py-8 text-gray-500">
                            {llmSearchQuery ? `No models found matching "${llmSearchQuery}"` : 'No models available'}
                          </div>
                        );
                      }

                      return sortedModels.map(model => (
                        <label
                          key={model.id}
                          className={`flex items-start p-4 border rounded-lg cursor-pointer transition-colors ${
                            formData.model === model.id
                              ? 'border-blue-600 bg-blue-50'
                              : 'border-gray-300 hover:border-blue-300'
                          }`}
                        >
                          <input
                            type="radio"
                            name="model"
                            checked={formData.model === model.id}
                            onChange={() => handleFormChange({ model: model.id })}
                            className="mt-1"
                          />
                          <div className="ml-3 flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <div className="font-medium text-gray-900">{model.name}</div>
                              <Badge color="blue" size="sm">{model.provider}</Badge>
                            </div>
                            <div className="text-xs text-gray-600 font-mono bg-gray-50 px-2 py-1 rounded">
                              {model.id}
                            </div>
                            {model.description && (
                              <div className="text-sm text-gray-600 mt-2">{model.description}</div>
                            )}
                            {model.maxTokens && (
                              <div className="text-xs text-gray-500 mt-1">Max tokens: {model.maxTokens.toLocaleString()}</div>
                            )}
                          </div>
                        </label>
                      ));
                    })()
                  )}
                </div>
              </div>
            )}

            {activeTab === 'kb' && (
              <div className="space-y-4 h-full flex flex-col overflow-hidden">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Select Knowledge Bases</h2>
                  <p className="text-sm text-gray-600">Choose knowledge bases (optional)</p>
                </div>

                {/* Search Box */}
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search knowledge bases..."
                    value={kbSearchQuery}
                    onChange={(e) => setKbSearchQuery(e.target.value)}
                    className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
                  />
                  <svg className="w-5 h-5 text-gray-400 absolute left-3 top-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>

                {/* Selected KBs */}
                {formData.knowledgeBases.length > 0 && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <p className="text-xs font-medium text-gray-700 mb-2">Selected ({formData.knowledgeBases.length})</p>
                    <div className="flex flex-wrap gap-2">
                      {formData.knowledgeBases.map(kbId => {
                        const kb = availableKBs.find(k => k.id === kbId);
                        if (!kb) return null;
                        return (
                          <span
                            key={kbId}
                            className="inline-flex items-center gap-1 px-2 py-1 bg-blue-600 text-white rounded text-xs font-medium"
                          >
                            {kb.name}
                            <button
                              type="button"
                              onClick={() => toggleKB(kbId)}
                              className="hover:bg-blue-700 rounded-full p-0.5 transition-colors"
                            >
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}

                <div className="flex-1 overflow-y-auto space-y-3 pr-2">
                  {loadingKBs ? (
                    <div className="flex flex-col items-center justify-center py-12 space-y-3">
                      <LoadingSpinner size="lg" />
                      <p className="text-gray-500 text-sm">Knowledge Base 목록을 불러오는 중...</p>
                    </div>
                  ) : (
                    availableKBs
                      .filter(kb =>
                        kbSearchQuery === '' ||
                        kb.name.toLowerCase().includes(kbSearchQuery.toLowerCase()) ||
                        (kb.description && kb.description.toLowerCase().includes(kbSearchQuery.toLowerCase())) ||
                        ((kb as any).bedrockKbId && (kb as any).bedrockKbId.toLowerCase().includes(kbSearchQuery.toLowerCase()))
                      )
                      // enabled 먼저, disabled 나중에 정렬
                      .sort((a, b) => {
                        if (a.status === 'enabled' && b.status !== 'enabled') return -1;
                        if (a.status !== 'enabled' && b.status === 'enabled') return 1;
                        return a.name.localeCompare(b.name);
                      })
                      .map(kb => {
                        const isDisabled = kb.status !== 'enabled';
                        return (
                          <label
                            key={kb.id}
                            className={`flex items-start p-4 border rounded-lg transition-colors ${
                              isDisabled
                                ? 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-60'
                                : formData.knowledgeBases.includes(kb.id)
                                  ? 'border-blue-600 bg-blue-50 cursor-pointer'
                                  : 'border-gray-300 hover:border-blue-300 cursor-pointer'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={formData.knowledgeBases.includes(kb.id)}
                              onChange={() => !isDisabled && toggleKB(kb.id)}
                              disabled={isDisabled}
                              className="mt-1"
                            />
                            <div className="ml-3 flex-1">
                              <div className="flex items-center gap-2">
                                <div className={`font-medium ${isDisabled ? 'text-gray-500' : 'text-gray-900'}`}>{kb.name}</div>
                                {isDisabled && (
                                  <span className="px-2 py-0.5 text-xs rounded bg-gray-200 text-gray-600">Disabled</span>
                                )}
                              </div>
                              <div className={`text-sm ${isDisabled ? 'text-gray-400' : 'text-gray-600'}`}>{kb.description}</div>
                              <div className="text-xs text-gray-500 mt-1 font-mono">
                                {(kb as any).bedrockKbId}
                              </div>
                            </div>
                          </label>
                        );
                      })
                  )}
                </div>
              </div>
            )}

            {activeTab === 'mcp' && (
              <div className="space-y-4 h-full flex flex-col overflow-hidden">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Select MCPs (Tools)</h2>
                  <p className="text-sm text-gray-600">Choose MCPs for your agent</p>
                </div>

                {/* Search Box */}
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search MCPs by name or description..."
                    value={mcpSearchQuery}
                    onChange={(e) => setMcpSearchQuery(e.target.value)}
                    className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
                  />
                  <svg className="w-5 h-5 text-gray-400 absolute left-3 top-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>

                {/* Selected MCPs */}
                {formData.mcps.length > 0 && (
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                    <p className="text-xs font-medium text-gray-700 mb-2">Selected ({formData.mcps.length})</p>
                    <div className="flex flex-wrap gap-2">
                      {formData.mcps.map(mcpId => {
                        const mcp = availableMCPs.find(m => m.id === mcpId);
                        if (!mcp) return null;
                        return (
                          <span
                            key={mcpId}
                            className="inline-flex items-center gap-1 px-2 py-1 bg-purple-600 text-white rounded text-xs font-medium"
                          >
                            {mcp.name}
                            <button
                              type="button"
                              onClick={() => toggleMCP(mcpId)}
                              className="hover:bg-purple-700 rounded-full p-0.5 transition-colors"
                            >
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}

                <div className="flex-1 overflow-y-auto space-y-3 pr-2">
                  {loadingMCPs ? (
                    <div className="flex flex-col items-center justify-center py-12 space-y-3">
                      <LoadingSpinner size="lg" />
                      <p className="text-gray-500 text-sm">MCP 목록을 불러오는 중...</p>
                    </div>
                  ) : (
                    availableMCPs
                      .filter(mcp =>
                        mcpSearchQuery === '' ||
                        mcp.name.toLowerCase().includes(mcpSearchQuery.toLowerCase()) ||
                        (mcp.description && mcp.description.toLowerCase().includes(mcpSearchQuery.toLowerCase())) ||
                        ((mcp as any).tags && (mcp as any).tags.some((tag: string) => tag.toLowerCase().includes(mcpSearchQuery.toLowerCase())))
                      )
                      // enabled 먼저, disabled 나중에 정렬
                      .sort((a, b) => {
                        if (a.status === 'enabled' && b.status !== 'enabled') return -1;
                        if (a.status !== 'enabled' && b.status === 'enabled') return 1;
                        return a.name.localeCompare(b.name);
                      })
                      .map(mcp => {
                        const isDisabled = mcp.status !== 'enabled';
                        return (
                          <label
                            key={mcp.id}
                            className={`flex items-start p-4 border rounded-lg transition-colors ${
                              isDisabled
                                ? 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-60'
                                : formData.mcps.includes(mcp.id)
                                  ? 'border-blue-600 bg-blue-50 cursor-pointer'
                                  : 'border-gray-300 hover:border-blue-300 cursor-pointer'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={formData.mcps.includes(mcp.id)}
                              onChange={() => !isDisabled && toggleMCP(mcp.id)}
                              disabled={isDisabled}
                              className="mt-1"
                            />
                            <div className="ml-3 flex-1">
                              <div className="flex items-center gap-2">
                                <div className={`font-medium ${isDisabled ? 'text-gray-500' : 'text-gray-900'}`}>{mcp.name}</div>
                                {isDisabled && (
                                  <span className="px-2 py-0.5 text-xs rounded bg-gray-200 text-gray-600">Disabled</span>
                                )}
                              </div>
                              <div className={`text-sm ${isDisabled ? 'text-gray-400' : 'text-gray-600'}`}>{mcp.description}</div>
                              <div className="text-xs text-gray-500 mt-1">
                                {(mcp as any).stats?.toolCount ?? mcp.toolList?.length ?? 0} tools • {mcp.version}
                              </div>
                            </div>
                          </label>
                        );
                      })
                  )}
                </div>
              </div>
            )}

            {activeTab === 'prompt' && (
              <div className="space-y-4 h-full overflow-y-auto">
                <h2 className="text-lg font-semibold text-gray-900">Agent Instructions</h2>
                <p className="text-sm text-gray-600 mb-4">
                  시스템 프롬프트를 작성하세요. Agent의 역할, 행동 방식, 제약사항 등을 정의합니다.
                </p>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Instructions <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <textarea
                      required
                      value={formData.instructions}
                      onChange={(e) => handleFormChange({ instructions: e.target.value })}
                      className="w-full px-4 py-2 pb-14 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm resize-none"
                      rows={20}
                      placeholder="You are a helpful AI assistant for AWS customers. You help with cloud services, architecture, and general inquiries. Always be polite and professional."
                    />
                    <div className="absolute bottom-4 right-6">
                      <button
                        type="button"
                        onClick={handleGenerateInstruction}
                        disabled={generatingInstruction || !agent}
                        className={`group flex items-center justify-center rounded-full text-white font-medium text-sm shadow-lg disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-xl overflow-hidden h-11 ${
                          generatingInstruction ? 'px-4 w-auto' : 'w-11 hover:w-auto hover:px-4'
                        }`}
                        style={{
                          background: 'linear-gradient(135deg, #3b82f6 0%, #a855f7 100%)',
                          transition: 'width 0.3s ease-in-out, padding 0.3s ease-in-out',
                        }}
                      >
                        {generatingInstruction ? (
                          <>
                            <LoadingSpinner size="sm" />
                            <span className="whitespace-nowrap ml-2">생성 중...</span>
                          </>
                        ) : (
                          <>
                            <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            <span className="whitespace-nowrap ml-0 opacity-0 w-0 overflow-hidden group-hover:ml-2 group-hover:opacity-100 group-hover:w-auto" style={{ transition: 'margin 0.3s ease-in-out, opacity 0.3s ease-in-out, width 0.3s ease-in-out' }}>
                              AI 추천
                            </span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    이 프롬프트는 agent의 행동을 정의합니다.
                  </p>
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* Right Panel: Test Chat (Local Mode) */}
        <Card className="p-6 h-[calc(100vh-250px)] flex flex-col">
          <div className="flex items-center justify-between mb-4 pb-4 border-b">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold">Test Chat</h3>
              <Badge variant="info" className="text-xs">Local</Badge>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsTestChatModalOpen(true)}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                title="확대"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
              {isPrepared && (
                <button
                  onClick={handleResetSession}
                  className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="세션 종료"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              )}
              <Button
                onClick={handlePrepare}
                disabled={preparing || !formData.model || !formData.instructions}
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

          {!isPrepared && !localSessionId ? (
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
              <div className="flex-1 overflow-y-auto space-y-4 mb-4">
                {messages.length === 0 && !sending ? (
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <p>메시지를 입력하여 테스트를 시작하세요</p>
                  </div>
                ) : (
                  <ChatMessageList
                    messages={messages}
                    isLoading={sending}
                    agentName={agent.name}
                    showMetadata={true}
                  />
                )}
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                  placeholder="메시지를 입력하세요..."
                  disabled={sending || isDirty}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                />
                <Button
                  onClick={handleSendMessage}
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
      </div>

      {/* AI Instruction Modal */}
      <Modal
        isOpen={showInstructionModal}
        onClose={() => setShowInstructionModal(false)}
        title="AI 추천 Instruction"
        maxWidth="4xl"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              AI가 생성한 Instruction 초안
            </label>
            <textarea
              value={suggestedInstruction}
              onChange={(e) => setSuggestedInstruction(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm font-mono"
              rows={20}
              placeholder="AI가 생성한 instruction이 여기에 표시됩니다..."
            />
            <p className="text-xs text-gray-500 mt-2">
              생성된 instruction을 검토하고 필요한 경우 수정하세요.
            </p>
          </div>
          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={() => setShowInstructionModal(false)}
            >
              취소
            </Button>
            <Button
              onClick={applyAIInstruction}
              disabled={!suggestedInstruction.trim()}
            >
              적용하기
            </Button>
          </div>
        </div>
      </Modal>

      {/* Test Chat Modal */}
      <ChatModal
        isOpen={isTestChatModalOpen}
        onClose={() => setIsTestChatModalOpen(false)}
        title={`Test Chat - ${agent?.name || 'Agent'}`}
        messages={messages}
        input={inputMessage}
        onInputChange={setInputMessage}
        onSend={handleSendMessage}
        isLoading={sending}
        disabled={!isPrepared || preparing}
        placeholder={isPrepared ? '메시지를 입력하세요...' : 'Prepare 버튼을 먼저 클릭하세요'}
      />

      {/* Deploy Status Modal */}
      {showDeployModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold text-gray-900">Agent 배포</h3>
                {(deployment?.status === 'ready' || deployment?.status === 'failed' || deployError) && (
                  <button
                    onClick={() => setShowDeployModal(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>

              {/* Error State */}
              {deployError && (
                <div className="text-center py-8">
                  <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
                    <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-gray-900 mb-2">배포 실패</p>
                  <p className="text-sm text-gray-600 mb-6">{deployError}</p>
                  <div className="flex justify-center gap-3">
                    <Button variant="outline" onClick={() => setShowDeployModal(false)}>
                      닫기
                    </Button>
                    <Button onClick={startDeployment}>
                      다시 시도
                    </Button>
                  </div>
                </div>
              )}

              {/* Success State */}
              {deployment?.status === 'ready' && !deployError && (
                <div className="text-center py-8">
                  <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
                    <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-gray-900 mb-2">배포 완료</p>
                  <p className="text-sm text-gray-600 mb-2">Agent가 성공적으로 배포되었습니다.</p>
                  <p className="text-sm font-medium text-blue-600 mb-6">v{deployment.version}</p>
                  <div className="flex justify-center gap-3">
                    <Button variant="outline" onClick={() => setShowDeployModal(false)}>
                      닫기
                    </Button>
                    <Button onClick={() => navigate(`/playground?agent=${id}&version=${deployment.version}`)}>
                      Playground에서 테스트
                    </Button>
                  </div>
                </div>
              )}

              {/* Progress State */}
              {!deployError && deployment?.status !== 'ready' && (
                <div className="py-4">
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
                  </div>

                  {/* Status Message */}
                  <div className="text-center space-y-2">
                    <p className="text-lg font-medium text-gray-900">
                      {!deployment && '배포 시작 중...'}
                      {deployment?.status === 'pending' && '배포 준비 중...'}
                      {deployment?.status === 'building' && (deployment.build_phase_message || 'Docker 이미지 빌드 중...')}
                      {deployment?.status === 'creating' && 'AgentCore Runtime 생성 중...'}
                    </p>
                    <p className="text-sm text-gray-600">
                      {!deployment && 'Agent 설정을 저장하고 배포를 시작합니다'}
                      {deployment?.status === 'pending' && 'Agent 코드 및 Dockerfile을 생성하고 있습니다'}
                      {deployment?.status === 'building' && !deployment.build_phase_message && 'ARM64 컨테이너 이미지를 빌드하고 있습니다 (약 2-3분)'}
                      {deployment?.status === 'building' && deployment.build_phase_message && `현재 단계: ${deployment.build_phase || 'BUILD'}`}
                      {deployment?.status === 'creating' && 'AgentCore Runtime을 시작하고 있습니다 (약 30초-1분)'}
                    </p>
                    <p className="text-xs text-gray-400 mt-4">
                      예상 소요 시간: 2-3분
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
