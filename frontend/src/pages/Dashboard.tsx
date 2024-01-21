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
import SyncRuleRow, { SyncRule } from '../components/SyncRuleRow';
import SyncRuleDraftRow from '../components/SyncRuleDraftRow';
import { useTranslation } from 'react-i18next';


const Dashboard: React.FC = () => {
  const { t } = useTranslation(['app']);

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
  }, [sessionChecked])


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
    // eslint-disable-next-line
  }, [user]);

  useEffect(() => {
    const fetchAccountsData = async () => {

      const response = await fetch(`${API}/accounts`, {
        method: 'GET',
        credentials: 'include'
      });
  
      if (!response.ok) {
        const error = await response.json();
        createToast(error.message || t("internal-server-error"), MessageKind.Error);
  
        throw new Error(`${t('dashboard.error.fetching-account')}: ${error.message}`);
      }
      let accounts = await response.json() as Account[];
      for (let i = 0; i < accounts.length; i++) {
        accounts[i].calendars = await fetchCalendars(accounts[i].uuid);
      }
      return accounts; // Assuming the data is an array of Account objects
    };

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
    // eslint-disable-next-line
  }, [sessionChecked, user]);

  useEffect(() => {
    if (accountsLoaded === true && accounts.length === 0 && showOnboarding === false) {
      setShowOnboarding(true);
    }
  }, [accountsLoaded, accounts, showOnboarding])

  const fetchSyncRule = async () => {
    const response = await fetch(
      `${API}/sync`,
      {
        credentials: 'include',
        method: 'GET'
      }
    )
    if (!response.ok) {
      createToast(t("dashboard.error.loading-rules"), MessageKind.Error)
      return
    }
    const rules_ = await response.json();
    setRules(rules_);
  }

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
      console.error(`${t("dashboard.error.fetching-calendars")}:`, error);
      return null
    }
  }

  return (

    <Layout onlyRequired={true}>
      <div className='container col-xxl-8'>
        {loading && <LoadingOverlay />}
        {user == null &&
          <div className='alert alert-light py-2 mt-4 border-2'>{t("dashboard.already-have-account")} <a href='login?login=true'>{t("dashboard.login")}</a></div>
        }
        {user != null && user.customer_id == null &&
          // show trial message
          <div className='container-sm p-0 my-2'>
            {daysLeft < 0 &&
              <p className='p-0 m-0 text-danger'> {t("dashboard.trial-ended")} </p>
            }
            {daysLeft >= 0 &&
              <p className='p-0 m-0'>{t("dashboard.days-left").replace("DAYS", daysLeft.toString())}</p>
            }
            <a className='m-0 p-0' href={`${PUBLIC_URL}/plan`}>{t("dashboard.upgrade")}</a>
          </div>
        }
        {accounts.length > 0 &&
          <>
            <div className='d-md-flex align-items-center justify-content-center d-flex-row my-3 px-0'>
              <span className='display-5 me-auto mb-2 mb-sm-0'>{t("dashboard.synchronize-calendars")}</span>
              <div className="break py-2"></div>
              <button className={`btn btn-primary ${(accounts.length >= 2 && rules.length === 0) ? 'glowing' : ''}`} onClick={() => setOpenDraft(true)}>Add Synchronization</button>
            </div>
            {rules.length === 0 && accounts && accounts.length > 0 &&
              <div className="alert alert-secondary" role="alert">
                {t("dashboard.no-syncs")}
              </div>
            }
            {rules.length > 0 && rules.map((rule) => <SyncRuleRow key={rule.uuid} rule={rule} />)
            }
            <SyncRuleDraftRow accounts={accounts} state={openDraft} setState={setOpenDraft} />
          </>
        }
        <div className='display-5 my-4'>{t("dashboard.connected-accounts")}</div>
        {accounts && accounts.length === 0 &&
          <div>
            <div className="alert alert-success" role="alert">
              <span className='fw-bold'> {t("dashboard.welcome")} 🎉 </span>
              {t("dashboard.first-thing")}
            </div>
          </div>
        }
        {accounts && accounts.length === 1 &&
          <div>
            <div className="alert alert-success" role="alert">
              <span className='fw-bold'> {t("dashboard.one-account")} ✅ </span><br/>
              {t("dashboard.second-account")}
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