import { useMutation } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import { usePageTitle } from '@/hooks/usePageTitle';
import { AuthShell, fieldClass, SuccessOverlay } from './AuthShell';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ForgotPage() {
  usePageTitle('Відновлення пароля — Coffee Time');
  const [email, setEmail] = useState('');
  const [touched, setTouched] = useState(false);
  const [shake, setShake] = useState(0);
  const forgot = useMutation({
    mutationFn: () => unwrap(api.POST('/api/auth/forgot', { body: { email } })),
    onError: () => setShake((s) => s + 1),
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (!EMAIL_RE.test(email.trim())) {
      setShake((s) => s + 1);
      return;
    }
    forgot.mutate();
  };

  return (
    <AuthShell
      title="Забули пароль?"
      subtitle="Не хвилюйтеся — введіть вашу пошту, і ми надішлемо посилання для відновлення доступу."
      features={[
        ['clock', 'Лист надійде протягом хвилини'],
        ['lock', 'Посилання дійсне 1 годину'],
        ['coffee-cup', 'Після входу — замовляйте улюблений смак'],
      ]}
      shake={shake}
    >
      {forgot.isSuccess ? (
        <SuccessOverlay title="Лист надіслано!" sub="Перевірте вашу пошту та перейдіть за посиланням.">
          <Link to="/login" style={{ marginTop: 8, fontSize: 13, color: '#8B4513', fontWeight: 700, textDecoration: 'none' }}>
            ← Повернутися до входу
          </Link>
        </SuccessOverlay>
      ) : (
        <>
          <p className="auth-form-title">Відновлення пароля</p>
          {forgot.error && <div className="auth-error-block" role="alert">{errorMessage(forgot.error)}</div>}
          <form noValidate onSubmit={onSubmit}>
            <div className={fieldClass(touched, EMAIL_RE.test(email.trim()))}>
              <label htmlFor="email">Електронна пошта</label>
              <div className="input-wrap">
                <input id="email" type="email" placeholder="your@email.com" value={email} autoComplete="email" required
                  onChange={(e) => { setEmail(e.target.value); setTouched(true); }} />
              </div>
              <span className="field-error">Введіть коректну електронну пошту</span>
            </div>
            <button type="submit" className={`auth-submit${forgot.isPending ? ' loading' : ''}`} disabled={forgot.isPending}>
              Надіслати посилання
            </button>
          </form>
          <div className="auth-switch">
            Згадали пароль? <Link to="/login">Увійти</Link>
          </div>
        </>
      )}
    </AuthShell>
  );
}
