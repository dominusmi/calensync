// Home.tsx

import React, { useEffect, useState } from 'react';
import { getLocalSession, getLoggedUser, User } from '../utils/session'; // Adjust the import path
import API, { PUBLIC_URL } from '../utils/const';
import AccountCard, { Account } from '../components/AccountCard';
import LoadingOverlay from '../components/LoadingOverlay';
import AddCalendarAccount from '../components/AddCalendarAccount';
import { createToast } from '../components/Toast';
import Layout from '../components/Layout';
import { MessageKind } from '../utils/common';
import ContactButton, { TallyComponent } from '../components/FeedbackButton';


const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountsLoaded, setAccountsLoaded] = useState(false);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [daysLeft, setDaysLeft] = useState<number>(0);

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

  // Render AccountCards for each account
  return (
    <Layout>
      <div className='container col-xxl-8'>
        {loading && <LoadingOverlay />}
        {user != null && user.customer_id == null &&
          // show trial message
          <div className='container-sm p-0 mt-2'>
            { daysLeft < 0 &&
              <p className='p-0 m-0 text-danger'>Your trial has ended. Upgrade now or risk losing all synchronised events. </p>
            }
            { daysLeft >= 0 && 
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
          <div className="container-sm card my-2 py-4 shadow-sm rounded border-0 template account-row">
            <div className="row">
              <h2>Welcome! 🎉</h2>
              <p>
                Let's get started. Give permission to your current account by clicking the button above.
              </p>
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
    </Layout>
  );
};

export default Dashboard;