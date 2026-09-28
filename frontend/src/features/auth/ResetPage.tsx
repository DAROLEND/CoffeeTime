import { useMutation, useQuery } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import { PageLoader } from '@/components/Spinner';
import { usePageTitle } from '@/hooks/usePageTitle';
import { AuthShell, fieldClass, PasswordInput, StrengthMeter, SuccessOverlay } from './AuthShell';

export default function ResetPage() {
  usePageTitle('Новий пароль — Coffee Time');
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [touched, setTouched] = useState(false);
  const [shake, setShake] = useState(0);

  const info = useQuery({ queryKey: ['reset', token], queryFn: () => unwrap(api.GET('/api/auth/reset', { params: { query: { token } } })) });
  const reset = useMutation({
    mutationFn: () => unwrap(api.POST('/api/auth/reset', { body: { token, password, confirm } })),
    onError: () => setShake((s) => s + 1),
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (password.length < 6 || password !== confirm) {
      setShake((s) => s + 1);
      return;
    }
    reset.mutate();
  };

  let body;
  if (info.isPending) body = <PageLoader />;
  else if (reset.isSuccess)
    body = (
      <SuccessOverlay title="Пароль змінено!" sub="Тепер ви можете увійти з новим паролем.">
        <Link to="/login" style={{ marginTop: 8, fontSize: 13, color: '#8B4513', fontWeight: 700, textDecoration: 'none' }}>
          → Увійти
        </Link>
      </SuccessOverlay>
    );
  else if (!info.data?.valid)
    body = (
      <>
        <p className="auth-form-title">Помилка</p>
        <div className="auth-error-block">{info.data?.error || errorMessage(info.error)}</div>
        <div className="auth-switch">
          <Link to="/forgot">← Запросити нове посилання</Link>
        </div>
      </>
    );
  else
    body = (
      <>
        <p className="auth-form-title">Введіть новий пароль</p>
        {reset.error && <div className="auth-error-block" role="alert">{errorMessage(reset.error)}</div>}
        <form noValidate onSubmit={onSubmit}>
          <div className={fieldClass(touched, password.length >= 6)}>
            <label htmlFor="password">Новий пароль</label>
            <PasswordInput id="password" wrapClassName="pw-wrap input-wrap" placeholder="Мінімум 6 символів" autoComplete="new-password" value={password}
              onChange={(e) => { setPassword(e.target.value); setTouched(true); }} />
            <StrengthMeter password={password} />
            <span className="field-error">Пароль занадто короткий</span>
          </div>
          <div className={fieldClass(touched && confirm.length > 0, confirm === password)}>
            <label htmlFor="confirm">Підтвердіть пароль</label>
            <PasswordInput id="confirm" wrapClassName="pw-wrap input-wrap" placeholder="Повторіть пароль" autoComplete="new-password" value={confirm}
              onChange={(e) => setConfirm(e.target.value)} />
            <span className="field-error">Паролі не співпадають</span>
          </div>
          <button type="submit" className={`auth-submit${reset.isPending ? ' loading' : ''}`} disabled={reset.isPending}>
            Зберегти пароль
          </button>
        </form>
      </>
    );

  return (
    <AuthShell
      title="Новий пароль"
      subtitle="Придумайте надійний пароль — і повертайтеся насолоджуватися улюбленим смаком."
      features={[
        ['lock', 'Мінімум 6 символів'],
        ['receipt', 'Збережіть пароль у надійному місці'],
        ['coffee-cup', "Після збереження — одразу в кав'ярню"],
      ]}
      shake={shake}
    >
      {body}
    </AuthShell>
  );
}
