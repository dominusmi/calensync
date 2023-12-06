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
      </Routes>
    </Router>
  );
}

export default App;
