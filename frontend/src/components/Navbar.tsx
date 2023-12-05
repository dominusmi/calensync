import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import Container from 'react-bootstrap/Container';
import { get_session_id } from '../utils/session';

function NavBar() {
  const isConnected = get_session_id();


  return (
    <div>
      {isConnected &&
        <Navbar expand="md" className="hero py-2 hero-navbar">
          <Container className='p-0'>
            <Navbar.Brand href="/"> <img
              src="/logo.png"
              width="30"
              height="30"
              className="d-inline-block align-top"
              alt="Calensync logo"
            /></Navbar.Brand>
            <Navbar.Toggle aria-controls="basic-navbar-nav" />
            <Navbar.Collapse id="basic-navbar-nav">
              <Nav className="me-auto">
                <Nav.Link href="/dashboard">Home</Nav.Link>
                <Nav.Link href="/plan">Plan</Nav.Link>
              </Nav>
            </Navbar.Collapse>
          </Container>
        </Navbar>
      }
      {!isConnected &&
        <Navbar expand="md" className="hero pt-2 hero-navbar ">
          <Container className='p-0'>
            <Navbar.Brand href="/"> <img
              src="/logo.png"
              width="40"
              height="40"
              className="d-inline-block align-top"
              alt="Calensync logo"
            /></Navbar.Brand>
            <Navbar.Toggle aria-controls="basic-navbar-nav" />
            <Navbar.Collapse id="basic-navbar-nav">
              <Nav className="me-auto lead">
                <Nav.Link href="/login">Login</Nav.Link>
              </Nav>
            </Navbar.Collapse>
          </Container>
        </Navbar>
      }
    </div>
  );
}

export default NavBar;