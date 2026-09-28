import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import type { AddToCartRequest, MenuCard } from '@/api/types';
import { useEscape, useScrollLock } from '@/hooks/useScrollLock';
import { usePresence } from '@/hooks/usePresence';
import { defaultSelection, fmtWeight, pizzaUnitPrice, stepWeight, variantDiff, variantPayload, type VariantSelection } from './menuLogic';
import { PizzaOptions } from './PizzaOptions';
import { VariantPicker } from './VariantPicker';

type Props = {
  card: MenuCard | null;
  inCart: boolean;
  onClose: () => void;
  /** Resolves true when the item was added. */
  onAdd: (request: AddToCartRequest, card: MenuCard) => Promise<boolean>;
};

function PriceTag({ value }: { value: number }) {
  // Brief yellow "pulse" when the price changes.
  const [flash, setFlash] = useState(false);
  useEffect(() => {
    setFlash(true);
    const t = window.setTimeout(() => setFlash(false), 250);
    return () => window.clearTimeout(t);
  }, [value]);
  return (
    <span className="im-price" style={{ transform: flash ? 'scale(1.08)' : 'scale(1)', color: flash ? '#FFC107' : '#8B4513' }}>
      {Math.round(value)} ₴
    </span>
  );
}

export function ItemModal({ card: openCard, inCart, onClose, onAdd }: Props) {
  const navigate = useNavigate();
  // Keep showing the last card while the close animation plays.
  const [card, setCard] = useState<MenuCard | null>(openCard);
  const { mounted, visible, closing } = usePresence(!!openCard);
  const [qty, setQty] = useState(1);
  const [weight, setWeight] = useState(1);
  const [size, setSize] = useState<'small' | 'large'>('small');
  const [crust, setCrust] = useState(false);
  const [selection, setSelection] = useState<VariantSelection>({ optionId: null, sizeLabel: null });
  const [sauceLabel, setSauceLabel] = useState<string | null>(null);
  const [state, setState] = useState<'idle' | 'saving' | 'added'>('idle');

  useEffect(() => {
    if (!openCard) return;
    setCard(openCard);
    setQty(1);
    setWeight(openCard.min_weight ?? 1);
    setSize('small');
    setCrust(false);
    setSelection(defaultSelection(openCard.variant_options));
    setSauceLabel(null);
    setState('idle');
  }, [openCard]);

  useScrollLock(!!openCard);
  useEscape(!!openCard, onClose);

  if (!mounted || !card) return null;

  const isCake = card.category === 'cake_items';
  const isSizedPizza = card.is_pizza && card.has_size;
  const vo = card.variant_options ?? null;
  const pricePerKg = card.price_per_kg ?? card.price;
  const minWeight = card.min_weight ?? 1;

  let total: number;
  if (isCake) total = pricePerKg * weight;
  else if (isSizedPizza) total = pizzaUnitPrice(card, size, crust) * qty;
  else total = (card.price + variantDiff(vo, selection)) * qty;

  // Items without choices just show "in cart"; anything with choices can
  // always be added again (a different size/filling is a different line).
  const hasChoices = isCake || isSizedPizza || (!!vo && vo.type !== 'sauce');
  const showInCart = state === 'added' || (inCart && !hasChoices);

  const submit = async () => {
    if (state !== 'idle') return;
    if (showInCart) {
      navigate('/cart');
      return;
    }
    const request: AddToCartRequest = { category: card.category, id: card.id, quantity: isCake ? 1 : qty };
    if (isCake) request.weight = weight;
    if (isSizedPizza) {
      request.selected_size = size;
      request.cheese_crust = crust;
    }
    const variant = variantPayload(vo, selection, sauceLabel);
    if (variant) request.selected_variant = variant;

    setState('saving');
    const ok = await onAdd(request, card);
    setState(ok ? 'added' : 'idle');
  };

  const buttonText = state === 'added' ? '✓ Додано!' : showInCart ? 'В кошику ✓' : isCake ? 'Замовити' : 'Додати в кошик';

  return (
    <div
      className={`item-modal-overlay${visible ? ' open' : ''}${closing ? ' closing' : ''}`}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="imModalName"
    >
      <div className="item-modal">
        <button className="item-modal-close" aria-label="Закрити" onClick={onClose}>
          ✕
        </button>
        <div className="im-img-col">{card.image && <img src={card.image} alt={card.name} />}</div>
        <div className="im-info-col">
          <span className="im-cat-badge">{card.label}</span>
          <h2 className="im-name" id="imModalName">
            {card.name}
          </h2>
          <p className="im-desc">{card.description}</p>
          <div className="im-divider" />

          {isSizedPizza && (
            <PizzaOptions price={card.price} priceLarge={card.price_large} size={size} crust={crust} onSize={setSize} onCrust={setCrust} />
          )}
          {vo && card.category !== 'pizza_items' && (
            <VariantPicker
              options={vo}
              basePrice={card.price}
              selection={selection}
              onChange={setSelection}
              sauceLabel={sauceLabel}
              onSauceChange={setSauceLabel}
            />
          )}

          <PriceTag value={total} />
          <div className="im-footer">
            {isCake ? (
              <div className="im-weight-wrap" style={{ display: 'flex' }}>
                <label className="im-weight-label">Вага (кг):</label>
                <div className="im-qty">
                  <button type="button" className="im-qty-btn" aria-label="Менше" onClick={() => setWeight((w) => stepWeight(w, -0.5, minWeight))}>
                    −
                  </button>
                  <span className="im-qty-val">{fmtWeight(weight)}</span>
                  <button type="button" className="im-qty-btn" aria-label="Більше" onClick={() => setWeight((w) => stepWeight(w, 0.5, minWeight))}>
                    +
                  </button>
                </div>
                <span className="im-weight-total">
                  {fmtWeight(weight)} кг × {pricePerKg} грн/кг = {Math.round(total)} грн
                </span>
              </div>
            ) : (
              <div className="im-qty">
                <button type="button" className="im-qty-btn" aria-label="Менше" onClick={() => setQty((q) => Math.max(1, q - 1))}>
                  −
                </button>
                <span className="im-qty-val">{qty}</span>
                <button type="button" className="im-qty-btn" aria-label="Більше" onClick={() => setQty((q) => Math.min(99, q + 1))}>
                  +
                </button>
              </div>
            )}
            <button
              type="button"
              className={`im-add-btn${showInCart && state !== 'added' ? ' in-cart' : ''}${state === 'added' ? ' just-added-modal' : ''}`}
              onClick={submit}
              disabled={state === 'saving'}
            >
              {buttonText}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
