import { useMutation } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import { usePageTitle } from '@/hooks/usePageTitle';
import '@/styles/pages/auth/change_password.css';

export default function ChangePasswordPage() {
  usePageTitle('Зміна паролю — Coffee Time');
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm_password: '' });
  const change = useMutation({
    mutationFn: () => unwrap(api.POST('/api/auth/change-password', { body: form })),
    onSuccess: () => setForm({ current_password: '', new_password: '', confirm_password: '' }),
  });
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    change.mutate();
  };

  return (
    <div className="pg-auth">
      <main className="profile">
        <h1>Зміна паролю</h1>
        {change.isSuccess && <div className="notification success">{change.data.message}</div>}
        {change.error && <div className="notification error">{errorMessage(change.error)}</div>}
        <form className="profile-form" onSubmit={onSubmit}>
          <label htmlFor="current_password">Поточний пароль:</label>
          <input type="password" id="current_password" required autoComplete="current-password" value={form.current_password} onChange={set('current_password')} />
          <label htmlFor="new_password">Новий пароль:</label>
          <input type="password" id="new_password" required autoComplete="new-password" value={form.new_password} onChange={set('new_password')} />
          <label htmlFor="confirm_password">Підтвердження нового паролю:</label>
          <input type="password" id="confirm_password" required autoComplete="new-password" value={form.confirm_password} onChange={set('confirm_password')} />
          <div className="form-actions">
            <button type="submit" className="save-btn" disabled={change.isPending}>
              Змінити пароль
            </button>
            <Link to="/profile" className="logout-btn">Назад до профілю</Link>
          </div>
          <div className="forgot-link">
            <Link to="/forgot">Забули пароль?</Link>
          </div>
        </form>
      </main>
    </div>
  );
}
