import { useEffect } from 'react';

type Props = {
  open: boolean;
  title: string;
  options: string[];
  onPick: (label: string) => void;
  onClose: () => void;
};

/**
 * Small toast-like picker for fast food that comes with a free sauce
 * choice: the item is added right away, and the pick updates that cart
 * line. Hides itself after 8 s.
 */
export function SaucePopup({ open, title, options, onPick, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(onClose, 8000);
    return () => window.clearTimeout(t);
  }, [open, onClose]);

  return (
    <div className={`sauce-popup${open ? ' show' : ''}`} aria-hidden={!open}>
      <div className="sp-header">
        <span className="sp-title">{title || 'Оберіть соус'}</span>
        <button className="sp-close" aria-label="Закрити" onClick={onClose}>
          ✕
        </button>
      </div>
      <div className="sp-options">
        {options.map((opt) => (
          <button key={opt} className="sp-option-btn" onClick={() => onPick(opt)}>
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}
