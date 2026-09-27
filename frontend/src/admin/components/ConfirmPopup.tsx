import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

type Props = {
  anchor: HTMLElement | null;
  text: string;
  confirmLabel: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

/** Small "Are you sure?" popover (the old .scp popup) anchored under a button. */
export function ConfirmPopup({ anchor, text, confirmLabel, danger, busy, onConfirm, onCancel }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  useLayoutEffect(() => {
    if (!anchor || !ref.current) return;
    const rect = anchor.getBoundingClientRect();
    setPos({ top: rect.bottom + window.scrollY + 6, left: Math.max(8, rect.right + window.scrollX - ref.current.offsetWidth) });
  }, [anchor]);

  useEffect(() => {
    if (!anchor) return;
    const close = (e: MouseEvent) => {
      const t = e.target as Node;
      if (!ref.current?.contains(t) && !anchor.contains(t)) onCancel();
    };
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onCancel();
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', esc);
    };
  }, [anchor, onCancel]);

  if (!anchor) return null;
  return createPortal(
    <div ref={ref} className={`scp${danger ? ' scp--danger' : ''}`} role="dialog" style={{ display: 'block', position: 'absolute', top: pos.top, left: pos.left }}>
      <p className="scp-text">{busy ? 'Видалення…' : text}</p>
      {!busy && (
        <div className="scp-btns">
          <button type="button" className={`scp-yes${danger ? ' scp-yes--danger' : ''}`} onClick={onConfirm}>
            {confirmLabel}
          </button>
          <button type="button" className="scp-no" onClick={onCancel}>
            Скасувати
          </button>
        </div>
      )}
    </div>,
    document.querySelector('.pg-admin') ?? document.body,
  );
}
