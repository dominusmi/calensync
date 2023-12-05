import React from 'react';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

export function toast_success(message: string) {
    toast.success(message, {
        position: 'top-right',
        autoClose: 3000,
        hideProgressBar: false,
        closeOnClick: true,
        pauseOnHover: true,
        draggable: true,
      });
}

export function toast_error(message: string) {
    toast.error(message, {
        position: 'top-right',
        autoClose: 3000,
        hideProgressBar: false,
        closeOnClick: true,
        pauseOnHover: true,
        draggable: true,
      });
}

const Toast = () => {

  return (
    <div>
      <ToastContainer />
    </div>
  );
};

export default Toast;