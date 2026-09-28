import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import { PageError, PageLoader } from '@/components/Spinner';
import { useAdminTitle } from '../AdminLayout';
import { useAdminToast } from '../AdminToast';
import { AdminModal } from '../components/Modal';
import { adminKeys, useAdminLayout } from '../useAdmin';

type Account = components['schemas']['AdminAccount'];
type PermOption = components['schemas']['PermOption'];

function PasswordField({ id, value, onChange, placeholder, required }: { id: string; value: string; onChange: (v: string) => void; placeholder: string; required?: boolean }) {
  const [shown, setShown] = useState(false);
  return (
    <div className="pw-wrap">
      <input type={shown ? 'text' : 'password'} id={id} value={value} onChange={(e) => onChange(e.target.value)} required={required} placeholder={placeholder} minLength={required ? undefined : 6} />
      <button type="button" className="eye-btn" aria-label={shown ? 'Сховати пароль' : 'Показати пароль'} onClick={() => setShown((s) => !s)}>
        👁
      </button>
    </div>
  );
}

function PermGrid({ all, value, onChange }: { all: PermOption[]; value: string[]; onChange: (perms: string[]) => void }) {
  return (
    <div className="perm-grid">
      {all.map((p) => (
        <label key={p.key} className="perm-check">
          <input type="checkbox" checked={value.includes(p.key)} onChange={(e) => onChange(e.target.checked ? [...value, p.key] : value.filter((k) => k !== p.key))} />
          <span>{p.label}</span>
        </label>
      ))}
    </div>
  );
}

function MyAccount() {
  const layout = useAdminLayout().data;
  const toast = useAdminToast();
  const client = useQueryClient();
  const [display, setDisplay] = useState<string | null>(null);
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const save = useMutation({
    mutationFn: () => unwrap(api.POST('/api/admin/users/me', { body: { display_name: display ?? layout?.display_name ?? '', current_password: current, new_password: next } })),
    onSuccess: (res) => {
      toast(res.message, 'success');
      setCurrent('');
      setNext('');
      client.invalidateQueries({ queryKey: adminKeys.layout });
      client.invalidateQueries({ queryKey: adminKeys.users });
    },
    onError: (err) => toast(errorMessage(err), 'error'),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <div className="panel" style={{ marginBottom: 28 }}>
      <div className="panel-head">
        <h2 className="panel-title">Мій акаунт</h2>
      </div>
      <form className="au-form" onSubmit={submit}>
        <div className="au-row2">
          <div className="au-field">
            <label>Логін</label>
            <input type="text" value={layout?.username ?? ''} disabled style={{ background: '#f5f5f5', color: '#aaa' }} />
          </div>
          <div className="au-field">
            <label htmlFor="myDisplay">Відображуване імʼя</label>
            <input type="text" id="myDisplay" value={display ?? layout?.display_name ?? ''} onChange={(e) => setDisplay(e.target.value)} placeholder="Як вас показувати в адмінці" />
          </div>
        </div>
        <div className="au-row2">
          <div className="au-field">
            <label htmlFor="curPass">
              Поточний пароль <span style={{ color: '#e53935' }}>*</span>
            </label>
            <PasswordField id="curPass" value={current} onChange={setCurrent} required placeholder="введіть поточний пароль" />
          </div>
          <div className="au-field">
            <label htmlFor="newPass">
              Новий пароль <small>(залиш порожнім щоб не міняти)</small>
            </label>
            <PasswordField id="newPass" value={next} onChange={setNext} placeholder="мінімум 6 символів" />
          </div>
        </div>
        <button type="submit" className="btn btn-primary" disabled={save.isPending}>
          💾 Зберегти
        </button>
      </form>
    </div>
  );
}

function CreateAccount({ allPerms }: { allPerms: PermOption[] }) {
  const toast = useAdminToast();
  const client = useQueryClient();
  const empty = { username: '', display_name: '', password: '', perms: [] as string[] };
  const [form, setForm] = useState(empty);
  const [permError, setPermError] = useState(false);
  const save = useMutation({
    mutationFn: () => unwrap(api.POST('/api/admin/users', { body: form })),
    onSuccess: (res) => {
      toast(res.message, 'success');
      setForm(empty);
      client.invalidateQueries({ queryKey: adminKeys.users });
    },
    onError: (err) => toast(errorMessage(err), 'error'),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!form.perms.length) return setPermError(true);
    save.mutate();
  };
  return (
    <div className="panel" style={{ marginBottom: 28 }}>
      <div className="panel-head">
        <h2 className="panel-title">Додати акаунт персоналу</h2>
      </div>
      <form className="au-form" onSubmit={submit}>
        <div className="au-row2">
          <div className="au-field">
            <label htmlFor="newLogin">
              Логін <span style={{ color: '#e53935' }}>*</span>
            </label>
            <input type="text" id="newLogin" placeholder="login123" minLength={3} required value={form.username} onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))} />
          </div>
          <div className="au-field">
            <label htmlFor="newDisplay">Відображуване імʼя</label>
            <input type="text" id="newDisplay" placeholder="Марія К." value={form.display_name} onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))} />
          </div>
        </div>
        <div className="au-row2">
          <div className="au-field">
            <label htmlFor="newPassword">
              Пароль <span style={{ color: '#e53935' }}>*</span>
            </label>
            <input type="password" id="newPassword" placeholder="мінімум 6 символів" minLength={6} required value={form.password} onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} />
          </div>
        </div>
        <div className="au-field">
          <label>
            Права доступу <span style={{ color: '#e53935' }}>*</span>
          </label>
          <PermGrid
            all={allPerms}
            value={form.perms}
            onChange={(perms) => {
              setPermError(false);
              setForm((f) => ({ ...f, perms }));
            }}
          />
          {permError && <div className="perm-error">Оберіть принаймні одне право доступу</div>}
        </div>
        <button type="submit" className="btn btn-primary" disabled={save.isPending}>
          + Створити акаунт
        </button>
      </form>
    </div>
  );
}

