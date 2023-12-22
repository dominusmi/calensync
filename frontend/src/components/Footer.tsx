import React from 'react';
import { PUBLIC_URL } from '../utils/const';
import { useTranslation } from 'react-i18next';

const Footer: React.FC<{ onlyRequired?: boolean }> = ({ onlyRequired = false }) => {
  const { t } = useTranslation();


  return (
    <footer className="container content mt-5 footer col-xxl-8" >
      <div className="row col-xxl-8 d-flex justify-content-between">
        <div className="col-12 col-sm-6 col-xxl-4 mt-sm-0 mt-3">
          <div className="row">
            <a href={`${PUBLIC_URL}/tos`}>{t("footer.tos")}</a>
          </div>
          <div className="row">
            <a href={`${PUBLIC_URL}/privacy`}>{t("footer.privacy")}</a>
          </div>
          <div className="row">
            <a href={`${PUBLIC_URL}/google-privacy`}>{t("footer.google_disclosure")}</a>
          </div>
          <div className="row">
            <p>Calensync © 2023</p>
          </div>
        </div>
        {!onlyRequired &&
          <div className="col-12 col-sm-6 col-xxl-4">
            <div className="row">
              <a href={`${PUBLIC_URL}/home`}>{t("footer.home")}</a>
            </div>
            <div className="row">
              <a href={`${PUBLIC_URL}/login`}>{t("footer.login")}</a>
            </div>
            <div className="row">
              <a href={`${PUBLIC_URL}/dashboard`}>{t("footer.dashboard")}</a>
            </div>
            <div className="row">
              <a href={`${PUBLIC_URL}/for-freelancers`}>{t("footer.for_freelancers")}</a>
            </div>
          </div>
        }
      </div>
    </footer>
  );
};

export default Footer;
