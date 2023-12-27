// Home.tsx

import React, { useEffect, useState } from 'react';
import { getLoggedUser, User } from '../utils/session'; // Adjust the import path
import API, { PUBLIC_URL } from '../utils/const';
import AccountCard, { Account } from '../components/AccountCard';
import LoadingOverlay from '../components/LoadingOverlay';
import AddCalendarAccount from '../components/AddCalendarAccount';
import { createToast } from '../components/Toast';
import Layout from '../components/Layout';
import { MessageKind } from '../utils/common';
import ContactButton, { TallyComponent } from '../components/FeedbackButton';
import { Button, Modal } from 'react-bootstrap';

const OnboardingModal: React.FC<{onClose: () => void}> = React.memo(({onClose}) => {
  return (
    <Modal
      show={true}
      size="lg"
      aria-labelledby="contained-modal-title-vcenter"
      centered
    >
      <Modal.Header>
        <Modal.Title id="contained-modal-title-vcenter">
          Let's onboard together
        </Modal.Title>
      </Modal.Header>
      <Modal.Body className=''>
        <div className='embed-container'>
          <iframe width="560" height="315" src="https://www.youtube.com/embed/q672j6cNCNc?si=tncAOhutUdFo9QR_" title="YouTube video player" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowFullScreen></iframe>
          </div>
      </Modal.Body>
      <Modal.Footer>
        <Button onClick={onClose} className='btn btn-ternary'>Skip</Button>
      </Modal.Footer>
    </Modal>
  );
});

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountsLoaded, setAccountsLoaded] = useState(false);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [daysLeft, setDaysLeft] = useState<number>(0);
  // Render AccountCards for each account
  const [showOnboarding, setShowOnboarding] = useState<boolean>(false);


  useEffect(() => {
    getLoggedUser().then((user) => {
      setUser(user);
      setSessionChecked(true)
    })
  }, [])


  useEffect(() => {
    if (user != null && user!.customer_id == null) {
      const currentDate = new Date();
      const targetDate = user.date_created.getTime() + 24 * 60 * 60 * 1000 * 7;
      const timeDifference = targetDate - currentDate.getTime();
      const daysDifference = Math.ceil(timeDifference / (24 * 60 * 60 * 1000));
      setDaysLeft(daysDifference);
    }
  }, [user]);

  useEffect(() => {
    let isMounted = true;

    const fetchData = async () => {
      const accountsData = await fetchAccountsData();
      setAccounts(accountsData);
      setAccountsLoaded(true);
    };

    if (loading) {
      fetchData();
    }

    return () => {
      isMounted = false;
    };
  }, [loading, sessionChecked]);

  useEffect(() => {
    if (accountsLoaded === true && accounts.length == 0 && showOnboarding === false) {
      console.log(accounts)
      setShowOnboarding(true);
    }
  }, [accountsLoaded])

  const fetchAccountsData = async () => {

    const response = await fetch(`${API}/accounts`, {
      method: 'GET',
      credentials: 'include'
    });

    if (!response.ok) {
      const error = await response.json();
      createToast(error.message || "Internal server error", MessageKind.Error);

      throw new Error(`Error fetching accounts data: ${error.message}`);
    }
    const data = await response.json();
    setLoading(false);
    return data; // Assuming the data is an array of Account objects
  };



  return (

    <Layout onlyRequired={true}>
      <div className='container col-xxl-8'>
        {loading && <LoadingOverlay />}
        {user != null && user.customer_id == null &&
          // show trial message
          <div className='container-sm p-0 mt-2'>
            {daysLeft < 0 &&
              <p className='p-0 m-0 text-danger'>Your trial has ended. Upgrade now or risk losing all synchronised events. </p>
            }
            {daysLeft >= 0 &&
              <p className='p-0 m-0'>You have {daysLeft} days left on your free trial. </p>
            }
            <a className='m-0 p-0' href={`${PUBLIC_URL}/plan`}>Upgrade</a>
          </div>
        }
        <AddCalendarAccount />
        {accounts && accounts.map((account) => (
          <AccountCard key={account.uuid} account={account} />
        ))}
        {accounts && accounts.length === 0 &&
          <div>
            <div className="container-sm card my-2 py-4 shadow-sm rounded border-0 template account-row">
              <div className="row">
                <h2>Welcome! 🎉</h2>
                <p>
                  Let's get started. Give permission to your current account by clicking the button above.
                </p>
              </div>
            </div>
          </div>
        }
        {accounts && accounts.length === 1 &&
          <div className="container-sm card my-2 py-4 shadow-sm rounded border-0 template account-row">
            <div className="row mx-sm-0">
              <h2>One down. ✅</h2>
              <p>
                Your first account is connected. You can now synchronize calendars inside of it,
                or add another Google Account and do cross-account syncing!
              </p>
            </div>
          </div>
        }

        <ContactButton />
        <TallyComponent />
      </div>
      {showOnboarding &&
        <OnboardingModal onClose={() => setShowOnboarding(false)} />
      }
    </Layout>
  );
};

export default Dashboard;