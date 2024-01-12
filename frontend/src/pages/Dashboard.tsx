// Home.tsx

import React, { useEffect, useState } from 'react';
import { getLocalSession, getLoggedUser, User } from '../utils/session'; // Adjust the import path
import API, { PUBLIC_URL } from '../utils/const';
import AccountCard, { Account, Calendar } from '../components/AccountCard';
import LoadingOverlay from '../components/LoadingOverlay';
import AddCalendarAccount from '../components/AddCalendarAccount';
import { createToast } from '../components/Toast';
import Layout from '../components/Layout';
import { MessageKind } from '../utils/common';
import ContactButton, { TallyComponent } from '../components/FeedbackButton';
import { Button, Modal } from 'react-bootstrap';
import SyncRuleRow, { SyncRule } from '../components/SyncRuleRow';
import SyncRuleDraftRow from '../components/SyncRuleDraftRow';

const OnboardingModal: React.FC<{ onClose: () => void }> = React.memo(({ onClose }) => {
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
  const [loading, setLoading] = useState(false);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountsLoaded, setAccountsLoaded] = useState(false);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [daysLeft, setDaysLeft] = useState<number>(0);
  const [rules, setRules] = useState<SyncRule[]>([])
  const [openDraft, setOpenDraft] = useState<boolean>(false)

  // Render AccountCards for each account
  const [showOnboarding, setShowOnboarding] = useState<boolean>(false);


  useEffect(() => {
    if( getLocalSession() != null && !sessionChecked){
      setLoading(true);
    }

    getLoggedUser().then((user) => {
      if (user == null) {
        setSessionChecked(true);
        setLoading(false);
      } else {
        setLoading(true);
        setUser(user);
        setSessionChecked(true)
      }
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
    if (user != null) {
      fetchSyncRule()
    }
  }, [user]);

  useEffect(() => {
    if (sessionChecked && user != null) {
      const fetchData = async () => {
        const accountsData = await fetchAccountsData();
        setAccounts(accountsData);
        setAccountsLoaded(true);
        setLoading(false);
      };

      fetchData();
    } else if (sessionChecked && user == null) {
      setLoading(false);
    }
  }, [sessionChecked, user]);

  useEffect(() => {
    if (accountsLoaded === true && accounts.length == 0 && showOnboarding === false) {
      setShowOnboarding(true);
    }
  }, [accountsLoaded])

  const fetchSyncRule = async () => {
    const response = await fetch(
      `${API}/sync`,
      {
        credentials: 'include',
        method: 'GET'
      }
    )
    if (!response.ok) {
      createToast("Couldn't load sync rules", MessageKind.Error)
      return
    }
    const rules_ = await response.json();
    setRules(rules_);
  }

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
    let accounts = await response.json() as Account[];
    for (let i = 0; i < accounts.length; i++) {
      accounts[i].calendars = await fetchCalendars(accounts[i].uuid);
    }
    return accounts; // Assuming the data is an array of Account objects
  };

  async function fetchCalendars(uuid: string) {
    try {
      const response = await fetch(
        `${API}/accounts/${uuid}/calendars`,
        {
          method: 'GET',
          credentials: 'include'
        }
      );
      return await response.json() as Calendar[];
    } catch (error) {
      console.error('Error fetching calendars:', error);
      return null
    }
  }

  return (

    <Layout onlyRequired={true}>
      <div className='container col-xxl-8'>
        {loading && <LoadingOverlay />}
        {user == null &&
          <div className='alert alert-light py-2 mt-4 border-2'>Already have an account? <a href='login?login=true'>Login</a></div>
        }
        {user != null && user.customer_id == null &&
          // show trial message
          <div className='container-sm p-0 my-2'>
            {daysLeft < 0 &&
              <p className='p-0 m-0 text-danger'>Your trial has ended. Upgrade now or risk losing all synchronised events. </p>
            }
            {daysLeft >= 0 &&
              <p className='p-0 m-0'>You have {daysLeft} days left on your free trial. </p>
            }
            <a className='m-0 p-0' href={`${PUBLIC_URL}/plan`}>Upgrade</a>
          </div>
        }
        {accounts.length > 0 &&
          <>
            <div className='d-md-flex align-items-center justify-content-center d-flex-row my-3 px-0'>
              <span className='display-5 me-auto mb-2 mb-sm-0'>Synchronize Calendars</span>
              <div className="break py-2"></div>
              <button className={`btn btn-primary ${(accounts.length >= 2 && rules.length == 0) ? 'glowing' : ''}`} onClick={() => setOpenDraft(true)}>Add Synchronization</button>
            </div>
            {rules.length == 0 && accounts && accounts.length > 0 &&
              <div className="alert alert-secondary" role="alert">
                You have no synchronizations yet, create the first one!
              </div>
            }
            {rules.length > 0 && rules.map((rule) => <SyncRuleRow key={rule.uuid} rule={rule} />)
            }
            <SyncRuleDraftRow accounts={accounts} state={openDraft} setState={setOpenDraft} />
          </>
        }
        <div className='display-5 my-4'>Connected accounts</div>
        {accounts && accounts.length === 0 &&
          <div>
            <div className="alert alert-success" role="alert">
              <span className='fw-bold'> Welcome to Calensync! 🎉 </span>
              The first thing you need to do is connect one or more Google accounts by clicking the button below
            </div>
          </div>
        }
        {accounts && accounts.length === 1 &&
          <div>
            <div className="alert alert-success" role="alert">
              <span className='fw-bold'> One account connected ✅ </span><br/>
              87% of people connect a second account, go ahead and click the button below
            </div>
          </div>
        }
        <AddCalendarAccount isConnected={user != null} glowing={accounts != null && accounts.length < 2}/>
        {accounts && accounts.map((account) => (
          <AccountCard key={account.uuid} account={account} />
        ))}

        <ContactButton />
        <TallyComponent />
      </div>
      {/* {showOnboarding &&
        <OnboardingModal onClose={() => setShowOnboarding(false)} />
      } */}
    </Layout>
  );
};

export default Dashboard;