// Home.tsx

import React, { useEffect, useState } from 'react';
import verify_session_id, { VerifySession, get_session_id } from '../utils/session'; // Adjust the import path
import API from '../utils/const';
import AccountCard, { Account } from '../components/AccountCard';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import LoadingOverlay from '../components/LoadingOverlay';
import AddCalendarAccount from '../components/AddCalendarAccount';
import Toast, { toast_error } from '../components/Toast';
import { toast } from 'react-toastify';

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountsLoaded, setAccountsLoaded] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const fetchData = async () => {
      try {
        const result = await verify_session_id();
        console.log(result)
        if (isMounted && result === VerifySession.OK) {
          const accountsData = await fetchAccountsData();
          setAccounts(accountsData);
          setAccountsLoaded(true);
        }else if(result == VerifySession.TOS){
          window.location.href = "/tos";
        }
      } catch (error) {
        console.error('Error fetching accounts data', error);
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
    console.log(response)
    if (!response.ok) {
      const error = await response.json();
      toast_error(error.message || "Internal server error");
      
      throw new Error(`Error fetching accounts data: ${error.message}`);
    }
    const data = await response.json();
    setLoading(false);
    return data; // Assuming the data is an array of Account objects
  };

  // Render AccountCards for each account
  return (
    <div className='App bg-light'>
      <div className='content'>
      <Navbar />
      {loading && <LoadingOverlay />}
      {accounts && accounts.map((account) => (
        <AccountCard key={account.uuid} account={account} />
      ))}
      { accounts && accounts.length === 0 &&
        <div className="container-sm card my-4 py-4 shadow-sm rounded border-0 template account-row">
          <div className="row mx-2">
            <h2>Connect your first Google calendar now!</h2>
          </div>
        </div>
      }
      <AddCalendarAccount />
      </div>
      <Toast/>
      <Footer />
    </div>
  );
};

export default Dashboard;