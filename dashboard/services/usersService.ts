import api from './axiosInstance';

export type UserRole = 'ADMIN' | 'CLIENTE';

export interface UserItem {
  id: number;
  nombre_usuario: string;
  correo: string;
  activo: boolean;
  rol: UserRole;
  fecha_registro: string;
}

export interface UsersListResponse {
  success: boolean;
  items: UserItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ListUsersParams {
  search?: string;
  rol?: UserRole | 'ALL';
  activo?: 'ALL' | 'true' | 'false';
  page?: number;
  pageSize?: number;
}

export interface CreateUserPayload {
  nombre_usuario: string;
  correo: string;
  contrasena: string;
  rol: UserRole;
  activo: boolean;
}

export interface UpdateUserPayload {
  nombre_usuario?: string;
  correo?: string;
  contrasena?: string;
  rol?: UserRole;
  activo?: boolean;
}

export async function listUsers(params: ListUsersParams): Promise<UsersListResponse> {
  const query = new URLSearchParams();
  if (params.search?.trim()) query.set('search', params.search.trim());
  if (params.rol && params.rol !== 'ALL') query.set('rol', params.rol);
  if (params.activo && params.activo !== 'ALL') query.set('activo', params.activo);
  query.set('page', String(params.page ?? 1));
  query.set('page_size', String(params.pageSize ?? 10));

  const response = await api.get<UsersListResponse>(`/usuarios?${query.toString()}`);
  return response.data;
}

export async function createUser(payload: CreateUserPayload): Promise<UserItem> {
  const response = await api.post<UserItem>('/usuarios', payload);
  return response.data;
}

export async function updateUser(id: number, payload: UpdateUserPayload): Promise<UserItem> {
  const response = await api.put<UserItem>(`/usuarios/${id}`, payload);
  return response.data;
}

export async function deleteUser(id: number): Promise<void> {
  await api.delete(`/usuarios/${id}`);
}
