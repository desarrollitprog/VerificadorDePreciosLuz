import { create } from 'zustand';
import { getTokenExpiryMs, hasValidToken, logout as tokenLogout, getUserRole, getUserName } from '../services/tokenUtils';

interface SessionState {
  isAuthenticated: boolean;
  role: 'ADMIN' | 'CLIENTE' | null;
  userName: string | null;
  checkSession: () => boolean;
  login: () => void;
  logout: () => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  isAuthenticated: hasValidToken(),
  role: getUserRole(),
  userName: getUserName(),

  checkSession: () => {
    const valid = hasValidToken();
    if (!valid && get().isAuthenticated) {
      set({ isAuthenticated: false });
    }
    return valid;
  },

  login: () => {
    set({
      isAuthenticated: true,
      role: getUserRole(),
      userName: getUserName(),
    });
  },

  logout: () => {
    tokenLogout();
    set({ isAuthenticated: false, role: null, userName: null });
  },
}));
