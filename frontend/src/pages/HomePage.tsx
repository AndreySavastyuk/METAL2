/**
 * Главная страница MetalQMS
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,

  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
  Alert,
  Paper,
  Chip
} from '@mui/material';
import {
  Inventory,
  Assignment,
  Science,
  Factory,
  TrendingUp,
  Schedule,
  CheckCircle,
  Warning,
  Add,
  Visibility
} from '@mui/icons-material';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useAuth } from '../contexts/AuthContext';

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { user, hasPermission } = useAuth();

  // Загрузка данных для дашборда
  const { data: dashboardData } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const response = await fetch('/api/v1/dashboard/');
      if (!response.ok) {
        throw new Error('Ошибка загрузки данных дашборда');
      }
      return response.json();
    }
  });

  // Быстрые действия в зависимости от роли
  const getQuickActions = () => {
    const actions = [];
    
    if (hasPermission('materials.create')) {
      actions.push({
        title: 'Добавить материал',
        description: 'Зарегистрировать новый материал в системе',
        icon: <Add />,
        color: 'primary' as const,
        path: '/materials/new'
      });
    }
    
    if (hasPermission('inspections.create')) {
      actions.push({
        title: 'Создать инспекцию',
        description: 'Назначить контроль качества материала',
        icon: <Assignment />,
        color: 'warning' as const,
        path: '/qc/inspections/new'
      });
    }
    
    if (hasPermission('tests.create')) {
      actions.push({
        title: 'Новый тест',
        description: 'Создать лабораторное испытание',
        icon: <Science />,
        color: 'secondary' as const,
        path: '/lab/tests/new'
      });
    }
    
    actions.push({
      title: 'Просмотр материалов',
      description: 'Посмотреть все материалы в системе',
      icon: <Visibility />,
      color: 'success' as const,
      path: '/materials'
    });

    return actions;
  };

  const quickActions = getQuickActions();

  // Статистические карточки
  const statisticsCards = [
    {
      title: 'Всего материалов',
      value: dashboardData?.total_materials || 0,
      icon: <Inventory />,
      color: '#1976d2',
      change: dashboardData?.materials_change || 0
    },
    {
      title: 'Активные инспекции',
      value: dashboardData?.active_inspections || 0,
      icon: <Assignment />,
      color: '#ed6c02',
      change: dashboardData?.inspections_change || 0
    },
    {
      title: 'Тестов в работе',
      value: dashboardData?.active_tests || 0,
      icon: <Science />,
      color: '#9c27b0',
      change: dashboardData?.tests_change || 0
    },
    {
      title: 'Готово к производству',
      value: dashboardData?.ready_for_production || 0,
      icon: <Factory />,
      color: '#2e7d32',
      change: dashboardData?.production_change || 0
    }
  ];

  return (
    <Box>
      {/* Приветствие */}
      <Box mb={4}>
        <Typography variant="h4" component="h1" gutterBottom>
          Добро пожаловать, {user?.name}!
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {format(new Date(), 'EEEE, d MMMM yyyy', { locale: ru })}
        </Typography>
      </Box>

      {/* Статистика */}
      <Grid container spacing={3} mb={4}>
        {statisticsCards.map((card, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography variant="h4" component="div" fontWeight="bold">
                      {card.value}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {card.title}
                    </Typography>
                    {card.change !== 0 && (
                      <Box display="flex" alignItems="center" mt={1}>
                        <TrendingUp 
                          sx={{ 
                            fontSize: 16, 
                            mr: 0.5, 
                            color: card.change > 0 ? 'success.main' : 'error.main' 
                          }} 
                        />
                        <Typography 
                          variant="caption" 
                          color={card.change > 0 ? 'success.main' : 'error.main'}
                        >
                          {card.change > 0 ? '+' : ''}{card.change}%
                        </Typography>
                      </Box>
                    )}
                  </Box>
                  <Avatar sx={{ bgcolor: card.color, width: 56, height: 56 }}>
                    {card.icon}
                  </Avatar>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        {/* Быстрые действия */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Быстрые действия
              </Typography>
              <Grid container spacing={2}>
                {quickActions.map((action, index) => (
                  <Grid item xs={12} sm={6} key={index}>
                    <Paper
                      sx={{
                        p: 2,
                        cursor: 'pointer',
                        transition: 'transform 0.2s, box-shadow 0.2s',
                        '&:hover': {
                          transform: 'translateY(-2px)',
                          boxShadow: 2
                        }
                      }}
                      onClick={() => navigate(action.path)}
                    >
                      <Box display="flex" alignItems="center" mb={1}>
                        <Avatar 
                          sx={{ 
                            bgcolor: `${action.color}.main`, 
                            width: 40, 
                            height: 40,
                            mr: 2 
                          }}
                        >
                          {action.icon}
                        </Avatar>
                        <Typography variant="subtitle1" fontWeight="medium">
                          {action.title}
                        </Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        {action.description}
                      </Typography>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Последние действия */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Последние действия
              </Typography>
              {dashboardData?.recent_activities?.length > 0 ? (
                <List>
                  {dashboardData.recent_activities.slice(0, 5).map((activity: any) => (
                    <React.Fragment key={activity.id}>
                      <ListItem alignItems="flex-start" sx={{ px: 0 }}>
                        <ListItemAvatar>
                          <Avatar sx={{ bgcolor: getActivityColor(activity.type) }}>
                            {getActivityIcon(activity.type)}
                          </Avatar>
                        </ListItemAvatar>
                        <ListItemText
                          primary={activity.description}
                          secondary={
                            <Box display="flex" alignItems="center" gap={1}>
                              <Typography variant="caption" color="text.secondary">
                                {format(new Date(activity.timestamp), 'dd.MM.yyyy HH:mm', { locale: ru })}
                              </Typography>
                              <Chip 
                                label={activity.user} 
                                size="small" 
                                variant="outlined" 
                              />
                            </Box>
                          }
                        />
                      </ListItem>
                      <Divider variant="inset" component="li" />
                    </React.Fragment>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary" textAlign="center">
                  Нет записей о последних действиях
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* График активности */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Активность за последние 7 дней
              </Typography>
              {dashboardData?.activity_chart ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={dashboardData.activity_chart}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip 
                      labelFormatter={(value) => format(new Date(value), 'dd.MM.yyyy', { locale: ru })}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="materials" 
                      stroke="#1976d2" 
                      name="Материалы" 
                      strokeWidth={2}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="inspections" 
                      stroke="#ed6c02" 
                      name="Инспекции" 
                      strokeWidth={2}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="tests" 
                      stroke="#9c27b0" 
                      name="Тесты" 
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Box textAlign="center" py={4}>
                  <Typography variant="body2" color="text.secondary">
                    Данные графика недоступны
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Уведомления */}
        {dashboardData?.notifications?.length > 0 && (
          <Grid item xs={12}>
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Уведомления
              </Typography>
              {dashboardData.notifications.map((notification: any) => (
                <Typography key={notification.id} variant="body2">
                  • {notification.message}
                </Typography>
              ))}
            </Alert>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

// Вспомогательные функции
const getActivityColor = (type: string) => {
  switch (type) {
    case 'material_created': return 'primary.main';
    case 'inspection_started': return 'warning.main';
    case 'test_completed': return 'success.main';
    case 'material_rejected': return 'error.main';
    default: return 'grey.500';
  }
};

const getActivityIcon = (type: string) => {
  switch (type) {
    case 'material_created': return <Add />;
    case 'inspection_started': return <Assignment />;
    case 'test_completed': return <CheckCircle />;
    case 'material_rejected': return <Warning />;
    default: return <Schedule />;
  }
};

export default HomePage;