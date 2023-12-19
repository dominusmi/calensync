import React, { ReactNode } from 'react';
import API, { ENV } from '../utils/const';

interface ErrorBoundaryProps {
    children: ReactNode;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps> {
    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        const body = JSON.stringify({
            message: error.message,
            stack: error.stack,
            componentStack: errorInfo.componentStack,
        });

        if (ENV == "development" || ENV == "production") {
            fetch(`${API}/console-error`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: body,
            });
        }else {
            console.log("Would've sent error", body)
        }
    }

    render() {
        return this.props.children;
    }
}

export default ErrorBoundary