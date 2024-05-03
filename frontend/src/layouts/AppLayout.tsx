import '@mantine/core/styles.css';

import React, { ReactNode, lazy, useEffect, useState } from 'react';
const Footer = lazy(() => import('../components/Footer'))
const NavBar = lazy(() => import('../components/Navbar'))
import Toast, { createToast } from '../components/Toast';
import { MessageKind, consumeMessages } from '../utils/common';
import { PlausibleProvider } from '../contexts/PlausibleProvider';
import { ClientOnly, Head } from 'vite-react-ssg';
import { sendErrorToH2E } from '../utils/app';
import { ColorSchemeScript, MantineProvider, createTheme } from '@mantine/core';

interface LayoutProps {
    children: ReactNode;
    onlyRequired?: boolean;
    dashboard?: boolean;
}


const AppLayout: React.FC<LayoutProps> = ({ children, onlyRequired = false, dashboard = false }) => {
    const [toastReady, setToastReady] = useState(false);
    const handleToastReady = () => {
        setToastReady(true);
    };


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
            sendErrorToH2E(ev)
        });

        return () => {
            window.removeEventListener('error', sendErrorToH2E);
        };
    }, [])

    return (
        <>
            <MantineProvider>
                <ClientOnly 
                    children={() => (
                        <PlausibleProvider>
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
                        </PlausibleProvider>
                    )}>

                </ClientOnly>
            </MantineProvider>

        </>
    );
};

export default AppLayout;
