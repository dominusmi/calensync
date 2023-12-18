import React, { useEffect, useState } from 'react';
import { ENV, PADDLE_CLIENT_TOKEN, PUBLIC_URL } from '../utils/const';
import Layout from '../components/Layout';
import { PaddlePricing } from '../components/PaddlePricing';
import { Paddle, initializePaddle } from '@paddle/paddle-js';
import { Helmet } from "react-helmet";

const Home: React.FC = () => {
    const [paddle, setPaddle] = useState<Paddle | null>(null);


    const signup = () => {
        window.location.href = `${PUBLIC_URL}/login`;
    }

    async function setupPaddle() {
        const paddleInstance = await initializePaddle({ environment: ENV == "production" ? "production" : "sandbox", token: PADDLE_CLIENT_TOKEN });
        if (paddleInstance) {
            setPaddle(paddleInstance);
        }
    }

    useEffect(() => {
        setupPaddle();
    }, [])

    return (
        <Layout verify_session={false}>
            <Helmet>
                <meta charSet="utf-8" />
                <title>Sync your Google Calendars</title>
                <link rel="canonical" href={`https://calensync.live${PUBLIC_URL}`} />
                <meta name="description" content="Calensync allows you to synchronize multiple Google calendars easily, while keeping the privacy 
                of the event description. It copies events between calendars and replaces them with a Blocker. The product uses as a SaaS subscription model. On top of that, it's open-source!" />
                <meta name="og:title" content="Synchronize your Google Calendars" />
                <meta name="og:url" content="{`https://calensync.live${PUBLIC_URL}`}" />
                <meta name="og:description" content="Calensync allows you to synchronize multiple Google calendars easily, while keeping the privacy 
                of the event description. It copies events between calendars and replaces them with a Blocker. The product uses as a SaaS subscription model. On top of that, it's open-source!" />
            </Helmet>
            <div className='hero'>
                <div className="container col-xxl-8 py-5">
                    <div className="row flex-lg-row-reverse align-items-center g-4 py-5 justify-content-center">
                        <div className="col-10 col-sm-8 col-lg-6">
                            <img src="hero.gif" className="d-block mx-lg-auto img-fluid hero-gif" alt="Bootstrap Themes" width="700" height="500" loading="lazy" />
                        </div>
                        <div className="col-lg-6">
                            <h1 className="display-5 fw-bold lh-1 mb-3">No more event conflicts.</h1>
                            <p className="lead">
                                Sync all your Google calendars together and save yourself trouble of having to reschedule appointments.
                                Make sure no one ever books a meeting when you're already busy.
                            </p>
                            <div className="d-grid gap-2 d-md-flex justify-content-md-start mt-4">
                                <button type="button" className="btn btn-primary btn-lg px-4 me-md-2" onClick={signup}>Signup</button>
                            </div>
                            <p className='mt-1'>7 days free trial, no credit-card or commitment, give us a try!</p>
                        </div>
                    </div>
                </div>
            </div>
            <div className='container col-xxl-8 '>
                <div className="row g-4 mt-5 mb-3 pt-5 pb-0 row-cols-1 row-cols-lg-2">
                    <div className="feature col">
                        <h2>Unlimited Calendars</h2>
                        <p className='lead'>No limit on the number of accounts and calendars you want to sync together. Gotta catch them all!</p>
                    </div>
                    <div className="feature col">
                        <h2>Synchronized in seconds</h2>
                        <p className='lead'>When an event is created or modified, it is updated on all calendars in seconds.</p>
                    </div>
                </div>
                <div className="row g-4 mt-3 mb-5 pt-3 pb-5 row-cols-1 row-cols-lg-2">
                    <div className="feature col">
                        <h2>Privacy first</h2>
                        <p className='lead'>Information about events is not synchronized between calendars - instead, a blocker event is created in order to protect your privacy.</p>
                    </div>
                    <div className="feature col">
                        <h2>Ready to go in 30 Seconds</h2>
                        <p className='lead'>You can have all your calendars synchronized in less than a minute. Don't believe us? Go ahead and get started right now!</p>
                    </div>
                </div>
            </div>
            <div className='hero py-5'>
                {paddle &&
                    <PaddlePricing paddle={paddle} isHome={true} />
                }
            </div>
            <div className='col-lg-7 col-md-8 col-11 container content card mt-4 pt-4 pb-2 mx-auto'>
                <a className='block-link' href={`${PUBLIC_URL}/blog/sync-multiple-google-calendars`}>
                    <p className='text-muted small p-0 m-0'>Blog</p>
                    <h2>How to Synchronize Google Calendars together</h2>
                    <p className='text-muted'>
                        If you're looking for how to sync multiple Google Calendars together, look no further.
                        This brief article will explain all there is to know.
                    </p>
                </a>
            </div>
            <div className='col-lg-7 col-md-8 col-11 container content card mt-4 pt-4 pb-2 mx-auto'>
                <a className='block-link' href={`${PUBLIC_URL}/blog/avoid-calendly-conflicts`}>
                    <p className='text-muted small p-0 m-0'>Blog</p>
                    <h2>Avoid Calendly conflicts</h2>
                    <p className='text-muted'>
                    Calendly conflicts can be terrible, so how can you avoid them? We discuss how Calensync helps
                    you solve this issue in two minutes!
                    </p>
                </a>
            </div>
        </Layout>
    );
};

export default Home;