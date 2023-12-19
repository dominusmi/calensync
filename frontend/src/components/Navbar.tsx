import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import Container from 'react-bootstrap/Container';
import { optimisticIsConnected, logout, getLocalSession } from '../utils/session';
import { PUBLIC_URL } from '../utils/const';
import { useEffect, useState } from 'react';

const NavBar: React.FC<{ verify_session?: boolean }> = ({ verify_session = true }) => {
  const [isConnected, setIsConnected] = useState<boolean>(false);

  useEffect(() => {
    if (verify_session) {
      optimisticIsConnected().then((loggedIn) => setIsConnected(loggedIn))
    } else {
      setIsConnected(getLocalSession() !== null);
    }
  }, [])

  function handleLogout() {
    logout().then(() => window.location.href = `/login`)
    localStorage.removeItem('session-id');
  }

  return (
    <Navbar expand="md" className="hero py-2 hero-navbar d-flex justify-content-center">
      <Container className='container px-xxl-0 col-xxl-8'>
        <Navbar.Brand href={`${PUBLIC_URL}/`}> <img
          src={`${PUBLIC_URL}/logo.png`}
          width="30"
          height="30"
          className="d-inline-block align-top"
          alt="Calensync logo"
        /></Navbar.Brand>
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          {isConnected &&
            <Nav className="me-auto lead">
              <Nav.Link href={`${PUBLIC_URL}/`}>Home</Nav.Link>
              <Nav.Link href={`${PUBLIC_URL}/dashboard`}>Dashboard</Nav.Link>
              <Nav.Link href={`${PUBLIC_URL}/plan`}>Plan</Nav.Link>
              <Nav.Link onClick={handleLogout}>Logout</Nav.Link>
            </Nav>
          }
          {!isConnected &&
            <Nav className="me-auto lead">
              <Nav.Link href={`${PUBLIC_URL}/`}>Home</Nav.Link>
              <Nav.Link href={`${PUBLIC_URL}/login`}>Login</Nav.Link>
            </Nav>
          }
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
}

export default NavBar;