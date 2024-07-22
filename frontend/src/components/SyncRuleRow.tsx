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
  uuid: string,
  summary: string,
  description: string
}

const SyncRuleRow: React.FC<{ rule: SyncRule, onChange: () => void }> = ({ rule, onChange }) => {
  const { t } = useTranslation(['app']);

  const [clickedDelete, setClickedDelete] = useState(false);
  const [clickedUpdate, setClickedUpdate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [deletionInProcess, _] = useState(sessionStorage.getItem(`rule-delete-${rule.uuid}`) != null)
  const [summary, setSummary] = useState(rule.summary);
  const [description, setDescription] = useState(rule.description);


  async function deleteRule() {
    try {
      setLoading(true)
      const response = await fetch(
        `${API}/sync/${rule.uuid}`,
        {
          method: "DELETE",
          credentials: 'include'
        }
      )
      if (response.ok) {
        createToast("Your rule has been set for deletion. This can take a few minutes to complete.", MessageKind.Info)
        sessionStorage.setItem(`rule-delete-${rule.uuid}`, 'true')
        onChange();
      } else {
        const data = await response.json();
        if (data.detail) {
          createToast(data.detail, MessageKind.Error)
        } else {
          createToast("Error while deleting synchronization", MessageKind.Error)
        }
      }

    } finally {
      setLoading(false)
    }
  }

  async function updateRule() {
    if (rule.description == description && rule.summary == summary) {
      return
    }
    try {
      setLoading(true)
      const response = await fetch(
        `${API}/sync/${rule.uuid}`,
        {
          method: "PATCH",
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            summary: summary,
            description: description
          })
        }
      )
      if (response.ok) {
        createToast("Your rule is being updated. This can take a few minutes to complete.", MessageKind.Info)
        onChange();
      } else {
        const data = await response.json();
        if (data.detail) {
          createToast(data.detail, MessageKind.Error)
        } else {
          createToast("Error while updating synchronization", MessageKind.Error)
        }
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card my-1">
      {loading && <LoadingOverlay />}
      <div className="d-flex flex-column flex-md-row align-items-md-center my-2 px-2 ps-4">
        <span className="badge bg-primary text-light mx-2my-sm-1 border" style={{ maxWidth: "94px" }}>Active</span>
        <div className="px-md-4 my-sm-1 my-2 pe-4">
          {deletionInProcess &&
            <div className='text-wrap'>[Rule set to be deleted]</div>
          }
          <div className='text-wrap'> {t("dashboard.sync.valid.from")} <span className='fw-bold'>{refactorCalendarName(rule.source)}</span> </div>
          <div className='text-wrap'>{t("dashboard.sync.valid.to")} <span className='fw-bold'>{refactorCalendarName(rule.destination)}</span></div>
        </div>
        <div className="me-md-auto mb-4 my-sm-1 ps-2">
          {rule.summary !== "%original%" &&
            <div className='text-wrap'>Custom title template: <span className='fw-bold'>{rule.summary}</span> </div>
          }
          {(rule.description != null && rule.summary !== "%original%") &&
            <div className='text-wrap'>Custom description template: <span className='fw-bold'>{rule.description}</span> </div>
          }
        </div>
        <div className="ms-md-auto my-sm-1">
          <button type="button" className="btn btn-outline-primary me-1" onClick={() => setClickedUpdate(true)}>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-tools" viewBox="0 0 16 16">
              <path d="M1 0 0 1l2.2 3.081a1 1 0 0 0 .815.419h.07a1 1 0 0 1 .708.293l2.675 2.675-2.617 2.654A3.003 3.003 0 0 0 0 13a3 3 0 1 0 5.878-.851l2.654-2.617.968.968-.305.914a1 1 0 0 0 .242 1.023l3.27 3.27a.997.997 0 0 0 1.414 0l1.586-1.586a.997.997 0 0 0 0-1.414l-3.27-3.27a1 1 0 0 0-1.023-.242L10.5 9.5l-.96-.96 2.68-2.643A3.005 3.005 0 0 0 16 3q0-.405-.102-.777l-2.14 2.141L12 4l-.364-1.757L13.777.102a3 3 0 0 0-3.675 3.68L7.462 6.46 4.793 3.793a1 1 0 0 1-.293-.707v-.071a1 1 0 0 0-.419-.814zm9.646 10.646a.5.5 0 0 1 .708 0l2.914 2.915a.5.5 0 0 1-.707.707l-2.915-2.914a.5.5 0 0 1 0-.708M3 11l.471.242.529.026.287.445.445.287.026.529L5 13l-.242.471-.026.529-.445.287-.287.445-.529.026L3 15l-.471-.242L2 14.732l-.287-.445L1.268 14l-.026-.529L1 13l.242-.471.026-.529.445-.287.287-.445.529-.026z" />
            </svg>
          </button>
          <button type="button" className="btn btn-outline-danger" onClick={() => setClickedDelete(true)}>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-trash" viewBox="0 0 16 16">
              <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z" />
              <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z" />
            </svg>
          </button>
        </div>
      </div>
      <Modal
        show={clickedDelete === true}
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
          <Button onClick={() => { setClickedDelete(false); deleteRule() }} variant='danger'>Delete</Button>
          <Button onClick={() => setClickedDelete(false)} variant='secondary'>Cancel</Button>
        </Modal.Footer>
      </Modal>
      <Modal
        show={clickedUpdate === true}
        onHide={() => setClickedUpdate(false)}
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
          <div>
            <span dangerouslySetInnerHTML={{ "__html": t("dashboard.sync.valid.update-info") }}></span>
            <div>
              <div className="form-group my-3">
                <label>{t("dashboard.sync.label-custom-title")}</label>
                <div>
                  <input type="text" className="form-control" id="exampleInputEmail1" value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="How to replace the title? use the magic word %original% to use the real event title" />
                </div>
                <small><span dangerouslySetInnerHTML={{ "__html": t("dashboard.sync.example-title") }}></span><span className='fw-bold'>{summary.replace("%original%", "Birthday party")}</span></small>
              </div>
            </div>
            <div>
              <div className="form-group my-3">
                <label>{t("dashboard.sync.label-custom-description")}</label>
                <input type="text" className="form-control" id="exampleInputEmail1" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="How to replace the description? use the magic word %original% to use the real event title" />
                <small><span dangerouslySetInnerHTML={{ "__html": t("dashboard.sync.example-description") }}></span> <span className='fw-bold'>{description.replace("%original%", "Let's all meet together for Tom's birthday")}</span></small>
              </div>
            </div>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button onClick={() => { setClickedUpdate(false); updateRule() }} variant='primary'>{t("common.save")}</Button>
          <Button onClick={() => setClickedUpdate(false)} variant='secondary'>Cancel</Button>
        </Modal.Footer>
      </Modal>
    </div >
  );
};

export default SyncRuleRow;