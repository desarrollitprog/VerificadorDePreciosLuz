import React, { useState } from 'react';
import axios from 'axios';

function LoginForm({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const res = await axios.post('/api/auth/login', {
        username,
        password
      });
      localStorage.setItem('token', res.data.access_token);
      onLogin();
    } catch (err) {
      setError('Credenciales incorrectas');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4">
      <h2>Iniciar sesión</h2>
      {error && <div className="alert alert-danger">{error}</div>}
      <div className="mb-3">
        <input className="form-control" placeholder="Usuario" value={username} onChange={e => setUsername(e.target.value)} />
      </div>
      <div className="mb-3">
        <input className="form-control" type="password" placeholder="Contraseña" value={password} onChange={e => setPassword(e.target.value)} />
      </div>
      <button className="btn btn-primary" type="submit">Entrar</button>
    </form>
  );
}

export default LoginForm;
