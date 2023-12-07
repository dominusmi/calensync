import React from 'react';
import LoginCard from '../components/LoginCard';
import Layout from '../components/Layout';

const Login: React.FC = () => {
  return (
    <Layout>
      <div className="container centered">
        <LoginCard />
      </div>
    </Layout>
  );
};

export default Login;