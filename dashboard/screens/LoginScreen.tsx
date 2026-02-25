import React, { useState } from 'react';
import { login, saveToken } from '../services/authService';
import { Lock, User, Eye, EyeOff, Video } from 'lucide-react';

interface LoginScreenProps {
  onLogin: () => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLogin }) => {
  const [showPassword, setShowPassword] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await login(username, password);
      saveToken(data.access_token);
      onLogin();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center p-4 overflow-hidden bg-background-light dark:bg-[#101922]">
      {/* Background Decoration */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-primary/20 blur-[120px] rounded-full mix-blend-screen opacity-40 animate-pulse"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-primary/10 blur-[100px] rounded-full mix-blend-screen opacity-30"></div>
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 brightness-100 contrast-150"></div>
      </div>

      <div className="relative z-10 w-full max-w-md transform rounded-xl border border-slate-200 bg-white p-8 shadow-2xl transition-all dark:border-slate-800 dark:bg-[#182430]">
        <div className="mb-8 text-center">
          <div className="mb-4 flex justify-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/20 text-primary">
              <Video size={28} />
            </div>
          </div>
          <h1 className="mb-2 text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            VERIFICADOR DE PRECIOS LUZ
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            BIENVENIDOS, POR FAVOR INGRESA TUS CREDENCIALES 
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300" htmlFor="username">
              NOMBRE DE USUARIO
            </label>
            <div className="relative">
              <input
                id="username"
                type="text"
                required
                className="block w-full rounded-lg border-slate-300 bg-slate-50 p-2.5 text-slate-900 placeholder:text-slate-400 focus:border-primary focus:ring-primary dark:border-slate-700 dark:bg-[#111a22] dark:text-white dark:placeholder:text-slate-500 sm:text-sm sm:leading-6 h-12 pl-10"
                placeholder="INGRESA TU USUARIO"
                value={username}
                onChange={e => setUsername(e.target.value)}
              />
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <User size={18} className="text-slate-400" />
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300" htmlFor="password">
              CONTRASEÑA
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                required
                className="block w-full rounded-lg border-slate-300 bg-slate-50 p-2.5 text-slate-900 placeholder:text-slate-400 focus:border-primary focus:ring-primary dark:border-slate-700 dark:bg-[#111a22] dark:text-white dark:placeholder:text-slate-500 sm:text-sm sm:leading-6 h-12 pr-10"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-500 dark:hover:text-slate-300 focus:outline-none"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>
            {/*<div className="text-sm">
              <a href="#" className="font-medium text-primary hover:text-blue-500 transition-colors">
                Forgot password?
              </a>
            </div>*/}
          <div>
            <button
              type="submit"
              className="group relative flex w-full justify-center rounded-lg bg-primary px-3 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary transition-all duration-200"
              disabled={loading}
            >
              <span className="absolute inset-y-0 left-0 flex items-center pl-3">
                <Lock className="h-5 w-5 text-blue-200 group-hover:text-blue-100" />
              </span>
              {loading ? 'Ingresando...' : 'Ingresar'}
            </button>
          </div>
          {error && <div className="text-red-500 text-sm mt-2 text-center">{error}</div>}
        </form>

        {/*<div className="mt-6 border-t border-slate-200 pt-6 text-center dark:border-slate-700">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            No Posee una Cuenta?{' '}
            <a href="#" className="font-medium text-primary hover:text-blue-500 hover:underline">
              Contacta a un Administrador
            </a>
          </p>
        </div>*/}
      </div>

      <p className="mt-8 text-center text-xs text-slate-400 dark:text-slate-600">
        © 2026 Verificador de Precios Luz. Todos los derechos reservados.
      </p>
    </div>
  );
};