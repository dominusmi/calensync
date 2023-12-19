import React, { useEffect, useState } from 'react';
import { ENV, PADDLE_CLIENT_TOKEN, PUBLIC_URL } from '../utils/const';
import Layout from '../components/Layout';
import { PaddlePricing } from '../components/PaddlePricing';
import { Paddle, initializePaddle } from '@paddle/paddle-js';
import { Helmet } from "react-helmet";
import { useTranslation } from 'react-i18next';

const Home: React.FC = () => {
    const { t } = useTranslation();
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
                <title>{t('title_sync_calendars')}</title>
                <link rel="canonical" href={`https://calensync.live${PUBLIC_URL}`} />
                <meta name="description" content={t("home.meta.description")} />
                <meta name="og:title" content={t("home.meta.og:title")} />
                <meta name="og:url" content={`https://calensync.live${PUBLIC_URL}`} />
                <meta name="og:description" content={t("home.meta.description")} />
            </Helmet>
            <div className='hero'>
                <div className="container col-xxl-8 py-5">
                    <div className="row flex-lg-row-reverse align-items-center g-4 py-5 justify-content-center">
                        <div className="col-10 col-sm-8 col-lg-6">
                            <img src="hero.gif" className="d-block mx-lg-auto img-fluid hero-gif" alt="Bootstrap Themes" width="700" height="500" loading="lazy" />
                        </div>
                        <div className="col-lg-6">
                            <h1 className="display-5 fw-bold lh-1 mb-3">{t("home.hero.title")}</h1>
                            <p className="lead">
                                {t("home.hero.heading")}
                            </p>
                            <div className="d-grid gap-2 d-md-flex justify-content-md-start mt-4">
                                <button type="button" className="btn btn-primary btn-lg px-4 me-md-2" onClick={signup}>{t("home.hero.cta")}</button>
                            </div>
                            <p className='mt-1 small'>{t("free_trial")}</p>
                        </div>
                    </div>
                </div>
            </div>
            <div className='container col-xxl-8 gy-4'>
                <div className="row g-lg-4 mt-4 mt-lg-3 mb-lg-3 pt-lg-3 pb-lg-2 row-cols-1 row-cols-lg-2">
                    <div className="feature col py-2">
                        <h2>{t("home.value.1_head")}</h2>
                        <p className='lead'>{t("home.value.1_content")}</p>
                    </div>
                    <div className="feature col py-2">
                        <h2>{t("home.value.2_head")}</h2>
                        <p className='lead'>{t("home.value.2_content")}</p>
                    </div>
                </div>
                <div className="row mt-0 mb-4 g-lg-4 mt-lg-3 mb-lg-2 pt-lg-3 pb-lg-5 row-cols-1 row-cols-lg-2">
                    <div className="feature col py-2">
                        <h2>{t("home.value.3_head")}</h2>
                        <p className='lead'>{t("home.value.3_content")}</p>
                    </div>
                    <div className="feature col py-2">
                        <h2>{t("home.value.4_head")}</h2>
                        <p className='lead'>{t("home.value.4_content")}</p>
                    </div>
                </div>
            </div>
            <div className='hero py-5'>
                {paddle &&
                    <PaddlePricing paddle={paddle} isHome={true} />
                }
            </div>
            <div className='container'>
                <div className='col-xxl-8 col-12 px-4 card mt-4 pt-4 pb-2 mx-auto'>
                    <a className='block-link' href={`${PUBLIC_URL}/blog/sync-multiple-google-calendars`}>
                        <p className='text-muted small p-0 m-0'>Blog</p>
                        <h2>{t("blog_list.sync_google_calendars.title")}</h2>
                        <p className='text-muted'>
                            {t("blog_list.sync_google_calendars.headline")}
                        </p>
                    </a>
                </div>
            </div>
            <div className='container'>
                <div className='col-xxl-8 col-12 px-4 card mt-4 pt-4 pb-2 mx-auto'>
                    <a className='block-link' href={`${PUBLIC_URL}/blog/avoid-calendly-conflicts`}>
                        <p className='text-muted small p-0 m-0'>Blog</p>
                        <h2>{t("blog_list.avoid_calendly_conflicts.title")}</h2>
                        <p className='text-muted'>
                            {t("blog_list.avoid_calendly_conflicts.headline")}
                        </p>
                    </a>
                </div>
            </div>
        </Layout >
    );
};

export default Home;