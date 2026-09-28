import { useMutation } from '@tanstack/react-query';
import { useEffect, useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router';
import { api } from '@/api/client';
import { ApiError, errorMessage, unwrap } from '@/api/errors';
import { useSession } from '@/api/queries';
import { usePageTitle } from '@/hooks/usePageTitle';
import { AuthShell, CHECK, fieldClass, PasswordInput, StrengthMeter } from './AuthShell';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const LOGIN_RE = /^[A-Za-zА-Яа-яЇїІіЄєҐґ0-9_]{3,}$/;

export default function RegisterPage() {
  usePageTitle('Реєстрація — Coffee Time');
  const navigate = useNavigate();
  const { data: session } = useSession();
  const [form, setForm] = useState({ email: '', login: '', password: '', confirm: '' });
  const [touched, setTouched] = useState({ email: false, login: false, password: false, confirm: false });
  const [errors, setErrors] = useState<string[]>([]);
  const [shake, setShake] = useState(0);

  const register = useMutation({
    mutationFn: () => unwrap(api.POST('/api/auth/register', { body: form })),
    onError: (err) => {
      setErrors(err instanceof ApiError && err.errors.length ? err.errors : [errorMessage(err)]);
      setShake((s) => s + 1);
    },
  });

  useEffect(() => {
    if (!register.isSuccess) return;
    const t = window.setTimeout(() => navigate('/login'), 2800);
    return () => window.clearTimeout(t);
  }, [register.isSuccess, navigate]);

  if (session?.user) return <Navigate to="/" replace />;

  const valid = {
    email: EMAIL_RE.test(form.email.trim()),
    login: LOGIN_RE.test(form.login.trim()),
    password: form.password.length >= 6,
    confirm: form.confirm.length > 0 && form.confirm === form.password,
  };
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    setTouched((t) => ({ ...t, [key]: true }));
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setTouched({ email: true, login: true, password: true, confirm: true });
    if (!Object.values(valid).every(Boolean)) {
      setShake((s) => s + 1);
      return;
    }
    setErrors([]);
    register.mutate();
  };

  return (
    <AuthShell
      title="Приєднуйся до Coffee Time"
      subtitle="Реєстрація займає менше хвилини — і кава вже чекає на тебе."
      features={[
        ['coffee-cup', 'Замовляй каву та їжу онлайн'],
        ['receipt', 'Зберігай історію замовлень'],
        ['pizza', 'Кава, піца, десерти — все в одному місці'],
      ]}
      shake={shake}
    >
      <div className={`auth-success${register.isSuccess ? ' show' : ''}`}>
        <svg className="auth-success-icon" viewBox="0 0 72 72" fill="none">
          <circle className="check-circle" cx="36" cy="36" r="32" stroke="#4CAF50" strokeWidth="3" fill="none" strokeLinecap="round" />
          <path className="check-mark" d="M22 37l10 10 18-20" stroke="#4CAF50" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        </svg>
        <p className="auth-success-text">Реєстрація успішна!</p>
        <p className="auth-success-sub">Переходимо до входу…</p>
      </div>

      {errors.length > 0 && (
        <div className="auth-error-block" role="alert">
          <ul>{errors.map((e) => <li key={e}>{e}</li>)}</ul>
        </div>
      )}

      <h2 className="auth-form-title">Реєстрація</h2>
      <form noValidate onSubmit={onSubmit}>
        <div className={fieldClass(touched.email, valid.email)}>
          <label htmlFor="regEmail">Електронна пошта</label>
          <div className="input-wrap">
            <input id="regEmail" type="email" value={form.email} autoComplete="email" placeholder="example@mail.com" onChange={set('email')} />
            {CHECK}
          </div>
          <span className="field-error">Введіть коректну пошту</span>
        </div>

        <div className={fieldClass(touched.login, valid.login)}>
          <label htmlFor="regLogin">Логін</label>
          <div className="input-wrap">
            <input id="regLogin" type="text" value={form.login} autoComplete="username" placeholder="мінімум 3 символи" onChange={set('login')} />
            {CHECK}
          </div>
          <span className="field-error">Мінімум 3 символи, лише літери, цифри, _</span>
        </div>

        <div className={fieldClass(touched.password, valid.password)}>
          <label htmlFor="regPassword">Пароль</label>
          <PasswordInput id="regPassword" value={form.password} autoComplete="new-password" placeholder="мінімум 6 символів" onChange={set('password')} />
          <span className="field-error">Мінімум 6 символів</span>
          <StrengthMeter password={form.password} />
        </div>

        <div className={fieldClass(touched.confirm, valid.confirm)}>
          <label htmlFor="regConfirm">Підтвердіть пароль</label>
          <PasswordInput id="regConfirm" value={form.confirm} autoComplete="new-password" placeholder="повторіть пароль" onChange={set('confirm')} />
          <span className="field-error">Паролі не співпадають</span>
        </div>

        <button type="submit" className={`auth-submit${register.isPending ? ' loading' : ''}`} disabled={register.isPending}>
          Зареєструватися
        </button>
        <p className="auth-switch">
          Вже маєте акаунт? <Link to="/login">Увійти</Link>
        </p>
      </form>
    </AuthShell>
  );
}
