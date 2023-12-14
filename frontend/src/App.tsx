import {
  BrowserRouter as Router,
  Routes,
  Route,
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
import BlogPage from "./pages/BlogPage";


function App() {
  return (
    <Router basename={PUBLIC_URL}>
      <Routes>
        <Route path="/" element={<Home/>} />
        <Route path="/dashboard" element={<Dashboard/>} />
        <Route path="/login" element={<Login/>} />
        <Route path="/tos" element={<Tos/>} />
        <Route path="/privacy" element={<Privacy/>} />
        <Route path="/plan" element={<Plan/>} />
        <Route path="/google-privacy" element={<GoogleDisclosure/>}></Route>
        <Route path="/blog/sync-multiple-google-calendars" element={<BlogPage/>}></Route>
      </Routes>
    </Router>
  );
}

export default App;
