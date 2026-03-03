import { useEffect, useState, useRef, useCallback } from 'react';

interface DeployProgressProps {
  payload: any;
  onComplete: (mcpId: string) => void;
  onError: (error: string) => void;
}

export function DeployProgress({ payload, onComplete, onError }: DeployProgressProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [statusText, setStatusText] = useState('Initializing...');
  const [isCompleted, setIsCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasStarted = useRef(false);
  const totalSteps = 8;

  const startDeployment = useCallback(async () => {
    if (hasStarted.current) return;
    hasStarted.current = true;

    try {
      const response = await fetch('/api/v1/mcps/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `HTTP error ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const chunk of lines) {
          if (!chunk.trim()) continue;

          const eventMatch = chunk.match(/^event:\s*(.+)$/m);
          const dataMatch = chunk.match(/^data:\s*(.+)$/m);

          if (dataMatch) {
            try {
              const data = JSON.parse(dataMatch[1]);
              const eventType = eventMatch ? eventMatch[1] : 'message';

              if (eventType === 'result') {
                if (data.success && data.mcpId) {
                  setCurrentStep(totalSteps);
                  setStatusText('Complete!');
                  setIsCompleted(true);
                  onComplete(data.mcpId);
                } else if (data.error) {
                  setError(data.error);
                  onError(data.error);
                }
              } else {
                // Progress step update
                if (data.status === 'completed') {
                  setCurrentStep(data.step);
                } else if (data.status === 'in_progress') {
                  setCurrentStep(data.step - 1);
                  setStatusText(data.title);
                } else if (data.status === 'failed') {
                  setError(data.details || 'Deployment failed');
                  onError(data.details || 'Deployment failed');
                }
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }
    } catch (err: any) {
      setError(err.message || 'Connection failed');
      onError(err.message || 'Connection failed');
    }
  }, [payload, onComplete, onError]);

  useEffect(() => {
    startDeployment();
  }, [startDeployment]);

  const progress = (currentStep / totalSteps) * 100;

  return (
    <div className="mt-4 space-y-2">
      {/* Progress Bar */}
      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ease-out ${
            error ? 'bg-red-500' : isCompleted ? 'bg-green-500' : 'bg-blue-600'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Status Text */}
      <div className="flex items-center justify-between text-sm">
        <span className={`${error ? 'text-red-600' : isCompleted ? 'text-green-600' : 'text-gray-600'}`}>
          {error ? error : isCompleted ? 'MCP created successfully!' : statusText}
        </span>
        <span className="text-gray-400 text-xs">
          {currentStep}/{totalSteps}
        </span>
      </div>
    </div>
  );
}
