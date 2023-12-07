import React, { ReactNode, useEffect, useState } from 'react';
import Footer from './Footer';
import NavBar from './Navbar';
import Toast from './Toast';
import { consumeMessages } from '../utils/common';

interface LayoutProps {
    children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
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