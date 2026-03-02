import React, { useEffect, useMemo, useState } from 'react';
import { Edit2, Eye, EyeOff, Filter, Plus, Search, Trash2, X, ChevronDown } from 'lucide-react';
import { useNotification } from '../components/useNotification';
import {
  createUser,
  deleteUser,
  listUsers,
  updateUser,
  UserItem,
  UserRole,
} from '../services/usersService';

type ActiveFilter = 'ALL' | 'true' | 'false';

type ModalMode = 'create' | 'edit';

interface ModalState {
  open: boolean;
  mode: ModalMode;
  user?: UserItem;
}

interface FormState {
  nombre_usuario: string;
  correo: string;
  contrasena: string;
  rol: UserRole;
  activo: boolean;
}

const defaultForm: FormState = {
  nombre_usuario: '',
  correo: '',
  contrasena: '',
  rol: 'CLIENTE',
  activo: true,
};

function getErrorMessage(error: any, fallback: string): string {
  const detail = error?.response?.data?.detail;

  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item: any) => {
        if (!item) return null;
        if (typeof item === 'string') return item;
        if (typeof item?.msg === 'string') return item.msg;
        return null;
      })
      .filter(Boolean);

    if (messages.length > 0) {
      return messages.join(' | ');
    }
  }

  return fallback;
}

