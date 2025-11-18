import { useToast } from '../contexts/ToastContext'
import { createErrorHandler } from '../services/api'

/**
 * Custom hook for comprehensive error handling throughout the app
 * Provides consistent error display, logging, and user feedback
 */
export const useErrorHandler = () => {
  const toastFunctions = useToast();
  return createErrorHandler(toastFunctions);
};

export default useErrorHandler;
