import { Card } from '../../components/common';
import { Globe, Clock } from 'lucide-react';

export function Settings() {
  // 브라우저 로컬 타임존
  const localTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  // 배포된 리전 (환경변수에서 가져오거나 기본값)
  const deployedRegion = import.meta.env.VITE_AWS_REGION || 'ap-northeast-1';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">Platform settings</p>
      </div>

      {/* Environment Information */}
      <Card>
        <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
          <Globe className="w-5 h-5" />
          Environment
        </h3>
        <dl className="space-y-4 text-sm">
          <div className="flex items-start gap-3">
            <Globe className="w-4 h-4 text-gray-400 mt-0.5" />
            <div>
              <dt className="text-gray-500 dark:text-gray-400 text-xs">Deployed Region</dt>
              <dd className="text-gray-900 dark:text-gray-100 font-medium">{deployedRegion}</dd>
            </div>
          </div>
          <div className="flex items-start gap-3 pt-2 border-t border-gray-100 dark:border-gray-700">
            <Clock className="w-4 h-4 text-gray-400 mt-0.5" />
            <div>
              <dt className="text-gray-500 dark:text-gray-400 text-xs">Your Local Timezone</dt>
              <dd className="text-gray-900 dark:text-gray-100 font-medium">{localTimezone}</dd>
            </div>
          </div>
        </dl>
      </Card>
    </div>
  );
}
