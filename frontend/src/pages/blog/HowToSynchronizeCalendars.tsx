import React from 'react';
import Layout from '../../components/Layout';
import { Helmet } from 'react-helmet';
import { PUBLIC_URL } from '../../utils/const';
import { useTranslation } from 'react-i18next';


const HowToSynchronizeCalendars: React.FC = () => {
  const { t } = useTranslation(['blog']);
  const ts = (s: string) => t(`sync_google_calendars.${s}`)
  return (
    <Layout verifySession={false}>
            <Helmet>
                <meta charSet="utf-8" />
                <title>{ts("title")}</title>
                <link rel="canonical" href={`https://calensync.live${PUBLIC_URL}/blog/sync-multiple-google-calendars`} />
                <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/en/blog/sync-multiple-google-calendars`} hrefLang="en"/>
                <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/fr/blog/sync-multiple-google-calendars`} hrefLang="fr"/>
                <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/it/blog/sync-multiple-google-calendars`} hrefLang="it"/>
                <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/blog/sync-multiple-google-calendars`} hrefLang="x-default" />
                <meta name="description" content={ts("meta.description")} />
                <meta name="og:title" content={ts("meta.og_title")} />
                <meta name="og:url" content={`https://calensync.live${PUBLIC_URL}/blog/sync-multiple-google-calendars`} />
                <meta name="og:description" content={ts("meta.description")} />
            </Helmet>
      <div className="container mt-4 d-flex m-auto d-flex justify-content-center">
        <article className='col-lg-8 col-sm-11 col-12'>
          <header className="mb-4 mt-4">
            <h1 className="fw-bolder mb-1">{ts("title")}</h1>
            <div className="text-muted fst-italic mb-2">{ts("date")}</div>
          </header>
          {/* <figure className="mb-4"><img className="img-fluid rounded" src="https://dummyimage.com/900x400/ced4da/6c757d.jpg" alt="..." /></figure> */}
          <section className="mb-5">
            <p className="fs-5 mb-4">
            {ts("headline")}
            </p>
            <h2 className="fw-bolder mb-4 mt-5">{ts("manually.title")}</h2>
            <p className="fs-5 mb-4">
              {ts("manually.headline")}
            </p>
            <ol>
              <li>{ts("manually.steps.1")}</li>
              <li>{ts("manually.steps.2")}</li>
              <li>{ts("manually.steps.3")}</li>
              <li>{ts("manually.steps.4")}</li>
              <li>{ts("manually.steps.5")}</li>
              <li>{ts("manually.steps.6")}</li>
              <li>{ts("manually.steps.7")}</li>
              <li>{ts("manually.steps.8")}</li>
            </ol>
            <p className="fs-5 mb-4">
              {ts("manually.end")}
            </p>
            <h3 className="fw-bolder mt-3">{ts("manually.pros.title")}</h3>
            <ul>
              <li>{ts("manually.pros.free")}</li>
            </ul>
            <h3 className="fw-bolder mt-3">{ts("manually.cons.title")}</h3>
            <ul>
              <li>{ts("manually.cons.privacy")}</li>
              <li>{ts("manually.cons.slow")}</li>
              <li>{ts("manually.cons.long")}</li>
            </ul>
            <h2 className="fw-bolder mb-4 mt-5">{ts("calensync.title")}</h2>
            <p className="fs-5 mb-4">
              {ts("calensync.headline")}
            </p>
            <ol>
              <li><a href="/dashboard">{ts("calensync.steps.1_span")}</a> {ts("calensync.steps.1_text")}</li>
              <li>{ts("calensync.steps.2")}</li>
              <li>{ts("calensync.steps.3")}</li>
            </ol>
            <h3 className="fw-bolder mt-3">{ts("calensync.pros.title")}</h3>
            <ul>
              <li>{ts("calensync.pros.fast")}</li>
              <li>{ts("calensync.pros.privacy")}</li>
              <li>{ts("calensync.pros.onboarding")}</li>
            </ul>
            <h3 className="fw-bolder mt-3">{ts("calensync.cons.title")}</h3>
            <ul>
              <li>{ts("calensync.cons.free")}</li>
            </ul>
          </section>
          <div className='d-flex justify-content-center'>
            <div className='row'>
            <button className='btn btn-primary centered' onClick={() => window.location.href=`${PUBLIC_URL}/login`}>{ts("cta")}</button>
            </div>
          </div>
        </article>
      </div>
    </Layout>
  );
};

export default HowToSynchronizeCalendars;