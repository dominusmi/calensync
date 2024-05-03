import React from 'react';
import { PUBLIC_URL } from '../utils/const';
import Layout from '../layouts/Layout';



const Privacy: React.FC = () => {
    return (
        <Layout>
        <div className="content">
            <div className="container card mt-4 p-4 shadow-sm rounded border-0">
                <div className="centered row my-4">
                    <h1>Google API Services Usage Disclosure</h1>
                    <h4>Calensync</h4>
                    <h6>Service provided by Opali Analytics OÜ</h6>
                </div>
                <div className="row mx-2">
                    <h2>Limited Use</h2>
                </div>
                <div className="row mx-2">
                    <h5 className='my-4'>Our service strictly complies with all conditions specified in the <span>
                        <a href="https://developers.google.com/terms/api-services-user-data-policy">
                            Google API Services User Data Policy
                        </a></span>
                        including the <span>
                            <a href="https://developers.google.com/terms/api-services-user-data-policy#additional_requirements_for_specific_api_scopes">
                                limited use policy of Google.
                            </a>
                        </span>
                        </h5>
                    <p>These include:</p>
                    <ul>
                        <li>
                            Do not allow humans to read the user's data unless you have obtained the user's 
                            affirmative agreement to view specific messages, files, or other data.
                        </li>
                        <li>
                            Do not use or transfer the data for serving ads, including retargeting, 
                            personalized, or interest-based advertising.
                        </li>
                        <li>
                            Limit your use of data to providing or improving user-facing features that are prominent in the requesting application's user interface. All other uses of the data are prohibited.
                        </li>
                        <li>
                            Only transfer the data to others if necessary to provide or improve user-facing 
                            features that are prominent in the requesting application's user interface.
                        </li>
                    </ul>
                    <p>
                        Our <span><a href={`${PUBLIC_URL}/privacy`}>privacy policy</a></span> page documents in detail what data our app is requesting 
                        and why the requests access to Google user data.
                    </p>
                </div>
            </div>
        </div>
        </Layout>
    );
};

export default Privacy;

