// src/components/Toast.jsx
import { toast, ToastContainer as Container } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Custom styles for toast to match website theme
const toastStyles = {
  background: 'linear-gradient(135deg, rgba(255, 106, 0, 0.15), rgba(20, 184, 166, 0.15))',
  backdropFilter: 'blur(10px)',
  border: '1px solid rgba(255, 106, 0, 0.3)',
  borderRadius: '12px',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(255, 106, 0, 0.1)',
  color: '#FFFFFF',
  fontFamily: 'Inter, sans-serif',
  padding: '16px 24px',
  minWidth: '300px',
  maxWidth: '500px',
};

// Progress bar colors based on toast type
const progressColors = {
  success: 'linear-gradient(90deg, #4ADE80, #22D3EE)',
  error: 'linear-gradient(90deg, #FF6A00, #FF4444)',
  warning: 'linear-gradient(90deg, #FAB51B, #FF6A00)',
  info: 'linear-gradient(90deg, #14B8A6, #4ADE80)',
  default: 'linear-gradient(90deg, #FF6A00, #14B8A6)',
};

// Toast Container Component - Centered
export const ToastContainer = () => {
  return (
    <Container
      position="top-center"
      autoClose={3000}
      hideProgressBar={false}
      newestOnTop={false}
      closeOnClick
      rtl={false}
      pauseOnFocusLoss
      draggable
      pauseOnHover
      theme="dark"
      style={{ zIndex: 99999 }}
      progressStyle={{
        background: 'linear-gradient(90deg, #FF6A00, #14B8A6)',
        height: '3px',
        borderRadius: '0 0 12px 12px',
      }}
      toastStyle={toastStyles}
      bodyClassName="custom-toast-body"
    />
  );
};

// Toast functions with custom styling and progress colors
export const showToast = {
  success: (message, options = {}) => {
    return toast.success(message, {
      icon: '✅',
      style: {
        ...toastStyles,
        border: '1px solid rgba(74, 222, 128, 0.4)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(74, 222, 128, 0.15)',
      },
      progressStyle: {
        background: progressColors.success,
        height: '3px',
        borderRadius: '0 0 12px 12px',
        transition: 'width 0.3s ease-in-out',
      },
      ...options,
    });
  },
  error: (message, options = {}) => {
    return toast.error(message, {
      icon: '❌',
      style: {
        ...toastStyles,
        border: '1px solid rgba(255, 82, 82, 0.4)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(255, 82, 82, 0.15)',
      },
      progressStyle: {
        background: progressColors.error,
        height: '3px',
        borderRadius: '0 0 12px 12px',
        transition: 'width 0.3s ease-in-out',
      },
      ...options,
    });
  },
  warning: (message, options = {}) => {
    return toast.warning(message, {
      icon: '⚠️',
      style: {
        ...toastStyles,
        border: '1px solid rgba(250, 181, 27, 0.4)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(250, 181, 27, 0.15)',
      },
      progressStyle: {
        background: progressColors.warning,
        height: '3px',
        borderRadius: '0 0 12px 12px',
        transition: 'width 0.3s ease-in-out',
      },
      ...options,
    });
  },
  info: (message, options = {}) => {
    return toast.info(message, {
      icon: 'ℹ️',
      style: {
        ...toastStyles,
        border: '1px solid rgba(20, 184, 166, 0.4)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(20, 184, 166, 0.15)',
      },
      progressStyle: {
        background: progressColors.info,
        height: '3px',
        borderRadius: '0 0 12px 12px',
        transition: 'width 0.3s ease-in-out',
      },
      ...options,
    });
  },
  default: (message, options = {}) => {
    return toast(message, {
      style: toastStyles,
      progressStyle: {
        background: progressColors.default,
        height: '3px',
        borderRadius: '0 0 12px 12px',
        transition: 'width 0.3s ease-in-out',
      },
      ...options,
    });
  },
  loading: (message, options = {}) => {
    return toast.loading(message, {
      icon: '⏳',
      style: {
        ...toastStyles,
        border: '1px solid rgba(20, 184, 166, 0.3)',
      },
      progressStyle: {
        background: 'linear-gradient(90deg, #14B8A6, #22D3EE)',
        height: '3px',
        borderRadius: '0 0 12px 12px',
        animation: 'progress-pulse 1.5s ease-in-out infinite',
      },
      ...options,
    });
  },
  dismiss: (toastId) => toast.dismiss(toastId),
  promise: (promise, messages, options = {}) => {
    return toast.promise(promise, messages, {
      style: toastStyles,
      progressStyle: {
        background: progressColors.default,
        height: '3px',
        borderRadius: '0 0 12px 12px',
        transition: 'width 0.3s ease-in-out',
      },
      ...options,
    });
  },
  update: (toastId, options) => {
    // Determine progress color based on type
    let progressColor = progressColors.default;
    if (options.type === 'success') progressColor = progressColors.success;
    else if (options.type === 'error') progressColor = progressColors.error;
    else if (options.type === 'warning') progressColor = progressColors.warning;
    else if (options.type === 'info') progressColor = progressColors.info;

    return toast.update(toastId, {
      style: toastStyles,
      progressStyle: {
        background: progressColor,
        height: '3px',
        borderRadius: '0 0 12px 12px',
        transition: 'width 0.3s ease-in-out',
      },
      ...options,
    });
  },
};

// Quick usage shortcuts
export const toastSuccess = showToast.success;
export const toastError = showToast.error;
export const toastWarning = showToast.warning;
export const toastInfo = showToast.info;

export default showToast;