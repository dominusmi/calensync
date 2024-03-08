import React, { ReactNode, lazy, useEffect, useState } from 'react';
const Footer = lazy(() => import('./Footer'))
const NavBar = lazy(() => import('./Navbar'))
import Toast, { createToast } from './Toast';
import { MessageKind, consumeMessages } from '../utils/common';
import axios from 'axios';

interface LayoutProps {
    children: ReactNode;
    verifySession?: boolean;
    onlyRequired?: boolean;
}

const Layout: React.FC<LayoutProps> = ({ children, verifySession = true, onlyRequired = false}) => {
    const [toastReady, setToastReady] = useState(false);
    const handleToastReady = () => {
        setToastReady(true);
    };

    const handleError = async (ev: any) => {
        try {
            await axios.post(
                `https://api.hook2email.com/hook/4b262ccb-a724-4bf7-b362-092b7407dba0/send`,
                { error: JSON.stringify(ev) },
                {
                    headers: {
                        'Content-Type': 'application/json',
                    },
                }
            );
        } catch (e) { }
    }

    useEffect(() => {
        // Your function to be triggered after the component is ready
        if (toastReady) {
            const urlParams = new URLSearchParams(window.location.search);
            let err = urlParams.get('error_msg');
            if (err !== null) {
                createToast(atob(err), MessageKind.Error);
            }
            let info = urlParams.get('msg');
            if (info !== null) {
                createToast(atob(info), MessageKind.Info);
            }
            consumeMessages();
        }
    }, [toastReady]);

    useEffect(() => {
        window.addEventListener('error', (ev) => {
            handleError(ev)
        });

        return () => {
            window.removeEventListener('error', handleError);
        };
    }, [])

    return (
        <div className='bg-light'>
            <div className='App'>
                <div className='content justify-content-center'>
                    <NavBar verify_session={onlyRequired} />
                    <main className=''>
                        {children}
                    </main>
                </div>
                <Toast onReady={handleToastReady} />
            </div>
            <Footer onlyRequired={onlyRequired} />
        </div>
    );
};

export default Layout;