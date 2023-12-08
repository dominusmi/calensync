import React, { useEffect, useState } from 'react';
import LoginCard from '../components/LoginCard';
import Layout from '../components/Layout';
import { ENV } from '../utils/const';
import LoadingOverlay from '../components/LoadingOverlay';


const Login: React.FC = () => {
  const [isProduction, setIsProduction] = useState<boolean>(ENV == 'production');

  return (
    <Layout verify_session={false}>
      <div className="container">
        { !isProduction &&
          <div className='centered'>
            <LoginCard />
          </div>
        }
        {
          isProduction &&
          <div className='mt-4'>
            <h3>Stay tuned.</h3>
            <iframe src="https://tally.so/embed/mZ2K5e?alignLeft=1&hideTitle=1&transparentBackground=1" width={"100%"} height={"100%"} style={{ minHeight: "500px" }}></iframe>
          </div>
        }
      </div>
    </Layout>
  );
};

export default Login;