function EditModal({ user, allPerms, onClose }: { user: Account | null; allPerms: PermOption[]; onClose: () => void }) {
  const toast = useAdminToast();
  const client = useQueryClient();
  const [form, setForm] = useState({ display_name: '', new_password: '', perms: [] as string[] });
  const [permError, setPermError] = useState(false);
  const [shownFor, setShownFor] = useState<number | null>(null);
  if (user && shownFor !== user.id) {
    setShownFor(user.id);
    setForm({ display_name: user.display_name, new_password: '', perms: user.perms });
    setPermError(false);
  }
  const save = useMutation({
    mutationFn: (id: number) => unwrap(api.PATCH('/api/admin/users/{user_id}', { params: { path: { user_id: id } }, body: form })),
    onSuccess: (res) => {
      toast(res.message, 'success');
      client.invalidateQueries({ queryKey: adminKeys.users });
      onClose();
    },
    onError: (err) => toast(errorMessage(err), 'error'),
  });
  const close = () => {
    setShownFor(null);
    onClose();
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!user) return;
    if (!form.perms.length) return setPermError(true);
    save.mutate(user.id);
  };
  return (
    <AdminModal open={!!user} onClose={close} className="modal-box" style={{ maxWidth: 520, width: 'min(520px, 94vw)' }} label="Редагувати акаунт">
      <button className="modal-close" type="button" onClick={close} aria-label="Закрити">
        ✕
      </button>
      <h3 style={{ fontSize: 16, fontWeight: 700, color: '#2c2c2a', marginBottom: 20 }}>Редагувати акаунт</h3>
      <form className="au-form" style={{ padding: 0 }} onSubmit={submit}>
        <div className="au-row2">
          <div className="au-field">
            <label>Логін</label>
            <input type="text" value={user?.username ?? ''} disabled style={{ background: '#f5f5f5', color: '#aaa' }} />
          </div>
          <div className="au-field">
            <label htmlFor="editDisplay">Відображуване імʼя</label>
            <input type="text" id="editDisplay" value={form.display_name} onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))} />
          </div>
        </div>
        <div className="au-field">
          <label htmlFor="editPass">
            Новий пароль <small>(залиш порожнім щоб не міняти)</small>
          </label>
          <input type="password" id="editPass" placeholder="мінімум 6 символів" minLength={6} value={form.new_password} onChange={(e) => setForm((f) => ({ ...f, new_password: e.target.value }))} />
        </div>
        <div className="au-field">
          <label>
            Права доступу <span style={{ color: '#e53935' }}>*</span>
          </label>
          <PermGrid
            all={allPerms}
            value={form.perms}
            onChange={(perms) => {
              setPermError(false);
              setForm((f) => ({ ...f, perms }));
            }}
          />
          {permError && <div className="perm-error">Оберіть принаймні одне право доступу</div>}
        </div>
        <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
          <button type="submit" className="btn btn-primary" disabled={save.isPending}>
            Зберегти
          </button>
          <button type="button" className="btn btn-outline" onClick={close}>
            Скасувати
          </button>
        </div>
      </form>
    </AdminModal>
  );
}

