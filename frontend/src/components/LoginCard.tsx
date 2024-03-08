import React, { useEffect, useState } from 'react';
import API, { PUBLIC_URL } from '../utils/const';
import LoadingOverlay from './LoadingOverlay';
import { MessageKind } from '../utils/common';
import { optimisticIsConnected } from '../utils/session';
import { createToast } from './Toast';
import { useTranslation } from 'react-i18next';


const loginCardStyle: React.CSSProperties = {
    width: '18rem',
    marginTop: '15vh', // Adjust this value as needed
    // Add any other styles you need
};

const LoginCard: React.FC = () => {
    const { t } = useTranslation(['app', 'common']);
    const [isLoading, setLoading] = useState(false);
    const [isLogin, setIsLogin] = useState(false);

    useEffect(() => {
        checkSessionOrRedirect();
        if (window.location.search.includes("login")) {
            setIsLogin(true);
        }
    }, [])


    const checkSessionOrRedirect = async () => {
        if (await optimisticIsConnected()) {
            window.location.href = "/dashboard"
        }
    }

    const onGoogleLogin = async () => {
        await handleGoogleLogin()
    }

    const handleGoogleLogin = async () => {
        try {
            const tos_string = "1"
            setLoading(true);

            const response = await fetch(`${API}/google/sso/prepare?tos=${tos_string}`, {
                method: 'GET',
                credentials: 'include'
            });

            if (!response.ok) {
                const error = await response.json();
                const message = error.message || 'A server error occurred'
                createToast(message, MessageKind.Error);
                throw new Error(message);
            }

            const data = await response.json();
            window.location.href = data.url;
        } finally {
            setLoading(false);
        }
    };

    function clickLogin() {
        setIsLogin(!isLogin);
    }

    return (
        <div className="d-flex align-items-center justify-content-center mx-sm-4 mx-2">
            <div
                className=" bg-white shadow-sm rounded border-0 p-4" style={loginCardStyle}>
                {!isLogin &&
                    <div>
                        <div className="my-2 text-center">
                            <h3>{t("common.sign_up")}</h3>
                            <p className="text-muted">Sign up and get started in 30 seconds!</p>
                        </div>
                        <div className="row text-center">
                            <div className="mx-auto mt-2 mb-4" id="google-sso-signup">
                                <button className="gsi-material-button" onClick={onGoogleLogin}>
                                    <div className="gsi-material-button-state"></div>
                                    <div className="gsi-material-button-content-wrapper">
                                        <div className="gsi-material-button-icon">
                                            <svg version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"
                                                xmlnsXlink="http://www.w3.org/1999/xlink">
                                                <path fill="#EA4335"
                                                    d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z">
                                                </path>
                                                <path fill="#4285F4"
                                                    d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z">
                                                </path>
                                                <path fill="#FBBC05"
                                                    d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z">
                                                </path>
                                                <path fill="#34A853"
                                                    d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z">
                                                </path>
                                                <path fill="none" d="M0 0h48v48H0z"></path>
                                            </svg>
                                        </div>
                                        <span className="gsi-material-button-contents">Sign up with Google</span>
                                    </div>
                                </button>
                                <div className='mx-auto mt-1 small'>
                                    <p className="mt-2 mb-0 small">By clicking this button, you acknowledge <br />you have read and accepted the <br />
                                        <a className='text-break' href='/tos'>Terms of Service</a> and the <a href='/privacy'>privacy policy</a></p>
                                </div>
                            </div>
                        </div>
                        <p>Already have an account? <a href={`${PUBLIC_URL}/login`} onClick={(e) => { e.preventDefault(); e.stopPropagation(); clickLogin() }}>Login</a></p>
                    </div>
                }
                {isLogin &&
                    <div>
                        <div className="my-2 text-center">
                            <h3>Login</h3>
                            <p className="text-muted">Login to view and manage your calendars</p>
                        </div>
                        <div className="row text-center">
                            <div className="mx-auto mt-2 mb-4" id="google-sso-login">
                                <button className="gsi-material-button" onClick={onGoogleLogin}>
                                    <div className="gsi-material-button-state"></div>
                                    <div className="gsi-material-button-content-wrapper">
                                        <div className="gsi-material-button-icon">
                                            <svg version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"
                                                xmlnsXlink="http://www.w3.org/1999/xlink">
                                                <path fill="#EA4335"
                                                    d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z">
                                                </path>
                                                <path fill="#4285F4"
                                                    d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z">
                                                </path>
                                                <path fill="#FBBC05"
                                                    d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z">
                                                </path>
                                                <path fill="#34A853"
                                                    d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z">
                                                </path>
                                                <path fill="none" d="M0 0h48v48H0z"></path>
                                            </svg>
                                        </div>
                                        <span className="gsi-material-button-contents">Sign in with Google</span>
                                    </div>
                                </button>
                            </div>
                        </div>
                        <p>Don't have an account? <a href={`${PUBLIC_URL}/login`} onClick={(e) => { e.preventDefault(); e.stopPropagation(); clickLogin() }}>Signup</a></p>
                    </div>
                }
            </div>
            {isLoading && <LoadingOverlay />}
        </div>
    );
};

export default LoginCard;
