import React, { useState } from 'react';
import { MessageKind, refactorCalendarName, refreshPage } from '../utils/common';
import API from '../utils/const';
import { createToast } from './Toast';
import { Button, Modal } from 'react-bootstrap';
import LoadingOverlay from './LoadingOverlay';
import { useTranslation } from 'react-i18next';

export interface SyncRule {
  source: string,
  destination: string,
  private: boolean,
  uuid: string
}

const SyncRuleRow: React.FC<{ rule: SyncRule }> = ({ rule}) => {
  const { t } = useTranslation(['app']);

  const [clickedDelete, setClickedDelete] = useState(false);
  const [loading, setLoading] = useState(false);

  async function deleteRule() {
    try{
      setLoading(true)
      const response = await fetch(
        `${API}/sync/${rule.uuid}`,
        {
          method: "DELETE",
          credentials: 'include'
        }
      )
      if (response.ok) {
        refreshPage()
      } else {
        const data = await response.json();
        if (data.detail) {
          createToast(data.detail, MessageKind.Error)
        } else {
          createToast("Error while deleting synchronization", MessageKind.Error)
        }
      }
      
    }finally{
      setLoading(false)
    }
  }

  return (
    <div className="card my-1">
      {loading && <LoadingOverlay />}
      <div className="d-flex flex-column flex-md-row align-items-md-center my-2 px-2 ps-4">
        <span className="badge bg-primary text-light mx-2my-sm-1 border" style={{ maxWidth: "94px" }}>Active</span>
        <div className="px-md-4 my-sm-1 my-2 pe-4">
          <div className='text-wrap'> {t("dashboard.sync.valid.from")} <span className='fw-bold'>{refactorCalendarName(rule.source)}</span> </div>
          <div className='text-wrap'>{t("dashboard.sync.valid.to")} <span className='fw-bold'>{refactorCalendarName(rule.destination)}</span></div>
        </div>
        <div className="me-md-auto mb-4 my-sm-1">
          <input className='form-check-input' type="checkbox" checked={rule.private} readOnly={true}></input>
          <label className='ps-1'>{t("dashboard.sync.valid.mark-busy")}</label>
        </div>
        <div className="ms-md-auto my-sm-1">
          <button type="button" className="btn btn-outline-danger" onClick={()=>setClickedDelete(true)}>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-trash" viewBox="0 0 16 16">
              <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z" />
              <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z" />
            </svg>
          </button>
        </div>
      </div>
        <Modal
          show={clickedDelete===true}
          onHide={() => setClickedDelete(false)}
          size="lg"
          aria-labelledby="contained-modal-title-vcenter"
          centered
        >
          <Modal.Header closeButton>
            <Modal.Title id="contained-modal-title-vcenter">
            {t("dashboard.sync.valid.are-you-sure")}
            </Modal.Title>
          </Modal.Header>
          <Modal.Body className=''>
            <p>
            {t("dashboard.sync.valid.delete-info")}
            </p>
          </Modal.Body>
          <Modal.Footer>
            <Button onClick={() => {setClickedDelete(false); deleteRule()}} variant='danger'>Delete</Button>
            <Button onClick={() => setClickedDelete(false)} variant='secondary'>Cancel</Button>
          </Modal.Footer>
        </Modal>
    </div>
  );
};

export default SyncRuleRow;