function deriveDisplayName(email: string): string {
  const [local] = (email || '').split('@');
  if (!local) return email;
  return local
    .replace(/[._-]/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export const UsersScreen: React.FC = () => {
  const showNotification = useNotification();

  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState('');
  const [rolFilter, setRolFilter] = useState<UserRole | 'ALL'>('ALL');
  const [activoFilter, setActivoFilter] = useState<ActiveFilter>('ALL');

  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  const [modal, setModal] = useState<ModalState>({ open: false, mode: 'create' });
  const [form, setForm] = useState<FormState>(defaultForm);
  const [showPassword, setShowPassword] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchUsers = async (targetPage = page) => {
    setLoading(true);
    try {
      const result = await listUsers({
        search,
        rol: rolFilter,
        activo: activoFilter,
        page: targetPage,
        pageSize,
      });
      setUsers(result.items || []);
      setTotal(Number(result.total || 0));
      setTotalPages(Math.max(1, Number(result.total_pages || 1)));
      setPage(Number(result.page || targetPage));
    } catch (error: any) {
      showNotification(getErrorMessage(error, 'No se pudo cargar la lista de usuarios'), 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers(1);
  }, [rolFilter, activoFilter]);

  const summaryText = useMemo(() => {
    const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
    const end = Math.min(page * pageSize, total);
    return `Mostrando ${start}-${end} de ${total} usuarios`;
  }, [page, pageSize, total]);

  const openCreate = () => {
    setModal({ open: true, mode: 'create' });
    setForm(defaultForm);
    setShowPassword(false);
  };

  const openEdit = (user: UserItem) => {
    setModal({ open: true, mode: 'edit', user });
    setForm({
      nombre_usuario: user.nombre_usuario,
      correo: user.correo,
      contrasena: '',
      rol: user.rol,
      activo: user.activo,
    });
    setShowPassword(false);
  };

  const closeModal = () => {
    setModal({ open: false, mode: 'create' });
    setForm(defaultForm);
    setShowPassword(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (modal.mode === 'create') {
        await createUser(form);
        showNotification('Usuario creado correctamente', 'success');
      } else if (modal.user) {
        const payload: any = {
          nombre_usuario: form.nombre_usuario,
          correo: form.correo,
          rol: form.rol,
          activo: form.activo,
        };
        if (form.contrasena.trim()) {
          payload.contrasena = form.contrasena;
        }
        await updateUser(modal.user.id, payload);
        showNotification('Usuario actualizado correctamente', 'success');
      }
      closeModal();
      await fetchUsers(page);
    } catch (error: any) {
      showNotification(getErrorMessage(error, 'No se pudo guardar el usuario'), 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (user: UserItem) => {
    const ok = window.confirm(`¿Eliminar usuario ${user.nombre_usuario}?`);
    if (!ok) return;

    try {
      await deleteUser(user.id);
      showNotification('Usuario eliminado', 'success');
      await fetchUsers(page);
    } catch (error: any) {
      showNotification(getErrorMessage(error, 'No se pudo eliminar el usuario'), 'error');
    }
  };

  return (
    <div className="max-w-7xl mx-auto flex flex-col gap-6">
      <div className="bg-white dark:bg-[#111a22] border border-slate-200 dark:border-slate-800 rounded-xl p-4 md:p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-3xl font-black tracking-tight text-slate-900 dark:text-white">Usuarios</h2>
            <p className="text-slate-500 mt-1">Administra los accesos y roles de tu plataforma</p>
          </div>

          <div className="w-full grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-12 gap-3 items-center">
            <div className="relative sm:col-span-2 xl:col-span-5">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input
                type="text"
                className="h-10 pl-10 pr-3 bg-slate-100 dark:bg-[#1c2936] border-none rounded-lg text-[13px] text-slate-900 dark:text-white placeholder-slate-500 focus:ring-2 focus:ring-primary w-full"
                placeholder="Buscar por correo..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') fetchUsers(1);
                }}
              />
            </div>

            <div className="relative xl:col-span-3">
              <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <select
                value={rolFilter}
                onChange={(e) => setRolFilter(e.target.value as UserRole | 'ALL')}
                className="w-full h-10 pl-9 pr-8 bg-slate-100 dark:bg-[#1c2936] border-none rounded-lg text-[13px] text-slate-900 dark:text-white appearance-none"
              >
                <option value="ALL">Todos los roles</option>
                <option value="ADMIN">Admin</option>
                <option value="CLIENTE">Cliente</option>
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" size={16} />
            </div>

            <div className="relative xl:col-span-2">
              <select
                value={activoFilter}
                onChange={(e) => setActivoFilter(e.target.value as ActiveFilter)}
                className="w-full h-10 px-3 pr-8 bg-slate-100 dark:bg-[#1c2936] border-none rounded-lg text-[13px] text-slate-900 dark:text-white appearance-none"
              >
                <option value="ALL">Todos</option>
                <option value="true">Activos</option>
                <option value="false">Inactivos</option>
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" size={16} />
            </div>

            <button
              onClick={openCreate}
              className="w-full h-10 xl:col-span-2 flex items-center justify-center gap-2 bg-blue-600 text-white px-3 rounded-lg text-[13px] font-semibold shadow hover:bg-blue-700 transition"
            >
              <Plus size={16} />
              Nuevo Usuario
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-[#111a22] border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-900/40 border-b border-slate-200 dark:border-slate-800">
                <th className="px-4 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Usuario</th>
                <th className="px-4 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Rol</th>
                <th className="px-4 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Estado</th>
                <th className="px-4 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Fecha Registro</th>
                <th className="px-4 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-500 text-sm">Cargando usuarios...</td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-500 text-sm">No hay usuarios para mostrar.</td>
                </tr>
              ) : (
                users.map((user) => {
                  const roleLabel = user.rol === 'ADMIN' ? 'ADMIN' : 'CLIENTE';
                  return (
                    <tr key={user.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="flex flex-col">
                          <span className="font-bold text-[15px] leading-tight text-slate-900 dark:text-white">{user.nombre_usuario}</span>
                          <span className="text-[12px] text-slate-500 dark:text-slate-400">{user.correo}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold uppercase ${
                          roleLabel === 'ADMIN'
                            ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                        }`}>
                          {roleLabel}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-bold ${
                          user.activo
                            ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                            : 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-400'
                        }`}>
                          <span className={`size-1.5 rounded-full ${user.activo ? 'bg-emerald-600 dark:bg-emerald-400' : 'bg-rose-600 dark:bg-rose-400'}`}></span>
                          {user.activo ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-[13px] text-slate-500 dark:text-slate-400">{new Date(user.fecha_registro).toLocaleDateString()}</td>
                      <td className="px-4 py-3.5 text-right">
                        <div className="flex justify-end gap-1.5">
                          <button
                            onClick={() => openEdit(user)}
                            className="p-1 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                          >
                            <Edit2 className="size-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(user)}
                            className="p-1 text-slate-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                          >
                            <Trash2 className="size-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="px-4 py-3 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-[13px] text-slate-500 dark:text-slate-400">
          <span>{summaryText}</span>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1 || loading}
              onClick={() => fetchUsers(page - 1)}
              className="px-2.5 py-1 border border-slate-200 dark:border-slate-700 rounded disabled:opacity-50"
            >
              Anterior
            </button>
            <span className="px-2.5 py-1 border border-slate-200 dark:border-slate-700 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
              {page}
            </span>
            <button
              disabled={page >= totalPages || loading}
              onClick={() => fetchUsers(page + 1)}
              className="px-2.5 py-1 border border-slate-200 dark:border-slate-700 rounded disabled:opacity-50"
            >
              Siguiente
            </button>
          </div>
        </div>
      </div>

      {modal.open && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 w-full max-w-md rounded-xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800">
            <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                {modal.mode === 'create' ? 'Crear Nuevo Usuario' : 'Editar Usuario'}
              </h3>
              <button onClick={closeModal} className="text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors">
                <X className="size-5" />
              </button>
            </div>

            <form
              className="p-6 space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                handleSave();
              }}
            >
              <div className="space-y-1.5">
                <label className="text-sm font-bold text-slate-900 dark:text-slate-200">Nombre de Usuario</label>
                <input
                  type="text"
                  value={form.nombre_usuario}
                  onChange={(e) => setForm((prev) => ({ ...prev, nombre_usuario: e.target.value }))}
                  placeholder="usuario_admin"
                  className="w-full px-4 py-2 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-bold text-slate-900 dark:text-slate-200">Correo Electrónico</label>
                <input
                  type="email"
                  value={form.correo}
                  onChange={(e) => setForm((prev) => ({ ...prev, correo: e.target.value }))}
                  placeholder="usuario@ejemplo.com"
                  className="w-full px-4 py-2 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-bold text-slate-900 dark:text-slate-200">
                  Contraseña {modal.mode === 'edit' && <span className="font-normal text-slate-500">(opcional para cambiar)</span>}
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={form.contrasena}
                    onChange={(e) => setForm((prev) => ({ ...prev, contrasena: e.target.value }))}
                    placeholder={modal.mode === 'create' ? 'Mín. 8, mayúscula, minúscula, número y símbolo' : 'Dejar vacío para mantener'}
                    className="w-full px-4 py-2 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white rounded-lg pr-10 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                    required={modal.mode === 'create'}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-blue-600"
                  >
                    {showPassword ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
                  </button>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-bold text-slate-900 dark:text-slate-200">Selector de Rol</label>
                <div className="relative">
                  <select
                    value={form.rol}
                    onChange={(e) => setForm((prev) => ({ ...prev, rol: e.target.value as UserRole }))}
                    className="w-full appearance-none px-4 py-2 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                  >
                    <option value="ADMIN">Admin</option>
                    <option value="CLIENTE">Cliente</option>
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none size-5" />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-bold text-slate-900 dark:text-slate-200">Estado</label>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setForm((prev) => ({ ...prev, activo: true }))}
                    className={`px-3 py-1.5 rounded-lg text-sm border ${form.activo ? 'bg-emerald-100 border-emerald-300 text-emerald-700' : 'border-slate-300 text-slate-600'}`}
                  >
                    Activo
                  </button>
                  <button
                    type="button"
                    onClick={() => setForm((prev) => ({ ...prev, activo: false }))}
                    className={`px-3 py-1.5 rounded-lg text-sm border ${!form.activo ? 'bg-rose-100 border-rose-300 text-rose-700' : 'border-slate-300 text-slate-600'}`}
                  >
                    Inactivo
                  </button>
                </div>
              </div>

              <div className="pt-4 flex gap-3">
                <button
                  type="button"
                  onClick={closeModal}
                  className="flex-1 py-2 text-sm font-bold border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800"
                  disabled={saving}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 py-2 text-sm font-bold bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60"
                >
                  {saving ? 'Guardando...' : 'Guardar Usuario'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
