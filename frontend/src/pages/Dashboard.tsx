// Home.tsx

import React, { useEffect, useState } from 'react';
import verify_session_id, { VerifySession, get_session_id, getLoggedUser, User } from '../utils/session'; // Adjust the import path
import API, { PUBLIC_URL } from '../utils/const';
import AccountCard, { Account } from '../components/AccountCard';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import LoadingOverlay from '../components/LoadingOverlay';
import AddCalendarAccount from '../components/AddCalendarAccount';
import { toast_msg } from '../components/Toast';
import Layout from '../components/Layout';
import { MessageKind, setMessage } from '../utils/common';

interface Window {
  Tally: any; // Adjust the type accordingly based on the Tally library
  TallyConfig: any;
}



const TallyComponent = () => {
  useEffect(() => {
    // Dynamically create and append the script tag
    const script = document.createElement('script');
    script.src = 'https://tally.so/widgets/embed.js';
    script.async = true;
    document.head.appendChild(script);

    let win = (window as unknown) as Window;

    // Set up Tally configuration after script has loaded
    script.onload = () => {
      const options: any = {
        emoji: {
          text: '👋',
          animation: 'wave'
        },
        open: {
          trigger: 'time',
          ms: 5000
        }
      };

      // Initialize Tally popup
      console.log(win.Tally)
      const tallyPopup = new win.Tally.openPopup("nroQgv", options);
    };
  }, []);

  return (
    <div id="tally-popup-container">
      {/* This div will be replaced by Tally's popup */}
    </div>
  );
};


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
      const targetDate = user.date_created;
      const timeDifference = targetDate.getTime() - currentDate.getTime();
      const daysDifference = -1 * Math.ceil(timeDifference / (24 * 60 * 60 * 1000));
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
      headers: {
        Authorization: get_session_id()!,
      },
    });
    if (!response.ok) {
      const error = await response.json();
      toast_msg(error.message || "Internal server error", MessageKind.Error);

      throw new Error(`Error fetching accounts data: ${error.message}`);
    }
    const data = await response.json();
    setLoading(false);
    return data; // Assuming the data is an array of Account objects
  };

  // Render AccountCards for each account
  return (
    <Layout>
      {loading && <LoadingOverlay />}
      {user != null && user.customer_id == null &&
        // show trial message
        <div className='container-sm p-0 mt-2'>
          <p className='p-0 m-0'>You have {daysLeft} days left on your free trial. </p>
          <a className='m-0 p-0' href={`${PUBLIC_URL}/plan`}>Upgrade</a>
        </div>
      }
      {accounts && accounts.map((account) => (
        <AccountCard key={account.uuid} account={account} />
      ))}
      {accounts && accounts.length === 0 &&
        <div className="container-sm card my-4 py-4 shadow-sm rounded border-0 template account-row">
          <div className="row mx-2">
            <h2>You're set 🎉</h2>
            <p>You can connect your Google calendars with the button below</p>
          </div>
        </div>
      }
      <AddCalendarAccount />
      <TallyComponent/>
    </Layout>
  );
};

export default Dashboard;