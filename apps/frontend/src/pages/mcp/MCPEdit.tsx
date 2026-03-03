import { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { Card, Badge, LoadingSpinner } from '../../components/common';
import { StepProgress, MCP_STEPS } from '../../components/mcp';
import { useToast } from '../../contexts/ToastContext';
import type { MCP } from '../../types';
import { formatLocalDateTime } from '../../utils/date';
import api from '../../utils/axios';

type MCPType = 'external' | 'internal-create' | 'internal-deploy';
type InternalTargetType = 'rest-api';
type ExternalAuthType = 'no_auth' | 'oauth';
type ExternalSubType = 'endpoint' | 'container' | null;

interface Target {
  id: string;
  name: string;
  description: string;
  type: InternalTargetType;
  // REST API specific
  restApiEndpoint?: string;
  restApiMethod?: string;
  restAuthType?: 'none' | 'oauth' | 'api_key';
  restApiKey?: string;
  restOAuthClientId?: string;
  restOAuthClientSecret?: string;
  restOAuthTokenUrl?: string;
  openApiSchema?: any;
}

export function MCPEdit() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [step, setStep] = useState<1 | 2 | 3>(2); // Start at step 2 (configure)
  const [mcpType, setMcpType] = useState<MCPType | null>(null);

  const [initialLoading, setInitialLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // External MCP sub-type (read-only, determined at creation)
  const [externalSubType, setExternalSubType] = useState<ExternalSubType>(null);

  // Common form data
  const [formData, setFormData] = useState({
    name: '',
    description: '',
  });

  // External MCP specific (Endpoint URL type)
  const [externalData, setExternalData] = useState({
    endpoint: '',
    authType: 'no_auth' as ExternalAuthType,
    // Endpoint URL (for external-endpoint type)
    endpointUrl: '',
    // OAuth Provider ARN (AgentCore Identity)
    oauthProviderArn: '' as string,
    // User Pool ID (Legacy, for backward compatibility)
    userPoolId: '' as string,
  });

  // OAuth2 Credential Providers (AgentCore Identity)
  interface OAuthProvider {
    arn: string;
    name: string;
    vendor: string;
    status: string;
    createdAt: string;
  }
  const [oauthProviders, setOauthProviders] = useState<OAuthProvider[]>([]);
  const [loadingOAuthProviders, setLoadingOAuthProviders] = useState(false);

  // Internal MCP specific - with multiple targets
  const [internalData, setInternalData] = useState({
    targets: [] as Target[],
    gatewayType: 'dedicated' as 'dedicated' | 'shared',
    gatewayId: '',
  });

  // Internal Deploy MCP specific
  const [deployData, setDeployData] = useState({
    ecrRepository: '',
    imageTag: '',
  });

  // Internal MCP (Deploy & Create) - Semantic Search
  const [enableSemanticSearch, setEnableSemanticSearch] = useState(false);
  // ECR Image type for card selection
  interface ECRImageInfo {
    tag: string;
    digest: string;
    pushedAt: string;
    sizeInBytes: number;
  }
  const [availableImages, setAvailableImages] = useState<ECRImageInfo[]>([]);
  const [loadingImageTags, setLoadingImageTags] = useState(false);

  const [editingTargetId, setEditingTargetId] = useState<string | null>(null);

  // Store initial data for change detection
  const [initialData, setInitialData] = useState<{
    description: string;
    // External MCP fields
    externalEndpoint?: string;
    externalAuthType?: string;
    externalOAuthProviderArn?: string;
    externalUserPoolId?: string;
    // Internal Create MCP
    targets?: Target[];
    // Internal Deploy MCP
    imageTag?: string;
    // Internal MCP (Deploy & Create) - Semantic Search
    enableSemanticSearch?: boolean;
  } | null>(null);


  // Load existing MCP data
  useEffect(() => {
    if (id) {
      fetchMCP(id);
    }
  }, [id]);



  const fetchMCP = async (mcpId: string) => {
    try {
      const response = await api.get(`/mcps/${mcpId}`);
      const mcp: MCP = response.data.data;

      // Set basic form data
      setFormData({
        name: mcp.name,
        description: mcp.description || '',
      });

      // Set MCP type
      setMcpType(mcp.type as MCPType);

      // Set type-specific data
      if (mcp.type === 'external') {
        // Determine sub-type from response
        const subType = mcp.subType as ExternalSubType || 'endpoint';
        setExternalSubType(subType);

        setExternalData({
          endpoint: mcp.endpoint || '',
          authType: (mcp.authType as ExternalAuthType) || 'no_auth',
          endpointUrl: mcp.endpointUrl || '',
          oauthProviderArn: mcp.oauthProviderArn || '',
          userPoolId: mcp.userPoolId || '',
        });

        // OAuth인 경우 Provider 목록 로드
        if (mcp.authType === 'oauth') {
          fetchOAuthProviders();
        }
      } else if (mcp.type === 'internal-create') {
        // Load targets from selectedApiTargets
        if (mcp.selectedApiTargets && mcp.selectedApiTargets.length > 0) {
          const mappedTargets: Target[] = mcp.selectedApiTargets.map((target: any) => ({
            id: target.id,
            name: target.name,
            description: target.description || '',
            type: 'rest-api' as InternalTargetType,
            restApiEndpoint: target.endpoint,
            restApiMethod: target.method,
            restAuthType: target.authType as 'none' | 'oauth' | 'api_key',
            openApiSchema: target.openApiSchema,
          }));
          setInternalData(prev => ({
            ...prev,
            targets: mappedTargets
          }));
        }
      } else if (mcp.type === 'internal-deploy') {
        // Internal Deploy MCP - load ECR info
        const ecrRepo = mcp.ecrRepository || '';
        const imgTag = mcp.imageTag || '';

        setDeployData({
          ecrRepository: ecrRepo,
          imageTag: imgTag,
        });

        // Fetch available image tags for the repository
        if (ecrRepo) {
          fetchECRImageTags(ecrRepo);
        }

        // Load Semantic Search setting
        if (mcp.enableSemanticSearch !== undefined) {
          setEnableSemanticSearch(mcp.enableSemanticSearch);
        }
      }

      // Load Semantic Search setting for internal-create
      if (mcp.type === 'internal-create' && mcp.enableSemanticSearch !== undefined) {
        setEnableSemanticSearch(mcp.enableSemanticSearch);
      }

      // Store initial data for change detection
      setInitialData({
        description: mcp.description || '',
        externalEndpoint: mcp.type === 'external' ? (mcp.endpointUrl || mcp.endpoint || '') : undefined,
        externalAuthType: mcp.type === 'external' ? (mcp.authType || 'no_auth') : undefined,
        externalOAuthProviderArn: mcp.type === 'external' ? (mcp.oauthProviderArn || '') : undefined,
        externalUserPoolId: mcp.type === 'external' ? (mcp.userPoolId || '') : undefined,
        targets: mcp.type === 'internal-create' && mcp.selectedApiTargets
          ? mcp.selectedApiTargets.map((target: any) => ({
              id: target.id,
              name: target.name,
              description: target.description || '',
              type: 'rest-api' as InternalTargetType,
              restApiEndpoint: target.endpoint,
              restApiMethod: target.method,
              restAuthType: target.authType as 'none' | 'oauth' | 'api_key',
              openApiSchema: target.openApiSchema,
            }))
          : undefined,
        // Internal Deploy MCP
        imageTag: mcp.type === 'internal-deploy' ? (mcp.imageTag || '') : undefined,
        // Internal MCP (Deploy & Create) - Semantic Search
        enableSemanticSearch: (mcp.type === 'internal-deploy' || mcp.type === 'internal-create')
          ? (mcp.enableSemanticSearch || false)
          : undefined,
      });
    } catch (error) {
      console.error('Failed to fetch MCP:', error);
      setError('Failed to load MCP');
    } finally {
      setInitialLoading(false);
    }
  };

  const fetchOAuthProviders = async () => {
    setLoadingOAuthProviders(true);
    try {
      const response = await api.get('/mcps/identity/oauth-providers');
      setOauthProviders(response.data.data || []);
    } catch (err) {
      console.error('Failed to fetch OAuth providers:', err);
      setOauthProviders([]);
    } finally {
      setLoadingOAuthProviders(false);
    }
  };

  const fetchECRImageTags = async (repository: string) => {
    setLoadingImageTags(true);
    try {
      const response = await api.get('/mcps/ecr/images/by-repository', {
        params: { repository }
      });
      const images = response.data.data || [];
      // Store full image objects for card display
      setAvailableImages(images);
    } catch (err) {
      console.error('Failed to load ECR image tags:', err);
      setAvailableImages([]);
    } finally {
      setLoadingImageTags(false);
    }
  };

  const addNewTarget = () => {
    const newTarget: Target = {
      id: `target-${Date.now()}`,
      name: '',
      description: '',
      type: 'rest-api',
      restApiMethod: 'GET',
      restApiEndpoint: '',
      restAuthType: 'none',
    };
    setInternalData(prev => ({
      ...prev,
      targets: [...prev.targets, newTarget]
    }));
    setEditingTargetId(newTarget.id);
  };

  const updateTarget = (targetId: string, updates: Partial<Target>) => {
    setInternalData(prev => ({
      ...prev,
      targets: prev.targets.map(t =>
        t.id === targetId ? { ...t, ...updates } : t
      )
    }));
  };

  const deleteTarget = (targetId: string) => {
    setInternalData(prev => ({
      ...prev,
      targets: prev.targets.filter(t => t.id !== targetId)
    }));
    if (editingTargetId === targetId) {
      setEditingTargetId(null);
    }
  };

  const handleNext = () => {
    setError('');

    if (step === 1) {
      if (!mcpType) {
        setError('Please select an MCP type');
        return;
      }
      setStep(2);
    } else if (step === 2) {
      // Validation
      if (!formData.name) {
        setError('Please provide an MCP name');
        return;
      }

      if (mcpType === 'external') {
        if (externalSubType === 'endpoint' && !externalData.endpointUrl) {
          setError('MCP Server Endpoint URL을 입력해주세요');
          return;
        }
      } else if (mcpType === 'internal-create') {
        if (internalData.targets.length === 0) {
          setError('Please add at least one target');
          return;
        }
        // Validate each target (simplified for edit mode)
        for (const target of internalData.targets) {
          if (!target.name) {
            setError(`Target "${target.id}" needs a name`);
            return;
          }
          if (target.type === 'rest-api' && !target.restApiEndpoint) {
            setError(`Target "${target.name}" needs an API endpoint`);
            return;
          }
          if (target.type === 'rest-api' && !target.restApiMethod) {
            setError(`Target "${target.name}" needs an HTTP method`);
            return;
          }
        }
      }

      // Check for changes
      if (initialData) {
        let hasChanges = false;

        // Check description
        if (formData.description !== initialData.description) {
          hasChanges = true;
        }

        // Check type-specific fields
        if (mcpType === 'external') {
          if (externalData.endpointUrl !== initialData.externalEndpoint ||
              externalData.authType !== initialData.externalAuthType ||
              externalData.oauthProviderArn !== initialData.externalOAuthProviderArn ||
              externalData.userPoolId !== initialData.externalUserPoolId) {
            hasChanges = true;
          }
        } else if (mcpType === 'internal-create' && initialData.targets) {
          // Compare targets by count and content
          if (internalData.targets.length !== initialData.targets.length) {
            hasChanges = true;
          } else {
            // Check if any target content has changed
            const currentTargetData = JSON.stringify(
              internalData.targets.map(t => ({
                name: t.name,
                endpoint: t.restApiEndpoint,
                method: t.restApiMethod,
              })).sort((a, b) => a.name.localeCompare(b.name))
            );
            const initialTargetData = JSON.stringify(
              initialData.targets.map(t => ({
                name: t.name,
                endpoint: t.restApiEndpoint,
                method: t.restApiMethod,
              })).sort((a, b) => a.name.localeCompare(b.name))
            );
            if (currentTargetData !== initialTargetData) {
              hasChanges = true;
            }
          }

          // Check Semantic Search change
          if (enableSemanticSearch !== initialData.enableSemanticSearch) {
            hasChanges = true;
          }
        } else if (mcpType === 'internal-deploy') {
          // Compare image tag
          if (deployData.imageTag !== initialData.imageTag) {
            hasChanges = true;
          }

          // Check Semantic Search change
          if (enableSemanticSearch !== initialData.enableSemanticSearch) {
            hasChanges = true;
          }
        }

        if (!hasChanges) {
          setError('변경된 내용이 없습니다');
          return;
        }
      }

      setStep(3);
    }
  };

  const handleBack = () => {
    setError('');
    if (step === 2) {
      // Edit 모드에서 Step 2의 Back은 MCP 목록으로 이동
      navigate('/mcps');
    } else if (step > 2) {
      setStep((step - 1) as 1 | 2 | 3);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');

    try {
      const updatePayload: any = {
        description: formData.description,
      };

      // Add targets for internal-create MCP
      if (mcpType === 'internal-create' && internalData.targets.length > 0) {
        updatePayload.targets = internalData.targets.map(target => ({
          name: target.name,
          description: target.description || '',
          endpoint: target.restApiEndpoint || '',
          method: target.restApiMethod || 'GET',
          openApiSchema: target.openApiSchema || {
            openapi: '3.0.0',
            info: {
              title: target.name,
              version: '1.0.0',
              description: target.description || ''
            },
            paths: {}
          },
        }));
      }

      // Add image_tag for internal-deploy MCP
      if (mcpType === 'internal-deploy') {
        updatePayload.image_tag = deployData.imageTag;
      }

      // Add enable_semantic_search for internal MCP (Deploy & Create)
      if (mcpType === 'internal-deploy' || mcpType === 'internal-create') {
        updatePayload.enable_semantic_search = enableSemanticSearch;
      }

      // Add endpoint_url and auth_type for external MCP (endpoint type)
      if (mcpType === 'external' && externalSubType === 'endpoint') {
        updatePayload.endpoint_url = externalData.endpointUrl;
        updatePayload.auth_type = externalData.authType;
        if (externalData.authType === 'oauth') {
          if (externalData.oauthProviderArn) {
            updatePayload.oauth_provider_arn = externalData.oauthProviderArn;
          }
          if (externalData.userPoolId) {
            updatePayload.user_pool_id = externalData.userPoolId;  // Legacy
          }
        }
      }

      const response = await api.put(`/mcps/${id}`, updatePayload);

      if (response.data.success) {
        // Navigate back to detail page
        navigate(`/mcps/${id}`);
      } else {
        setError('Failed to update MCP. Please try again.');
      }
    } catch (err: any) {
      console.error('Failed to update MCP:', err);
      setError(err.response?.data?.detail || 'Failed to update MCP. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (initialLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <Link to={`/mcps/${id}`} className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
          ← Back to MCP
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Edit MCP</h1>
        <p className="text-gray-600 mt-1">
          Update Model Context Protocol configuration
        </p>
      </div>

      {/* Progress Steps */}
      <StepProgress steps={MCP_STEPS} currentStep={step} />

      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-red-800">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Step 1: MCP Type (Read-only) */}
      {step === 1 && (
        <div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <p className="text-sm text-blue-900">
              <strong>Note:</strong> MCP type cannot be changed after creation. Current type is displayed below.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-6">
            <Card
              className={`opacity-60 cursor-not-allowed transition-all ${
                mcpType === 'external' ? 'ring-2 ring-blue-600 bg-blue-50' : ''
              }`}
            >
              <div className="text-center py-8">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">External MCP</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Connect to an existing MCP server hosted externally
                </p>
                <div className="mt-4 text-xs text-gray-500">
                  • External endpoint<br />
                  • No auth or OAuth 2.0 (via Okta)<br />
                  • Pre-built MCP server
                </div>
              </div>
            </Card>

            <Card
              className={`opacity-60 cursor-not-allowed transition-all ${
                (mcpType === 'internal-create' || mcpType === 'internal-deploy') ? 'ring-2 ring-blue-600 bg-blue-50' : ''
              }`}
            >
            <div className="text-center py-8">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Internal MCP</h3>
              <p className="text-sm text-gray-600 mb-4">
                Create MCP from your Lambda functions or REST APIs
              </p>
              <div className="mt-4 text-xs text-gray-500">
                • Multiple targets<br />
                • Lambda functions<br />
                • REST APIs with auth
              </div>
            </div>
          </Card>
        </div>
        </div>
      )}

      {/* Step 2: Configure based on type */}
      {step === 2 && (
        <div className="space-y-6">
          {/* Common Fields */}
          <Card>
            <h3 className="font-semibold text-gray-900 mb-6">Basic Information</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  MCP Name <span className="text-error-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  disabled
                  value={formData.name}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500 cursor-not-allowed"
                  placeholder="My MCP"
                />
                <p className="text-xs text-gray-500 mt-1">
                  MCP name cannot be changed after creation. Editing creates a new version.
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
                  rows={3}
                  placeholder="Description of this MCP..."
                />
              </div>

              {/* Semantic Search - for internal types only */}
              {(mcpType === 'internal-deploy' || mcpType === 'internal-create') && (
                <div className="pt-4 border-t border-gray-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Semantic Search
                      </label>
                      <p className="text-xs text-gray-500 mt-1">
                        Tool 검색을 위한 Semantic Search를 활성화합니다. 활성화하면 에이전트가 자연어 쿼리를 기반으로 가장 관련성 높은 Tool을 찾을 수 있습니다.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setEnableSemanticSearch(!enableSemanticSearch)}
                      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 ${
                        enableSemanticSearch ? 'bg-blue-600' : 'bg-gray-200'
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                          enableSemanticSearch ? 'translate-x-5' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* External MCP Configuration */}
          {mcpType === 'external' && (
            <>
              {/* Sub-type Selection (Read-only) */}
              <Card>
                <h3 className="font-semibold text-gray-900 mb-6">External MCP 유형</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div
                    className={`p-6 border-2 rounded-lg text-left transition-all ${
                      externalSubType === 'endpoint'
                        ? 'border-blue-600 bg-blue-50'
                        : 'border-gray-200 bg-gray-50 opacity-60'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xl">🔗</span>
                      <span className="font-semibold text-gray-900">Endpoint URL</span>
                      {externalSubType === 'endpoint' && (
                        <span className="ml-auto px-2 py-0.5 text-xs font-medium bg-blue-600 text-white rounded">선택됨</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600">기존 MCP 서버 엔드포인트에 직접 연결</p>
                  </div>

                  <div
                    className={`p-6 border-2 rounded-lg text-left transition-all ${
                      externalSubType === 'container'
                        ? 'border-blue-600 bg-blue-50'
                        : 'border-gray-200 bg-gray-50 opacity-60'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xl">📦</span>
                      <span className="font-semibold text-gray-900">Container Image</span>
                      {externalSubType === 'container' && (
                        <span className="ml-auto px-2 py-0.5 text-xs font-medium bg-blue-600 text-white rounded">선택됨</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600">ECR 이미지를 Runtime으로 배포</p>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-3">
                  MCP 유형은 생성 시 결정되며 변경할 수 없습니다.
                </p>
              </Card>

              {/* Endpoint URL Configuration */}
              {externalSubType === 'endpoint' && (
                <Card>
                  <h3 className="font-semibold text-gray-900 mb-6">Endpoint URL 설정</h3>
                  <div className="space-y-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        MCP Server Endpoint URL <span className="text-error-500">*</span>
                      </label>
                      <input
                        type="url"
                        required
                        value={externalData.endpointUrl}
                        onChange={(e) => setExternalData({ ...externalData, endpointUrl: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none font-mono text-sm"
                        placeholder="https://mcp-server.example.com"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        MCP Protocol을 지원하는 서버의 엔드포인트 URL을 입력하세요.
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        인증 방식
                      </label>
                      <select
                        value={externalData.authType}
                        onChange={(e) => {
                          const newAuthType = e.target.value as ExternalAuthType;
                          setExternalData({ ...externalData, authType: newAuthType });
                          if (newAuthType === 'oauth' && oauthProviders.length === 0) {
                            fetchOAuthProviders();
                          }
                        }}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
                      >
                        <option value="no_auth">No Authentication (공용 Cognito 사용)</option>
                        <option value="oauth">OAuth 2.0 (OAuth Provider 선택)</option>
                      </select>
                    </div>

                    {/* OAuth Provider Selection */}
                    {externalData.authType === 'oauth' && (
                      <div className="space-y-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                        <div className="flex items-start gap-2">
                          <div className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold mt-0.5">
                            i
                          </div>
                          <div className="flex-1">
                            <h4 className="font-medium text-blue-900 mb-2">OAuth 2.0 인증</h4>
                            <p className="text-sm text-blue-800 mb-3">
                              선택한 OAuth Provider를 통해 OAuth 2.0 인증이 적용됩니다.
                            </p>
                            <div className="bg-white p-3 rounded border border-blue-200">
                              <label className="text-xs font-medium text-gray-700 mb-2 block">OAuth2 Credential Provider</label>
                              {loadingOAuthProviders ? (
                                <div className="flex items-center gap-2 text-gray-500 py-2">
                                  <LoadingSpinner size="sm" />
                                  <span className="text-xs">OAuth Provider 목록 로딩 중...</span>
                                </div>
                              ) : oauthProviders.length === 0 ? (
                                <div className="text-xs text-gray-500">
                                  사용 가능한 OAuth Provider가 없습니다.
                                </div>
                              ) : (
                                <select
                                  value={externalData.oauthProviderArn}
                                  onChange={(e) => setExternalData({ ...externalData, oauthProviderArn: e.target.value })}
                                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none text-sm"
                                >
                                  <option value="">-- OAuth Provider 선택 --</option>
                                  {oauthProviders.map((provider) => (
                                    <option key={provider.arn} value={provider.arn}>
                                      {provider.name} ({provider.vendor})
                                    </option>
                                  ))}
                                </select>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              )}

              {/* Container Image Configuration (read-only info for now) */}
              {externalSubType === 'container' && (
                <Card>
                  <h3 className="font-semibold text-gray-900 mb-6">Container Image 설정</h3>
                  <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <div className="flex-shrink-0 w-5 h-5 rounded-full bg-amber-500 text-white flex items-center justify-center text-xs font-bold mt-0.5">
                        !
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium text-amber-900 mb-1">Container Image MCP 편집</h4>
                        <p className="text-sm text-amber-800">
                          Container Image 타입 External MCP의 편집 기능은 개발 중입니다.
                        </p>
                      </div>
                    </div>
                  </div>
                </Card>
              )}
            </>
          )}

          {/* Internal MCP Configuration */}
          {mcpType === 'internal-create' && (
            <>
              <Card>
                <div className="flex items-center justify-between mb-6">
                  <h3 className="font-semibold text-gray-900">
                    Targets ({internalData.targets.length}) <span className="text-red-500">*</span>
                  </h3>
                  <button
                    type="button"
                    onClick={addNewTarget}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                  >
                    + Add Target
                  </button>
                </div>

                {internalData.targets.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <p className="mb-2">No targets added yet</p>
                    <p className="text-sm">Click "Add Target" to create a new target</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {internalData.targets.map((target) => (
                      <div key={target.id} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1 space-y-3">
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Target Name <span className="text-error-500">*</span>
                              </label>
                              <input
                                type="text"
                                value={target.name}
                                onChange={(e) => updateTarget(target.id, { name: e.target.value })}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                                placeholder="Target name"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Description
                              </label>
                              <input
                                type="text"
                                value={target.description}
                                onChange={(e) => updateTarget(target.id, { description: e.target.value })}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                                placeholder="Target description"
                              />
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() => deleteTarget(target.id)}
                            className="ml-4 text-red-600 hover:text-red-700 text-sm font-medium"
                          >
                            Delete
                          </button>
                        </div>

                        <div className="space-y-4">
                          {/* REST API Configuration */}
                          {target.type === 'rest-api' && (
                            <div className="space-y-3 p-4 bg-green-50 rounded-lg border border-green-200">
                              <h4 className="font-medium text-gray-900 text-sm">REST API Configuration</h4>

                              <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                  API Endpoint <span className="text-error-500">*</span>
                                </label>
                                <input
                                  type="url"
                                  value={target.restApiEndpoint || ''}
                                  onChange={(e) => updateTarget(target.id, { restApiEndpoint: e.target.value })}
                                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none font-mono text-sm"
                                  placeholder="https://api.example.com"
                                />
                              </div>

                              <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                  Method <span className="text-error-500">*</span>
                                </label>
                                <select
                                  value={target.restApiMethod || 'GET'}
                                  onChange={(e) => updateTarget(target.id, { restApiMethod: e.target.value })}
                                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                                >
                                  <option value="GET">GET</option>
                                  <option value="POST">POST</option>
                                  <option value="PUT">PUT</option>
                                  <option value="DELETE">DELETE</option>
                                  <option value="PATCH">PATCH</option>
                                </select>
                              </div>

                                {/* Authentication Type */}
                                <div>
                                  <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Authentication Type
                                  </label>
                                  <select
                                    value={target.restAuthType || 'none'}
                                    onChange={(e) => updateTarget(target.id, { restAuthType: e.target.value as 'none' | 'oauth' | 'api_key' })}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                                  >
                                    <option value="none">No Authentication</option>
                                    <option value="oauth">OAuth 2.0</option>
                                    <option value="api_key">API Key</option>
                                  </select>
                                </div>

                                {/* API Key Field */}
                                {target.restAuthType === 'api_key' && (
                                  <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                      API Key <span className="text-error-500">*</span>
                                    </label>
                                    <input
                                      type="password"
                                      value={target.restApiKey || ''}
                                      onChange={(e) => updateTarget(target.id, { restApiKey: e.target.value })}
                                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                                      placeholder="Enter API key"
                                    />
                                  </div>
                                )}

                                {/* OAuth Fields */}
                                {target.restAuthType === 'oauth' && (
                                  <>
                                    <div>
                                      <label className="block text-sm font-medium text-gray-700 mb-1">
                                        OAuth Client ID <span className="text-error-500">*</span>
                                      </label>
                                      <input
                                        type="text"
                                        value={target.restOAuthClientId || ''}
                                        onChange={(e) => updateTarget(target.id, { restOAuthClientId: e.target.value })}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                                        placeholder="Enter OAuth client ID"
                                      />
                                    </div>
                                    <div>
                                      <label className="block text-sm font-medium text-gray-700 mb-1">
                                        OAuth Client Secret <span className="text-error-500">*</span>
                                      </label>
                                      <input
                                        type="password"
                                        value={target.restOAuthClientSecret || ''}
                                        onChange={(e) => updateTarget(target.id, { restOAuthClientSecret: e.target.value })}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                                        placeholder="Enter OAuth client secret"
                                      />
                                    </div>
                                    <div>
                                      <label className="block text-sm font-medium text-gray-700 mb-1">
                                        OAuth Token URL <span className="text-error-500">*</span>
                                      </label>
                                      <input
                                        type="url"
                                        value={target.restOAuthTokenUrl || ''}
                                        onChange={(e) => updateTarget(target.id, { restOAuthTokenUrl: e.target.value })}
                                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                                        placeholder="https://example.com/oauth/token"
                                      />
                                    </div>
                                  </>
                                )}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </>
          )}

          {/* Internal Deploy MCP Configuration */}
          {mcpType === 'internal-deploy' && (
            <Card>
              <h3 className="font-semibold text-gray-900 mb-6">Container Configuration</h3>
              <div className="space-y-4">
                {/* ECR Repository (Read-only) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    ECR Repository
                  </label>
                  <input
                    type="text"
                    value={deployData.ecrRepository}
                    disabled
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg font-mono text-sm bg-gray-50 text-gray-600 cursor-not-allowed"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    ECR Repository는 수정할 수 없습니다. 새 Repository를 사용하려면 새 MCP를 생성하세요.
                  </p>
                </div>

                {/* Image Tag (Card-style selection like Create page) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    이미지 태그 선택 <span className="text-error-500">*</span>
                  </label>
                  {loadingImageTags ? (
                    <div className="flex items-center gap-2 text-gray-500 p-4">
                      <LoadingSpinner size="sm" />
                      <span>Loading images...</span>
                    </div>
                  ) : availableImages.length === 0 ? (
                    <div className="text-sm text-gray-500 p-4 bg-gray-50 rounded-lg">
                      레포지터리에 이미지가 없습니다. 현재 선택: <span className="font-mono">{deployData.imageTag}</span>
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {availableImages.map((image, idx) => (
                        <div
                          key={idx}
                          onClick={() => setDeployData({ ...deployData, imageTag: image.tag })}
                          className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                            deployData.imageTag === image.tag
                              ? 'border-blue-600 bg-blue-50'
                              : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="font-medium text-gray-900 flex items-center gap-2">
                                <span className="text-blue-600">🏷️</span>
                                {image.tag}
                                {image.tag === initialData.imageTag && (
                                  <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">현재</span>
                                )}
                              </div>
                              <div className="text-xs text-gray-500 mt-1 space-y-0.5">
                                <div>Pushed: {formatLocalDateTime(image.pushedAt)}</div>
                                <div>Size: {(image.sizeInBytes / 1024 / 1024).toFixed(2)} MB</div>
                                <div className="font-mono text-[10px]">{image.digest.substring(0, 19)}...</div>
                              </div>
                            </div>
                            {deployData.imageTag === image.tag && (
                              <div className="text-blue-600 font-bold text-xl">✓</div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-gray-500 mt-2">
                    배포할 새 이미지 태그를 선택하세요. 변경 시 새로운 Runtime이 생성됩니다.
                  </p>
                </div>

                {/* Warning about deployment */}
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <div className="flex-shrink-0 w-5 h-5 rounded-full bg-amber-500 text-white flex items-center justify-center text-xs font-bold mt-0.5">
                      !
                    </div>
                    <div className="flex-1">
                      <h4 className="font-medium text-amber-900 mb-1">배포 주의사항</h4>
                      <p className="text-sm text-amber-800">
                        Image Tag를 변경하면 Runtime이 새 이미지로 업데이트됩니다.
                        이 과정은 1-2분 정도 소요될 수 있으며, 그 동안 MCP를 사용할 수 없습니다.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Step 3: Review & Create */}
      {step === 3 && (
        <Card>
          <h3 className="font-semibold text-gray-900 mb-6">Review Configuration</h3>
          <div className="space-y-6">
            {/* Basic Info */}
            <div>
              <h4 className="text-sm font-medium text-gray-500 mb-3">Basic Information</h4>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">Name:</dt>
                  <dd className="font-medium text-gray-900">{formData.name}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Description:</dt>
                  <dd className="font-medium text-gray-900">{formData.description || 'N/A'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Type:</dt>
                  <dd className="font-medium text-gray-900">
                    {mcpType === 'external' && 'External MCP'}
                    {mcpType === 'internal-create' && 'Internal MCP - 생성'}
                    {mcpType === 'internal-deploy' && 'Internal MCP - 배포 (컨테이너)'}
                  </dd>
                </div>
                {/* Semantic Search for internal types */}
                {(mcpType === 'internal-deploy' || mcpType === 'internal-create') && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Semantic Search:</dt>
                    <dd>
                      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
                        enableSemanticSearch
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          enableSemanticSearch ? 'bg-green-500' : 'bg-gray-400'
                        }`} />
                        {enableSemanticSearch ? 'Enabled' : 'Disabled'}
                        {initialData?.enableSemanticSearch !== enableSemanticSearch && (
                          <span className="text-blue-600 ml-1">(Changed)</span>
                        )}
                      </span>
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            {/* External Configuration */}
            {mcpType === 'external' && (
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-3">External MCP Configuration</h4>
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-500">유형:</dt>
                    <dd className="font-medium text-gray-900">
                      {externalSubType === 'endpoint' ? 'Endpoint URL' : 'Container Image'}
                    </dd>
                  </div>
                  {externalSubType === 'endpoint' && (
                    <>
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Endpoint URL:</dt>
                        <dd className="font-medium text-gray-900 font-mono text-xs">{externalData.endpointUrl}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-gray-500">인증 방식:</dt>
                        <dd className="font-medium text-gray-900">
                          {externalData.authType === 'no_auth' ? 'No Authentication (공용 Cognito)' : 'OAuth 2.0'}
                        </dd>
                      </div>
                      {externalData.authType === 'oauth' && externalData.oauthProviderArn && (
                        <div className="flex justify-between">
                          <dt className="text-gray-500">OAuth Provider:</dt>
                          <dd className="font-medium text-gray-900 font-mono text-xs">
                            {oauthProviders.find(p => p.arn === externalData.oauthProviderArn)?.name || 'N/A'}
                          </dd>
                        </div>
                      )}
                    </>
                  )}
                </dl>
              </div>
            )}

            {/* Internal Configuration */}
            {mcpType === 'internal-create' && (
              <>
                <div>
                  <h4 className="text-sm font-medium text-gray-500 mb-3">Targets ({internalData.targets.length})</h4>
                  <div className="space-y-3">
                    {internalData.targets.map((target) => (
                      <div key={target.id} className="p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <div className="font-medium text-gray-900">{target.name}</div>
                            {target.description && (
                              <div className="text-sm text-gray-600 mt-1">{target.description}</div>
                            )}
                          </div>
                          <Badge variant="success">REST API</Badge>
                        </div>
                        <dl className="space-y-1 text-sm mt-3">
                          {target.type === 'rest-api' && (
                            <>
                              {target.restApiMethod && (
                                <div className="flex justify-between">
                                  <dt className="text-gray-500">Method:</dt>
                                  <dd>
                                    <span className={`px-2 py-0.5 rounded text-white font-medium text-xs ${
                                      target.restApiMethod === 'GET' ? 'bg-blue-500' :
                                      target.restApiMethod === 'POST' ? 'bg-green-500' :
                                      target.restApiMethod === 'PUT' ? 'bg-orange-500' :
                                      target.restApiMethod === 'PATCH' ? 'bg-orange-400' :
                                      target.restApiMethod === 'DELETE' ? 'bg-red-500' :
                                      'bg-gray-500'
                                    }`}>
                                      {target.restApiMethod.toUpperCase()}
                                    </span>
                                  </dd>
                                </div>
                              )}
                              <div className="flex justify-between">
                                <dt className="text-gray-500">Endpoint:</dt>
                                <dd className="font-medium text-gray-900 font-mono text-xs">{target.restApiEndpoint}</dd>
                              </div>
                              <div className="flex justify-between">
                                <dt className="text-gray-500">Auth:</dt>
                                <dd className="font-medium text-gray-900 capitalize">
                                  {target.restAuthType === 'apiKey' || target.restAuthType === 'api_key' ? 'API Key' :
                                   target.restAuthType === 'oauth' ? 'OAuth 2.0' :
                                   target.restAuthType || 'none'}
                                </dd>
                              </div>
                            </>
                          )}
                        </dl>

                        {/* Tool Parameters */}
                        {target.openApiSchema && target.openApiSchema.paths && (
                          <div className="mt-4 pt-4 border-t border-gray-200">
                            <div className="text-xs font-medium text-gray-500 mb-2">Request Parameters:</div>
                            <div className="space-y-3">
                              {Object.entries(target.openApiSchema.paths).map(([path, methods]: [string, any]) =>
                                Object.entries(methods).map(([method, operation]: [string, any]) => {
                                  if (!['get', 'post', 'put', 'delete', 'patch'].includes(method.toLowerCase())) return null;

                                  const params = operation.parameters || [];
                                  const requestBody = operation.requestBody;

                                  // Skip if no parameters and no request body
                                  if (params.length === 0 && !requestBody) return null;

                                  return (
                                    <div key={`${path}-${method}`} className="text-xs bg-white p-3 rounded border border-gray-200">
                                      {/* Parameters */}
                                      {params.length > 0 && (
                                        <div>
                                          <div className="text-gray-500 font-medium mb-2">Parameters:</div>
                                          <div className="space-y-1.5 ml-2">
                                            {params.map((param: any, idx: number) => (
                                              <div key={idx} className="flex items-start gap-2">
                                                <span className="text-blue-600 font-mono font-medium">{param.name}</span>
                                                {param.required && <span className="text-red-500">*</span>}
                                                <span className="text-gray-400">({param.in})</span>
                                                {param.schema?.type && (
                                                  <span className="text-gray-500">- {param.schema.type}</span>
                                                )}
                                                {param.description && (
                                                  <span className="text-gray-600">: {param.description}</span>
                                                )}
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}

                                      {/* Request Body */}
                                      {requestBody && (
                                        <div className={params.length > 0 ? 'mt-3 pt-3 border-t border-gray-100' : ''}>
                                          <div className="text-gray-500 font-medium mb-2">
                                            Request Body:
                                            {requestBody.required && <span className="text-red-500 ml-1">*</span>}
                                          </div>
                                          <div className="ml-2">
                                            {(() => {
                                              const schema = requestBody.content?.['application/json']?.schema;
                                              if (!schema) return <span className="text-gray-600">object</span>;

                                              // Show properties if available
                                              if (schema.properties) {
                                                return (
                                                  <div className="space-y-1.5">
                                                    {Object.entries(schema.properties).map(([propName, propSchema]: [string, any]) => (
                                                      <div key={propName} className="flex items-start gap-2">
                                                        <span className="text-blue-600 font-mono font-medium">{propName}</span>
                                                        {schema.required?.includes(propName) && <span className="text-red-500">*</span>}
                                                        {propSchema.type && (
                                                          <span className="text-gray-500">- {propSchema.type}</span>
                                                        )}
                                                        {propSchema.description && (
                                                          <span className="text-gray-600">: {propSchema.description}</span>
                                                        )}
                                                      </div>
                                                    ))}
                                                  </div>
                                                );
                                              }

                                              return <span className="text-gray-600">{schema.type || 'object'}</span>;
                                            })()}
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  );
                                })
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-500 mb-3">Gateway</h4>
                  <dl className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Gateway Type:</dt>
                      <dd className="font-medium text-gray-900">
                        Dedicated (자동 생성)
                      </dd>
                    </div>
                  </dl>
                </div>
              </>
            )}

            {/* Internal Deploy Configuration */}
            {mcpType === 'internal-deploy' && (
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-3">Container Configuration</h4>
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-500">ECR Repository:</dt>
                    <dd className="font-medium text-gray-900 font-mono text-xs">{deployData.ecrRepository}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Image Tag:</dt>
                    <dd className="font-medium text-gray-900">
                      {initialData?.imageTag !== deployData.imageTag ? (
                        <span>
                          <span className="line-through text-gray-400">{initialData?.imageTag}</span>
                          <span className="mx-2">→</span>
                          <span className="text-blue-600 font-mono">{deployData.imageTag}</span>
                        </span>
                      ) : (
                        <span className="font-mono">{deployData.imageTag}</span>
                      )}
                    </dd>
                  </div>
                </dl>

                {/* Warning if image tag changed */}
                {initialData?.imageTag !== deployData.imageTag && (
                  <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <div className="flex-shrink-0 w-4 h-4 rounded-full bg-amber-500 text-white flex items-center justify-center text-xs font-bold mt-0.5">
                        !
                      </div>
                      <p className="text-sm text-amber-800">
                        Image Tag 변경 시 Runtime이 새 이미지로 업데이트됩니다. (약 1-2분 소요)
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between pt-6 border-t border-gray-200">
        <button
          onClick={handleBack}
          disabled={step === 1}
          className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Back
        </button>

        {step < 3 ? (
          <button
            onClick={handleNext}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Next
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {submitting ? (
              <>
                <LoadingSpinner size="sm" />
                Saving...
              </>
            ) : (
              'Save Changes'
            )}
          </button>
        )}
      </div>
    </div>
  );
}
