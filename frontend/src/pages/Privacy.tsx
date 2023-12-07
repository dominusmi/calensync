import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import API from '../utils/const';
import { get_session_id } from '../utils/session';

const Privacy: React.FC = () => {
    return (
        <div className="App bg-light content">
            <div className="container-sm card my-4 p-4 shadow-sm rounded border-0">
                <div className="centered row my-4">
                    <h1>Privacy Policy</h1>
                    <h4>Calensync</h4>
                    <h6>Service provided by Opali Analytics OÜ</h6>
                </div>
                <div className="row m-2">
                    <h2>For visitors on the website</h2>
                </div>
                <div className="p-4">
                    <ul>
                        <li>
                            Personal data isn't gathered.
                        </li>
                        <li>
                            Cookies or other information aren't stored within browsers.
                        </li>
                        <li>
                            No information is ever passed to, forwarded, or sold to third parties.
                        </li>
                        <li>
                            No information is extracted for analysis of personal behaviour or trends.
                        </li>
                    </ul>
                </div>
                <div className="row m-2">
                    <h2>For users of the app
                    </h2>
                </div>
                <div className="p-4">
                    <ul>
                        <li>
                            The email for the Google accounts you decide to connect is stored for necessary usage,
                            and is never shared with any third-party.
                        </li>
                        <li>A first party cookie is used in order to keep track of your logged in session.</li>
                        <li>Unused monthly events in the paid plan are forfeited at the end of the term.</li>
                        <li>Payment is facilitated by Paddle; as part of the payment, you may
                            be required to submit an email which they process for billing. See their privacy policy for information.
                        </li>
                    </ul>
                    We use three external providers.
‍                    <ul>
                        <li>Amazon Web Services, Inc. for the infrastructure. It is fully hosted in Sweden / Stockholm, eu-north-1, and allthe data is kept and processed in this region only</li>
                        <li>Paddle.com Market Ltd for the payment processing</li>
                        <li>Github.com for website hosting</li>
                    </ul>                   
                </div>
                <div className="row m-2">
                    <h2>Deletion of your data
                    </h2>
                </div>
                <div className="p-4">
                    If you do not use your account and want to delete your data, please send us 
                    an email at support@opali.xyz . We will handle the request as fast as possible.
                </div>
                <div className="row m-2">
                    <h2>Retention and Changes to This Policy
                    </h2>
                </div>
                <div className="p-4">
                    <ul>
                        <li>Your information will be retained as required by this policy, for legal obligations, resolving disputes, enforcing agreements, and protecting legal rights.</li>
                        <li>We may update this policy to comply with regulations and reflect new practices, with announcements on our email list.</li>
                        <li>For inquiries or concerns about this privacy policy or your data, contact us at privacy@opali.xyz </li>
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
            </div>
            <Footer />
        </div>
    );
};

export default Privacy;
