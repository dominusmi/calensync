import React from 'react';
import Layout from '../../components/Layout';
import { Helmet } from 'react-helmet';
import { PUBLIC_URL } from '../../utils/const';


const HowToAvoidCalendlyConflicts: React.FC = () => {
  return (
    <Layout verify_session={false}>
            <Helmet>
                <meta charSet="utf-8" />
                <title>Avoid Calendly Conflicts</title>
                <link rel="canonical" href={`https://calensync.live${PUBLIC_URL}/blog/sync-multiple-google-calendars`} />
                <meta name="description" content="Calendly conflicts can be terrible, so how can you avoid them?" />
                <meta name="og:title" content="Avoid Calendly Conflicts" />
                <meta name="og:url" content="{`https://calensync.live${PUBLIC_URL}/blog/sync-multiple-google-calendars`}" />
                <meta name="og:description" content="Calendly conflicts can be terrible, so how can you avoid them?" />
            </Helmet>
      <div className="container mt-4 d-flex m-auto d-flex justify-content-center">
      <article className='col-lg-8 col-sm-11 col-12'>
          <header className="mb-4 mt-4">
            <h1 className="fw-bolder mb-1">How to avoid Calendly conflicts</h1>
            <div className="text-muted fst-italic mb-2">December 2023</div>
          </header>
          {/* <figure className="mb-4"><img className="img-fluid rounded" src="https://dummyimage.com/900x400/ced4da/6c757d.jpg" alt="..." /></figure> */}
          <section className="mb-5">
            <p className="fs-5 mb-4">
              Automated event creation has been one of the simplest yet greatest inventions for productivity
              enhancement. However, in this day and age, it is common for people to have multiple calendars,
              including a mix of personal and professional, and it's never nice having to reschedule events
              because of a conflict between your medical appointment and a demo for a lead. So how do you
              avoid these conflicts?
            </p>
            <h2 className="fw-bolder mb-4 mt-5">Using .ics files</h2>
            <p className="fs-5 mb-4">
              Your calendar can be exported into a .ics file and then added to other calendars. This is a 
              cumbersome but entirely free way of doing it. Without going into more depth, some of the issues
              with it include syncing is quite delayed, and there's no privacy so your events are literally 
              copy pasted.
            </p>
            <p className="fs-5 mb-4">
              You can read more about it in <a href="/blog/sync-multiple-google-calendars">this post</a> we recently wrote.
            </p>
            <h2 className="fw-bolder mb-4 mt-5">Using Calensync</h2>
            <p className="fs-5 mb-4">
              This is precisely why we created Calensync: 
              That's precisely why we created Calensync: to provide a better service at a very fair price.
              With Calendly, you can synchronize all your Google Calendars in less than 2 minutes. The process is 
              simple:
            </p>
            <ol>
              <li>Login to the dashboard</li>
              <li>Connect as many Google Accounts as needed</li>
              <li>Pick which calendars to synchronize</li>
            </ol>
            <p className="fs-5 mb-4">
              Synchronization is near instantaneous. You will see "Blocker" events appearing in the synced calendars,
              so that you will avoid all Calendly conflicts in the future!
            </p>
          </section>
        </article>
      </div>
    </Layout>
  );
};

export default HowToAvoidCalendlyConflicts;