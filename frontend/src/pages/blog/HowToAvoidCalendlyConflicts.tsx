import React from 'react';
import Layout from '../../components/Layout';
import { Helmet } from 'react-helmet';
import { PUBLIC_URL } from '../../utils/const';
import { useTranslation } from 'react-i18next';


const HowToAvoidCalendlyConflicts: React.FC = () => {
  const { t } = useTranslation(['blog']);
  const ts = (s: string) => t(`avoid_calendly_conflicts.${s}`)
  
  return (
    <Layout verifySession={false}>
            <Helmet>
                <meta charSet="utf-8" />
                <title>{ts("title")}</title>
                <meta name="description" content={ts("meta.description")} />
                <meta name="og:title" content={ts("meta.title")} />
                <meta name="og:url" content={`https://calensync.live${PUBLIC_URL}/blog/avoid-calendly-conflicts`} />
                <meta name="og:description" content={ts("meta.description")} />
                <link rel="canonical" href={`https://calensync.live${PUBLIC_URL}`} />
                <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/fr/blog/avoid-calendly-conflicts`} hrefLang="fr"/>
                <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/en/blog/avoid-calendly-conflicts`} hrefLang="en"/>
                <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}/it/blog/avoid-calendly-conflicts`} hrefLang="it"/>                <link rel="alternate" href={`https://calensync.live${PUBLIC_URL}`} hrefLang="x-default" />
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
              {ts("intro")}
            </p>
            <h2 className="fw-bolder mb-4 mt-5">{ts("s1.title")}</h2>
            <p className="fs-5 mb-4">
              {ts("s1.content")}
            </p>
            <p className="fs-5 mb-4">
              {ts("s1.link")} <a href="/blog/sync-multiple-google-calendars">{ts("s1.link-span")}</a> {ts("s1.link-post")}
            </p>
            <h2 className="fw-bolder mb-4 mt-5">{ts("s2.title")}</h2>
            <p className="fs-5 mb-4">
              {ts("s2.content")}
            </p>
            <h2 className="fw-bolder mb-4 mt-5">{ts("s3.title")}</h2>
            <p className="fs-5 mb-4">
              {ts("s3.content")}
            </p>
            <h2 className="fw-bolder mb-4 mt-5">{ts("calensync.title")}</h2>
            <p className="fs-5 mb-4">
              {ts("calensync.content")}
            </p>
            <ol>
              <li>{ts("calensync.steps.1")} <a href="/dashboard">dashboard</a></li>
              <li>{ts("calensync.steps.2")}</li>
              <li>{ts("calensync.steps.3")}</li>
            </ol>
            <p className="fs-5 mb-4">
              {ts("calensync.conclusion")}
            </p>
          </section>
        </article>
      </div>
    </Layout>
  );
};

export default HowToAvoidCalendlyConflicts;