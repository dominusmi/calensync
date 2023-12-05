import React from 'react';
import LoginCard from '../components/LoginCard';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const Login: React.FC = () => {
  return (
    <div className="App bg-light">
      <Navbar />
      <div className="container centered content">
        <LoginCard />
      </div>
      <Footer />
    </div>
  );
};

export default Login;