import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import LoginPage from './pages/LoginPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        {/* Aquí puedes agregar tu layout o dashboard personalizado más adelante */}
      </Routes>
    </Router>
  );
}

export default App;
