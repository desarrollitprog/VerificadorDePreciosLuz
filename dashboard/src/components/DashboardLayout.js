import React from 'react';
import Sidebar from './Sidebar';
import Header from './Header';
import StatsCards from './StatsCards';
import BannerForm from './BannerForm';
import BannerTable from './BannerTable';

const DashboardLayout = ({ banners, onBannerView, onBannerEdit, onBannerDelete, onBannerSubmit }) => (
  <div className="app-container">
    <Sidebar />
    <main className="main-content">
      <Header />
      <StatsCards />
      <BannerForm onSubmit={onBannerSubmit} />
      <BannerTable
        banners={banners}
        onView={onBannerView}
        onEdit={onBannerEdit}
        onDelete={onBannerDelete}
      />
    </main>
  </div>
);

export default DashboardLayout;