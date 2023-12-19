import React from 'react';
import { PUBLIC_URL } from '../utils/const';
import { useTranslation } from 'react-i18next';

const Footer: React.FC = () => {
  const { t } = useTranslation();

  return (
    <footer className="container mt-5 footer bg-light p-3 col-xxl-8  ">
      <div className='row'>
        <a href={`${PUBLIC_URL}/tos`}>{t("footer.tos")}</a>
      </div>
      <div className='row'>
        <a href={`${PUBLIC_URL}/privacy`}>{t("footer.privacy")}</a>
      </div>
      <div className='row'>
        <a href={`${PUBLIC_URL}/google-privacy`}>{t("footer.google_disclosure")}</a>
      </div>
      <div className='row'>
        <p>Calensync © 2023</p>
      </div>
    </footer>
  );
};

export default Footer;
