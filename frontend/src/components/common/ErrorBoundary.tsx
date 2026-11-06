import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertOctagon, RotateCcw, Home, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });
    // Keep console log for dev debugging
    console.error('ErrorBoundary caught an unhandled error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      const title = this.props.fallbackTitle || 'Something went wrong on this page';
      const errorMessage = this.state.error?.message || 'An unexpected rendering error occurred.';

      return (
        <div className="min-h-[400px] flex items-center justify-center p-6">
          <div className="bg-white rounded-2xl border border-rose-200 p-8 max-w-xl w-full shadow-lg text-center space-y-5">
            <div className="w-14 h-14 bg-rose-50 border border-rose-200 rounded-2xl flex items-center justify-center mx-auto text-rose-600 shadow-sm">
              <AlertOctagon className="w-7 h-7" />
            </div>

            <div className="space-y-2">
              <h3 className="text-xl font-bold text-slate-900 tracking-tight">{title}</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
                The AI Job Search Agent UI caught a component-level error. The application remains active and your candidate data is completely safe.
              </p>
            </div>

            <div className="p-3 bg-rose-50/70 rounded-xl border border-rose-100 text-left">
              <p className="text-xs font-mono text-rose-700 break-words line-clamp-3">
                {errorMessage}
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <button
                onClick={this.handleReset}
                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Reload View
              </button>

              <button
                onClick={() => {
                  window.location.href = '/';
                }}
                className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition"
              >
                <Home className="w-3.5 h-3.5" /> Go to Dashboard
              </button>

              <button
                onClick={() => this.setState({ showDetails: !this.state.showDetails })}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-600 transition"
              >
                {this.state.showDetails ? (
                  <>
                    Hide Stack <ChevronUp className="w-3.5 h-3.5" />
                  </>
                ) : (
                  <>
                    Technical Details <ChevronDown className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>

            {this.state.showDetails && (
              <div className="mt-4 p-4 bg-slate-900 rounded-xl text-left overflow-auto max-h-48">
                <pre className="text-[11px] font-mono text-slate-300 leading-normal whitespace-pre-wrap">
                  {this.state.error?.stack || errorMessage}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
