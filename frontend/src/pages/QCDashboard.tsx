/**
 * Панель управления ОТК (Отдел технического контроля)
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
  Tab,
  Tabs,
  Badge,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider
} from '@mui/material';
import {
  Assignment,
  Visibility,
  // Edit,
  CheckCircle,

  Schedule,
  TrendingUp,
  Assessment,
  Add,
  FilterList
} from '@mui/icons-material';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div hidden={value !== index}>
    {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
  </div>
);

const QCDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0);

  // Загрузка данных инспекций
  const { data: inspectionsData, isLoading: inspectionsLoading } = useQuery({
    queryKey: ['qc-inspections'],
    queryFn: async () => {
      const response = await fetch('/api/v1/qc/inspections/dashboard/');
      if (!response.ok) {
        throw new Error('Ошибка загрузки данных инспекций');
      }
      return response.json();
    }
  });

  // Загрузка статистики
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['qc-stats'],
    queryFn: async () => {
      const response = await fetch('/api/v1/qc/stats/');
      if (!response.ok) {
        throw new Error('Ошибка загрузки статистики');
      }
      return response.json();
    }
  });

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'warning';
      case 'in_progress': return 'info';
      case 'completed': return 'success';
      case 'rejected': return 'error';
      default: return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending': return 'Ожидает';
      case 'in_progress': return 'В работе';
      case 'completed': return 'Завершена';
      case 'rejected': return 'Отклонена';
      default: return status;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  const getPriorityText = (priority: string) => {
    switch (priority) {
      case 'high': return 'Высокий';
      case 'medium': return 'Средний';
      case 'low': return 'Низкий';
      default: return priority;
    }
  };

  if (inspectionsLoading || statsLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  // Данные для графиков
  const chartData = statsData?.daily_inspections || [];
  const pieData = [
    { name: 'Завершены', value: statsData?.completed_inspections || 0, color: '#4caf50' },
    { name: 'В работе', value: statsData?.in_progress_inspections || 0, color: '#2196f3' },
    { name: 'Ожидают', value: statsData?.pending_inspections || 0, color: '#ff9800' },
    { name: 'Отклонены', value: statsData?.rejected_inspections || 0, color: '#f44336' }
  ];

  return (
    <Box>
      {/* Заголовок */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Панель ОТК
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => navigate('/qc/inspections/new')}
        >
          Новая инспекция
        </Button>
      </Box>

      {/* Статистические карточки */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Schedule color="warning" sx={{ mr: 2, fontSize: 40 }} />
                <Box>
                  <Typography variant="h4" component="div">
                    {statsData?.pending_inspections || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Ожидают инспекции
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Assignment color="info" sx={{ mr: 2, fontSize: 40 }} />
                <Box>
                  <Typography variant="h4" component="div">
                    {statsData?.in_progress_inspections || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    В работе
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <CheckCircle color="success" sx={{ mr: 2, fontSize: 40 }} />
                <Box>
                  <Typography variant="h4" component="div">
                    {statsData?.completed_today || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Завершено сегодня
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <TrendingUp color="primary" sx={{ mr: 2, fontSize: 40 }} />
                <Box>
                  <Typography variant="h4" component="div">
                    {statsData?.efficiency_percentage || 0}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Эффективность
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Основная панель */}
        <Grid item xs={12} lg={8}>
          <Card>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={activeTab} onChange={handleTabChange}>
                <Tab 
                  label={
                    <Badge badgeContent={statsData?.pending_inspections || 0} color="warning">
                      Ожидающие
                    </Badge>
                  } 
                  icon={<Schedule />} 
                />
                <Tab 
                  label={
                    <Badge badgeContent={statsData?.my_tasks || 0} color="primary">
                      Мои задачи
                    </Badge>
                  } 
                  icon={<Assignment />} 
                />
                <Tab label="Статистика" icon={<Assessment />} />
              </Tabs>
            </Box>

            <TabPanel value={activeTab} index={0}>
              {/* Ожидающие инспекции */}
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Материал</TableCell>
                      <TableCell>Поставщик</TableCell>
                      <TableCell>Приоритет</TableCell>
                      <TableCell>Дата создания</TableCell>
                      <TableCell>Действия</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {inspectionsData?.pending?.map((inspection: any) => (
                      <TableRow key={inspection.id}>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            {inspection.material.grade} - {inspection.material.size}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            #{inspection.material.id}
                          </Typography>
                        </TableCell>
                        <TableCell>{inspection.material.supplier}</TableCell>
                        <TableCell>
                          <Chip
                            label={getPriorityText(inspection.priority)}
                            color={getPriorityColor(inspection.priority)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          {format(new Date(inspection.created_at), 'dd.MM.yyyy', { locale: ru })}
                        </TableCell>
                        <TableCell>
                          <Tooltip title="Просмотр">
                            <IconButton 
                              size="small"
                              onClick={() => navigate(`/materials/${inspection.material.id}`)}
                            >
                              <Visibility />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Начать инспекцию">
                            <IconButton 
                              size="small"
                              onClick={() => navigate(`/qc/inspections/${inspection.id}`)}
                            >
                              <Assignment />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    )) || (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          <Typography variant="body2" color="text.secondary">
                            Нет ожидающих инспекций
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </TabPanel>

            <TabPanel value={activeTab} index={1}>
              {/* Мои задачи */}
              <List>
                {inspectionsData?.my_tasks?.map((task: any) => (
                  <React.Fragment key={task.id}>
                    <ListItem>
                      <ListItemText
                        primary={
                          <Box display="flex" alignItems="center" gap={1}>
                            <Typography variant="body1">
                              {task.material.grade} - {task.material.size}
                            </Typography>
                            <Chip
                              label={getStatusText(task.status)}
                              color={getStatusColor(task.status)}
                              size="small"
                            />
                          </Box>
                        }
                        secondary={
                          <Typography variant="body2" color="text.secondary">
                            Поставщик: {task.material.supplier} • 
                            Создано: {format(new Date(task.created_at), 'dd.MM.yyyy HH:mm', { locale: ru })}
                          </Typography>
                        }
                      />
                      <ListItemSecondaryAction>
                        <Tooltip title="Просмотр">
                          <IconButton 
                            onClick={() => navigate(`/qc/inspections/${task.id}`)}
                          >
                            <Visibility />
                          </IconButton>
                        </Tooltip>
                      </ListItemSecondaryAction>
                    </ListItem>
                    <Divider />
                  </React.Fragment>
                )) || (
                  <Typography variant="body2" color="text.secondary" textAlign="center">
                    Нет назначенных задач
                  </Typography>
                )}
              </List>
            </TabPanel>

            <TabPanel value={activeTab} index={2}>
              {/* Статистика */}
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>
                    Инспекции по дням
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <RechartsTooltip />
                      <Bar dataKey="count" fill="#1976d2" />
                    </BarChart>
                  </ResponsiveContainer>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>
                    Распределение по статусам
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <RechartsTooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Grid>
              </Grid>
            </TabPanel>
          </Card>
        </Grid>

        {/* Боковая панель */}
        <Grid item xs={12} lg={4}>
          <Grid container spacing={2}>
            {/* Быстрые действия */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Быстрые действия
                  </Typography>
                  <Box display="flex" flexDirection="column" gap={1}>
                    <Button
                      variant="contained"
                      startIcon={<Add />}
                      fullWidth
                      onClick={() => navigate('/qc/inspections/new')}
                    >
                      Новая инспекция
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<Assessment />}
                      fullWidth
                      onClick={() => navigate('/qc/reports')}
                    >
                      Отчеты
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<FilterList />}
                      fullWidth
                      onClick={() => navigate('/qc/inspections?filter=my')}
                    >
                      Мои инспекции
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Уведомления */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Уведомления
                  </Typography>
                  {statsData?.notifications?.length > 0 ? (
                    <List dense>
                      {statsData.notifications.map((notification: any) => (
                        <ListItem key={notification.id}>
                          <ListItemText
                            primary={notification.title}
                            secondary={notification.message}
                          />
                        </ListItem>
                      ))}
                    </List>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Нет новых уведомлений
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Последние действия */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Последние действия
                  </Typography>
                  {statsData?.recent_activities?.length > 0 ? (
                    <List dense>
                      {statsData.recent_activities.map((activity: any, index: number) => (
                        <React.Fragment key={index}>
                          <ListItem>
                            <ListItemText
                              primary={activity.description}
                              secondary={format(new Date(activity.timestamp), 'dd.MM.yyyy HH:mm', { locale: ru })}
                            />
                          </ListItem>
                          {index < statsData.recent_activities.length - 1 && <Divider />}
                        </React.Fragment>
                      ))}
                    </List>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Нет записей о действиях
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
};

export default QCDashboard;