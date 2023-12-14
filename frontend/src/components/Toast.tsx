import React, { useEffect } from 'react';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { MessageKind } from '../utils/common';

export function createToast(message: string, kind: MessageKind) {
  let f = toast.info;
  if(kind == MessageKind.Error){
    f = toast.error;
  }else if(kind == MessageKind.Success){
    f = toast.success;
  }

  f(message, {
    position: 'top-right',
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
  });
}


const Toast: React.FC<{onReady: () => void}> = ({ onReady }) => {
  useEffect(() => {
    onReady();
  }, [onReady]);
  return (
    <div>
      <ToastContainer />
    </div>
  );
};

export default Toast;