import React from 'react';
import { PUBLIC_URL } from '../utils/const';
import { useTranslation } from 'react-i18next';
import { blogs } from '../_blog/routes';
import { getBlogByLanguage } from '../utils/blog';

const Footer: React.FC<{ onlyRequired?: boolean }> = ({ onlyRequired = false }) => {
  const { t, i18n } = useTranslation();


  return (
    <footer className="container content py-3 footer col-xxl-8" >
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
            <a href={`${PUBLIC_URL}/en`}>English</a>
          </div>
          <div className="row">
            <a href={`${PUBLIC_URL}/fr`}>Français</a>
          </div>
          <div className="row">
            <a href={`${PUBLIC_URL}/it`}>Italiano</a>
          </div>
          <div className="row">
            <p>Calensync © 2023</p>
          </div>
        </div>
          <div className="col-12 col-sm-6 col-xxl-4">
            <div className="row">
              <a href={`${PUBLIC_URL}/blog`}>{t("footer.blog")}</a>
            </div>
            <div className="row">
              <a href={`${PUBLIC_URL}/for-freelancers`}>{t("footer.for_freelancers")}</a>
            </div>
            <div className="row">
              <a href={`${PUBLIC_URL}${getBlogByLanguage(blogs['calensync-vs-notion'], i18n.resolvedLanguage).url}`}>Calensync vs Notion</a>
              <a href={`${PUBLIC_URL}${getBlogByLanguage(blogs['calensync-vs-onecal'], i18n.resolvedLanguage).url}`}>Calensync vs OneCal</a>
              <a href={`${PUBLIC_URL}${getBlogByLanguage(blogs['calensync-vs-syncthemcalendars'], i18n.resolvedLanguage).url}`}>Calensync vs SyncThemCalendars</a>
            </div>
          </div>
      </div>
    </footer>
  );
};

export default Footer;
