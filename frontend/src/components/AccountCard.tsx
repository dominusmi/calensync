import React, { useState } from 'react';
import API from '../utils/const';
import { Accordion } from 'react-bootstrap';
import { Tooltip } from 'react-tooltip'
import LoadingOverlay from './LoadingOverlay';

export interface Calendar {
    uuid: string;
    name: string;
}

export interface Account {
    uuid: string;
    key: string;
    calendars: Calendar[] | null;
}


const AccountCard: React.FC<{ account: Account }> = ({ account }) => {
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const refreshCalendars = async () => {
        setIsLoading(true);
        try { 
            const response = await fetch(
                `${API}/accounts/${account.uuid}/calendars/refresh`,
                {
                    credentials: 'include',
                    method: 'POST'
                }
            )
            if(response.ok){
                window.location.reload()
            }
        }finally{
            setIsLoading(false);
        }
    }

    return (
        <div className="container-sm card my-1 my-sm-2 py-3 shadow-sm rounded border-0 template account-row">
            { isLoading && 
                <LoadingOverlay/>
            }
            <div className="row mx-xs-0 mx-sm-2">
                <Accordion>
                    <Accordion.Item eventKey="0">
                        <Accordion.Header>
                            <div className="row my-2">
                                <div className="col-12">
                                    <h6 key={`${account.uuid}-title`} className="mb-1 email-value">{account.key}<span className='text-muted small'>'s Google calendars</span></h6>
                                </div>
                            </div>
                        </Accordion.Header>
                        <Accordion.Body>
                            <>
                                {account && account.calendars && account.calendars.map((calendar) => (
                                    <div className='d-flex' key={`${calendar.uuid}-div`}>
                                        <label className="form-check-label xs-small">{calendar.name.replace("@group.v.calendar.google.com", "")}</label>
                                        {calendar.name.includes("group.v.calendar.google.com") &&
                                            <div className='mx-2 my-0 google-calendar-tooltip'>ℹ️</div>
                                        }
                                    </div>
                                ))}
                                <button className='btn btn-primary mt-2' onClick={refreshCalendars}>Refresh Calendars</button>
                            </>

                        </Accordion.Body>
                    </Accordion.Item>
                </Accordion>
            </div>
            <Tooltip style={{ zIndex: 999 }} anchorSelect='.google-calendar-tooltip'>This is a Google generated calendar. <br></br>It is read-only, so events can be copied from it, but not to it.</Tooltip>
        </div>
    );
};

export default AccountCard;
