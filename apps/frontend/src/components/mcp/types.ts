/**
 * MCP 관련 공통 타입 정의
 */

export type MCPType = 'external' | 'external-endpoint' | 'external-container' | 'internal-deploy' | 'internal-create';
export type ExternalSubType = 'endpoint' | 'container' | null;
export type InternalTargetType = 'rest-api';
export type AuthType = 'none' | 'oauth' | 'api_key';

export interface Target {
  id: string;
  name: string;
  description: string;
  type: InternalTargetType;
  schemaLocation: string;
  restApiEndpoint?: string;
  restApiMethod?: string;
  restAuthType?: AuthType;
  restApiKey?: string;
  restOAuthClientId?: string;
  restOAuthClientSecret?: string;
  restOAuthTokenUrl?: string;
  openApiSchema?: any;
}

export interface ECRRepository {
  name: string;
  uri: string;
  arn: string;
  createdAt: string;
}

export interface ECRImage {
  tag: string;
  digest: string;
  pushedAt: string;
  sizeInBytes: number;
  repositoryName: string;
}

export interface CognitoUserPool {
  id: string;
  name: string;
  arn: string;
  createdAt: string;
  domain?: string;
}

export interface OAuthProvider {
  name: string;
  arn: string;
  vendor: string;
  createdAt: string;
}

export interface ExternalEndpointData {
  endpointUrl: string;
  authType: 'no_auth' | 'oauth';
  oauthProviderArn: string;
  userPoolId: string;
}

export interface InternalData {
  targets: Target[];
  gatewayType: 'dedicated';
  gatewayId: string;
}

export interface FormData {
  name: string;
  description: string;
}

// Auth type mapping from OpenAPI schema
export const AUTH_TYPE_MAP: Record<string, AuthType> = {
  oauth2: 'oauth',
  oauth: 'oauth',
  apiKey: 'api_key',
  api_key: 'api_key',
  none: 'none',
  '': 'none',
};
