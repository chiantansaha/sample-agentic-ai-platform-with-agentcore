import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
          <div className="max-w-md w-full bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-error-50 rounded-lg flex items-center justify-center text-error-500 text-xl">
                ⚠️
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Something went wrong
                </h2>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              An error occurred while rendering this component. Please try refreshing the page.
            </p>
            {this.state.error && (
              <pre className="bg-gray-50 p-3 rounded text-xs text-gray-700 overflow-auto">
                {this.state.error.message}
              </pre>
            )}
            <button
              onClick={() => window.location.reload()}
              className="mt-4 w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Refresh Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
