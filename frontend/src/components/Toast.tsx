import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';

type ToastApi = (message: string) => void;

const ToastContext = createContext<ToastApi>(() => {});

/** The site-wide "ct-toast" (styles in animations.css). */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('');
  const [visible, setVisible] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  const show = useCallback<ToastApi>((msg) => {
    setMessage(msg);
    setVisible(true);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setVisible(false), 2200);
  }, []);

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div className={`ct-toast${visible ? ' show' : ''}`} role="status" aria-live="polite">
        {message}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  return useContext(ToastContext);
}
