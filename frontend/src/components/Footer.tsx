import React from 'react';

const Footer: React.FC = () => {
  return (
    <footer className="container mt-5 footer bg-light p-3">
      <div className='row'>
        <a href="/tos">Terms of Use</a>
      </div>
      <div className='row'>
        <a href="/privacy">Privacy Policy</a>
      </div>
      <div className='row'>
        <p>Calensync © 2023</p>
      </div>
    </footer>
  );
};

export default Footer;
