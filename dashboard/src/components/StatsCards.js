import React from 'react';
import './StatsCards.css'; // Puedes mover los estilos aquí si lo deseas

const stats = [
  {
    label: 'Banners Activos',
    value: '24',
    change: '↑ 12% vs mes anterior',
    icon: '🎯',
    changeClass: 'positive',
  },
  {
    label: 'Impresiones Totales',
    value: '127.5k',
    change: '↑ 23% esta semana',
    icon: '👁️',
    changeClass: 'positive',
  },
  {
    label: 'CTR Promedio',
    value: '4.2%',
    change: '↑ 0.8% mejora',
    icon: '📊',
    changeClass: 'positive',
  },
  {
    label: 'Ingresos Generados',
    value: '$12.4k',
    change: '↑ $2.1k este mes',
    icon: '💰',
    changeClass: 'positive',
  },
];

const StatsCards = () => (
  <div className="stats-grid animate-in">
    {stats.map((stat, idx) => (
      <div className="stat-card" key={idx}>
        <div className="stat-header">
          <div>
            <div className="stat-label">{stat.label}</div>
            <div className="stat-value">{stat.value}</div>
            <span className={`stat-change ${stat.changeClass}`}>{stat.change}</span>
          </div>
          <div className="stat-icon">{stat.icon}</div>
        </div>
      </div>
    ))}
  </div>
);

export default StatsCards;
