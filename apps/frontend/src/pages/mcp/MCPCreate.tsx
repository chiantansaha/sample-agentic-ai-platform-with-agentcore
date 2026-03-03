import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Card, Badge, LoadingSpinner } from '../../components/common';
import { StepProgress, MCP_STEPS, DeployProgress } from '../../components/mcp';
import { formatLocalDateTime } from '../../utils/date';
import api from '../../utils/axios';

type MCPType = 'external' | 'external-endpoint' | 'external-container' | 'internal-deploy' | 'internal-create';
type ExternalSubType = 'endpoint' | 'container' | null;
type InternalTargetType = 'rest-api';

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

interface ECRRepository {
  name: string;
  uri: string;
  arn: string;
  createdAt: string;
}


interface ECRImage {
  tag: string;
  digest: string;
  pushedAt: string;
  sizeInBytes: number;
  repositoryName: string;
}

interface CognitoUserPool {
  id: string;
  name: string;
  domain?: string;
  discovery_url: string;
  created_at?: string;
}

interface OAuthProvider {
  arn: string;
  name: string;
  vendor: string;
  status: string;
  createdAt: string;
}

export function MCPCreate() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [mcpType, setMcpType] = useState<MCPType | null>(null);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Common form data
  const [formData, setFormData] = useState({
    name: '',
    description: '',
  });
  const [nameValidationError, setNameValidationError] = useState<string>('');

  // External MCP sub-type selection
  const [externalSubType, setExternalSubType] = useState<ExternalSubType>(null);

  // External MCP (Endpoint URL) specific
  const [externalEndpointData, setExternalEndpointData] = useState({
    endpointUrl: '',
    authType: 'no_auth' as 'no_auth' | 'oauth',
    oauthProviderArn: '',  // AgentCore Identity OAuth2 Credential Provider ARN
    userPoolId: '',  // Legacy (for backward compatibility)
  });

  // External MCP (Container Image) - uses ecrRepositories, ecrImages, selectedRepository, selectedImage from Internal Deploy
  const [externalContainerData, setExternalContainerData] = useState({
    authType: 'no_auth' as 'no_auth' | 'oauth',
    userPoolId: '',
    environment: {} as Record<string, string>,
  });

  // Cognito User Pools for OAuth selection (Legacy)
  const [userPools, setUserPools] = useState<CognitoUserPool[]>([]);
  const [loadingUserPools, setLoadingUserPools] = useState(false);

  // OAuth2 Credential Providers (AgentCore Identity)
  const [oauthProviders, setOauthProviders] = useState<OAuthProvider[]>([]);
  const [loadingOAuthProviders, setLoadingOAuthProviders] = useState(false);

  // Internal MCP specific - with multiple targets
  // Note: Internal MCPs always use Dedicated Gateway (1:1 mapping)
  const [internalData, setInternalData] = useState({
    targets: [] as Target[],
    gatewayType: 'dedicated' as const, // Always dedicated for internal MCPs
    gatewayId: '',
  });

  // Internal Deploy (ECR Container) specific
  const [ecrRepositories, setEcrRepositories] = useState<ECRRepository[]>([]);
  const [ecrImages, setEcrImages] = useState<ECRImage[]>([]);
  const [selectedRepository, setSelectedRepository] = useState<string>('');
  const [selectedImage, setSelectedImage] = useState<string>('');
  const [loadingEcrRepos, setLoadingEcrRepos] = useState(false);
  const [loadingEcrImages, setLoadingEcrImages] = useState(false);

  // Internal Deploy Configuration
  const [enableSemanticSearch, setEnableSemanticSearch] = useState(false);

  const [editingTargetId, setEditingTargetId] = useState<string | null>(null);
  const [schemaJsonStrings, setSchemaJsonStrings] = useState<Record<string, string>>({});
  const [schemaJsonErrors, setSchemaJsonErrors] = useState<Record<string, string>>({});

  // Deploy Progress state (inline in Step 3)
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployPayload, setDeployPayload] = useState<any>(null);

  useEffect(() => {
    if (mcpType === 'internal-deploy' && step === 2) {
      if (ecrRepositories.length === 0) fetchEcrRepositories();
    } else if (mcpType === 'external-container' && step === 2) {
      // External Container also needs ECR repositories
      if (ecrRepositories.length === 0) fetchEcrRepositories();
    }
    // External Endpoint only needs user pools which are fetched on demand
  }, [mcpType, step]);

  const fetchUserPools = async () => {
    setLoadingUserPools(true);
    try {
      const response = await api.get('/mcps/cognito/user-pools');
      setUserPools(response.data.data || []);
    } catch (err) {
      console.error('Failed to fetch user pools:', err);
      setUserPools([]);
    } finally {
      setLoadingUserPools(false);
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

  const fetchEcrRepositories = async () => {
    setLoadingEcrRepos(true);
    try {
      // Fetch all ECR repositories
      const repoResponse = await api.get('/mcps/ecr/repositories');
      const repositories = repoResponse.data.data || [];
      setEcrRepositories(repositories);
      // Don't auto-select - let user choose
    } catch (err) {
      setError('Failed to load ECR repositories');
      console.error('Failed to load ECR repositories:', err);
    } finally {
      setLoadingEcrRepos(false);
    }
  };

  const fetchEcrImages = async (repositoryName: string) => {
    setLoadingEcrImages(true);
    setEcrImages([]);
    setSelectedImage('');
    try {
      const imagesResponse = await api.get('/mcps/ecr/images/by-repository', {
        params: { repository: repositoryName }
      });
      setEcrImages(imagesResponse.data.data || []);
    } catch (err) {
      console.error('Failed to load ECR images:', err);
      setEcrImages([]);
    } finally {
      setLoadingEcrImages(false);
    }
  };

  const handleRepositoryChange = async (repositoryName: string) => {
    setSelectedRepository(repositoryName);
    await fetchEcrImages(repositoryName);
  };

  const addNewTarget = () => {
    const newTarget: Target = {
      id: `target-${Date.now()}`,
      name: '',
      description: '',
      type: 'rest-api',
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

      // AWS Gateway 명명 규칙 검증
      if (formData.name.length < 1 || formData.name.length > 64) {
        setError('MCP name must be between 1 and 64 characters');
        return;
      }
      
      if (!/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(formData.name)) {
        setError('MCP name can only use letters, numbers, hyphens (-), and underscores (_). Example: my-mcp-name');
        return;
      }

      if (mcpType === 'external') {
        // External MCP requires sub-type selection
        if (!externalSubType) {
          setError('Please select External MCP type (Endpoint URL or Container Image)');
          return;
        }
      }

      if (mcpType === 'external' && externalSubType === 'endpoint') {
        // Validate Endpoint URL
        if (!externalEndpointData.endpointUrl.trim()) {
          setError('Please enter MCP server endpoint URL');
          return;
        }
        // Basic URL validation
        try {
          new URL(externalEndpointData.endpointUrl);
        } catch {
          setError('Please enter a valid URL (e.g., https://example.com/)');
          return;
        }
        // OAuth requires OAuth Provider selection
        if (externalEndpointData.authType === 'oauth' && !externalEndpointData.oauthProviderArn) {
          setError('Please select an OAuth2 Credential Provider for OAuth authentication');
          return;
        }
      } else if (mcpType === 'external' && externalSubType === 'container') {
        // Validate Container Image
        if (!selectedRepository) {
          setError('Please select an ECR repository');
          return;
        }
        if (!selectedImage) {
          setError('Please select an image');
          return;
        }
        // OAuth requires User Pool selection
        if (externalContainerData.authType === 'oauth' && !externalContainerData.userPoolId) {
          setError('Please select a Cognito User Pool for OAuth authentication');
          return;
        }
      } else if (mcpType === 'internal-deploy') {
        if (!selectedRepository) {
          setError('Please select an ECR repository');
          return;
        }
        if (!selectedImage) {
          setError('Please select an image');
          return;
        }
      } else if (mcpType === 'internal-create') {
        if (internalData.targets.length === 0) {
          setError('Please add at least one target');
          return;
        }
        // Validate each target
        for (const target of internalData.targets) {
          if (!target.name) {
            setError(`Target "${target.id}" needs a name`);
            return;
          }
          if (target.type === 'rest-api' && !target.restApiEndpoint) {
            setError(`Target "${target.name}" needs an API endpoint`);
            return;
          }
          // Validate auth credentials
          if (target.type === 'rest-api' && target.restAuthType === 'api_key' && !target.restApiKey) {
            setError(`Target "${target.name}" needs an API key`);
            return;
          }
          if (target.type === 'rest-api' && target.restAuthType === 'oauth' &&
              (!target.restOAuthClientId || !target.restOAuthClientSecret || !target.restOAuthTokenUrl)) {
            setError(`Target "${target.name}" needs all OAuth credentials`);
            return;
          }
          // Validate OpenAPI Schema (required)
          if (!schemaJsonStrings[target.id]?.trim()) {
            setError(`Target "${target.name}" needs an OpenAPI Schema`);
            return;
          }
          try {
            JSON.parse(schemaJsonStrings[target.id]);
          } catch {
            setError(`Target "${target.name}" has invalid JSON in OpenAPI Schema`);
            setSchemaJsonErrors(prev => ({ ...prev, [target.id]: 'Invalid JSON format' }));
            return;
          }
        }
        if (internalData.gatewayType === 'shared' && !internalData.gatewayId) {
          setError('Please select a gateway');
          return;
        }
      }

      setStep(3);
    }
  };

  const handleBack = () => {
    setError('');
    if (step > 1) {
      setStep((step - 1) as 1 | 2 | 3);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');

    try {
      // Determine the actual MCP type for backend
      let actualType = mcpType;
      if (mcpType === 'external') {
        actualType = externalSubType === 'endpoint' ? 'external-endpoint' : 'external-container';
      }

      let payload: any = {
        type: actualType,
        name: formData.name,
        description: formData.description,
      };

      if (mcpType === 'external' && externalSubType === 'endpoint') {
        // External MCP (Endpoint URL)
        payload = {
          ...payload,
          endpoint_url: externalEndpointData.endpointUrl,
          auth_type: externalEndpointData.authType,
          oauth_provider_arn: externalEndpointData.authType === 'oauth' ? externalEndpointData.oauthProviderArn : null,
          user_pool_id: externalEndpointData.authType === 'oauth' ? externalEndpointData.userPoolId : null,  // Legacy
        };
      } else if (mcpType === 'external' && externalSubType === 'container') {
        // External MCP (Container Image)
        payload = {
          ...payload,
          ecr_repository: selectedRepository,
          image_tag: selectedImage,
          auth_type: externalContainerData.authType,
          user_pool_id: externalContainerData.authType === 'oauth' ? externalContainerData.userPoolId : null,
          environment: Object.keys(externalContainerData.environment).length > 0 ? externalContainerData.environment : null,
        };
      } else if (mcpType === 'internal-deploy') {
        payload = {
          ...payload,
          ecr_repository: selectedRepository,
          image_tag: selectedImage,
          resources: {},
          environment: {},
          enable_semantic_search: enableSemanticSearch,
        };
        // For internal-deploy, use SSE with inline progress
        setDeployPayload(payload);
        setIsDeploying(true);
        setSubmitting(false);
        return; // Early return - deployment handled by inline progress
      } else if (mcpType === 'internal-create') {
        payload = {
          ...payload,
          targets: internalData.targets.map(target => ({
            name: target.name,
            description: target.description || '',
            endpoint: target.restApiEndpoint || '',
            method: target.restApiMethod || 'GET',
            openApiSchema: target.openApiSchema || {},
          })),
          enable_semantic_search: enableSemanticSearch,
        };
      }

      // 실제 API 호출 (non-internal-deploy types)
      await api.post('/mcps/', payload);

      // Navigate back to list
      navigate('/mcps');
    } catch (err: any) {
      console.error('Failed to create MCP:', err);
      setError(err.response?.data?.detail || 'Failed to create MCP. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // Handle deploy progress completion
  const handleDeployComplete = (mcpId: string) => {
    // Small delay to show success state before navigating
    setTimeout(() => {
      navigate('/mcps');
    }, 1500);
  };

  // Handle deploy progress error
  const handleDeployError = (errorMsg: string) => {
    setError(errorMsg);
  };

  // Reset deploying state to go back to review
  const handleDeployRetry = () => {
    setIsDeploying(false);
    setDeployPayload(null);
    setError('');
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <Link to="/mcps" className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
          ← Back to MCPs
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Create MCP</h1>
        <p className="text-gray-600 mt-1">
          Set up a new Model Context Protocol integration
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

      {/* Step 1: Select MCP Type */}
      {step === 1 && (
        <div className="grid grid-cols-3 gap-6">
          {/* External MCP Card */}
          <Card
            hoverable={mcpType !== 'external'}
            onClick={() => setMcpType('external')}
            className={`cursor-pointer transition-all relative ${
              mcpType === 'external' ? 'ring-4 ring-blue-600 bg-blue-50 shadow-lg' : ''
            }`}
          >
            {mcpType === 'external' && (
              <div className="absolute top-4 right-4">
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              </div>
            )}
            <div className="text-center py-8">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">External MCP</h3>
              <p className="text-sm text-gray-600 mb-4">
                Slack, GitHub 등 외부 MCP 서버 연결
              </p>
              <div className="mt-4 text-xs text-gray-500 text-left px-4">
                • 오픈소스/서드파티 MCP 서버 연동<br />
                • Endpoint URL로 간편 연결<br />
                • No Auth / OAuth 2.0 인증 지원
              </div>
            </div>
          </Card>

          <Card
            hoverable={mcpType !== 'internal-deploy'}
            onClick={() => setMcpType('internal-deploy')}
            className={`cursor-pointer transition-all relative ${
              mcpType === 'internal-deploy' ? 'ring-4 ring-blue-600 bg-blue-50 shadow-lg' : ''
            }`}
          >
            {mcpType === 'internal-deploy' && (
              <div className="absolute top-4 right-4">
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              </div>
            )}
            <div className="text-center py-8">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Internal MCP - 배포</h3>
              <p className="text-sm text-gray-600 mb-4">
                MCP 서버 이미지를 직접 배포
              </p>
              <div className="mt-4 text-xs text-gray-500 text-left px-4">
                • ECR에 업로드된 MCP 서버 이미지 선택<br />
                • AgentCore Runtime으로 자동 배포<br />
                • 전용 Gateway 및 엔드포인트 생성
              </div>
            </div>
          </Card>

          <Card
            hoverable={mcpType !== 'internal-create'}
            onClick={() => setMcpType('internal-create')}
            className={`cursor-pointer transition-all relative ${
              mcpType === 'internal-create' ? 'ring-4 ring-blue-600 bg-blue-50 shadow-lg' : ''
            }`}
          >
            {mcpType === 'internal-create' && (
              <div className="absolute top-4 right-4">
                <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              </div>
            )}
            <div className="text-center py-8">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Internal MCP - 생성</h3>
              <p className="text-sm text-gray-600 mb-4">
                REST API를 MCP Tool로 변환
              </p>
              <div className="mt-4 text-xs text-gray-500 text-left px-4">
                • 기존 REST API 엔드포인트 등록<br />
                • 자동으로 MCP Tool로 래핑<br />
                • 여러 API를 하나의 MCP로 통합
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Step 2: Configure based on type */}
      {step === 2 && (
        <div className="space-y-6">
          {/* Dedicated Gateway Info for Internal MCPs */}
          {(mcpType === 'internal-deploy' || mcpType === 'internal-create') && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0">
                  <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-blue-800 mb-1">Dedicated Gateway 자동 생성</h4>
                  <p className="text-sm text-blue-700">
                    내부 MCP는 자동으로 전용 Dedicated Gateway가 생성됩니다. 각 MCP는 독립적인 Gateway를 통해 안전하게 관리됩니다.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Shared Gateway Info for External MCPs */}
          {mcpType === 'external' && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0">
                  <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-blue-800 mb-1">Shared Gateway에 Target 추가</h4>
                  <p className="text-sm text-blue-700">
                    {externalSubType === 'endpoint'
                      ? '외부 MCP 서버 엔드포인트가 공유 Gateway에 Target으로 등록됩니다.'
                      : externalSubType === 'container'
                      ? 'ECR 이미지가 Runtime으로 배포된 후 공유 Gateway에 Target으로 등록됩니다.'
                      : '외부 MCP는 공유 Gateway에 Target으로 추가됩니다.'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Common Fields */}
          <Card>
            <h3 className="font-semibold text-gray-900 mb-6">Basic Information</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  MCP Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => {
                    const value = e.target.value;
                    setFormData({ ...formData, name: value });

                    // Real-time validation
                    if (value && !/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(value)) {
                      setNameValidationError('Only English letters, numbers, hyphens (-), and underscores (_) are allowed. Must start with a letter or number.');
                    } else if (value.length > 64) {
                      setNameValidationError('Maximum 64 characters allowed.');
                    } else {
                      setNameValidationError('');
                    }
                  }}
                  className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none ${
                    nameValidationError ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="my-mcp-name"
                  maxLength={64}
                  pattern="^[a-zA-Z0-9][a-zA-Z0-9_-]*$"
                  lang="en"
                  autoComplete="off"
                />
                {nameValidationError ? (
                  <p className="mt-1 text-xs text-red-600">
                    {nameValidationError}
                  </p>
                ) : (
                  <p className="mt-1 text-xs text-gray-500">
                    Use letters, numbers, hyphens (-), and underscores (_). Max 64 characters.
                  </p>
                )}
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
            </div>
          </Card>

          {/* Configuration for Internal MCP (Deploy & Create) */}
          {(mcpType === 'internal-deploy' || mcpType === 'internal-create') && (
            <Card>
              <h3 className="font-semibold text-gray-900 mb-6">Configuration</h3>
              <div className="space-y-4">
                {/* Semantic Search Toggle */}
                <div className="flex items-start justify-between p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex-1 pr-4">
                    <div className="flex items-center gap-2 mb-2">
                      <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      <h4 className="font-medium text-gray-900">Semantic Search</h4>
                    </div>
                    <p className="text-sm text-gray-600">
                      자연어 쿼리를 사용하여 Tool을 검색할 수 있는 Semantic Search를 활성화합니다.
                      단순 키워드 매칭을 넘어 지능적이고 컨텍스트를 인식하는 Tool 매칭이 가능합니다.
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
                      className={`inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        enableSemanticSearch ? 'translate-x-5' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>
                {enableSemanticSearch && (
                  <div className="ml-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <svg className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                      </svg>
                      <p className="text-xs text-blue-700">
                        Semantic Search는 AI 임베딩을 사용하여 Tool 설명의 의미를 이해합니다.
                        "항공편 정보 찾기"와 같은 쿼리가 입력되면 정확한 키워드 일치 대신 의미적으로 Tool을 매칭합니다.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* External MCP Sub-type Selection */}
          {mcpType === 'external' && (
            <Card>
              <h3 className="font-semibold text-gray-900 mb-6">External MCP 유형 선택 <span className="text-red-500">*</span></h3>
              <div className="grid grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => setExternalSubType('endpoint')}
                  className={`p-6 border-2 rounded-lg text-left transition-all ${
                    externalSubType === 'endpoint'
                      ? 'border-blue-600 bg-blue-50'
                      : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      externalSubType === 'endpoint' ? 'bg-blue-600' : 'bg-gray-100'
                    }`}>
                      <svg className={`w-5 h-5 ${externalSubType === 'endpoint' ? 'text-white' : 'text-gray-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                      </svg>
                    </div>
                    <div className="font-semibold text-gray-900">Endpoint URL</div>
                  </div>
                  <p className="text-sm text-gray-600">
                    기존에 배포된 MCP 서버의 엔드포인트 URL에 직접 연결합니다.
                  </p>
                </button>

                <button
                  type="button"
                  disabled
                  className="p-6 border-2 rounded-lg text-left transition-all border-gray-200 bg-gray-50 opacity-60 cursor-not-allowed relative"
                >
                  <div className="absolute top-2 right-2">
                    <span className="px-2 py-1 text-xs font-medium bg-amber-100 text-amber-700 rounded-full">
                      개발 예정
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-gray-100">
                      <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                      </svg>
                    </div>
                    <div className="font-semibold text-gray-400">Container Image</div>
                  </div>
                  <p className="text-sm text-gray-400">
                    ECR에서 컨테이너 이미지를 선택하여 Runtime으로 배포합니다.
                  </p>
                </button>
              </div>
            </Card>
          )}

          {/* External MCP (Endpoint URL) Configuration */}
          {mcpType === 'external' && externalSubType === 'endpoint' && (
            <Card>
              <h3 className="font-semibold text-gray-900 mb-6">Endpoint URL Configuration</h3>

              <div className="space-y-6">
                {/* Endpoint URL Input */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    MCP Server Endpoint URL <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="url"
                    value={externalEndpointData.endpointUrl}
                    onChange={(e) => setExternalEndpointData({ ...externalEndpointData, endpointUrl: e.target.value })}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none font-mono text-sm"
                    placeholder="https://knowledge-mcp.global.api.aws/"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    기존에 배포된 MCP 서버의 엔드포인트 URL을 입력하세요.
                  </p>
                </div>

                {/* Authentication Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    인증 방식 <span className="text-red-500">*</span>
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    <button
                      type="button"
                      onClick={() => {
                        setExternalEndpointData({ ...externalEndpointData, authType: 'no_auth', userPoolId: '' });
                      }}
                      className={`p-4 border-2 rounded-lg text-center transition-all ${
                        externalEndpointData.authType === 'no_auth'
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200 hover:border-blue-300'
                      }`}
                    >
                      <div className="font-medium text-gray-900">No Auth</div>
                      <div className="text-xs text-gray-500 mt-1">공용 Cognito 사용</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setExternalEndpointData({ ...externalEndpointData, authType: 'oauth' });
                        if (oauthProviders.length === 0) fetchOAuthProviders();
                      }}
                      className={`p-4 border-2 rounded-lg text-center transition-all ${
                        externalEndpointData.authType === 'oauth'
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200 hover:border-blue-300'
                      }`}
                    >
                      <div className="font-medium text-gray-900">OAuth 2.0</div>
                      <div className="text-xs text-gray-500 mt-1">OAuth Provider 선택</div>
                    </button>
                  </div>
                </div>

                {/* OAuth Provider Selection (OAuth only) */}
                {externalEndpointData.authType === 'oauth' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      OAuth2 Credential Provider <span className="text-red-500">*</span>
                    </label>
                    {loadingOAuthProviders ? (
                      <div className="flex items-center gap-2 text-gray-500 p-4">
                        <LoadingSpinner size="sm" />
                        <span>OAuth Provider 목록 로딩 중...</span>
                      </div>
                    ) : oauthProviders.length === 0 ? (
                      <div className="text-sm text-gray-500 p-4 bg-gray-50 rounded-lg">
                        사용 가능한 OAuth Provider가 없습니다. AgentCore Identity에서 먼저 생성해주세요.
                      </div>
                    ) : (
                      <select
                        value={externalEndpointData.oauthProviderArn}
                        onChange={(e) => setExternalEndpointData({ ...externalEndpointData, oauthProviderArn: e.target.value })}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none"
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
                )}
              </div>
            </Card>
          )}

          {/* External MCP (Container Image) Configuration - 개발 예정으로 인해 현재 비활성화 */}
          {mcpType === 'external' && externalSubType === 'container' && (
            <Card>
              <h3 className="font-semibold text-gray-900 mb-6">Container Image Configuration</h3>

              <div className="space-y-6">
                {/* ECR Repository Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    ECR 레포지터리 <span className="text-red-500">*</span>
                  </label>
                  {loadingEcrRepos ? (
                    <div className="flex items-center gap-2 text-gray-500 p-4">
                      <LoadingSpinner size="sm" />
                      <span>Loading repositories...</span>
                    </div>
                  ) : ecrRepositories.length === 0 ? (
                    <div className="text-sm text-gray-500 p-4 bg-gray-50 rounded-lg">
                      사용 가능한 ECR 레포지터리가 없습니다.
                    </div>
                  ) : (
                    <>
                      <select
                        value={selectedRepository}
                        onChange={(e) => handleRepositoryChange(e.target.value)}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent outline-none text-sm"
                      >
                        <option value="">-- 레포지터리 선택 --</option>
                        {ecrRepositories.map((repo) => (
                          <option key={repo.name} value={repo.name}>
                            {repo.name}
                          </option>
                        ))}
                      </select>
                      {selectedRepository && (
                        <div className="mt-2 text-xs text-gray-500 font-mono bg-gray-50 p-2 rounded">
                          URI: {ecrRepositories.find(r => r.name === selectedRepository)?.uri || 'N/A'}
                        </div>
                      )}
                    </>
                  )}
                </div>

                {/* ECR Image Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    이미지 태그 선택 <span className="text-red-500">*</span>
                  </label>
                  {!selectedRepository ? (
                    <div className="text-sm text-gray-500 p-4 bg-gray-50 rounded-lg">
                      먼저 ECR 레포지터리를 선택하세요.
                    </div>
                  ) : loadingEcrImages ? (
                    <div className="flex items-center gap-2 text-gray-500 p-4">
                      <LoadingSpinner size="sm" />
                      <span>Loading images...</span>
                    </div>
                  ) : ecrImages.length === 0 ? (
                    <div className="text-sm text-gray-500 p-4 bg-gray-50 rounded-lg">
                      레포지터리에 이미지가 없습니다.
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {ecrImages.map((image, idx) => (
                        <div
                          key={idx}
                          onClick={() => setSelectedImage(image.tag)}
                          className={`p-3 border-2 rounded-lg cursor-pointer transition-all ${
                            selectedImage === image.tag
                              ? 'border-purple-600 bg-purple-50'
                              : 'border-gray-200 hover:border-purple-300 hover:bg-purple-50'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="font-medium text-gray-900 flex items-center gap-2">
                                <span className="text-purple-600">🏷️</span>
                                {image.tag}
                              </div>
                              <div className="text-xs text-gray-500 mt-1">
                                Pushed: {formatLocalDateTime(image.pushedAt)} | Size: {(image.sizeInBytes / 1024 / 1024).toFixed(2)} MB
                              </div>
                            </div>
                            {selectedImage === image.tag && (
                              <div className="text-purple-600 font-bold text-xl">✓</div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Authentication Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    인증 방식 <span className="text-red-500">*</span>
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    <button
                      type="button"
                      onClick={() => {
                        setExternalContainerData({ ...externalContainerData, authType: 'no_auth', userPoolId: '' });
                      }}
                      className={`p-4 border-2 rounded-lg text-center transition-all ${
                        externalContainerData.authType === 'no_auth'
                          ? 'border-purple-600 bg-purple-50'
                          : 'border-gray-200 hover:border-purple-300'
                      }`}
                    >
                      <div className="font-medium text-gray-900">No Auth</div>
                      <div className="text-xs text-gray-500 mt-1">공용 Cognito 사용</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setExternalContainerData({ ...externalContainerData, authType: 'oauth' });
                        if (userPools.length === 0) fetchUserPools();
                      }}
                      className={`p-4 border-2 rounded-lg text-center transition-all ${
                        externalContainerData.authType === 'oauth'
                          ? 'border-purple-600 bg-purple-50'
                          : 'border-gray-200 hover:border-purple-300'
                      }`}
                    >
                      <div className="font-medium text-gray-900">OAuth 2.0</div>
                      <div className="text-xs text-gray-500 mt-1">User Pool 선택</div>
                    </button>
                  </div>
                </div>

                {/* User Pool Selection (OAuth only) */}
                {externalContainerData.authType === 'oauth' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Cognito User Pool <span className="text-red-500">*</span>
                    </label>
                    {loadingUserPools ? (
                      <div className="flex items-center gap-2 text-gray-500 p-4">
                        <LoadingSpinner size="sm" />
                        <span>User Pool 목록 로딩 중...</span>
                      </div>
                    ) : userPools.length === 0 ? (
                      <div className="text-sm text-gray-500 p-4 bg-gray-50 rounded-lg">
                        사용 가능한 User Pool이 없습니다.
                      </div>
                    ) : (
                      <select
                        value={externalContainerData.userPoolId}
                        onChange={(e) => setExternalContainerData({ ...externalContainerData, userPoolId: e.target.value })}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent outline-none"
                      >
                        <option value="">-- User Pool 선택 --</option>
                        {userPools.map((pool) => (
                          <option key={pool.id} value={pool.id}>
                            {pool.name} ({pool.id})
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                )}

                {/* Environment Variables (Optional) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Environment Variables (선택사항)
                  </label>
                  <p className="text-xs text-gray-500 mb-3">
                    컨테이너에 전달할 환경 변수를 설정합니다.
                  </p>
                  <div className="space-y-2">
                    {Object.entries(externalContainerData.environment).map(([key, value], idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <input
                          type="text"
                          value={key}
                          readOnly
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm font-mono"
                        />
                        <span className="text-gray-400">=</span>
                        <input
                          type="text"
                          value={value}
                          readOnly
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm font-mono"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            const newEnv = { ...externalContainerData.environment };
                            delete newEnv[key];
                            setExternalContainerData({ ...externalContainerData, environment: newEnv });
                          }}
                          className="p-2 text-red-500 hover:bg-red-50 rounded"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    ))}
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        id="new-env-key"
                        placeholder="KEY"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono"
                      />
                      <span className="text-gray-400">=</span>
                      <input
                        type="text"
                        id="new-env-value"
                        placeholder="value"
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          const keyInput = document.getElementById('new-env-key') as HTMLInputElement;
                          const valueInput = document.getElementById('new-env-value') as HTMLInputElement;
                          if (keyInput.value && valueInput.value) {
                            setExternalContainerData({
                              ...externalContainerData,
                              environment: {
                                ...externalContainerData.environment,
                                [keyInput.value]: valueInput.value
                              }
                            });
                            keyInput.value = '';
                            valueInput.value = '';
                          }
                        }}
                        className="p-2 text-purple-600 hover:bg-purple-50 rounded border border-purple-300"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* Internal Deploy (ECR Container) Configuration */}
          {mcpType === 'internal-deploy' && (
            <>
              <Card>
                <h3 className="font-semibold text-gray-900 mb-6">ECR 컨테이너 배포 설정</h3>
                <div className="space-y-6">
                  {/* ECR Repository Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      ECR 레포지터리 <span className="text-error-500">*</span>
                    </label>
                    {loadingEcrRepos ? (
                      <div className="flex items-center gap-2 text-gray-500 p-4">
                        <LoadingSpinner size="sm" />
                        <span>Loading repositories...</span>
                      </div>
                    ) : ecrRepositories.length === 0 ? (
                      <div className="text-sm text-gray-500 p-4 bg-gray-50 rounded-lg">
                        사용 가능한 ECR 레포지터리가 없습니다.
                      </div>
                    ) : (
                      <>
                        <select
                          value={selectedRepository}
                          onChange={(e) => handleRepositoryChange(e.target.value)}
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none text-sm"
                        >
                          <option value="">-- 레포지터리 선택 --</option>
                          {ecrRepositories.map((repo) => (
                            <option key={repo.name} value={repo.name}>
                              {repo.name}
                            </option>
                          ))}
                        </select>
                        {selectedRepository && (
                          <div className="mt-2 text-xs text-gray-500 font-mono bg-gray-50 p-2 rounded">
                            URI: {ecrRepositories.find(r => r.name === selectedRepository)?.uri || 'N/A'}
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {/* ECR Image Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      이미지 태그 선택 <span className="text-error-500">*</span>
                    </label>
                    {!selectedRepository ? (
                      <div className="text-sm text-gray-500 p-4 bg-gray-50 rounded-lg">
                        먼저 ECR 레포지터리를 선택하세요.
                      </div>
                    ) : loadingEcrImages ? (
                      <div className="flex items-center gap-2 text-gray-500 p-4">
                        <LoadingSpinner size="sm" />
                        <span>Loading images...</span>
                      </div>
                    ) : ecrImages.length === 0 ? (
                      <div className="text-sm text-gray-500 p-4 bg-gray-50 rounded-lg">
                        레포지터리에 이미지가 없습니다.
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-96 overflow-y-auto">
                        {ecrImages.map((image, idx) => (
                          <div
                            key={idx}
                            onClick={() => setSelectedImage(image.tag)}
                            className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                              selectedImage === image.tag
                                ? 'border-blue-600 bg-blue-50'
                                : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <div className="font-medium text-gray-900 flex items-center gap-2">
                                  <span className="text-blue-600">🏷️</span>
                                  {image.tag}
                                </div>
                                <div className="text-xs text-gray-500 mt-1 space-y-0.5">
                                  <div>Pushed: {formatLocalDateTime(image.pushedAt)}</div>
                                  <div>Size: {(image.sizeInBytes / 1024 / 1024).toFixed(2)} MB</div>
                                  <div className="font-mono text-[10px]">{image.digest.substring(0, 19)}...</div>
                                </div>
                              </div>
                              {selectedImage === image.tag && (
                                <div className="text-blue-600 font-bold text-xl">✓</div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </Card>

              {/* Gateway Info for Deploy */}
              <Card>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <div className="text-blue-600 mt-0.5">
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <h4 className="text-sm font-semibold text-blue-900 mb-1">
                        컨테이너 배포 정보
                      </h4>
                      <p className="text-sm text-blue-800">
                        선택한 ECR 이미지가 AgentCore 런타임에 배포되어 MCP 서버로 실행됩니다.
                        자동으로 스케일링되며 전용 엔드포인트가 생성됩니다.
                      </p>
                    </div>
                  </div>
                </div>
              </Card>
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
                                  />
                                </div>
                              )}

                              {target.restAuthType === 'oauth' && (
                                <div className="space-y-3">
                                  <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                      Client ID <span className="text-error-500">*</span>
                                    </label>
                                    <input
                                      type="text"
                                      value={target.restOAuthClientId || ''}
                                      onChange={(e) => updateTarget(target.id, { restOAuthClientId: e.target.value })}
                                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                                    />
                                  </div>
                                  <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                      Client Secret <span className="text-error-500">*</span>
                                    </label>
                                    <input
                                      type="password"
                                      value={target.restOAuthClientSecret || ''}
                                      onChange={(e) => updateTarget(target.id, { restOAuthClientSecret: e.target.value })}
                                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                                    />
                                  </div>
                                  <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                      Token URL <span className="text-error-500">*</span>
                                    </label>
                                    <input
                                      type="url"
                                      value={target.restOAuthTokenUrl || ''}
                                      onChange={(e) => updateTarget(target.id, { restOAuthTokenUrl: e.target.value })}
                                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                                    />
                                  </div>
                                </div>
                              )}
                              {/* OpenAPI Schema */}
                              <div className="mt-4 pt-4 border-t border-gray-200">
                                <div className="flex items-center justify-between mb-1">
                                  <label className="block text-sm font-medium text-gray-700">
                                    OpenAPI Schema <span className="text-error-500">*</span>
                                  </label>
                                  <button
                                    type="button"
                                    disabled
                                    title="Coming Soon"
                                    className="text-xs px-3 py-1 border border-gray-300 rounded-md text-gray-500 bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                                  >
                                    S3에서 불러오기 <span className="ml-1 text-[10px] bg-gray-200 text-gray-500 px-1.5 py-0.5 rounded">TBD</span>
                                  </button>
                                </div>
                                <textarea
                                  value={schemaJsonStrings[target.id] ?? ''}
                                  onChange={(e) => {
                                    const val = e.target.value;
                                    setSchemaJsonStrings(prev => ({ ...prev, [target.id]: val }));
                                    // Clear error while typing
                                    if (schemaJsonErrors[target.id]) {
                                      setSchemaJsonErrors(prev => ({ ...prev, [target.id]: '' }));
                                    }
                                    // Try parsing on each change
                                    if (val.trim() === '') {
                                      updateTarget(target.id, { openApiSchema: undefined });
                                    } else {
                                      try {
                                        const parsed = JSON.parse(val);
                                        updateTarget(target.id, { openApiSchema: parsed });
                                        setSchemaJsonErrors(prev => ({ ...prev, [target.id]: '' }));
                                      } catch {
                                        // Don't set error during typing, only on blur
                                      }
                                    }
                                  }}
                                  onBlur={(e) => {
                                    const val = e.target.value.trim();
                                    if (val === '') {
                                      updateTarget(target.id, { openApiSchema: undefined });
                                      setSchemaJsonErrors(prev => ({ ...prev, [target.id]: '' }));
                                    } else {
                                      try {
                                        const parsed = JSON.parse(val);
                                        updateTarget(target.id, { openApiSchema: parsed });
                                        setSchemaJsonErrors(prev => ({ ...prev, [target.id]: '' }));
                                      } catch {
                                        setSchemaJsonErrors(prev => ({ ...prev, [target.id]: 'Invalid JSON format' }));
                                      }
                                    }
                                  }}
                                  rows={12}
                                  className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-600 outline-none font-mono text-sm ${
                                    schemaJsonErrors[target.id] ? 'border-red-500' : 'border-gray-300'
                                  }`}
                                  placeholder={`{
  "openapi": "3.0.0",
  "info": { "title": "My API", "version": "1.0.0" },
  "paths": {
    "/items": {
      "get": {
        "summary": "List items",
        "parameters": [
          { "name": "limit", "in": "query", "schema": { "type": "integer" } }
        ]
      }
    }
  }
}`}
                                />
                                {schemaJsonErrors[target.id] && (
                                  <p className="text-xs text-red-500 mt-1">{schemaJsonErrors[target.id]}</p>
                                )}
                              </div>
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
                    {mcpType === 'external' && externalSubType === 'endpoint' && 'External MCP - Endpoint URL'}
                    {mcpType === 'external' && externalSubType === 'container' && 'External MCP - Container Image'}
                    {mcpType === 'internal-deploy' && 'Internal MCP - 배포 (컨테이너)'}
                    {mcpType === 'internal-create' && 'Internal MCP - 생성'}
                  </dd>
                </div>
              </dl>
            </div>

            {/* External Endpoint URL Configuration */}
            {mcpType === 'external' && externalSubType === 'endpoint' && (
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-3">Endpoint URL Configuration</h4>
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Endpoint URL:</dt>
                    <dd className="font-medium text-gray-900 font-mono text-xs">{externalEndpointData.endpointUrl}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Authentication:</dt>
                    <dd className="font-medium text-gray-900">
                      {externalEndpointData.authType === 'no_auth' ? 'No Auth (공용 Cognito)' : 'OAuth 2.0'}
                    </dd>
                  </div>
                  {externalEndpointData.authType === 'oauth' && externalEndpointData.oauthProviderArn && (
                    <div className="flex justify-between">
                      <dt className="text-gray-500">OAuth Provider:</dt>
                      <dd className="font-medium text-gray-900 font-mono text-xs">
                        {oauthProviders.find(p => p.arn === externalEndpointData.oauthProviderArn)?.name || 'N/A'}
                      </dd>
                    </div>
                  )}
                </dl>
              </div>
            )}

            {/* External Container Image Configuration */}
            {mcpType === 'external' && externalSubType === 'container' && (
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-3">Container Image Configuration</h4>
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-500">ECR Repository:</dt>
                    <dd className="font-medium text-gray-900">{selectedRepository || 'N/A'}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Repository URI:</dt>
                    <dd className="font-medium text-gray-900 font-mono text-xs">
                      {ecrRepositories.find(r => r.name === selectedRepository)?.uri || 'N/A'}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Image Tag:</dt>
                    <dd className="font-medium text-gray-900 font-mono text-xs">{selectedImage || 'N/A'}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Authentication:</dt>
                    <dd className="font-medium text-gray-900">
                      {externalContainerData.authType === 'no_auth' ? 'No Auth (공용 Cognito)' : 'OAuth 2.0'}
                    </dd>
                  </div>
                  {externalContainerData.authType === 'oauth' && externalContainerData.userPoolId && (
                    <div className="flex justify-between">
                      <dt className="text-gray-500">User Pool:</dt>
                      <dd className="font-medium text-gray-900 font-mono text-xs">
                        {userPools.find(p => p.id === externalContainerData.userPoolId)?.name || externalContainerData.userPoolId}
                      </dd>
                    </div>
                  )}
                  {Object.keys(externalContainerData.environment).length > 0 && (
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Environment Variables:</dt>
                      <dd className="font-medium text-gray-900">
                        {Object.keys(externalContainerData.environment).length} variable(s) defined
                      </dd>
                    </div>
                  )}
                </dl>
              </div>
            )}

            {/* Internal Deploy Configuration */}
            {mcpType === 'internal-deploy' && (
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-3">컨테이너 배포 설정</h4>
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-500">ECR Repository:</dt>
                    <dd className="font-medium text-gray-900">{selectedRepository || 'N/A'}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Repository URI:</dt>
                    <dd className="font-medium text-gray-900 font-mono text-xs">
                      {ecrRepositories.find(r => r.name === selectedRepository)?.uri || 'N/A'}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Selected Image:</dt>
                    <dd className="font-medium text-gray-900 font-mono text-xs">{selectedImage || 'N/A'}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Semantic Search:</dt>
                    <dd className="font-medium">
                      {enableSemanticSearch ? (
                        <span className="text-green-600">Enabled</span>
                      ) : (
                        <span className="text-gray-500">Disabled</span>
                      )}
                    </dd>
                  </div>
                  {selectedImage && ecrImages.length > 0 && (
                    <>
                      {(() => {
                        const image = ecrImages.find(img =>
                          (img.imageTags && img.imageTags.includes(selectedImage)) ||
                          img.imageDigest === selectedImage
                        );
                        if (image) {
                          return (
                            <>
                              <div className="flex justify-between">
                                <dt className="text-gray-500">Image Pushed:</dt>
                                <dd className="font-medium text-gray-900 text-xs">
                                  {formatLocalDateTime(image.imagePushedAt)}
                                </dd>
                              </div>
                              <div className="flex justify-between">
                                <dt className="text-gray-500">Image Size:</dt>
                                <dd className="font-medium text-gray-900">
                                  {(image.imageSizeInBytes / 1024 / 1024).toFixed(2)} MB
                                </dd>
                              </div>
                            </>
                          );
                        }
                        return null;
                      })()}
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
                    {internalData.targets.map((target, idx) => (
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
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Semantic Search:</dt>
                      <dd className="font-medium">
                        {enableSemanticSearch ? (
                          <span className="text-green-600">Enabled</span>
                        ) : (
                          <span className="text-gray-500">Disabled</span>
                        )}
                      </dd>
                    </div>
                  </dl>
                </div>
              </>
            )}
          </div>
        </Card>
      )}

      {/* Navigation Buttons */}
      <div className="pt-6 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <button
            onClick={handleBack}
            disabled={step === 1 || isDeploying}
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
              disabled={submitting || isDeploying}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {submitting ? (
                <>
                  <LoadingSpinner size="sm" />
                  Creating...
                </>
              ) : isDeploying ? (
                'Deploying...'
              ) : (
                'Create MCP'
              )}
            </button>
          )}
        </div>

        {/* Deploy Progress Bar - shown below buttons when deploying */}
        {isDeploying && deployPayload && (
          <DeployProgress
            payload={deployPayload}
            onComplete={handleDeployComplete}
            onError={handleDeployError}
          />
        )}
      </div>
    </div>
  );
}
