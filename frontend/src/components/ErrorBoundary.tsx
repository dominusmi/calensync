import React, { ReactNode } from 'react';
import { ENV } from '../utils/const';

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
            fetch('https://api.hook2email.com/hook/4b262ccb-a724-4bf7-b362-092b7407dba0/send', {
                method: 'POST',
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