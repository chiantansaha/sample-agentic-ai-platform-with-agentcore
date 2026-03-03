/**
 * AgentForm - Agent 생성/수정 통합 페이지
 *
 * Create/Edit 모드를 mode prop으로 구분하여 동일한 UI/로직을 공유합니다.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import type { Agent, MCP, KnowledgeBase, Deployment } from '../../types';
import { Card, Button, LoadingSpinner, Badge, Modal } from '../../components/common';
import { ChatPanel, DeployModal } from '../../components/agent';
import { useLocalChat } from '../../hooks';
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
  name: string;
  description: string;
  model: string;
  knowledgeBases: string[];
  mcps: string[];
  instructions: string;
}

interface AgentFormProps {
  mode: 'create' | 'edit';
}

export function AgentForm({ mode }: AgentFormProps) {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditMode = mode === 'edit';

  // 로컬 테스트용 임시 Agent ID - useRef로 안정적으로 유지 (리렌더링 시에도 동일한 값 유지)
  const tempAgentIdRef = useRef<string | null>(null);
  if (!isEditMode && tempAgentIdRef.current === null) {
    tempAgentIdRef.current = `temp-${Date.now()}`;
  }
  const agentId = isEditMode ? id! : tempAgentIdRef.current!;

  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('basic');

  const [agent, setAgent] = useState<Agent | null>(null);
  const [formData, setFormData] = useState<FormData>({
    name: '',
    description: '',
    model: '',
    knowledgeBases: [],
    mcps: [],
    instructions: '',
  });

  // Local Chat Hook
  const {
    messages,
    inputMessage,
    sending,
    isPrepared,
    preparing,
    isDirty,
    setInputMessage,
    setIsDirty,
    prepare,
    sendMessage,
  } = useLocalChat({
    agentId,
    onPrepareError: (error) => alert(error),
  });

  // Chat Modal
  const [isTestChatModalOpen, setIsTestChatModalOpen] = useState(false);

  // Deployment state
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [deployError, setDeployError] = useState<string | null>(null);
  const [savedAgentId, setSavedAgentId] = useState<string | null>(null); // Create 모드에서 저장된 agent ID

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

  // Search states
  const [llmSearchQuery, setLlmSearchQuery] = useState('');
  const [kbSearchQuery, setKbSearchQuery] = useState('');
  const [mcpSearchQuery, setMcpSearchQuery] = useState('');

  // Load resources
  useEffect(() => {
    loadResources();
    if (isEditMode && id) {
      loadAgent(id);
    } else {
      setLoading(false);
    }
  }, [isEditMode, id]);

  const loadAgent = async (agentId: string) => {
    try {
      const response = await api.get(`/agents/${agentId}`);
      const agentData = response.data.data;

      setAgent(agentData);

      // Extract model ID
      let modelId = '';
      if (agentData.llm_model && typeof agentData.llm_model === 'object') {
        modelId = agentData.llm_model.model_id || '';
      } else if (agentData.llmModel && typeof agentData.llmModel === 'object') {
        modelId = agentData.llmModel.modelId || agentData.llmModel.model_id || '';
      } else {
        modelId = agentData.model || agentData.llm_model_id || agentData.llmModelId || '';
      }

      // Extract instructions
      let instructions = '';
      if (agentData.instruction && typeof agentData.instruction === 'object') {
        instructions = agentData.instruction.system_prompt || '';
      } else {
        instructions = agentData.instructions || agentData.system_prompt || '';
      }

      setFormData({
        name: agentData.name || '',
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

    } catch (error) {
      console.error('Failed to load agent:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadResources = async () => {
    setLoadingKBs(true);
    api.get('/knowledge-bases')
      .then((res) => setAvailableKBs(res.data.data || []))
      .finally(() => setLoadingKBs(false));

    setLoadingMCPs(true);
    api.get('/mcps/')
      .then((res) => setAvailableMCPs(res.data.data || []))
      .finally(() => setLoadingMCPs(false));

    setLoadingModels(true);
    api.get('/agents/llms')
      .then((res) => setAvailableModels(res.data.data || []))
      .finally(() => setLoadingModels(false));
  };

  const handleFormChange = (updates: Partial<FormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
    setIsDirty(true);
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

  // Prepare handler
  const handlePrepare = async () => {
    await prepare({
      system_prompt: formData.instructions,
      model: formData.model,
      mcp_ids: formData.mcps,
      kb_ids: formData.knowledgeBases,
    });
  };

  // AI Instruction Generation
  const handleGenerateInstruction = async () => {
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
        name: formData.name || (agent?.name || ''),
        description: formData.description,
        model: formData.model,
        knowledgeBases: kbInfos,
        mcps: mcpInfos,
        currentInstructions: formData.instructions,
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

  // Poll deployment status (Edit mode only)
  const pollDeploymentStatus = useCallback(async (deploymentId: string) => {
    const maxAttempts = 100;
    let attempts = 0;

    const poll = async () => {
      try {
        const response = await api.get(`/playground/runtime/deployments/${deploymentId}/status`);
        const status = response.data.data;

        setDeployment(prev => prev ? { ...prev, ...status } : null);

        if (status.status === 'ready' || status.status === 'failed') {
          if (status.status === 'failed') {
            setDeployError(status.error_message || 'Unknown error');
          }
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 3000);
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
  const startDeployment = useCallback(async (agentId: string, newVersion?: string) => {
    if (!agentId) return;

    setDeployError(null);
    setDeployment(null);
    setShowDeployModal(true);

    try {
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
        agent_id: agentId,
        version: versionStr,
        force_rebuild: true
      });

      const deploymentData: Deployment = response.data.data;
      setDeployment(deploymentData);

      if (deploymentData.status !== 'ready') {
        pollDeploymentStatus(deploymentData.id);
      }
    } catch (error: any) {
      console.error('Failed to deploy runtime:', error);
      let errorMessage = error.response?.data?.detail || 'Runtime 배포 실패';

      if (errorMessage.includes('CODEBUILD_PROJECT_NAME') ||
          errorMessage.includes('source_bucket') ||
          errorMessage.includes('CodeBuild')) {
        errorMessage = '로컬 환경에서는 배포가 지원되지 않습니다. AWS 환경에서 테스트하거나, Prepare 버튼으로 로컬 테스트를 사용하세요.';
      }

      setDeployError(errorMessage);
    }
  }, [agent, id, pollDeploymentStatus]);

  // Validate disabled resources
  const validateResources = (): boolean => {
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
      return false;
    }

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
      return false;
    }

    return true;
  };

  const handleSave = async () => {
    if (!validateResources()) return;

    setSaving(true);

    try {
      const selectedModel = availableModels.find(m => m.id === formData.model);

      if (isEditMode && agent) {
        // Edit mode - PUT request
        const agentAny = agent as any;
        const existingLlm = agentAny.llm_model || {};

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
          const savedAgent = response.data.data;
          const newVersion = savedAgent.current_version || savedAgent.currentVersion;
          setAgent(savedAgent);
          startDeployment(id!, newVersion);
        }
      } else {
        // Create mode - POST request
        const response = await api.post('/agents', {
          name: formData.name,
          description: formData.description,
          llm_model_id: formData.model,
          llm_model_name: selectedModel?.name || '',
          llm_provider: selectedModel?.provider || '',
          system_prompt: formData.instructions,
          temperature: 0.7,
          max_tokens: 2000,
          knowledge_bases: formData.knowledgeBases,
          mcps: formData.mcps,
        });

        if (response.status === 200 || response.status === 201) {
          const savedAgent = response.data.data;
          const newVersion = savedAgent.current_version || savedAgent.currentVersion || '1.0.0';
          setAgent(savedAgent);
          setSavedAgentId(savedAgent.id); // Create 모드에서 저장된 agent ID 기록
          startDeployment(savedAgent.id, newVersion);
        }
      }
    } catch (error) {
      console.error('Failed to save agent:', error);
      alert('Agent 저장에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const canSave = isEditMode
    ? isDirty && formData.model && formData.instructions
    : formData.name && formData.model && formData.instructions;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (isEditMode && !agent) {
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
          {isEditMode && (
            <Link to={`/agents/${id}`} className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
              ← Back to Agent
            </Link>
          )}
          <h1 className="text-3xl font-bold text-gray-900">
            {isEditMode ? 'Edit Agent' : 'Create New Agent'}
          </h1>
          <p className="text-gray-600 mt-1">
            {isEditMode ? agent?.name : 'Configure your agent and test it'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link to={isEditMode ? `/agents/${id}` : '/agents'}>
            <Button variant="outline">Cancel</Button>
          </Link>
          <Button onClick={handleSave} disabled={saving || !canSave}>
            {saving ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                Deploying...
              </>
            ) : (
              'Deploy new version'
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
          <Card className="p-6 max-h-[calc(100vh-250px)] flex flex-col overflow-hidden">
            {activeTab === 'basic' && (
              <div className="space-y-4 h-full overflow-y-auto">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h2>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Agent Name {!isEditMode && <span className="text-red-500">*</span>}
                  </label>
                  {isEditMode ? (
                    <>
                      <input
                        type="text"
                        disabled
                        value={agent?.name || ''}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500 cursor-not-allowed"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Agent name cannot be changed after creation
                      </p>
                    </>
                  ) : (
                    <>
                      <input
                        type="text"
                        required
                        value={formData.name}
                        onChange={(e) => {
                          if (e.target.value.length <= 100) {
                            handleFormChange({ name: e.target.value });
                          }
                        }}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="My Agent"
                        maxLength={100}
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {formData.name.length}/100자
                      </p>
                    </>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
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

                {/* Currently Selected Model */}
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

                {/* Model List */}
                <div className="flex-1 overflow-y-auto space-y-3 pr-2 max-h-[500px]">
                  {loadingModels ? (
                    <div className="flex flex-col items-center justify-center py-12 space-y-3">
                      <LoadingSpinner size="lg" />
                      <p className="text-gray-500 text-sm">모델 목록을 불러오는 중...</p>
                    </div>
                  ) : (
                    (() => {
                      const uniqueModels = availableModels.filter((model, index, self) =>
                        index === self.findIndex(m => m.id === model.id)
                      );

                      const filteredModels = uniqueModels.filter(model =>
                        llmSearchQuery === '' ||
                        model.name.toLowerCase().includes(llmSearchQuery.toLowerCase()) ||
                        model.provider.toLowerCase().includes(llmSearchQuery.toLowerCase()) ||
                        model.id.toLowerCase().includes(llmSearchQuery.toLowerCase())
                      );

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
                        disabled={generatingInstruction || (!formData.name && !agent?.name)}
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

        {/* Right Panel: Test Chat */}
        <ChatPanel
          messages={messages}
          inputMessage={inputMessage}
          sending={sending}
          isPrepared={isPrepared}
          preparing={preparing}
          isDirty={isDirty}
          onInputChange={setInputMessage}
          onSend={sendMessage}
          onPrepare={handlePrepare}
          agentName={agent?.name || 'Agent'}
          prepareDisabled={!formData.model || !formData.instructions || (!isEditMode && !formData.name)}
          isModalOpen={isTestChatModalOpen}
          onModalOpen={() => setIsTestChatModalOpen(true)}
          onModalClose={() => setIsTestChatModalOpen(false)}
        />
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

      {/* Deploy Status Modal */}
      <DeployModal
        isOpen={showDeployModal}
        onClose={() => {
          setShowDeployModal(false);
          // Create 모드에서 저장 후 상세 페이지로 이동
          const targetId = savedAgentId || agent?.id || id;
          if (!isEditMode && targetId) {
            navigate(`/agents/${targetId}`);
          }
        }}
        deployment={deployment}
        deployError={deployError}
        onRetry={() => startDeployment(savedAgentId || agent?.id || id!)}
        onGoToPlayground={() => navigate(`/playground?agent=${savedAgentId || agent?.id || id}&version=${deployment?.version}`)}
      />

    </div>
  );
}
