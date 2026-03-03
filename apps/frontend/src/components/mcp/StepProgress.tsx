/**
 * Step Progress Component
 * 멀티 스텝 폼의 진행 상태를 표시
 */

interface Step {
  number: number;
  label: string;
}

interface StepProgressProps {
  steps: Step[];
  currentStep: number;
}

export function StepProgress({ steps, currentStep }: StepProgressProps) {
  return (
    <div className="flex items-center justify-center gap-4">
      {steps.map((step, index) => (
        <div key={step.number} className="flex items-center gap-4">
          <div className={`flex items-center gap-2 ${currentStep >= step.number ? 'text-blue-600' : 'text-gray-400'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-semibold ${
              currentStep >= step.number ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
            }`}>
              {step.number}
            </div>
            <span className="font-medium">{step.label}</span>
          </div>
          {index < steps.length - 1 && (
            <div className="w-12 h-0.5 bg-gray-300" />
          )}
        </div>
      ))}
    </div>
  );
}

// 기본 MCP 생성/편집 스텝 정의
export const MCP_STEPS: Step[] = [
  { number: 1, label: 'Select Type' },
  { number: 2, label: 'Configure' },
  { number: 3, label: 'Review & Create' },
];
