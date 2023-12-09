import React from 'react';
import { PUBLIC_URL } from '../utils/const';

const Footer: React.FC = () => {
  return (
    <footer className="container mt-5 footer bg-light p-3">
      <div className='row'>
        <a href={`${PUBLIC_URL}/tos`}>Terms of Use</a>
      </div>
      <div className='row'>
        <a href={`${PUBLIC_URL}/privacy`}>Privacy Policy</a>
      </div>
      <div className='row'>
        <a href={`${PUBLIC_URL}/google-privacy`}>Google Usage Disclosure</a>
      </div>
      <div className='row'>
        <p>Calensync © 2023</p>
      </div>
    </footer>
  );
};

export default Footer;
