import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import { toast } from "sonner";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = {
    hasError: false,
    error: null,
  };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
    toast.error("Something went wrong", {
      description: error.message,
      duration: Infinity,
      action: {
        label: "Reload",
        onClick: () => window.location.reload(),
      },
    });
  }

  private handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  private handleHome = () => {
    window.location.href = "/";
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="flex min-h-screen items-center justify-center bg-background px-4">
          <div className="w-full max-w-md rounded-2xl border bg-card p-8 shadow-xl text-center animate-fade-in">
            <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-danger/10">
              <AlertTriangle className="h-8 w-8 text-danger" aria-hidden />
            </div>
            <h1 className="text-2xl font-bold text-foreground">Something went wrong</h1>
            <p className="mt-3 text-muted-foreground">
              {this.state.error?.message || "An unexpected error occurred. Please try again."}
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Button variant="brand" size="lg" onClick={this.handleRetry} className="w-full sm:w-auto">
                <RefreshCw className="h-4 w-4 mr-2" aria-hidden />
                Try again
              </Button>
              <Button variant="outline" size="lg" onClick={this.handleHome} className="w-full sm:w-auto">
                <Home className="h-4 w-4 mr-2" aria-hidden />
                Go home
              </Button>
            </div>
            <p className="mt-6 text-xs text-muted-foreground">
              If this persists, please contact support.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}