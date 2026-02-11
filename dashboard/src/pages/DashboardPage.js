import React from 'react';
import BannerForm from '../components/BannerForm';
import BannerTable from '../components/BannerTable';

function DashboardPage() {
  // TODO: Lógica de dashboard principal
  return (
    <div>
      <BannerForm onUpload={() => {}} />
      <BannerTable banners={[]} onDelete={() => {}} onToggle={() => {}} />
    </div>
  );
}

export default DashboardPage;
