import React, { useEffect, useState } from 'react';
import AccountCalendar from './AccountCalendar';
import API from '../utils/const';
import { getLocalSession } from '../utils/session';
import axios from 'axios';
import { createToast } from './Toast';

export interface Calendar {
    uuid: string;
    name: string;
    active: boolean;
}

export interface Account {
    uuid: string;
    key: string;
    calendars: Calendar[] | null;
}

interface AccountCardProps {
    account: Account;
}


const AccountCard: React.FC<{ account: Account }> = ({ account }) => {
    const [calendars, setCalendars] = useState<Array<Calendar>>([]);
    const [isLoading, setLoading] = useState(true);

    useEffect(() => {
        const fetchCalendars = async () => {
            try {
                const response = await axios.get(
                    `${API}/accounts/${account.uuid}/calendars`,
                    {
                        method: 'GET',
                        withCredentials: true
                    }
                );
                setCalendars(response.data);
                setLoading(false);
            } catch (error) {
                console.error('Error fetching calendars:', error);
            }
        };

        fetchCalendars();
    }, [account.uuid]);

    return (
        <div className="container-sm card my-2 my-sm-4 py-4 shadow-sm rounded border-0 template account-row">
            <div className="row mx-xs-0 mx-sm-2">
                <div className="row my-2">
                    <div className="col-12">
                        <h6 className="mb-1 email-value">{account.key}<span className='text-muted small'>'s Google calendars</span></h6>
                    </div>
                </div>
                {calendars && calendars.map((calendar) => (
                    <AccountCalendar key={calendar.name} calendar={calendar} />
                ))}
            </div>
        </div>
    );
};

export default AccountCard;
