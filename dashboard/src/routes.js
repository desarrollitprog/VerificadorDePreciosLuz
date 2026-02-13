// Configuración de rutas para el layout principal
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';

const routes = [
  { path: '/dashboard', name: 'Dashboard', element: DashboardPage },
  // Puedes agregar más rutas aquí según tu modelo
  // { path: '/usuarios', name: 'Usuarios', element: UsuariosPage },
];

export default routes;
