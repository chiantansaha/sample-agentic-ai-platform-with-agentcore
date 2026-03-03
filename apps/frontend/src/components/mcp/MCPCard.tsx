import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { MCP, Status, MCPHealthStatus, Health } from '../../types';
import { StatusIndicator, Card } from '../common';
import { formatLocalDate } from '../../utils/date';
import api from '../../utils/axios';

interface MCPCardProps {
  mcp: MCP;
  onStatusToggle?: (mcpId: string, currentStatus: Status) => void;
}

export function MCPCard({ mcp, onStatusToggle }: MCPCardProps) {
  const [healthStatus, setHealthStatus] = useState<MCPHealthStatus | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);

  // Fetch health status when card mounts (only for enabled MCPs)
  useEffect(() => {
    if (mcp.status === 'enabled') {
      fetchHealth();
    }
  }, [mcp.id, mcp.status]);

  const fetchHealth = async () => {
    setHealthLoading(true);
    try {
      const response = await api.get(`/mcps/${mcp.id}/health`);
      if (response.data.success) {
        setHealthStatus(response.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch health:', error);
    } finally {
      setHealthLoading(false);
    }
  };

  // Convert health status to Health type
  const getHealthValue = (): Health | undefined => {
    if (mcp.status !== 'enabled') return undefined;
    if (!healthStatus?.health) return undefined;
    if (healthStatus.health.healthy === true) return 'healthy';
    if (healthStatus.health.healthy === false) return 'unhealthy';
    return 'unknown';
  };

  // MCP 타입 표시 텍스트 및 스타일
  const getTypeDisplay = () => {
    switch (mcp.type) {
      case 'external':
        return { label: 'External', color: 'text-purple-700', bg: 'bg-purple-50', icon: '🌐' };
      case 'internal-deploy':
        return { label: 'Internal (Container)', color: 'text-blue-700', bg: 'bg-blue-50', icon: '📦' };
      case 'internal-create':
        return { label: 'Internal (API)', color: 'text-green-700', bg: 'bg-green-50', icon: '🔧' };
      default:
        return { label: 'Unknown', color: 'text-gray-700', bg: 'bg-gray-50', icon: '❓' };
    }
  };

  const typeDisplay = getTypeDisplay();

  const handleToggleClick = (e: React.MouseEvent) => {
    e.preventDefault(); // Prevent navigation
    e.stopPropagation(); // Stop event bubbling
    if (onStatusToggle) {
      onStatusToggle(mcp.id, mcp.status);
    }
  };

  return (
    <Link to={`/mcps/${mcp.id}`} className="block h-full">
      <Card hoverable className="flex flex-col h-full hover:shadow-lg transition-shadow">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 hover:text-blue-600 transition-colors">
              {mcp.name}
            </h3>
            <div className="space-y-1 mt-1">
              <p className="text-xs text-gray-500">
                <span className="font-medium">Version:</span> {mcp.version}
              </p>
              <p className="text-xs text-gray-500 font-mono break-all">
                {mcp.endpoint}
              </p>
            </div>
          </div>
          <div className={`ml-2 px-2 py-1 ${typeDisplay.bg} rounded-md border border-gray-200`}>
            <span className={`text-xs font-medium ${typeDisplay.color}`}>
              {typeDisplay.label}
            </span>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-gray-600 mb-4 line-clamp-2">
          {mcp.description}
        </p>

        {/* Stats */}
        <div className="flex items-center gap-4 mb-4 text-sm">
          <div className="text-gray-600">
            <span className="font-medium text-gray-900">{mcp.toolList?.length || 0}</span> tools
          </div>
        </div>

        {/* Footer */}
        <div className="mt-auto pt-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <StatusIndicator status={mcp.status} />
              {mcp.status === 'enabled' && (
                healthLoading ? (
                  <span className="w-2 h-2 rounded-full bg-gray-300 animate-pulse" title="Checking health..." />
                ) : (
                  <span
                    className={`w-2 h-2 rounded-full ${
                      getHealthValue() === 'healthy' ? 'bg-green-500' :
                      getHealthValue() === 'unhealthy' ? 'bg-red-500' :
                      'bg-gray-400'
                    }`}
                    title={`Health: ${getHealthValue() || 'Unknown'}`}
                  />
                )
              )}
              {onStatusToggle && (
                <button
                  onClick={handleToggleClick}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                    mcp.status === 'enabled' ? 'bg-blue-600' : 'bg-gray-300'
                  }`}
                  title={mcp.status === 'enabled' ? 'Disable MCP' : 'Enable MCP'}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      mcp.status === 'enabled' ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              )}
            </div>
            <span className="text-xs text-gray-500">
              {formatLocalDate(mcp.updatedAt)}
            </span>
          </div>
        </div>
      </Card>
    </Link>
  );
}
