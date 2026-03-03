/**
 * DeployModal - Agent 배포 상태 모달
 *
 * Agent 저장 후 자동 배포 진행 상황을 보여주는 모달입니다.
 */
import type { Deployment } from '../../types';
import { Button } from '../common';

interface DeployModalProps {
  isOpen: boolean;
  onClose: () => void;
  deployment: Deployment | null;
  deployError: string | null;
  onRetry: () => void;
  onGoToPlayground: () => void;
}

export function DeployModal({
  isOpen,
  onClose,
  deployment,
  deployError,
  onRetry,
  onGoToPlayground,
}: DeployModalProps) {
  if (!isOpen) return null;

  const canClose = deployment?.status === 'ready' || deployment?.status === 'failed' || deployError;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-semibold text-gray-900">Agent 배포</h3>
            {canClose && (
              <button
                onClick={onClose}
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
                <Button variant="outline" onClick={onClose}>
                  닫기
                </Button>
                <Button onClick={onRetry}>
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
                <Button variant="outline" onClick={onClose}>
                  닫기
                </Button>
                <Button onClick={onGoToPlayground}>
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
  );
}
