// Home.tsx

import React, { useEffect, useState } from 'react';
import verify_session_id, { VerifySession, get_session_id } from '../utils/session'; // Adjust the import path
import API, { PUBLIC_URL } from '../utils/const';
import AccountCard, { Account } from '../components/AccountCard';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import LoadingOverlay from '../components/LoadingOverlay';
import AddCalendarAccount from '../components/AddCalendarAccount';
import { toast_msg } from '../components/Toast';
import Layout from '../components/Layout';
import { MessageKind, setMessage } from '../utils/common';

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountsLoaded, setAccountsLoaded] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const fetchData = async () => {
      const result = await verify_session_id();
      if (isMounted && result === VerifySession.OK) {
        const accountsData = await fetchAccountsData();
        setAccounts(accountsData);
        setAccountsLoaded(true);
      } else if (result == VerifySession.TOS) {
        setMessage("Must accept Terms of Use", MessageKind.Info)
        window.location.href = `${PUBLIC_URL}/tos`;
      } else if (result == VerifySession.LOGIN) {
        window.location.href = `${PUBLIC_URL}/login`;
      } else {
        setMessage("Could not verify session", MessageKind.Success)
        window.location.href = `${PUBLIC_URL}/login`;
      }
    };

    if (loading) {
      fetchData();
    }

    return () => {
      isMounted = false;
    };
  }, [loading]);

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
    </Layout>
  );
};

export default Dashboard;