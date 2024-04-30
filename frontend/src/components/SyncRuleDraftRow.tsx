import React, { useRef, useState } from 'react';
import { Account } from './AccountCard';
import { createToast } from './Toast';
import { MessageKind, refactorCalendarName, refreshPage, sleep } from '../utils/common';
import API from '../utils/const';
import LoadingOverlay from './LoadingOverlay';
import { useTranslation } from 'react-i18next';
import { Accordion } from 'react-bootstrap';


const SyncRuleDraftRow: React.FC<{ accounts: Account[], setState: (x: boolean) => void, successCallback: () => void }> = ({ accounts, setState, successCallback }) => {
    const { t } = useTranslation(['app']);

    const sourceRef = useRef<HTMLSelectElement | null>(null);
    const destinationRef = useRef<HTMLSelectElement | null>(null);
    const [summary, setSummary] = useState("%original%");
    const [description, setDescription] = useState("%original%");
    const [loading, setLoading] = useState(false);

    async function createSyncRule() {
        setLoading(true);
        const source = sourceRef.current?.value;
        const destination = destinationRef.current?.value;

        try {
            if (source == null || destination == null) {
                createToast("Invalid source or destination", MessageKind.Error);
                return
            }
            else if (source === destination) {
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
                    summary: summary,
                    description: description
                })
            });

            const body = await response.json();
            if (!response.ok) {
                let msg = "Error while creating sync rule";
                if (body.detail != null) {
                    msg = body.detail
                }
                createToast(msg, MessageKind.Error);
                setLoading(false);
                return
            }
            successCallback();
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className='' key='test'>
            <div className='my-3 card px-sm-2 px-1'>
                {loading && <LoadingOverlay />}
                <div className="d-flex-lg align-items-center my-2 my-lg-2">
                    <div className='row my-md-2'><span className="badge bg-secondary text-light ms-3 col-3 col-lg-1" style={{ maxWidth: "94px" }}>Draft</span></div>
                    <div className="btn-group pe-lg-2 col-12 col-lg-3 form-floating my-lg-0 my-2">
                        <select className="form-select" aria-label="Floating label select example" ref={sourceRef} >
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
                        <label className='' >{t("dashboard.sync.draft.source")}</label>
                    </div>
                    <div className="btn-group pe-lg-2 col-12 col-lg-3 form-floating my-lg-0 my-2">
                        <select className="form-select" aria-label="Floating label select example" ref={destinationRef} >
                            {accounts.map((a) => {
                                return (
                                    <React.Fragment key={`${a.uuid}-destination-fragment`}>
                                        <option key={`${a.uuid}-destination`} disabled={true}>{a.key}</option>
                                        {
                                            a.calendars?.filter(c => !c.readonly).map(c =>
                                                <option key={`${c.uuid}-destination`} value={c.uuid}>{refactorCalendarName(c.name)}</option>
                                            )}
                                    </React.Fragment>
                                )
                            }
                            )}
                        </select>
                        <label className='' >{t("dashboard.sync.draft.destination")}</label>
                    </div>
                    <Accordion className='my-3'>
                        <Accordion.Item eventKey="0">
                            <Accordion.Header className='px-0 mx-0'><span className='text-primary'>{t("dashboard.sync.customize-event-template")}</span></Accordion.Header>
                            <Accordion.Body>
                                <div>
                                    <div className="form-group my-3">
                                        <label>Title template</label>
                                        <div>
                                            <input type="text" className="form-control" id="exampleInputEmail1" value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="How to replace the title? use the magic word %original% to use the real event title" />
                                        </div>
                                        <small><span dangerouslySetInnerHTML={{"__html": t("dashboard.sync.example-title")}}></span><span className='fw-bold'>{summary.replace("%original%", "Birthday party")}</span></small>
                                    </div>
                                </div>
                                <div>
                                    <div className="form-group my-3">
                                        <label>Description template</label>
                                        <input type="text" className="form-control" id="exampleInputEmail1" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="How to replace the description? use the magic word %original% to use the real event title" />
                                        <small><span dangerouslySetInnerHTML={{"__html": t("dashboard.sync.example-description")}}></span> <span className='fw-bold'>{description.replace("%original%", "Let's all meet together for Tom's birthday")}</span></small>
                                    </div>
                                </div>
                            </Accordion.Body>
                        </Accordion.Item>
                    </Accordion>
                    <div className="btn-group pe-lg-2 my-2 col-12 col-lg-1 my-lg-0 my-2" role="group" aria-label="Fourth group">
                        <button type="button" className="btn btn-primary" onClick={createSyncRule}>{t("common.save")}</button>
                    </div>
                    <div className="btn-group pe-lg-2 my-2 col-12 col-lg-1 my-lg-0 my-2" role="group" aria-label="Fourth group">
                        <button type="button" className="btn btn-outline-primary" onClick={() => setState(false)}>{t("common.cancel")}</button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SyncRuleDraftRow;