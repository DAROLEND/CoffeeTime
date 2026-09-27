import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import { useSession } from '@/api/queries';
import { usePageTitle } from '@/hooks/usePageTitle';
import { safeRedirect } from '@/lib/safeRedirect';
import { AuthShell, CHECK, fieldClass, PasswordInput } from './AuthShell';

export default function LoginPage() {
  usePageTitle('Авторизація — Coffee Time');
  const navigate = useNavigate();
  const client = useQueryClient();
  const [params] = useSearchParams();
  const { data: session } = useSession();
  const info = useQuery({ queryKey: ['login-info'], queryFn: () => unwrap(api.GET('/api/auth/login-info')), staleTime: 0 });

  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [touched, setTouched] = useState({ login: false, password: false });
  const [error, setError] = useState('');
  const [shake, setShake] = useState(0);

  useEffect(() => {
    if (info.data?.remembered_email) {
      setLogin((v) => v || info.data.remembered_email);
      setRemember(true);
    }
  }, [info.data]);

  const submit = useMutation({
    mutationFn: () => unwrap(api.POST('/api/auth/login', { body: { login, password, remember } })),
    onSuccess: async (res) => {
      await client.invalidateQueries();
      navigate(res.kind === 'admin' ? res.redirect : safeRedirect(params.get('next'), res.redirect), { replace: true });
    },
    onError: (err) => {
      setError(errorMessage(err));
      setShake((s) => s + 1);
      void info.refetch();
    },
  });

  if (session?.user && !submit.isPending && !submit.isSuccess) return <Navigate to={safeRedirect(params.get('next'))} replace />;

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setTouched({ login: true, password: true });
    if (login.trim().length < 3 || !password) {
      setShake((s) => s + 1);
      return;
    }
    setError('');
    submit.mutate();
  };

  const locked = info.data?.is_locked;

  return (
    <AuthShell
      title="З поверненням до Coffee Time"
      subtitle="Увійдіть, щоб зручно оформлювати замовлення та насолоджуватися улюбленим смаком."
      features={[
        ['coffee-cup', 'Швидке замовлення в пару кліків'],
        ['receipt', 'Історія ваших замовлень'],
        ['pizza', 'Кава, піца, десерти — все в одному місці'],
      ]}
      shake={shake}
    >
      {(error || locked) && (
        <div className="auth-error-block" role="alert">
          {locked ? `Забагато невдалих спроб. Спробуйте через ${info.data?.lock_minutes ?? 15} хвилин.` : error}
        </div>
      )}
      <h2 className="auth-form-title">Вхід</h2>
      <form noValidate onSubmit={onSubmit}>
        <div className={fieldClass(touched.login, login.trim().length >= 3)}>
          <label htmlFor="loginEmail">Електронна пошта або логін</label>
          <div className="input-wrap">
            <input id="loginEmail" type="text" value={login} autoComplete="username" placeholder="example@mail.com"
              onChange={(e) => { setLogin(e.target.value); setTouched((t) => ({ ...t, login: true })); }} />
            {CHECK}
          </div>
          <span className="field-error">Заповніть це поле</span>
        </div>

        <div className={fieldClass(touched.password, password.length >= 1)}>
          <label htmlFor="loginPassword">Пароль</label>
          <PasswordInput id="loginPassword" value={password} autoComplete="current-password" placeholder="••••••••"
            onChange={(e) => { setPassword(e.target.value); setTouched((t) => ({ ...t, password: true })); }} />
          <span className="field-error">Введіть пароль</span>
        </div>

        <div className="auth-controls">
          <label className="cb-wrap">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            <span className="cb-box">
              <svg className="cb-check" width="10" height="8" viewBox="0 0 10 8" fill="none"><path d="M1 4l3 3 5-6" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </span>
            Запам'ятати мене
          </label>
          <Link to="/forgot" className="forgot-link">Забули пароль?</Link>
        </div>

        <button type="submit" className={`auth-submit${submit.isPending ? ' loading' : ''}`} disabled={submit.isPending}>
          Увійти
        </button>
        <p className="auth-switch">
          Ще не маєте акаунту? <Link to="/register">Зареєструватися</Link>
        </p>
      </form>
    </AuthShell>
  );
}
