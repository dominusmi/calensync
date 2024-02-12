import {
  BrowserRouter as Router,
  Routes,
  Route,
} from "react-router-dom";


import './App.css'; // Make sure the file path is correct
import { ENV, PUBLIC_URL } from "./utils/const";

import ErrorBoundary from "./components/ErrorBoundary";
import { initReactI18next } from "react-i18next";
import i18nextBrowserLanguageDetector from "i18next-browser-languagedetector"
import i18next from "i18next";
import LocalesImportPlugin from "./components/LocalesLazyImport";

import { SUPPORTED_LANGUAGES } from "./utils/common";
import React from "react";
import { blogRoutes } from "./_blog/routes";
import Blog from "./pages/Blog";

const Login = React.lazy(() => import("./pages/Login"));
const Dashboard = React.lazy(() => import("./pages/Dashboard"));
const Tos = React.lazy(() => import('./pages/Tos'));
const Plan = React.lazy(() => import('./pages/Plan'));
const Home = React.lazy(() => import("./pages/Home"));
const Privacy = React.lazy(() => import("./pages/Privacy"));
const GoogleDisclosure = React.lazy(() => import("./pages/GoogleDisclosure"));
const ForFreelancer = React.lazy(() => import("./pages/ForFreelancer"));

i18next
  .use(initReactI18next)
  .use(i18nextBrowserLanguageDetector)
  .use(LocalesImportPlugin)
  .init({
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
    ns: ['common'],
    detection: {
      order: ['path', 'sessionStorage', 'navigator'],
      caches: ['sessionStorage'],
      lookupFromPathIndex: ENV === "development" ? 1 : 0
    },
    supportedLngs: SUPPORTED_LANGUAGES,
    saveMissing: true, // for missing key handler to fire
    missingKeyHandler: function (lng, ns, key, fallbackValue) {
      console.log("Missing:", key);
    }
  });


function App() {
  return (
    <ErrorBoundary>
      <Router basename={PUBLIC_URL}>
        <Routes>
          <Route path="/:lang?/" element={<Home />} />
          <Route path="/:lang?/dashboard" element={<Dashboard />} />
          <Route path="/:lang?/login" element={<Login />} />
          <Route path="/:lang?/plan" element={<Plan />} />
          <Route path="/:lang?/tos" element={<Tos />} />
          <Route path="/:lang?/privacy" element={<Privacy />} />
          <Route path="/:lang?/google-privacy" element={<GoogleDisclosure />}></Route>
          <Route path="/:lang?/for-freelancers" element={<ForFreelancer />}></Route>
          <Route path="/:lang?/blog" element={<Blog />}></Route>
          {blogRoutes.map(([url, Component]) => {
            return <Route path={`/:lang?${url}`} element={<Component />} />
          })}
          {/* <Route path="/:lang?/blog/sync-multiple-google-calendars" element={<HowToSynchronizeCalendars />}></Route> */}
          {/* <Route path="/:lang?/blog/avoid-calendly-conflicts" element={<HowToAvoidCalendlyConflicts />}></Route> */}
          {/* <Route path="/:lang?/blog/sync-all-google-calendars-into-one" element={<SynchronizeAllCalendarsIntoOne />}></Route> */}
        </Routes>
      </Router>
    </ErrorBoundary>
  );
}

export default App;