import { optimisticIsConnected, logout, getLocalSession } from '../utils/session';
import { PUBLIC_URL } from '../utils/const';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import LoadingOverlay from './LoadingOverlay';
import { Container, Nav, Navbar } from 'react-bootstrap';

const NavBar: React.FC<{ verify_session?: boolean }> = ({ verify_session = true }) => {
  const { t } = useTranslation();
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    if (verify_session) {
      optimisticIsConnected().then((loggedIn) => setIsConnected(loggedIn))
    } else {
      setIsConnected(getLocalSession() !== null);
    }
  }, [verify_session])

  function handleLogout() {
    setIsLoading(true);
    logout().then(() => {
      window.location.href = `/dashboard`
    }).finally(() => setIsLoading(false))
    localStorage.removeItem('session-id');
  }

  return (
    <Navbar expand="md" className="hero py-2 hero-navbar d-flex justify-content-center">
      { isLoading && <LoadingOverlay/>}
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
              <Nav.Link href={`${PUBLIC_URL}/`}>{t('navbar.home')}</Nav.Link>
              <Nav.Link href={`${PUBLIC_URL}/dashboard`}>{t('navbar.dashboard')}</Nav.Link>
              <Nav.Link href={`${PUBLIC_URL}/plan`}>{t('navbar.plan')}</Nav.Link>
              <Nav.Link onClick={handleLogout}>{t('navbar.logout')}</Nav.Link>
            </Nav>
          }
          {!isConnected &&
            <Nav className="me-auto lead">
              <Nav.Link href={`${PUBLIC_URL}/`}>{t('navbar.home')}</Nav.Link>
              <Nav.Link href={`${PUBLIC_URL}/dashboard`}>{t('navbar.dashboard')}</Nav.Link>
            </Nav>
          }
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
}

export default NavBar;