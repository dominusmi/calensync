import React, { ReactNode, useEffect, useState } from 'react';
import Footer from './Footer';
import NavBar from './Navbar';
import Toast from './Toast';
import { consumeMessages } from '../utils/common';
import axios from 'axios';
import API from '../utils/const';

interface LayoutProps {
    children: ReactNode;
    verify_session?: boolean;
}

const Layout: React.FC<LayoutProps> = ({ children, verify_session = true }) => {
    const [toastReady, setToastReady] = useState(false);

    const handleToastReady = () => {
        setToastReady(true);
    };

    const handleError = async (ev: any) => {
        console.log("event")
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
        } catch(e) {}
    }

    useEffect(() => {
        // Your function to be triggered after the component is ready
        consumeMessages();
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
        <div className='App bg-light'>
            <div className='content justify-content-center'>
            <NavBar verify_session={verify_session} />
                <main className=''>
                    {children}
                </main>
            </div>
            <Footer />
            <Toast onReady={handleToastReady} />
        </div>
    );
};

export default Layout;