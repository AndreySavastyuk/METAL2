/**
 * Главный компонент приложения MetalQMS с маршрутизацией
 */
import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import { Box, CircularProgress, Typography } from '@mui/material';

// Компоненты layout и auth
import Layout from './components/layout/Layout';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Страницы
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import MaterialsPage from './pages/MaterialsPage';
import MaterialDetailPage from './pages/MaterialDetailPage';
import MaterialFormPage from './pages/MaterialFormPage';
import QCDashboard from './pages/QCDashboard';
import LaboratoryPage from './pages/LaboratoryPage';
import ProductionPage from './pages/ProductionPage';

// Компонент загрузки
const LoadingScreen: React.FC = () => (
  <Box
    display="flex"
    flexDirection="column"
    justifyContent="center"
    alignItems="center"
    minHeight="100vh"
    bgcolor="#f5f5f5"
  >
    <CircularProgress size={48} sx={{ mb: 2 }} />
    <Typography variant="h6" color="primary" gutterBottom>
      🏭 MetalQMS
    </Typography>
    <Typography variant="body1" color="text.secondary">
      Загрузка системы управления качеством...
    </Typography>
  </Box>
);

const App: React.FC = () => {
  const { isLoading, isAuthenticated } = useAuth();

  // Показываем экран загрузки пока проверяем аутентификацию
  if (isLoading) {
    return <LoadingScreen />;
  }

  // Если пользователь не аутентифицирован, показываем только страницу входа
  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  // Основные маршруты для аутентифицированных пользователей
  return (
    <Layout>
      <Routes>
        {/* Главная страница */}
        <Route path="/" element={<HomePage />} />

        {/* Материалы */}
        <Route path="/materials" element={
          <ProtectedRoute requiredPermission="materials.view">
            <MaterialsPage />
          </ProtectedRoute>
        } />
        
        <Route path="/materials/new" element={
          <ProtectedRoute requiredPermission="materials.create">
            <MaterialFormPage />
          </ProtectedRoute>
        } />
        
        <Route path="/materials/:id" element={
          <ProtectedRoute requiredPermission="materials.view">
            <MaterialDetailPage />
          </ProtectedRoute>
        } />
        
        <Route path="/materials/:id/edit" element={
          <ProtectedRoute requiredPermission="materials.edit">
            <MaterialFormPage />
          </ProtectedRoute>
        } />

        {/* Контроль качества (ОТК) */}
        <Route path="/qc/*" element={
          <ProtectedRoute requiredPermission="inspections.view">
            <Routes>
              <Route path="inspections" element={<QCDashboard />} />
              <Route path="inspections/new" element={<QCDashboard />} />
              <Route path="inspections/:id" element={<QCDashboard />} />
              <Route path="reports" element={<QCDashboard />} />
            </Routes>
          </ProtectedRoute>
        } />

        {/* Лаборатория (ЦЗЛ) */}
        <Route path="/lab/*" element={
          <ProtectedRoute requiredPermission="tests.view">
            <Routes>
              <Route path="tests" element={<LaboratoryPage />} />
              <Route path="tests/new" element={<LaboratoryPage />} />
              <Route path="tests/:id" element={<LaboratoryPage />} />
              <Route path="equipment" element={<LaboratoryPage />} />
              <Route path="reports" element={<LaboratoryPage />} />
            </Routes>
          </ProtectedRoute>
        } />

        {/* Производство */}
        <Route path="/production" element={
          <ProtectedRoute requiredPermission="production.view">
            <ProductionPage />
          </ProtectedRoute>
        } />

        {/* Перенаправление на страницу входа */}
        <Route path="/login" element={<Navigate to="/" replace />} />

        {/* 404 страница */}
        <Route path="*" element={
          <Box
            display="flex"
            flexDirection="column"
            justifyContent="center"
            alignItems="center"
            minHeight="50vh"
            textAlign="center"
          >
            <Typography variant="h1" color="primary" gutterBottom>
              404
            </Typography>
            <Typography variant="h4" gutterBottom>
              Страница не найдена
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              Запрашиваемая страница не существует или была удалена.
            </Typography>
          </Box>
        } />
      </Routes>
    </Layout>
  );
};

export default App;