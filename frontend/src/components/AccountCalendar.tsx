import React, { useEffect, useState } from 'react';
import { Calendar } from './AccountCard';
import API from '../utils/const';
import { get_session_id } from '../utils/session';
import axios from 'axios';

const AccountCalendar: React.FC<{calendar: Calendar}> = ({calendar}) => {
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
                            Authorization: get_session_id()!,
                            'Content-Type': 'application/json',
                        },
                    }
                );
                calendar.active = !isChecked
                setChecked(!isChecked);
            } catch (error: any) {
                // Handle error if needed
                console.error('Error updating backend:', error?.message);
            }

        }

        updateBackend(calendar.uuid, kind);
    };

    useEffect(() => {
        console.log("checked")
        // Update the local state when the calendar prop changes
        setChecked(calendar.active);
      }, [calendar.active]);

    return (
        <div key={calendar.uuid} className="row row-cols-12 row-cols-xs-9 template calendar-row my-1">
            <div className="col-md-1 form-check form-switch">
                <input className="form-check-input" type="checkbox" role="switch" id="flexSwitchCheckDefault"
                    checked={calendar.active}
                    onChange={updateChecked}
                />
            </div>
            <div className="col-md-11 p-0 name-value">{calendar.name}</div>

        </div>
    );
    return (
        <div></div>
    )
};

export default AccountCalendar;
