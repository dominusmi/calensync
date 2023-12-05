import React, { useEffect, useState } from 'react';
import AccountCalendar from './AccountCalendar';
import API from '../utils/const';
import { get_session_id } from '../utils/session';
import axios from 'axios';

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
                        headers: {
                            Authorization: get_session_id()!
                        }
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
        <div className="container-sm card my-4 py-4 shadow-sm rounded border-0 template account-row">
            <div className="row mx-2">
                <div className="row my-2">
                    <div className="col-10">
                        <h4 className="mb-1 email-value">{account.key}</h4>
                    </div>
                    <div className="col-2">
                        <button className="btn btn-lg refresh-account"><svg xmlns="http://www.w3.org/2000/svg" width="20"
                            height="20" fill="currentColor" className="bi bi-arrow-clockwise" viewBox="0 0 16 16">
                            <path fillRule="evenodd"
                                d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z" />
                            <path
                                d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z" />
                        </svg>
                        </button>
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
