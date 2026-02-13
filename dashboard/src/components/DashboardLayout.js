// src/components/DashboardLayout.js
import React from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';

const DashboardLayout = ({ children }) => (
  <div>
    {/* Navbar */}
    <nav className="navbar navbar-dark bg-dark px-3">
      <span className="navbar-brand mb-0 h1">Panel Publicidad Kiosko</span>
      <button className="btn btn-outline-light btn-sm">Cerrar sesión</button>
    </nav>
    <div className="container-fluid">
      <div className="row">
        {/* Sidebar */}
        <nav className="col-md-2 d-none d-md-block bg-light sidebar py-4">
          <div className="sidebar-sticky">
            <ul className="nav flex-column">
              <li className="nav-item">
                <a className="nav-link active" href="#">
                  Banners
                </a>
              </li>
              {/* Puedes agregar más secciones aquí */}
            </ul>
          </div>
        </nav>
        {/* Main content */}
        <main className="col-md-9 ms-sm-auto col-lg-10 px-md-4 py-4">
          {children}
        </main>
      </div>
    </div>
  </div>
);

export default DashboardLayout;