export default function UsersPage() {
  useAdminTitle('Персонал');
  const toast = useAdminToast();
  const client = useQueryClient();
  const [editing, setEditing] = useState<Account | null>(null);
  const q = useQuery({ queryKey: adminKeys.users, queryFn: () => unwrap(api.GET('/api/admin/users')) });
  const remove = useMutation({
    mutationFn: (id: number) => unwrap(api.DELETE('/api/admin/users/{user_id}', { params: { path: { user_id: id } } })),
    onSuccess: (res) => {
      toast(res.message, 'success');
      client.invalidateQueries({ queryKey: adminKeys.users });
    },
    onError: (err) => toast(errorMessage(err), 'error'),
  });

  if (q.isPending) return <PageLoader />;
  if (q.error) return <PageError message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  const { users, all_perms } = q.data;
  const permLabel = Object.fromEntries(all_perms.map((p) => [p.key, p.label]));

  return (
    <>
      <MyAccount />
      <CreateAccount allPerms={all_perms} />

      <div className="panel">
        <div className="panel-head">
          <h2 className="panel-title">Акаунти ({users.length})</h2>
        </div>
        <div className="au-list">
          {users.map((u) => {
            const isSuper = u.role === 'super';
            return (
              <div key={u.id} className="au-row">
                <div className={`au-avatar${isSuper ? ' au-avatar--super' : ''}`}>{(u.display_name || u.username).charAt(0).toUpperCase()}</div>
                <div className="au-info">
                  <div className="au-name">
                    {u.display_name || u.username}
                    {u.display_name && <span className="au-login">@{u.username}</span>}
                    {u.is_me && <span className="au-badge au-badge--you">Це ви</span>}
                    <span className={`au-badge ${isSuper ? 'au-badge--super' : 'au-badge--staff'}`}>{isSuper ? 'Super' : 'Staff'}</span>
                  </div>
                  <div className="au-perms">
                    {isSuper ? (
                      <span className="au-perm-tag au-perm-tag--all">Повний доступ</span>
                    ) : !u.perms.length ? (
                      <span className="au-perm-none">Немає прав</span>
                    ) : (
                      u.perms.map((p) => (
                        <span key={p} className="au-perm-tag">
                          {permLabel[p] ?? p}
                        </span>
                      ))
                    )}
                  </div>
                </div>
                <div className="au-actions">
                  {!isSuper ? (
                    <>
                      <button className="btn btn-sm btn-outline" onClick={() => setEditing(u)}>
                        ✏️ Редагувати
                      </button>
                      <button className="btn btn-sm btn-danger" aria-label={`Видалити ${u.username}`} onClick={() => window.confirm(`Видалити акаунт «${u.username}»?`) && remove.mutate(u.id)}>
                        🗑
                      </button>
                    </>
                  ) : (
                    u.is_me && <span style={{ fontSize: 12, color: '#bbb' }}>Ваш акаунт</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <EditModal user={editing} allPerms={all_perms} onClose={() => setEditing(null)} />
    </>
  );
}
