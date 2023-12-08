import React, { ReactNode, useEffect, useState } from 'react';
import Footer from './Footer';
import NavBar from './Navbar';
import Toast from './Toast';
import { MessageKind, consumeMessages, setMessage } from '../utils/common';
import verify_session_id, { VerifySession } from '../utils/session';
import { PUBLIC_URL } from '../utils/const';

interface LayoutProps {
    children: ReactNode;
    verify_session?: boolean;
}

const Layout: React.FC<LayoutProps> = ({ children, verify_session = true }) => {
    const [toastReady, setToastReady] = useState(false);

    const handleToastReady = () => {
        setToastReady(true);
    };

    useEffect(() => {
        // Your function to be triggered after the component is ready
        consumeMessages();
    }, [toastReady]);

    return (
        <div className='App bg-light'>
            <div className='content'>
                <NavBar />
                <main>
                    {children}
                </main>
            </div>
            <Footer />
            <Toast onReady={handleToastReady} />
        </div>
    );
};

export default Layout;