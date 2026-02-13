// Configuración de la barra lateral para tu modelo
export default [
  {
    component: 'CNavItem',
    name: 'Dashboard',
    to: '/dashboard',
    icon: 'cil-speedometer',
  },
  {
    component: 'CNavItem',
    name: 'Banners',
    to: '/dashboard',
    icon: 'cil-image',
  },
  // Puedes agregar más secciones aquí según tu modelo
  // Ejemplo:
  // {
  //   component: 'CNavItem',
  //   name: 'Usuarios',
  //   to: '/usuarios',
  //   icon: 'cil-user',
  // },
];
