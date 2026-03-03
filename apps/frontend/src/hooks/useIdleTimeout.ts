import { useEffect, useRef, useCallback } from 'react';

interface UseIdleTimeoutOptions {
  /**
   * 비활성 타임아웃 시간 (밀리초)
   * 기본값: 30분 (1800000ms)
   */
  idleTimeout?: number;

  /**
   * 절대 타임아웃 시간 (밀리초)
   * 최초 로그인 후 이 시간이 지나면 무조건 로그아웃
   * 기본값: 8시간 (28800000ms)
   */
  absoluteTimeout?: number;

  /**
   * 타임아웃 발생 시 호출될 콜백
   */
  onTimeout: () => void;

  /**
   * 타임아웃 경고 (타임아웃 1분 전)
   * 선택적 - 사용자에게 경고를 주고 싶을 때
   */
  onWarning?: () => void;

  /**
   * 경고 시간 (타임아웃 몇 초 전에 경고할지)
   * 기본값: 60초
   */
  warningTime?: number;
}

const IDLE_TIMEOUT_DEFAULT = 30 * 60 * 1000; // 30분
const ABSOLUTE_TIMEOUT_DEFAULT = 8 * 60 * 60 * 1000; // 8시간
const WARNING_TIME_DEFAULT = 60 * 1000; // 1분

/**
 * 사용자 비활성 상태를 감지하고 타임아웃 처리하는 훅
 *
 * @example
 * ```tsx
 * useIdleTimeout({
 *   idleTimeout: 30 * 60 * 1000, // 30분
 *   absoluteTimeout: 8 * 60 * 60 * 1000, // 8시간
 *   onTimeout: () => {
 *     console.log('세션 만료!');
 *     logout();
 *   },
 *   onWarning: () => {
 *     console.log('1분 후 로그아웃됩니다!');
 *   }
 * });
 * ```
 */
export function useIdleTimeout({
  idleTimeout = IDLE_TIMEOUT_DEFAULT,
  absoluteTimeout = ABSOLUTE_TIMEOUT_DEFAULT,
  onTimeout,
  onWarning,
  warningTime = WARNING_TIME_DEFAULT,
}: UseIdleTimeoutOptions) {
  const idleTimerRef = useRef<number | null>(null);
  const warningTimerRef = useRef<number | null>(null);
  const absoluteTimerRef = useRef<number | null>(null);
  const loginTimeRef = useRef<number>(Date.now());

  // 타이머 정리
  const clearTimers = useCallback(() => {
    if (idleTimerRef.current) {
      clearTimeout(idleTimerRef.current);
      idleTimerRef.current = null;
    }
    if (warningTimerRef.current) {
      clearTimeout(warningTimerRef.current);
      warningTimerRef.current = null;
    }
  }, []);

  // 타이머 리셋 (사용자 활동 감지 시)
  const resetTimer = useCallback(() => {
    clearTimers();

    // 절대 타임아웃 체크
    const elapsedTime = Date.now() - loginTimeRef.current;
    if (elapsedTime >= absoluteTimeout) {
      console.log('⏰ 절대 타임아웃 (최대 세션 시간 초과)');
      onTimeout();
      return;
    }

    // 남은 절대 타임아웃 시간 계산
    const remainingAbsoluteTime = absoluteTimeout - elapsedTime;

    // 비활성 타임아웃이 남은 절대 타임아웃보다 크면 절대 타임아웃 사용
    const effectiveIdleTimeout = Math.min(idleTimeout, remainingAbsoluteTime);

    // 경고 타이머 설정 (타임아웃 전 경고)
    if (onWarning && effectiveIdleTimeout > warningTime) {
      warningTimerRef.current = window.setTimeout(() => {
        console.log('⚠️ 비활성 경고 - 곧 로그아웃됩니다');
        onWarning();
      }, effectiveIdleTimeout - warningTime);
    }

    // 비활성 타임아웃 타이머 설정
    idleTimerRef.current = window.setTimeout(() => {
      console.log('⏰ 비활성 타임아웃 (30분 동안 활동 없음)');
      onTimeout();
    }, effectiveIdleTimeout);
  }, [idleTimeout, absoluteTimeout, warningTime, onTimeout, onWarning, clearTimers]);

  useEffect(() => {
    // 로그인 시간 기록
    loginTimeRef.current = Date.now();

    // 사용자 활동 감지 이벤트
    const events = [
      'mousedown',
      'mousemove',
      'keypress',
      'scroll',
      'touchstart',
      'click',
    ];

    // 이벤트 핸들러
    const handleActivity = () => {
      resetTimer();
    };

    // 이벤트 리스너 등록
    events.forEach((event) => {
      document.addEventListener(event, handleActivity);
    });

    // 절대 타임아웃 타이머 설정 (최초 1회)
    absoluteTimerRef.current = window.setTimeout(() => {
      console.log('⏰ 절대 타임아웃 (최대 세션 시간 8시간 초과)');
      onTimeout();
    }, absoluteTimeout);

    // 초기 타이머 시작
    resetTimer();

    // 클린업
    return () => {
      clearTimers();
      if (absoluteTimerRef.current) {
        clearTimeout(absoluteTimerRef.current);
      }
      events.forEach((event) => {
        document.removeEventListener(event, handleActivity);
      });
    };
  }, [resetTimer, clearTimers, absoluteTimeout, onTimeout]);
}
