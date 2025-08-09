/**
 * Компонент защищенного маршрута
 */
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth, UserRole } from '../../contexts/AuthContext';
import { Box, CircularProgress, Typography } from '@mui/material';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: UserRole;
  requiredPermission?: string;
  redirectTo?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
  requiredPermission,
  redirectTo = '/login'
}) => {
  const { isAuthenticated, isLoading, user, hasPermission, hasRole } = useAuth();
  const location = useLocation();

  // Показываем загрузку пока проверяем аутентификацию
  if (isLoading) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
      >
        <CircularProgress size={48} />
        <Typography variant="body1" sx={{ mt: 2 }}>
          Проверка аутентификации...
        </Typography>
      </Box>
    );
  }

  // Если не аутентифицирован, перенаправляем на логин
  if (!isAuthenticated) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />;
  }

  // Проверяем роль если требуется
  if (requiredRole && !hasRole(requiredRole)) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        p={3}
      >
        <Typography variant="h4" color="error" gutterBottom>
          🚫 Доступ запрещен
        </Typography>
        <Typography variant="body1" color="textSecondary" textAlign="center">
          У вас нет прав для доступа к этой странице.
          <br />
          Требуется роль: <strong>{requiredRole}</strong>
          <br />
          Ваша роль: <strong>{user?.role}</strong>
        </Typography>
      </Box>
    );
  }

  // Проверяем разрешение если требуется
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        p={3}
      >
        <Typography variant="h4" color="error" gutterBottom>
          🚫 Недостаточно прав
        </Typography>
        <Typography variant="body1" color="textSecondary" textAlign="center">
          У вас нет прав для выполнения этого действия.
          <br />
          Требуется разрешение: <strong>{requiredPermission}</strong>
        </Typography>
      </Box>
    );
  }

  // Если все проверки пройдены, показываем дочерние компоненты
  return <>{children}</>;
};

export default ProtectedRoute;