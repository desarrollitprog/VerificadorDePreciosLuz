import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login as loginService, saveToken } from '../services/authService';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await loginService(username, password);
      saveToken(data.access_token);
      navigate('/');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-light dark:bg-background-dark">
      <div className="glass-panel p-8 sm:p-10 rounded-2xl shadow-2xl border border-white/20 dark:border-white/5 w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="h-12 w-12 bg-primary rounded-xl flex items-center justify-center mb-4">
            <span className="material-icons text-white text-3xl">wifi_tethering</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">PConnect</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 font-medium">Portal de Gestión Digital Signage</p>
        </div>
        <form className="space-y-6" onSubmit={handleSubmit}>
          <div className="input-group">
            <label htmlFor="username" className="block text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1.5 ml-1">Usuario</label>
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span className="material-icons text-gray-400 text-xl">person_outline</span>
              </div>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                required
                className="block w-full pl-10 pr-3 py-3 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-slate-850/50 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 sm:text-sm"
                placeholder="usuario123"
                value={username}
                onChange={e => setUsername(e.target.value)}
              />
            </div>
          </div>
          <div className="input-group">
            <label htmlFor="password" className="block text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1.5 ml-1">Contraseña</label>
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span className="material-icons text-gray-400 text-xl">lock_outline</span>
              </div>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="block w-full pl-10 pr-10 py-3 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-slate-850/50 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 sm:text-sm"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input id="remember-me" name="remember-me" type="checkbox" className="h-4 w-4 text-primary focus:ring-primary border-gray-300 dark:border-gray-600 rounded bg-gray-100 dark:bg-gray-800" />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-600 dark:text-gray-300">Recordarme</label>
            </div>
            <div className="text-sm">
              <a href="#" className="font-medium text-primary hover:text-blue-400 hover:underline">¿Olvidaste tu contraseña?</a>
            </div>
          </div>
          {error && <div className="text-red-500 text-sm text-center">{error}</div>}
          <div>
            <button type="submit" className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-semibold rounded-lg text-white bg-primary hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-primary transition-all duration-200 shadow-lg shadow-primary/25 hover:shadow-primary/40 transform hover:-translate-y-0.5" disabled={loading}>
              <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                <span className="material-icons text-blue-300 group-hover:text-blue-200 text-lg">login</span>
              </span>
              {loading ? 'Ingresando...' : 'Iniciar Sesión'}
            </button>
          </div>
        </form>
        <div className="mt-8 text-xs text-gray-400 dark:text-gray-500 text-center">© 2026 PConnect Suite</div>
      </div>
    </div>
  );
};

export default Login;
