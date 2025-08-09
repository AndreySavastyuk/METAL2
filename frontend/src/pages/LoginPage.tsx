/**
 * Страница входа в систему (выбор роли)
 */
import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Typography,
  Grid,
  Avatar,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  AdminPanelSettings,
  Warehouse,
  Verified as QualityControl,
  Science
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth, UserRole } from '../contexts/AuthContext';

interface RoleOption {
  role: UserRole;
  name: string;
  description: string;
  icon: React.ReactNode;
  color: 'primary' | 'secondary' | 'success' | 'warning';
}

const roleOptions: RoleOption[] = [
  {
    role: 'admin',
    name: 'Администратор',
    description: 'Полный доступ ко всем функциям системы',
    icon: <AdminPanelSettings />,
    color: 'primary'
  },
  {
    role: 'warehouse',
    name: 'Склад',
    description: 'Управление материалами и сертификатами',
    icon: <Warehouse />,
    color: 'success'
  },
  {
    role: 'qc',
    name: 'ОТК',
    description: 'Контроль качества и инспекции',
    icon: <QualityControl />,
    color: 'warning'
  },
  {
    role: 'lab',
    name: 'ЦЗЛ',
    description: 'Лабораторные испытания и анализы',
    icon: <Science />,
    color: 'secondary'
  }
];

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  
  const [selectedRole, setSelectedRole] = useState<UserRole | null>(null);
  const [isLogging, setIsLogging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Получаем путь для редиректа после входа
  const from = (location.state as any)?.from?.pathname || '/';

  const handleRoleSelect = async (role: UserRole) => {
    try {
      setSelectedRole(role);
      setIsLogging(true);
      setError(null);
      
      await login(role);
      
      // Перенаправляем на исходную страницу или главную
      navigate(from, { replace: true });
    } catch (err) {
      setError('Ошибка входа в систему. Попробуйте еще раз.');
      console.error('Login error:', err);
    } finally {
      setIsLogging(false);
      setSelectedRole(null);
    }
  };

  return (
    <Container maxWidth="md">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          py: 4
        }}
      >
        {/* Заголовок */}
        <Box textAlign="center" mb={4}>
          <Typography variant="h3" component="h1" gutterBottom color="primary">
            🏭 MetalQMS
          </Typography>
          <Typography variant="h5" color="text.secondary" gutterBottom>
            Система управления качеством
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Выберите свою роль для входа в систему
          </Typography>
        </Box>

        {/* Ошибка */}
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Роли */}
        <Grid container spacing={3}>
          {roleOptions.map((option) => (
            <Grid item xs={12} sm={6} md={3} key={option.role}>
              <Card
                sx={{
                  height: '100%',
                  cursor: 'pointer',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 4
                  },
                  position: 'relative',
                  ...(selectedRole === option.role && {
                    border: 2,
                    borderColor: 'primary.main'
                  })
                }}
                onClick={() => !isLogging && handleRoleSelect(option.role)}
              >
                <CardContent
                  sx={{
                    textAlign: 'center',
                    p: 3,
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center'
                  }}
                >
                  {/* Иконка роли */}
                  <Box mb={2}>
                    <Avatar
                      sx={{
                        width: 64,
                        height: 64,
                        mx: 'auto',
                        bgcolor: `${option.color}.main`,
                        fontSize: '2rem'
                      }}
                    >
                      {option.icon}
                    </Avatar>
                  </Box>

                  {/* Название роли */}
                  <Typography variant="h6" component="h2" gutterBottom>
                    {option.name}
                  </Typography>

                  {/* Описание роли */}
                  <Typography 
                    variant="body2" 
                    color="text.secondary"
                    sx={{ mb: 2, flexGrow: 1 }}
                  >
                    {option.description}
                  </Typography>

                  {/* Кнопка или индикатор загрузки */}
                  {isLogging && selectedRole === option.role ? (
                    <CircularProgress size={24} />
                  ) : (
                    <Button
                      variant="contained"
                      color={option.color}
                      size="small"
                      disabled={isLogging}
                    >
                      Войти
                    </Button>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Информация о системе */}
        <Box textAlign="center" mt={4}>
          <Typography variant="body2" color="text.secondary">
            MetalQMS v1.0.0 - Система для контроля качества металлургического производства
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default LoginPage;