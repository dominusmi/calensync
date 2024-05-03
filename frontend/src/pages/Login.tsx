import React from 'react';
import LoginCard from '../components/LoginCard';
import Layout from '../layouts/Layout';


const Login: React.FC = () => {
  return (
    <Layout verifySession={false} onlyRequired={false}>
      <div className="container">
          <div className='centered'>
            <LoginCard />
          </div>
      </div>
    </Layout>
  );
};

export default Login;