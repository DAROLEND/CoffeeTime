import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import { qk } from '@/api/queries';
import { useEscape, useScrollLock } from '@/hooks/useScrollLock';
import { usePresence } from '@/hooks/usePresence';
import {
  defaultSelection, pizzaUnitPrice, selectionFromVariant, variantDiff, variantPayload, type VariantSelection,
} from '../menu/menuLogic';
import { PizzaOptions } from '../menu/PizzaOptions';
import { VariantPicker } from '../menu/VariantPicker';

type Props = {
  index: number | null;
  onClose: () => void;
  onSave: (index: number, patch: { selected_size?: 'small' | 'large'; cheese_crust?: boolean; selected_variant?: string }) => Promise<boolean>;
};

/** "Change options" dialog for a cart line (pizza size/crust, filling, scoops). */
export function CartEditModal({ index, onClose, onSave }: Props) {
  const [shownIndex, setShownIndex] = useState<number | null>(index);
  const { mounted, visible, closing } = usePresence(index !== null);
  useEffect(() => {
    if (index !== null) setShownIndex(index);
  }, [index]);

  const item = useQuery({
    queryKey: qk.cartItem(shownIndex ?? -1),
    queryFn: () => unwrap(api.GET('/api/cart/items/{index}', { params: { path: { index: shownIndex! } } })),
    enabled: shownIndex !== null && index !== null,
    staleTime: 0,
  });
  const detail = item.data;

  const [size, setSize] = useState<'small' | 'large'>('small');
  const [crust, setCrust] = useState(false);
  const [selection, setSelection] = useState<VariantSelection>({ optionId: null, sizeLabel: null });
  const [sauceLabel, setSauceLabel] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!detail) return;
    setSize(detail.selected_size === 'large' ? 'large' : 'small');
    setCrust(detail.cheese_crust === 1);
    const stored = selectionFromVariant(detail.selected_variant);
    setSelection(stored.optionId ? stored : defaultSelection(detail.variant_options));
    setSauceLabel(stored.sauceLabel);
  }, [detail]);

  useScrollLock(index !== null);
  useEscape(index !== null, onClose);

  if (!mounted) return null;

  const isPizza = detail?.category === 'pizza_items' && detail.has_size_choice;
  const vo = detail?.variant_options ?? null;
  let price = detail?.unit_price ?? 0;
  if (detail && isPizza) price = pizzaUnitPrice({ price: detail.price, price_large: detail.price_large ?? 0 }, size, crust);
  else if (detail && vo) price = detail.price + variantDiff(vo, selection);

  const save = async () => {
    if (!detail || saving || shownIndex === null) return;
    setSaving(true);
    const patch = isPizza
      ? { selected_size: size, cheese_crust: crust }
      : { selected_variant: variantPayload(vo, selection, sauceLabel) ?? '' };
    const ok = await onSave(shownIndex, patch);
    setSaving(false);
    if (ok) onClose();
  };

  return (
    <div
      className={`item-modal-overlay${visible ? ' open' : ''}${closing ? ' closing' : ''}`}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-label="Змінити опції товару"
    >
      <div className="item-modal">
        <button className="item-modal-close" aria-label="Закрити" onClick={onClose}>
          &times;
        </button>
        <div className="im-img-col">{detail?.image && <img src={detail.image} alt={detail.name} />}</div>
        <div className="im-info-col">
          {!detail ? (
            <div className="cmd-loading">
              <div className="cmd-spinner" />
            </div>
          ) : (
            <>
              <h2 className="im-name">{detail.name}</h2>
              <p className="im-desc">{detail.desc}</p>
              <div className="im-divider" />
              {isPizza && (
                <PizzaOptions price={detail.price} priceLarge={detail.price_large ?? 0} size={size} crust={crust} onSize={setSize} onCrust={setCrust} />
              )}
              {!isPizza && vo && (
                <div className="ce-scoops-wrap">
                  <VariantPicker
                    options={vo}
                    basePrice={detail.price}
                    selection={selection}
                    onChange={setSelection}
                    sauceLabel={sauceLabel}
                    onSauceChange={setSauceLabel}
                  />
                </div>
              )}
              <span className="im-price">{Math.round(price)} ₴</span>
              <div className="im-footer">
                <button type="button" className="im-cancel-btn" onClick={onClose}>
                  Скасувати
                </button>
                <button type="button" className={`im-add-btn${saving ? ' saving' : ''}`} onClick={save} disabled={saving}>
                  {saving ? 'Збереження...' : 'Зберегти зміни'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
