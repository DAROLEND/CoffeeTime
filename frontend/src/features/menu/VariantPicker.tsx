import type { VariantOptions } from '@/api/types';
import { SCOOP_ICONS } from './ScoopIcons';
import type { VariantSelection } from './menuLogic';

type Props = {
  options: VariantOptions;
  basePrice: number;
  selection: VariantSelection;
  onChange: (sel: VariantSelection) => void;
  sauceLabel?: string | null;
  onSauceChange?: (label: string | null) => void;
};

const round = (n: number) => Math.round(n);

/**
 * Option buttons for a variant product, shared by the menu modal and the
 * cart's edit modal:
 * - `scoops` (ice cream) and `size` (fast food): one row of buttons
 * - `filling` (fast food): filling buttons, then its sizes if it has any
 * - `sauce` (fast food): a free, single-choice sauce
 */
export function VariantPicker({ options: vo, basePrice, selection, onChange, sauceLabel, onSauceChange }: Props) {
  if (vo.type === 'sauce') {
    return (
      <div className="im-free-sauce">
        <div className="im-option-label">{vo.label || 'Оберіть соус'}:</div>
        <div className="im-scoops-grid">
          {vo.options.map((opt) => (
            <button
              key={opt.id}
              type="button"
              className={`im-scoop-btn${sauceLabel === opt.label ? ' selected' : ''}`}
              aria-pressed={sauceLabel === opt.label}
              onClick={() => onSauceChange?.(sauceLabel === opt.label ? null : opt.label)}
            >
              <span className="isb-label">{opt.label}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  const label = vo.type === 'scoops' ? 'Кількість кульок' : vo.label || 'Начинка';
  const selected = vo.options.find((o) => o.id === selection.optionId);

  return (
    <>
      <div>
        <div className="im-option-label">{label}:</div>
        <div className="im-scoops-grid">
          {vo.options.map((opt, i) => (
            <button
              key={opt.id}
              type="button"
              className={`im-scoop-btn${opt.id === selection.optionId ? ' selected' : ''}`}
              aria-pressed={opt.id === selection.optionId}
              onClick={() => onChange({ optionId: opt.id, sizeLabel: opt.sizes[0]?.label ?? null })}
            >
              {vo.type === 'scoops' && SCOOP_ICONS[i] && <span className="isb-icon">{SCOOP_ICONS[i]}</span>}
              <span className="isb-label">{opt.label}</span>
              <span className="isb-price">{round(basePrice + opt.price_diff)} ₴</span>
            </button>
          ))}
        </div>
      </div>
      {selected && selected.sizes.length > 0 && (
        <div key={selected.id} className="im-size-wrap im-ff-size-sub">
          <div className="im-option-label">Розмір:</div>
          <div className="im-size-btns">
            {selected.sizes.map((sz) => (
              <button
                key={sz.label}
                type="button"
                className={`im-size-btn${sz.label === selection.sizeLabel ? ' active' : ''}`}
                onClick={() => onChange({ optionId: selected.id, sizeLabel: sz.label })}
              >
                {sz.label}
                <br />
                <span className="im-size-price">{round(basePrice + selected.price_diff + sz.price_diff)} ₴</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
