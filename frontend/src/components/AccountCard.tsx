import React, { useState } from 'react';
import API from '../utils/const';
import { Accordion } from 'react-bootstrap';
import { Tooltip } from 'react-tooltip'
import LoadingOverlay from './LoadingOverlay';
import { useTranslation } from 'react-i18next';
import { ActionIcon, Flex, Button } from '@mantine/core';
import { IconReload } from '@tabler/icons-react';
import { handleApiError } from '../utils/app';
import { createToast } from './Toast';
import { MessageKind } from '../utils/common';

export interface Calendar {
    uuid: string;
    name: string;
    readonly: boolean;
}

export interface Account {
    uuid: string;
    key: string;
    calendars: Calendar[] | null;
}


const AccountCard: React.FC<{ account: Account }> = ({ account }) => {
    const { t } = useTranslation(['app']);
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
            if (response.ok) {
                window.location.reload()
            }
        } finally {
            setIsLoading(false);
        }
    }

    const refreshCalendarEvents = async (calendar_uuid: string) => {
        setIsLoading(true);
        try {
            const response = await fetch(
                `${API}/calendars/${calendar_uuid}/resync`,
                {
                    credentials: 'include',
                    method: 'POST'
                }
            )
            if (response.ok) {
                createToast("All rules that use this calendar are going to be refreshed.", MessageKind.Info);
            } else{
                handleApiError(response, t)
            }
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <div className="container-sm card my-1 my-sm-2 py-3 shadow-sm rounded border-0 template account-row">
            {isLoading &&
                <LoadingOverlay />
            }
            <div className="row mx-xs-0 mx-sm-2">
                <Accordion>
                    <Accordion.Item eventKey="0">
                        <Accordion.Header>
                            <div className="d-flex justify-content-between align-items-center my-2">
                                <h6 key={`${account.uuid}-title`} className="mb-1 email-value">
                                    {account.key}<span className='text-muted small'> 's Google calendars</span>
                                </h6>
                            </div>
                        </Accordion.Header>
                        <Accordion.Body>
                            <Flex direction='column'>
                                <div className='mb-3'>
                                    <button className='btn btn-primary ' onClick={refreshCalendars}>
                                        {t("dashboard.refresh-calendars")}
                                    </button>
                                </div>
                                {account && account.calendars && account.calendars.map((calendar) => (
                                    <Flex direction={{base: 'column', md: 'row'}} key={`${calendar.uuid}-div`} align='start' mb='md' justify={{base: 'left', md: 'space-between'}}>
                                        <label className="form-check-label xs-small">{calendar.name.replace("@group.v.calendar.google.com", "")}</label>
                                        {calendar.name.includes("group.v.calendar.google.com") &&
                                            <div className='mx-2 my-0 google-calendar-tooltip'>ℹ️</div>
                                        }
                                        <button className='btn btn-primary' onClick={() => refreshCalendarEvents(calendar.uuid)} >
                                            <IconReload stroke={1} /> {t("dashboard.refresh-events")}
                                        </button>
                                    </Flex>
                                ))}
                            </Flex>

                        </Accordion.Body>
                    </Accordion.Item>
                </Accordion>
            </div>
            <Tooltip style={{ zIndex: 999 }} anchorSelect='.google-calendar-tooltip'>This is a Google generated calendar. <br></br>It is read-only, so events can be copied from it, but not to it.</Tooltip>
        </div>
    );
};

export default AccountCard;
