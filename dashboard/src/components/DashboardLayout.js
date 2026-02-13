import React from 'react';
import Sidebar from './Sidebar';
import Header from './Header';
import StatsCards from './StatsCards';
import BannerForm from './BannerForm';
import BannerTable from './BannerTable';
import './Sidebar.css';
import './app-flex-layout.css';

const DashboardLayout = ({ banners, onBannerView, onBannerEdit, onBannerDelete, onBannerSubmit }) => (
  <div className="app-flex-layout">
    <Sidebar />
    <div className="main-flex-content">
      <Header />
      <StatsCards />
      <BannerForm onSubmit={onBannerSubmit} />
      <BannerTable
        banners={banners}
        onView={onBannerView}
        onEdit={onBannerEdit}
        onDelete={onBannerDelete}
      />
    </div>
  </div>
);

export default DashboardLayout;