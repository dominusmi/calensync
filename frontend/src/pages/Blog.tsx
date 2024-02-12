import React, { useEffect, useState } from 'react';
import { ENV, PUBLIC_URL } from '../utils/const';
import Layout from '../components/Layout';
import { Helmet } from "react-helmet";
import { useTranslation } from 'react-i18next';
import { BlogProperties, getBlogForLanguage } from 'reactyll';
import { blogs } from '../_blog/routes';
import { ExtraProperties } from '../components/BlogTemplate';

const Blog: React.FC = () => {
    const { t, i18n } = useTranslation();

    return (
        <Layout verifySession={false} onlyRequired={false}>
            <Helmet>
                <meta charSet="utf-8" />
                <title>{t('blogs.title')}</title>
                <link rel="canonical" href={`https://calensync.live${window.location.pathname}`} />
                <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/fr`} hrefLang="fr" />
                <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/en`} hrefLang="en" />
                <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/it`} hrefLang="it" />
                <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}`} hrefLang="x-default" />
                <meta name="description" content={t("blogs.meta.description")} />
                <meta name="og:title" content={t("blogs.meta.og_title")} />
                <meta name="og:url" content={`https://calensync.live${PUBLIC_URL}`} />
                <meta name="og:description" content={t("blogs.meta.description")} />
            </Helmet>
            <div className='container col-xxl-8 gy-4'>
                <div className="row g-lg-4 mt-4 mt-lg-3 mb-lg-3 pt-lg-3 pb-lg-2 row-cols-1 row-cols-lg-2">
                    <div className="feature col py-2">
                        <h1>Blog </h1>
                        <p className='lead'>What we've talked about recently..</p>
                    </div>
                </div>
            </div>
            <div className='hero py-5'>
                {Object.values(blogs).map((blogLang) => {
                    console.log(blogLang)
                    return [getBlogForLanguage(blogLang, i18n.language, "en") as BlogProperties & ExtraProperties].map((blog) => (
                        <div  key={blog.url} className='col-xxl-8 col-12 px-4 card mt-4 pt-4 pb-2 mx-auto'>
                            <a className='block-link' href={`${PUBLIC_URL}${blog.url}`}>
                                <h2>{blog.title}</h2>
                                <p className='text-muted'>
                                    {blog.headline}
                                </p>
                            </a>
                        </div>
                    ))
                }
                )
                }
            </div>
        </Layout >
    );
};

export default Blog;