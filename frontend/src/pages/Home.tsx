import React, { useState } from 'react';
import Footer from '../components/Footer';
import Navbar from '../components/Navbar';
import { PUBLIC_URL } from '../utils/const';
import Layout from '../components/Layout';

const Home: React.FC = () => {
    const [isChecked, setIsChecked] = useState(false);
    const [cost, setCost] = useState(4);

    const signup = () => {
        window.location.href = `${PUBLIC_URL}/login`;
    }

    const changePricingSwitch = () => {
        if (isChecked) {
            setCost(4);
        } else {
            setCost(25);
        }
        setIsChecked(!isChecked);
    }

    return (
        <Layout verify_session={false}>
            <div className='hero'>
                <div className="container col-xxl-8 py-5">
                    <div className="row flex-lg-row-reverse align-items-center g-5 py-5">
                        <div className="col-10 col-sm-8 col-lg-6">
                            <img src="hero.gif" className="d-block mx-lg-auto img-fluid hero-gif" alt="Bootstrap Themes" width="700" height="500" loading="lazy" />
                        </div>
                        <div className="col-lg-6">
                            <h1 className="display-5 fw-bold lh-1 mb-3">No more calendar event conflicts.</h1>
                            <p className="lead">
                                Save yourself the pain of rescheduling.
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
                <div className='container centered'>
                    <div className='row mb-4'>
                        <div className="feature col">
                            <h1>Pricing</h1>
                            <p className='lead'>Simple pricing for a simple product. 7 days free trial, no commitment, no credit card. Then..</p>
                        </div>
                    </div>
                    <div className="d-flex justify-content-center">
                        <h3 className="mb-0 mx-4">Monthly</h3>
                        <div className="pricing-switch form-check form-switch mx-4">
                            <input className="form-check-input" type="checkbox" role="switch" id="flexSwitchCheckDefault" checked={isChecked} onChange={changePricingSwitch} />
                        </div>
                        <h3 className="mb-0 ml-4">Yearly</h3><p className='text-muted mx-1 align-middle'>48% Off!</p>
                    </div>
                    <div className='row mt-3'>
                        <h2 className='fw-bold display-6 mb-0'>
                            {cost}$
                        </h2>
                        <p className='text-muted small mb-4'>*Excluding VAT</p>
                        <div className="d-grid gap-2 d-md-flex justify-content-md-center mt-1">
                            <button type="button" className="btn btn-primary btn-lg px-4 me-md-2" onClick={signup}>Signup</button>
                        </div>
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default Home;