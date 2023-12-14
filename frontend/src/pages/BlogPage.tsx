import React from 'react';
import Layout from '../components/Layout';
import { Helmet } from 'react-helmet';
import { PUBLIC_URL } from '../utils/const';


const BlogPage: React.FC = () => {
  return (
    <Layout verify_session={false}>
            <Helmet>
                <meta charSet="utf-8" />
                <title>How to sync Google Calendars</title>
                <link rel="canonical" href={`https://calensync.live${PUBLIC_URL}/blog/sync-multiple-google-calendars`} />
                <meta name="description" content="In this post, we describe the two ways to synchronize Google Calendars together" />
                <meta name="og:title" content="How to sync Google Calendars" />
                <meta name="og:url" content="{`https://calensync.live${PUBLIC_URL}/blog/sync-multiple-google-calendars`}" />
                <meta name="og:description" content="In this post, we describe the two ways to synchronize Google Calendars together" />
            </Helmet>
      <div className="container mt-4 d-flex m-auto d-flex justify-content-center">
        <article className='col-7'>
          <header className="mb-4 mt-4">
            <h1 className="fw-bolder mb-1">How to sync multiple Google Calendars</h1>
            <div className="text-muted fst-italic mb-2">December 2023</div>
          </header>
          {/* <figure className="mb-4"><img className="img-fluid rounded" src="https://dummyimage.com/900x400/ced4da/6c757d.jpg" alt="..." /></figure> */}
          <section className="mb-5">
            <p className="fs-5 mb-4">
              If you're looking for how to sync multiple Google Calendars together, look no further.
              This brief article will explain all there is to know.
            </p>
            <h2 className="fw-bolder mb-4 mt-5">Syncing manually</h2>
            <p className="fs-5 mb-4">
              Syncing your calendars manually involves multiple steps.
            </p>
            <ol>
              <li>From your Google Calendar page (on desktop), click the three button icons next to the calendar</li>
              <li>Go to the Import/Export tab</li>
              <li>Go to Export</li>
              <li>Export the calendars you wish to synchronize</li>
              <li>This will trigger a file download</li>
              <li>Go to your second calendar</li>
              <li>Using the same menu, this time go to Import</li>
              <li>Upload the downloaded file</li>
            </ol>
            <p className="fs-5 mb-4">
              You have now succesfully synced your first calendar to the second, and you will have to repeat this in every
              syncing direction.
            </p>
            <h3 className="fw-bolder mt-3">Pros of manual syncing</h3>
            <ul>
              <li>It's free</li>
            </ul>
            <h3 className="fw-bolder mt-3">Cons of manual syncing</h3>
            <ul>
              <li>No privacy control: your events will appear as they are</li>
              <li>Syncing is slow, usually daily</li>
              <li>Setup is long, especially for multiple calendars</li>
            </ul>
            <h2 className="fw-bolder mb-4 mt-5">Using Calensync</h2>
            <p className="fs-5 mb-4">
              That's precisely why we created Calensync: to provide a better service at a very fair price.
              Here's how the setup works:
            </p>
            <ol>
              <li><a href="/login">Login</a> using any of your Google Accounts</li>
              <li>Click "Connect Google Calendars" and connect each account</li>
              <li>Switch on synchronization of the calendars as needed</li>
            </ol>
            <h3 className="fw-bolder mt-3">Pros of Calensync</h3>
            <ul>
              <li>Instant synchronization</li>
              <li>Privacy protected</li>
              <li>Setup in 2 minutes</li>
            </ul>
            <h3 className="fw-bolder mt-3">Cons of manual syncing</h3>
            <ul>
              <li>It's not free (but it's affordable)</li>
            </ul>
          </section>
        </article>
      </div>
    </Layout>
  );
};

export default BlogPage;