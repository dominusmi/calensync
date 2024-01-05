import React from 'react';
import Layout from '../../components/Layout';
import { Helmet } from 'react-helmet';
import { PUBLIC_URL } from '../../utils/const';
import { useTranslation } from 'react-i18next';


const HowToSynchronizeCalendars: React.FC = () => {
  const { t } = useTranslation(['blog']);
  const ts = (s: string) => t(`sync_google_calendars_into_one.${s}`)
  return (
    <Layout verifySession={false}>
      <Helmet>
        <meta charSet="utf-8" />
        <title>{ts("title")}</title>
        <link rel="canonical" href={`https://calensync.live${PUBLIC_URL}/blog/sync-all-google-calendars-into-one`} />
        <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/en/blog/sync-all-google-calendars-into-one`} hrefLang="en" />
        <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/fr/blog/sync-all-google-calendars-into-one`} hrefLang="fr" />
        <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/it/blog/sync-all-google-calendars-into-one`} hrefLang="it" />
        <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/blog/sync-all-google-calendars-into-one`} hrefLang="x-default" />
        <meta name="description" content={ts("meta.description")} />
        <meta name="og:title" content={ts("meta.og_title")} />
        <meta name="og:url" content={`https://calensync.live${PUBLIC_URL}/blog/sync-all-google-calendars-into-one`} />
        <meta name="og:description" content={ts("meta.description")} />
      </Helmet>
      <div className="container mt-4 d-flex m-auto d-flex justify-content-center">
        <article className='col-lg-8 col-sm-11 col-12'>
          <header className="mb-4 mt-4">
            <h1 className="fw-bolder mb-1">{ts("title")}</h1>
            <div className="text-muted fst-italic mb-2">{ts("date")}</div>
          </header>
          <section className="mb-5">
            <p className="fs-5 mb-4">
              {ts("s1_1")}
            </p>
            <p className="fs-5 mb-4">
            {ts("s1_2")}
            </p>
            <p className="fs-5 mb-4">
            {ts("s1_3")}
            </p>
            <div className='centered'>
              <button type="button" className="btn btn-primary btn-lg px-4 me-md-2" onClick={() => window.location.href = "/login"}>{ts("cta")}</button>
            </div>
            <h2 className="mt-5 pt-3">
            {ts("h2")}
            </h2>
            <p className="fs-5 mb-4">
            {ts("s2_1")}
            </p>
            <img className='container my-2' src="/assets/blog/no-accounts.png" alt='Screenshot of dashboard with no accounts connected'></img>
            <h2 className="mt-5 pt-3">
            {ts("h3")}
            </h2>
            <p className="fs-5 mb-4">
            {ts("s3_1")}
            </p>
            <img className='container my-2' src="/assets/blog/google-permissions.png" alt='Google permissions screen'></img>
            <p className="fs-5 mb-4">
            {ts("s3_2")}
            </p>
            <img className='container my-2' src="/assets/blog/first-account.png" alt='Screenshot of dashboard with one account connected'></img>

            <p className="fs-5 mb-4">
            {ts("s3_3")}
            </p>

            <img className='container my-2' src="/assets/blog/all-accounts.png" alt='Screenshot of dashboard with all accounts connected'></img>
            <h2 className="mt-5 pt-3">
            {ts("h4")}
            </h2>
            <p className="fs-5 mb-4">
            {ts("s4_1")}
            </p>
            <img className='container my-2' src="/assets/blog/first-rule-draft.png" alt='Screenshot of dashboard with all accounts connected'></img>
            <p className="fs-5 mb-4">
            {ts("s4_2")}
            </p>
            <img className='container my-2' src="/assets/blog/second-rule-draft.png" alt='Screenshot of dashboard with all accounts connected'></img>
            <p className="fs-5 mb-4">
            {ts("s4_3")}
            </p>
            <h2 className="mt-5 pt-3">
            {ts("h5")}
            </h2>
            <p className="fs-5 mb-4">
            {ts("s5_1")}
            </p>
            <img className='container my-2' src="/assets/blog/third-rule-draft.png" alt='Screenshot of dashboard with all accounts connected'></img>
            <p className="fs-5 mb-4">
            {ts("s5_2")}
            </p>
            <img className='container my-2' src="/assets/blog/all-done.png" alt='Screenshot of dashboard with all accounts connected'></img>
            <div className='centered'>
              <button type="button" className="btn btn-primary btn-lg px-4 me-md-2" onClick={() => window.location.href = "/login"}>{ts("cta")}</button>
            </div>
          </section>
        </article>
      </div>
    </Layout>
  );
};

export default HowToSynchronizeCalendars;