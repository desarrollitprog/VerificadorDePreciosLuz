import React, { useState } from 'react';
import { loginStart } from '../services/authService';

const Login: React.FC<{ onLoginSuccess: () => void }> = () => {
  const [username, setUsername] = useState('');
  const [correo, setCorreo] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await loginStart(username, correo, password);
      setError('Este formulario es legacy. Usa la pantalla principal para completar 2FA.');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-dark">
      <form onSubmit={handleSubmit} className="bg-[#1f2b38] p-8 rounded-xl shadow-lg w-full max-w-sm flex flex-col gap-4">
        <h2 className="text-2xl font-bold text-white mb-2">Iniciar sesión</h2>
        <input
          type="text"
          placeholder="Usuario"
          className="px-4 py-2 rounded bg-background-dark border border-border-dark text-white focus:outline-none focus:ring-2 focus:ring-primary"
          value={username}
          onChange={e => setUsername(e.target.value)}
          required
        />
        <input
          type="email"
          placeholder="Correo"
          className="px-4 py-2 rounded bg-background-dark border border-border-dark text-white focus:outline-none focus:ring-2 focus:ring-primary"
          value={correo}
          onChange={e => setCorreo(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Contraseña"
          className="px-4 py-2 rounded bg-background-dark border border-border-dark text-white focus:outline-none focus:ring-2 focus:ring-primary"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
        />
        {error && <div className="text-red-400 text-sm">{error}</div>}
        <button
          type="submit"
          className="bg-primary text-white py-2 rounded font-semibold hover:bg-primary/90 transition-all disabled:opacity-60"
          disabled={loading}
        >
          {loading ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </div>
  );
};

export default Login;
