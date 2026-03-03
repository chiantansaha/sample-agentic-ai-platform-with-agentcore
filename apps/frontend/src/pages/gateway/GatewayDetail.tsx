import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import type { Gateway } from '../../types';
import { LoadingSpinner, StatusIndicator, Card, Badge } from '../../components/common';
import { formatLocalDate } from '../../utils/date';
import api from '../../utils/axios';

interface ConnectedMCP {
  id: string;
  name: string;
  type: 'external' | 'internal';
  status: 'active' | 'inactive';
}

export function GatewayDetail() {
  const { id } = useParams<{ id: string }>();
  const [gateway, setGateway] = useState<Gateway | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'mcps'>('overview');
  const [connectedMCPs, setConnectedMCPs] = useState<ConnectedMCP[]>([]);

  useEffect(() => {
    if (id) {
      fetchGateway(id);
    }
  }, [id]);

  const fetchGateway = async (gatewayId: string) => {
    try {
      const response = await api.get(`/gateways/${gatewayId}/`);
      const data = response.data;
      setGateway(data.data);

      // Mock connected MCPs
      if (data.data.type === 'shared') {
        setConnectedMCPs([
          { id: 'mcp-1', name: 'Customer Service MCP', type: 'external', status: 'active' },
          { id: 'mcp-2', name: 'Flight Info MCP', type: 'internal', status: 'active' },
          { id: 'mcp-3', name: 'Booking MCP', type: 'internal', status: 'inactive' },
        ]);
      } else {
        setConnectedMCPs([
          { id: 'mcp-1', name: 'Dedicated MCP', type: 'internal', status: 'active' },
        ]);
      }
    } catch (error) {
      console.error('Failed to fetch Gateway:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!gateway) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Gateway not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/gateways" className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
          ← Back to Gateways
        </Link>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900">{gateway.name}</h1>
            <p className="text-gray-600 mt-1 font-mono text-sm">{gateway.endpoint}</p>
            <div className="flex items-center gap-3 mt-3">
              <Badge variant={gateway.type === 'dedicated' ? 'primary' : 'success'}>
                {gateway.type === 'dedicated' ? 'Dedicated' : 'Shared'}
              </Badge>
              <StatusIndicator status={gateway.status} />
              <StatusIndicator health={gateway.health} />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to={`/gateways/${gateway.id}/edit`}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-sm"
            >
              Edit
            </Link>
            <button
              onClick={() => {/* TODO: Delete functionality */}}
              className="px-6 py-2 border border-red-600 text-red-600 rounded-lg hover:bg-red-50 transition-colors font-medium"
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          {(['overview', 'mcps'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`
                py-2 px-1 border-b-2 font-medium text-sm capitalize transition-colors
                ${
                  activeTab === tab
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-2 gap-6">
          <Card>
            <h3 className="font-semibold text-gray-900 mb-4">Basic Information</h3>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-gray-500">Type</dt>
                <dd className="text-gray-900 font-medium capitalize">{gateway.type}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Endpoint</dt>
                <dd className="text-gray-900 font-mono text-xs">{gateway.endpoint}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Created</dt>
                <dd className="text-gray-900 font-medium">
                  {formatLocalDate(gateway.createdAt)}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Last Updated</dt>
                <dd className="text-gray-900 font-medium">
                  {formatLocalDate(gateway.updatedAt)}
                </dd>
              </div>
            </dl>
          </Card>

          <Card>
            <h3 className="font-semibold text-gray-900 mb-4">Statistics</h3>
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Connected MCPs</dt>
                <dd className="text-gray-900 font-medium">{connectedMCPs.length}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Total Requests (24h)</dt>
                <dd className="text-gray-900 font-medium">1,234,567</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Uptime</dt>
                <dd className="text-gray-900 font-medium">99.9%</dd>
              </div>
            </dl>
          </Card>
        </div>
      )}

      {activeTab === 'mcps' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">
              Connected MCPs ({connectedMCPs.length})
            </h3>
          </div>
          <div className="grid gap-4">
            {connectedMCPs.map((mcp) => (
              <Link key={mcp.id} to={`/mcps/${mcp.id}`}>
                <Card hoverable>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-medium text-gray-900">{mcp.name}</h4>
                        <Badge variant={mcp.type === 'external' ? 'primary' : 'success'}>
                          {mcp.type === 'external' ? 'External' : 'Internal'}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 mt-2">
                        <StatusIndicator
                          status={mcp.status === 'active' ? 'active' : 'inactive'}
                        />
                      </div>
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
