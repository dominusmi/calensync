import React, { useEffect } from 'react';
import { Helmet } from 'react-helmet';
import { useTranslation } from 'react-i18next';
import Layout from '../components/Layout';
import { PUBLIC_URL } from '../utils/const';
import { BlogPage } from 'reactyll';
import MarkDown from 'react-markdown'
import rehypeRaw from 'rehype-raw';

export interface ExtraProperties {
    date: string
    headline: string
}

const content: BlogPage<ExtraProperties> = JSON.parse(atob(`%REPLACE%`));


const HowToSynchronizeCalendars: React.FC = () => {
    const { t } = useTranslation(['blog']);
    const ts = (s: string) => t(`sync_google_calendars_into_one.${s}`)

    useEffect(() => {
        const handleButtonClick = (event: any) => {
            // Check if the clicked element has the specified class name
            if (event.target.classList.contains('cta')) {
                window.location.href = "/dashboard"
            }
        };

        const parentElement = document.getElementById('blog-wrapper');
        if (parentElement) {
            document.addEventListener('click', handleButtonClick);
        }

        return () => {
            if (parentElement) {
                parentElement.removeEventListener('click', handleButtonClick);
            }
        };
    }, []);

    return (
        <Layout verifySession={false}>
            <Helmet>
                <meta charSet="utf-8" />
                <title>{ts("title")}</title>
                <link rel="canonical" href={`https://calensync.live${PUBLIC_URL}/${content.properties.language}${content.properties.url}`} />
                {content.languages.map(([language, url]) => (
                    <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/${language}${url}`} hrefLang={language} />
                ))}
                <meta name="description" content={ts("meta.description")} />
                <meta name="og:title" content={ts("meta.og_title")} />
                <meta name="og:url" content={`https://calensync.live${PUBLIC_URL}/blog/sync-all-google-calendars-into-one`} />
                <meta name="og:description" content={ts("meta.description")} />
            </Helmet>
            <div className="container mt-4 d-flex m-auto d-flex justify-content-center" id="blog-wrapper">
                <article className='col-lg-8 col-sm-11 col-12'>
                    <header className="mb-4 mt-4">
                        <h1 className="fw-bolder mb-1">{content.properties.title}</h1>
                        <div className="text-muted fst-italic mb-2">{content.properties.date}</div>
                    </header>

                    <section className="mb-5">
                        <MarkDown
                            rehypePlugins={[rehypeRaw]}
                            children={content.markdown}
                            components={{
                                h1(props) {
                                    const { children, className, node, ...rest } = props
                                    return <h1 className='test'>{children}</h1>
                                },
                                p(props) {
                                    const { children, className, node, ...rest } = props
                                    return <p className="fs-5 mb-4">
                                        {children}
                                    </p>
                                },
                                strong(props) {
                                    const { children, className, node, ...rest } = props
                                    return <b className='bold'>{children}</b>
                                },
                                h2(props) {
                                    const { children, className, node, ...rest } = props
                                    return <h2 className="mt-5 pt-3">{children}</h2>
                                },
                                img(props) {
                                    const { children, className, node, src, alt, ...rest } = props
                                    return <img className='container my-2' src={src} alt={alt}></img>
                                }
                            }}
                        />
                    </section>
                </article>
            </div>
        </Layout>
    );
};

export default HowToSynchronizeCalendars;