import React, { useEffect, useRef, useState } from 'react';
import { Account } from './AccountCard';
import { createToast } from './Toast';
import { MessageKind, refactorCalendarName, refreshPage, sleep } from '../utils/common';
import API from '../utils/const';
import LoadingOverlay from './LoadingOverlay';

const SyncRuleDraftRow: React.FC<{ accounts: Account[], state: boolean, setState: (x: boolean) => void}> = ({ accounts, state, setState }) => {
    const sourceRef = useRef<HTMLSelectElement | null>(null);
    const destinationRef = useRef<HTMLSelectElement | null>(null);
    const busyRef = useRef<HTMLInputElement | null>(null);
    const [loading, setLoading] = useState(false);

    async function createSyncRule(){
        setLoading(true);
        const source = sourceRef.current?.value;
        const destination = destinationRef.current?.value;
        const markAsPrivate = busyRef.current?.checked || false;

        try {
            if(source == null || destination == null){
                createToast("Invalid source or destination", MessageKind.Error);
                return
            }
            else if(source == destination){
                createToast("Source and destination must be different", MessageKind.Error);
                return
            }
            const response = await fetch(`${API}/sync`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json', 
                },
                body: JSON.stringify({
                    source_calendar_id: source,
                    destination_calendar_id: destination,
                    private: markAsPrivate
                })
            });

            const body = await response.json();
            if(!response.ok){
                let msg = "Error while creating sync rule";
                if(body.detail != null){
                    msg = body.detail
                }
                createToast(msg, MessageKind.Error);
                setLoading(false);
                return
            }
            refreshPage();
            await sleep(1000);
        } finally {
            setLoading(false);
        }
    }

    if(!state){
      return (<></>)
    }

    return (
        <div className='' key='test'>
            <div className='my-3 card px-sm-2 px-1'>
                { loading && <LoadingOverlay/> }
                <div className="d-flex-lg align-items-center my-2 my-lg-2">
                    <div className='row my-md-2'><span className="badge bg-secondary text-light ms-3 col-3 col-lg-1" style={{ maxWidth: "94px" }}>Draft</span></div>
                    <div className="btn-group pe-lg-2 col-12 col-lg-3 form-floating my-lg-0 my-2">
                        <select className="form-select" id="floatingSelect" aria-label="Floating label select example" ref={sourceRef} >
                            {accounts.map((a) => {
                                return (
                                    <React.Fragment key={`${a.uuid}-source-fragment`}>
                                        <option key={`${a.uuid}-source`} disabled={true}>{a.key}</option>
                                        {
                                            a.calendars?.map(c =>
                                                <option key={`${c.uuid}-source`} value={c.uuid}>{refactorCalendarName(c.name)}</option>
                                            )}
                                    </React.Fragment>
                                )
                            }
                            )}
                        </select>
                        <label className='' >Source calendar</label>
                    </div>
                    <div className="btn-group pe-lg-2 col-12 col-lg-3 form-floating my-lg-0 my-2">
                        <select className="form-select" id="floatingSelect" aria-label="Floating label select example" ref={destinationRef} >
                            {accounts.map((a) => {
                                return (
                                    <React.Fragment key={`${a.uuid}-destination-fragment`}>
                                        <option key={`${a.uuid}-destination`} disabled={true}>{a.key}</option>
                                        {
                                            a.calendars?.map(c =>
                                                <option key={`${c.uuid}-destination`} value={c.uuid}>{refactorCalendarName(c.name)}</option>
                                            )}
                                    </React.Fragment>
                                )
                            }
                            )}
                        </select>
                        <label className='' >Destinations calendar</label>
                    </div>
                    <div className="btn-group pe-lg-2 col-12 col-lg-4 my-lg-0 my-2" role="group" aria-label="Third group">
                        <div className="me-2 form-check px-4">
                            <input className="form-check-input" type="checkbox" value="" readOnly={true} ref={busyRef}/>
                            <label className="form-check-label text-start">
                                Replace event name with "Busy"
                            </label>
                        </div>
                    </div>
                    <div className="btn-group pe-lg-2 my-2 col-12 col-lg-1 my-lg-0 my-2" role="group" aria-label="Fourth group">
                        <button type="button" className="btn btn-primary" onClick={createSyncRule}>Save</button>
                    </div>
                    <div className="btn-group pe-lg-2 my-2 col-12 col-lg-1 my-lg-0 my-2" role="group" aria-label="Fourth group">
                        <button type="button" className="btn btn-outline-primary" onClick={() => setState(false)}>Cancel</button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SyncRuleDraftRow;