import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';

type Kind = 'success' | 'error';
type Toast = { id: number; text: ReactNode; kind: Kind; shown: boolean; ms: number };
type Api = (text: ReactNode, kind?: Kind, ms?: number) => void;

const Ctx = createContext<Api>(() => {});

/** Stacking "admin-toast" notifications (styles in admin.css). */
export function AdminToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const show = useCallback<Api>((text, kind = 'success', ms = 3500) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, text, kind, shown: false, ms }]);
    requestAnimationFrame(() => requestAnimationFrame(() => setToasts((t) => t.map((x) => (x.id === id ? { ...x, shown: true } : x)))));
    window.setTimeout(() => {
      setToasts((t) => t.map((x) => (x.id === id ? { ...x, shown: false } : x)));
      window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 350);
    }, ms);
  }, []);
  return (
    <Ctx.Provider value={show}>
      {children}
      {toasts.map((t, i) => (
        <div key={t.id} className={`admin-toast ${t.kind}${t.shown ? ' show' : ''}`} role="status" style={{ bottom: 24 + i * 64, maxWidth: 380, lineHeight: 1.5 }}>
          {t.text}
        </div>
      ))}
    </Ctx.Provider>
  );
}

export const useAdminToast = () => useContext(Ctx);
