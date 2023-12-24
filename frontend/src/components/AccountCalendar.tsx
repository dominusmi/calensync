import React, { useEffect, useState } from 'react';
import { Calendar } from './AccountCard';
import API from '../utils/const';
import { getLocalSession } from '../utils/session';
import axios from 'axios';
import { createToast } from './Toast';
import { MessageKind } from '../utils/common';
import { Tooltip } from 'react-tooltip'

const AccountCalendar: React.FC<{ calendar: Calendar }> = ({ calendar }) => {
    const [isChecked, setChecked] = useState(calendar.active);

    const updateChecked = async () => {
        const kind = isChecked ? 'deactivate' : 'activate';

        const updateBackend = async (uuid: string, kind: string) => {
            try {
                const response = await axios.patch(
                    `${API}/calendars/${uuid}`,
                    { kind },
                    {
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        withCredentials: true
                    },
                );
                calendar.active = !isChecked
                if (calendar.active) {
                    createToast("The synchronization has begun! You should see the events within 30 seconds", MessageKind.Success);
                }
                else {
                    createToast("Succesfully un-synced calendar", MessageKind.Success);
                }
                setChecked(!isChecked);
            } catch (error: any) {
                // Handle error if needed
                console.error('Error updating backend:', error?.message);
            }

        }

        updateBackend(calendar.uuid, kind);
    };

    useEffect(() => {
        // Update the local state when the calendar prop changes
        setChecked(calendar.active);
    }, [calendar.active]);

    return (

        <div key={calendar.uuid} className="row row-cols-12 row-cols-xs-9 calendar-row my-1 overflow-auto text-break">
            <div className="col pl-1 d-flex">
                <div className='form-check form-switch'>
                    <input className="form-check-input" type="checkbox" role="switch" id="flexSwitchCheckDefault"
                        checked={calendar.active}
                        onChange={updateChecked}
                    />
                </div>
                <label className="form-check-label xs-small">{calendar.name.replace("@group.v.calendar.google.com", "")}</label>
                {calendar.name.includes("group.v.calendar.google.com") &&
                    <div>
                        <p className='mx-2 my-0 google-calendar'>ℹ️</p>
                    </div>
                }
            </div>
            <Tooltip anchorSelect='.google-calendar'>This is a Google generated calendar. <br></br>It is read-only, so events can be copied from it, but not to it.</Tooltip>
        </div>
    );
    return (
        <div></div>
    )
};

export default AccountCalendar;
