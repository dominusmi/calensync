import React, { useEffect, useState } from 'react';
import API from '../utils/const';
import { getLocalSession } from '../utils/session';
import axios from 'axios';
import { createToast } from './Toast';
import { Accordion } from 'react-bootstrap';
import { Tooltip } from 'react-tooltip'

export interface Calendar {
    uuid: string;
    name: string;
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
                <Accordion>
                    <Accordion.Item eventKey="0">
                        <Accordion.Header>
                            <div className="row my-2">
                                <div className="col-12">
                                    <h6  key={`${account.uuid}-title`} className="mb-1 email-value">{account.key}<span className='text-muted small'>'s Google calendars</span></h6>
                                </div>
                            </div>
                        </Accordion.Header>
                        <Accordion.Body>
                            {calendars && calendars.map((calendar) => (
                                <div className='d-flex' key={`${calendar.uuid}-div`}>
                                    <label className="form-check-label xs-small">{calendar.name.replace("@group.v.calendar.google.com", "")}</label>
                                    {calendar.name.includes("group.v.calendar.google.com") &&
                                            <div className='mx-2 my-0 google-calendar-tooltip'>ℹ️</div>
                                    }
                                </div>
                            ))}
                        </Accordion.Body>
                    </Accordion.Item>
                </Accordion>
            </div>
            <Tooltip style={{zIndex: 999}} anchorSelect='.google-calendar-tooltip'>This is a Google generated calendar. <br></br>It is read-only, so events can be copied from it, but not to it.</Tooltip>
        </div>
    );
};

export default AccountCard;
