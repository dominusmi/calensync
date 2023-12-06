import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { toast } from 'react-toastify';
import API, { PUBLIC_URL } from '../utils/const';
import { get_session_id } from '../utils/session';
import Toast, { toast_error } from '../components/Toast';

const Tos: React.FC = () => {
    const [isChecked, setIsChecked] = useState(false);

    const handleCheckboxChange = () => {
        setIsChecked(!isChecked);
    };

    const isConnected = get_session_id() !== null;

    const acceptTos = async () => {
        if (!isChecked) {
            console.log("Must be checked");
            toast_error("You must accept the Terms and Conditions");
            return
        }
        try {
            const response = await fetch(
                `${API}/tos`,
                {
                    method: 'POST',
                    headers: {
                        Authorization: get_session_id()!
                    }
                }
            );
            if(response.ok){
                window.location.href = `${PUBLIC_URL}/dashboard`;
            }
            else {
                try {
                    let error = await response.json();
                    toast_error(error.detail || "Unknown error")
                } catch(e) {
                    toast_error(`Unknown error, status ${response.status}`)
                }
            }
        }
        catch {
            console.log("Error")
        }

    }

    return (
        <div className="App bg-light content">
            <div className="container-sm card my-4 p-4 shadow-sm rounded border-0">
                <div className="centered row my-4">
                    <h1>Terms and Conditions</h1>
                    <h4>Calensync</h4>
                </div>
                <div className="p-4">
                    <p>
                        Calensync is a service provided by <b>Opali Analytics OÜ</b>. In this document, when we refer to the “company”, “we”, “our”, “us”, “service” or “services”, we
                        mean <b>Opali Analytics OÜ</b>. <br /><br />
                        We reserve the right to modify these Terms of Service in the future. Significant changes to our
                        policies will be announced by email to all signed-up customers.
                        By utilising our service, either now or in the future, you consent to the most recent Terms of
                        Service. This applies to all our current and future products, and all features that we may add to
                        our service over time.
                    </p>
                    <p>
                        There may be instances where we do not exercise or enforce a right or
                        provision within the Terms of Service; this does not constitute a waiver of that right or provision.
                        Please be aware that these terms include a limitation of our liability.
                        If you disagree with these Terms of Service, please refrain from using this service. Breaching any
                        of the terms below may lead to the termination of your account.

                    </p>
                </div>
                <div className="row m-2">
                    <h2>Account terms</h2>
                </div>
                <div className="p-4">
                    <ul>
                        <li>
                            You must ensure the security of your account. We will not be held
                            responsible for any loss or damage resulting from your failure to adhere to this security
                            obligation.
                        </li>
                        <li>
                            You are accountable for all activities that occur under your account (including activities by
                            others who have logins under your account).
                        </li>
                        <li>
                            Our service must not be used for any illegal activities or to breach any laws in your
                            jurisdiction.
                        </li>
                        <li>
                            You must use a valid Google account to signup and login
                        </li>
                        <li>
                            Only humans may register accounts. Accounts created by bots or other automated methods are not
                            allowed.
                        </li>
                    </ul>
                </div>
                <div className="row m-2">
                    <h2>Payment, refunds, upgrading and downgrading terms
                    </h2>
                </div>
                <div className="p-4">
                    <ul>
                        <li>Payments are processed by Paddle, who also handle customer service inquiries and returns. All
                            fees include applicable taxes, collected and remitted by Paddle. Our order process is conducted
                            by our
                            online reseller Paddle.com. Paddle.com is the Merchant of Record for all our orders.
                            Paddle provides all customer service inquiries and handles returns</li>
                        <li>Automatic billing is also done through Paddle, which allows several payment methods.</li>
                        <li>Upgrading or downgrading your paid plan can be done at any time within your account settings.
                            Downgrading may result in loss of features or capacity, for which Opali Analytics is not liable.
                        </li>
                        <li>You have 14 days from the beginning of the subscription to get a full-refund.
                            After that, refund reviews will be handled case-by-case.
                            We guarantee if the request was made in the 14-days grace period, will honour it, although it could
                            take several working days to be fulfilled.
                            Please contact support@opali.xyz. We do our best to keep customers happy and correct any errors
                            that may have occured.
                        </li>
                        <li>Fees are non-refundable. </li>
                    </ul>
                </div>
                <div className="row m-2">
                    <h2>Cancellation and termination
                    </h2>
                </div>
                <div className="p-4">

                    <ul>
                        <li>To cancel an account, please contact us at support@opali.xyz . This email address is also provided in
                            your dashboard.</li>
                        <li>Cancellation before the end of the current paid period will take effect at the end of the
                            billing cycle, with no further charges. All stats will become inaccessible and will be
                            permanently deleted from backups within 60 days.</li>
                        <li>You may delete your account and all site stats at any time.</li>
                        <li>We reserve the right to suspend or terminate your account for any reason, leading to
                            deactivation or deletion of your account and access to your stats. </li>
                        <li>We may refuse service to anyone for any reason.</li>
                        <li>Abuse of any service customer, company employee, or officer may lead to immediate account
                            termination. </li>
                        <li>
                            The freemium plan is offered with no guarantees.
                            Unlike paid-plans, we reserve the right to modify and/or terminate it with no notice.
                            If you were affected, we will do our best to notify you by email.
                        </li>
                    </ul>
                </div>
                <div className="row m-2">
                    <h2>Modifications to the service and prices
                    </h2>
                </div>
                <div className="p-4">
                    <ul>
                        <li>We reserve the right to modify or discontinue any part of the service, temporarily or
                            permanently, with or without notice.</li>
                        <li>Pricing changes may occur. If prices change for existing customers, at least 30 days notice will
                            be given via email, blog, or affected services.</li>
                        <li>Opali Analytics is not liable for any modification, price change, suspension, or discontinuance
                            of the service. </li>
                    </ul>
                </div>
                <div className="row m-2">
                    <h2>Copyright and Intellectual Property
                    </h2>
                </div>
                <div className="p-4">

                    <p>
                        Except in case of explicit consent, you do not have the right to:
                    </p>
                    <ul>
                        <li>modify or copy the materials;</li>
                        <li>use the materials for any commercial purpose or for any public display;</li>
                        <li>attempt to reverse engineer any software contained on Opali Website;</li>
                        <li>remove any copyright or other proprietary notations from the materials; or</li>
                        <li>transfer the materials to another person or "mirror" the materials on any other server.</li>
                    </ul>
                    <p>
                        Furthermore:
                    </p>
                    <ul>
                        <li>You are solely responsible for content and material submitted, published, transmitted, emailed,
                            or displayed through the service.</li>
                        <li>We claim no intellectual property rights over your material.</li>
                        <li>Feedback, suggestions, and ideas about the service may be used by us without payment or
                            attribution to you.</li>
                    </ul>
                </div>
                <div className="row m-2">
                    <h2>Privacy and security of your data
                    </h2>
                </div>
                <div className="p-4">

                    <ul>
                        <li>Please review the privacy policy, which contains more detailed information on the topic.</li>
                        <li>We employ various measures to protect and secure your data, including backups, redundancies, and
                            encryption.</li>
                        <li>You retain all rights, title, and interest in your website data. We do not collect or store
                            personally identifiable information or use behavioural insights for advertising.</li>
                        <li>You agree to comply with all applicable laws, including privacy and data protection regulations.
                        </li>
                        <li>Sensitive information must not be sent to the company where unauthorised disclosure could cause
                            significant harm. </li>
                    </ul>
                </div>
                <div className="row m-2">
                    <h2>Service offering
                    </h2>
                </div>
                <div className="p-4">

                    <ul>
                        <li>
                            On the platform, you are able to connect multiple Google accounts, and choose which calendars
                            to sync together. We make use of Google API in order to synchronize events on your accounts.
                        </li>
                        <li>
                            We carefully test our updates to make sure we provide the best possible service.
                            However, we cannot guarantee a bug-free software. We make sure to fix bugs as fast as possible,
                            especially those regarding security and privacy.
                        </li>
                    </ul>
                </div>
                <div className="row m-2">
                    <h2>General conditions</h2>
                </div>
                <div className="p-4">

                    <ul>
                        <li>Your use of Opali Analytics is at your sole risk, provided on an “as is” and “as available”
                            basis.
                        </li>
                        <li>We make no guarantees that our services will meet your specific requirements or expectations.
                        </li>
                        <li>Technical support is provided via email. We do our best to respond in timely manner, but we do not
                            guarantee a response time. The address is support@opali.xyz</li>
                        <li>We may access your data for support requests and to maintain and safeguard Opali Analytics.</li>
                        <li>Third-party vendors are used to provide necessary hardware, storage, payment processing, and
                            related
                            technology. </li>
                    </ul>
                </div>
                <div className="row m-2">

                    <h2>Liability</h2>
                </div>
                <div className="p-4">

                    <ul>

                        <li>Opali Analytics OÜ shall not be liable for any direct, indirect, incidental, lost profits,
                            special, consequential, punitive, or exemplary damages, under any theory of liability.</li>
                        <li>Your choice to use our services is a bet on us, and if it does not work out, the responsibility
                            is yours, not ours.</li>
                        <li>This agreement is governed by the laws of Estonia, and the courts of Estonia have exclusive
                            jurisdiction.</li>
                        <li>For questions about the Terms of Service, please contact us at support@opali.xyz</li>
                    </ul>
                </div>
                <div className="row m-2">

                    <h2>Your Privacy</h2>
                </div>
                <div className="p-4">

                    <p>The Privacy Policy can be found at <a
                        href="https://calensync.live/privacy">calensync.live/privacy</a>. By accepting these terms and conditions,
                        you also accept the privacy policy. </p>
                </div>
                { isConnected && 
                <div id="section-form">
                    <hr className="border-2 my-4" />
                    <div className="form-check my-2">
                        <input type="checkbox" className="form-check-input" checked={isChecked} onChange={handleCheckboxChange} />
                        <label className="form-check-label">I have read and I accept the Terms and
                            Conditions described on this page</label>
                    </div>
                    <button className="btn btn-primary" onClick={acceptTos}>Submit</button>
                </div>
                }
            </div>
            <Toast />
            <Footer />
        </div>
    );
};

export default Tos;
