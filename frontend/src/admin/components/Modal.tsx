import type { CSSProperties, ReactNode } from 'react';
import { useEscape, useScrollLock } from '@/hooks/useScrollLock';

/**
 * The admin ".modal-overlay" dialog. It stays mounted so the CSS
 * open/close transition plays; a backdrop click or Esc closes it.
 */
export function AdminModal({
  open,
  onClose,
  className = 'modal',
  style,
  label,
  children,
}: {
  open: boolean;
  onClose: () => void;
  className?: string;
  style?: CSSProperties;
  label?: string;
  children: ReactNode;
}) {
  // Esc inside the photo cropper closes only the cropper.
  useEscape(open, () => !document.getElementById('imgCropModal') && onClose());
  useScrollLock(open);
  return (
    <div className={`modal-overlay${open ? ' open' : ''}`} onMouseDown={(e) => e.target === e.currentTarget && onClose()} aria-hidden={!open}>
      <div className={className} style={style} role="dialog" aria-modal="true" aria-label={label}>
        {children}
      </div>
    </div>
  );
}
