import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import DefaultLayout from './Layout/DefaultLayout';
import LoginPage from './pages/LoginPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/*" element={<DefaultLayout />} />
      </Routes>
    </Router>
  );
}

export default App;
