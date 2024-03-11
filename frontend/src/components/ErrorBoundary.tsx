import React from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
}

// If your ErrorBoundary doesn't use props, you can just use an empty interface
// or extend from React.PropsWithChildren if you plan to use children props
interface ErrorBoundaryProps {}

class ErrorBoundary extends React.Component<React.PropsWithChildren<ErrorBoundaryProps>, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI.
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // You can also log the error to an error reporting service
    logErrorToMyService(error, errorInfo);
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return <h1>Something went wrong.</h1>;
    }

    // Normally, just render children
    return this.props.children;
  }
}

function logErrorToMyService(error: Error, errorInfo: React.ErrorInfo): void {
  // Implementation of logging to a logging service
  console.error('Logging to my service', error, errorInfo);
}

export default ErrorBoundary;