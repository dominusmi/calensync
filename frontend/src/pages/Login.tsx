import React, { useEffect, useState } from 'react';
import LoginCard from '../components/LoginCard';
import Layout from '../components/Layout';


const Login: React.FC = () => {
  return (
    <Layout verifySession={false} onlyRequired={true}>
      <div className="container">
          <div className='centered'>
            <LoginCard />
          </div>
      </div>
    </Layout>
  );
};

export default Login;