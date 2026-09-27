import { CHEESE_CRUST } from './menuLogic';

type Props = {
  price: number;
  priceLarge: number;
  size: 'small' | 'large';
  crust: boolean;
  onSize: (size: 'small' | 'large') => void;
  onCrust: (crust: boolean) => void;
};

/** 30/40 cm size buttons + the cheese-crust checkbox. */
export function PizzaOptions({ price, priceLarge, size, crust, onSize, onCrust }: Props) {
  return (
    <>
      <div className="im-size-wrap">
        <div className="im-option-label">Розмір:</div>
        <div className="im-size-btns">
          <button type="button" className={`im-size-btn${size === 'small' ? ' active' : ''}`} onClick={() => onSize('small')}>
            30 см
            <br />
            <span className="im-size-price">{Math.round(price)} ₴</span>
          </button>
          <button
            type="button"
            className={`im-size-btn${size === 'large' ? ' active' : ''}`}
            disabled={!priceLarge}
            onClick={() => priceLarge && onSize('large')}
          >
            40 см
            <br />
            <span className="im-size-price">{priceLarge > 0 ? `${Math.round(priceLarge)} ₴` : ''}</span>
          </button>
        </div>
      </div>
      <div className={`pizza-option-row${crust ? ' active' : ''}`}>
        <label>
          <input type="checkbox" checked={crust} onChange={(e) => onCrust(e.target.checked)} style={{ display: 'none' }} />
          <div className={`cb-box${crust ? ' active' : ''}`} />
          <span>Сирний бортик</span>
          <span className="crust-price-label">+{CHEESE_CRUST[size]} ₴</span>
        </label>
      </div>
    </>
  );
}
