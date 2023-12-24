import {
  BrowserRouter as Router,
  Routes,
  Route,
  useParams,
} from "react-router-dom";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Tos from './pages/Tos';
import Plan from './pages/Plan';
import Home from "./pages/Home";
import './App.css'; // Make sure the file path is correct
import Privacy from "./pages/Privacy";
import { PUBLIC_URL } from "./utils/const";
import GoogleDisclosure from "./pages/GoogleDisclosure";
import HowToSynchronizeCalendars from "./pages/blog/HowToSynchronizeCalendars";
import HowToAvoidCalendlyConflicts from "./pages/blog/HowToAvoidCalendlyConflicts";
import ErrorBoundary from "./components/ErrorBoundary";
import { initReactI18next, I18nextProvider } from "react-i18next";
import i18nextBrowserLanguageDetector from "i18next-browser-languagedetector"
import i18next, { BackendModule, LanguageDetectorModule } from "i18next";
import LanguageDetector from 'i18next-browser-languagedetector';
import LocalesImportPlugin from "./components/LocalesLazyImport";
import ForFreelancer from "./pages/ForFreelancer";



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
      caches: ['sessionStorage']
    },
    supportedLngs: ["en", "fr", "it"],
    saveMissing: true, // for missing key handler to fire
    missingKeyHandler: function (lng, ns, key, fallbackValue) {
      console.log("Missing:", key);
    }
  });



function App() {
  const { lang } = useParams();
  // if (i18next.resolvedLanguage && sessionStorage.getItem("i18nextLng") === null) {
    // sessionStorage.setItem("i18nextLng", i18next.resolvedLanguage!);
  // }

  return (
    <ErrorBoundary>
      <Router basename={PUBLIC_URL}>
        <Routes>
          <Route path="/:lang?/" element={<Home />} />
          <Route path="/:lang?/dashboard" element={<Dashboard />} />
          <Route path="/:lang?/login" element={<Login />} />
          <Route path="/:lang?/tos" element={<Tos />} />
          <Route path="/:lang?/privacy" element={<Privacy />} />
          <Route path="/:lang?/plan" element={<Plan />} />
          <Route path="/:lang?/google-privacy" element={<GoogleDisclosure />}></Route>
          <Route path="/:lang?/for-freelancers" element={<ForFreelancer />}></Route>
          <Route path="/:lang?/blog/sync-multiple-google-calendars" element={<HowToSynchronizeCalendars />}></Route>
          <Route path="/:lang?/blog/avoid-calendly-conflicts" element={<HowToAvoidCalendlyConflicts />}></Route>
        </Routes>
      </Router>
    </ErrorBoundary>
  );
}

export default App;