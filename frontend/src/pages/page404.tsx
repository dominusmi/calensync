/* eslint-disable */

import React from 'react';
import Layout from '../components/Layout';
import { Head } from 'vite-react-ssg';

const PageNotFound: React.FC = () => {
    return (
        <Layout verifySession={false} onlyRequired={false}>
            <Head>
                <meta charSet="utf-8" />
                <title>404 | Not found</title>
                <link rel="canonical" href={`https://calensync.live/404`} />
            </Head>
            <div className='hero'>
                <div className="container col-xxl-8 py-5">
                    <h1 className="display-5 fw-bold lh-1 mb-3">Oh no! 404</h1>
                    <h2 className="lead">This page does not exist</h2>
                </div>
            </div>
        </Layout >
    );
};

export default PageNotFound;