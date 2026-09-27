import { useEffect, useState } from 'react';
import type { MenuSauce } from '@/api/types';
import { useEscape, useScrollLock } from '@/hooks/useScrollLock';

export type PickedSauce = { id: number; name: string; qty: number };

type Props = {
  open: boolean;
  itemName: string;
  sauces: MenuSauce[];
  /** Called with the chosen sauces ([] when skipped or closed). */
  onDone: (sauces: PickedSauce[]) => void;
};

/** "Додати соус?" bottom sheet offered after adding pizza / fast food. */
export function SaucePicker({ open, itemName, sauces, onDone }: Props) {
  const [picked, setPicked] = useState<Record<number, number>>({});

  useEffect(() => {
    if (open) setPicked({});
  }, [open]);

  useScrollLock(open);
  useEscape(open, () => onDone([]));

  const toggle = (id: number) =>
    setPicked((p) => {
      const next = { ...p };
      if (next[id]) delete next[id];
      else next[id] = 1;
      return next;
    });
  const setQty = (id: number, qty: number) => setPicked((p) => ({ ...p, [id]: Math.max(1, Math.min(10, qty)) }));

  const confirm = () =>
    onDone(
      sauces.filter((s) => picked[s.id]).map((s) => ({ id: s.id, name: s.name, qty: picked[s.id] })),
    );

  return (
    <div
      className={`sm-overlay${open ? ' open' : ''}`}
      role="dialog"
      aria-modal="true"
      aria-hidden={!open}
      onClick={(e) => e.target === e.currentTarget && onDone([])}
    >
      <div className="sm-box">
        <div className="sm-head">
          <div>
            <div className="sm-title">Додати соус?</div>
            <div className="sm-subtitle">До: {itemName}</div>
          </div>
          <button className="sm-close" type="button" aria-label="Закрити" onClick={() => onDone([])}>
            ✕
          </button>
        </div>
        <div className="sm-list">
          {sauces.map((sc) => {
            const qty = picked[sc.id];
            return (
              <div key={sc.id} className={`sm-row${qty ? ' sm-row--on' : ''}`}>
                <button className="sm-toggle" type="button" onClick={() => toggle(sc.id)} aria-pressed={!!qty}>
                  {sc.image ? (
                    <img src={sc.image} className="sm-img" alt="" />
                  ) : (
                    <span className="sm-img sm-img--empty">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#c8b9a8" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>
                    </span>
                  )}
                  <span className="sm-name">{sc.name}</span>
                  <span className={`sm-price${sc.price <= 0 ? ' sm-price--free' : ''}`}>
                    {sc.price > 0 ? `+${Math.round(sc.price * (qty || 1))} ₴` : 'Безкоштовно'}
                  </span>
                </button>
                <div className="sm-check" onClick={() => toggle(sc.id)}>
                  <svg className="sm-check-icon" width="10" height="8" viewBox="0 0 10 8" fill="none"><path d="M1 4l3 3 5-6" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </div>
                <div className="sm-qty">
                  <button className="sm-qty-btn sm-minus" type="button" aria-label="Менше" onClick={() => setQty(sc.id, (qty || 1) - 1)}>
                    −
                  </button>
                  <span className="sm-qty-val">{qty || 1}</span>
                  <button className="sm-qty-btn sm-plus" type="button" aria-label="Більше" onClick={() => setQty(sc.id, (qty || 1) + 1)}>
                    +
                  </button>
                </div>
              </div>
            );
          })}
        </div>
        <div className="sm-footer">
          <button className="sm-skip" type="button" onClick={() => onDone([])}>
            Пропустити
          </button>
          <button className="sm-confirm" type="button" onClick={confirm}>
            Додати в кошик
          </button>
        </div>
      </div>
    </div>
  );
}
