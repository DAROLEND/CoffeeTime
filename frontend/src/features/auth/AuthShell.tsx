import { useEffect, useState, type ReactNode } from 'react';
import { Icon, type IconName } from '@/components/Icon';
import '@/styles/pages/auth/auth.css';

type Props = {
  title: string;
  subtitle: string;
  features: [IconName, string][];
  /** Bump to replay the shake animation on the form panel. */
  shake?: number;
  children: ReactNode;
};

/** Two-panel auth card: brand panel on the left, the form on the right. */
export function AuthShell({ title, subtitle, features, shake = 0, children }: Props) {
  const [shaking, setShaking] = useState(false);
  useEffect(() => {
    if (!shake) return;
    setShaking(true);
  }, [shake]);

  return (
    <div className="pg-auth">
      <div className="auth-page">
        <div className="auth-card">
          <div className="auth-left">
            <img src="/static/images/main/logo.svg" alt="Coffee Time" className="auth-logo" />
            <div className="auth-left-middle">
              <h2 className="auth-left-title">{title}</h2>
              <p className="auth-left-sub">{subtitle}</p>
            </div>
            <div className="auth-features">
              {features.map(([icon, text]) => (
                <div className="auth-feature" key={text}>
                  <Icon name={icon} size={20} color="rgba(255,255,255,0.85)" className="auth-feature-icon" />
                  <span>{text}</span>
                </div>
              ))}
            </div>
          </div>
          <div className={`auth-right${shaking ? ' shake' : ''}`} onAnimationEnd={() => setShaking(false)}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

const EYE_SHOW = (
  <svg className="eye-show" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>
);
const EYE_HIDE = (
  <svg className="eye-hide" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" /><line x1="1" y1="1" x2="23" y2="23" /></svg>
);

type PasswordProps = React.InputHTMLAttributes<HTMLInputElement> & { wrapClassName?: string; toggleClassName?: string };

/** Password input with a show/hide toggle. */
export function PasswordInput({ wrapClassName = 'pw-wrap', toggleClassName = 'eye-toggle', ...input }: PasswordProps) {
  const [visible, setVisible] = useState(false);
  return (
    <div className={wrapClassName}>
      <input {...input} type={visible ? 'text' : 'password'} />
      <button type="button" className={toggleClassName} aria-label={visible ? 'Сховати пароль' : 'Показати пароль'} onClick={() => setVisible((v) => !v)}>
        {visible ? EYE_HIDE : EYE_SHOW}
      </button>
    </div>
  );
}

const LEVELS = ['', 'weak', 'fair', 'good', 'strong'] as const;
const LABELS = ['', 'Слабкий', 'Середній', 'Добрий', 'Надійний'];

export function passwordStrength(pw: string): number {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 6) score++;
  if (pw.length >= 10) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/[0-9]/.test(pw) || /[^A-Za-z0-9]/.test(pw)) score++;
  return Math.min(4, score);
}

export function StrengthMeter({ password }: { password: string }) {
  const s = passwordStrength(password);
  return (
    <>
      <div className="pw-strength">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className={`pw-bar${i < s ? ` ${LEVELS[s]}` : ''}`} />
        ))}
      </div>
      <div className={`pw-strength-label${s ? ` ${LEVELS[s]}` : ''}`}>{LABELS[s]}</div>
    </>
  );
}

export const CHECK = (
  <span className="field-check">
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7l4 4 6-6" stroke="#4CAF50" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
  </span>
);

export function SuccessOverlay({ title, sub, children }: { title: string; sub: string; children?: ReactNode }) {
  return (
    <div className="auth-success show">
      <svg className="auth-success-icon" viewBox="0 0 72 72" fill="none">
        <circle className="check-circle" cx="36" cy="36" r="33" stroke="#4CAF50" strokeWidth="3" fill="none" />
        <path className="check-mark" d="M22 36l10 10 18-18" stroke="#4CAF50" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <p className="auth-success-text">{title}</p>
      <p className="auth-success-sub">{sub}</p>
      {children}
    </div>
  );
}

/** valid / invalid class for a `.form-field`, only once the user typed. */
export function fieldClass(touched: boolean, valid: boolean): string {
  if (!touched) return 'form-field';
  return `form-field ${valid ? 'valid' : 'invalid'}`;
}
