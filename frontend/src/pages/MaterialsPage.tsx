/**
 * Страница списка материалов
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
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
  TextField,
  InputAdornment,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  TablePagination
} from '@mui/material';
import {
  Add,
  Search,
  Visibility,
  Edit,
  QrCode,
  FilterList,
  Download
} from '@mui/icons-material';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { useAuth } from '../contexts/AuthContext';

interface Material {
  id: number;
  grade: string;
  size: string;
  supplier: string;
  order_number: string;
  certificate_number: string;
  heat_number: string;
  status: string;
  created_at: string;
  requires_ppsd: boolean;
  qr_code?: string;
}

const MaterialsPage: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [supplierFilter, setSupplierFilter] = useState('');

  // Загрузка материалов
  const { data: materialsData, isLoading, error } = useQuery({
    queryKey: ['materials', page, rowsPerPage, searchQuery, statusFilter, supplierFilter],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: (page + 1).toString(),
        page_size: rowsPerPage.toString(),
        ...(searchQuery && { search: searchQuery }),
        ...(statusFilter && { status: statusFilter }),
        ...(supplierFilter && { supplier: supplierFilter })
      });

      const response = await fetch(`/api/v1/materials/?${params}`);
      if (!response.ok) {
        throw new Error('Ошибка загрузки материалов');
      }
      return response.json();
    }
  });

  // Загрузка справочников для фильтров
  const { data: suppliers } = useQuery({
    queryKey: ['suppliers'],
    queryFn: async () => {
      const response = await fetch('/api/v1/suppliers/');
      if (!response.ok) {
        throw new Error('Ошибка загрузки поставщиков');
      }
      return response.json();
    }
  });

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'received': return 'info';
      case 'qc_pending': return 'warning';
      case 'lab_testing': return 'secondary';
      case 'production_ready': return 'success';
      case 'rejected': return 'error';
      default: return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'received': return 'Получен';
      case 'qc_pending': return 'Ожидает ОТК';
      case 'lab_testing': return 'В лаборатории';
      case 'production_ready': return 'Готов к производству';
      case 'rejected': return 'Отклонен';
      default: return status;
    }
  };

  if (error) {
    return (
      <Alert severity="error">
        Ошибка загрузки материалов. Попробуйте обновить страницу.
      </Alert>
    );
  }

  const materials = materialsData?.results || [];
  const totalCount = materialsData?.count || 0;

  return (
    <Box>
      {/* Заголовок и действия */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Материалы
        </Typography>
        {hasPermission('materials.create') && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => navigate('/materials/new')}
          >
            Добавить материал
          </Button>
        )}
      </Box>

      {/* Фильтры и поиск */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Поиск"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
                placeholder="Марка, поставщик, номер..."
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>Статус</InputLabel>
                <Select
                  value={statusFilter}
                  label="Статус"
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <MenuItem value="">Все статусы</MenuItem>
                  <MenuItem value="received">Получен</MenuItem>
                  <MenuItem value="qc_pending">Ожидает ОТК</MenuItem>
                  <MenuItem value="lab_testing">В лаборатории</MenuItem>
                  <MenuItem value="production_ready">Готов к производству</MenuItem>
                  <MenuItem value="rejected">Отклонен</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>Поставщик</InputLabel>
                <Select
                  value={supplierFilter}
                  label="Поставщик"
                  onChange={(e) => setSupplierFilter(e.target.value)}
                >
                  <MenuItem value="">Все поставщики</MenuItem>
                  {suppliers?.map((supplier: any) => (
                    <MenuItem key={supplier.id} value={supplier.name}>
                      {supplier.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={2}>
              <Button
                fullWidth
                variant="outlined"
                startIcon={<FilterList />}
                onClick={() => {
                  setSearchQuery('');
                  setStatusFilter('');
                  setSupplierFilter('');
                }}
              >
                Сбросить
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Таблица материалов */}
      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Материал</TableCell>
                <TableCell>Поставщик</TableCell>
                <TableCell>Заказ/Сертификат</TableCell>
                <TableCell>Статус</TableCell>
                <TableCell>Дата создания</TableCell>
                <TableCell>Действия</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : materials.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <Typography variant="body2" color="text.secondary">
                      {searchQuery || statusFilter || supplierFilter 
                        ? 'Материалы не найдены по заданным фильтрам'
                        : 'Материалы еще не добавлены'
                      }
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                materials.map((material: Material) => (
                  <TableRow key={material.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        #{material.id}
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      <Box>
                        <Typography variant="body2" fontWeight="medium">
                          {material.grade} - {material.size}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Плавка: {material.heat_number}
                        </Typography>
                        {material.requires_ppsd && (
                          <Chip 
                            label="ППСД" 
                            size="small" 
                            color="warning" 
                            sx={{ ml: 1 }}
                          />
                        )}
                      </Box>
                    </TableCell>
                    
                    <TableCell>
                      <Typography variant="body2">
                        {material.supplier}
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      <Typography variant="body2">
                        Заказ: {material.order_number}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Сертификат: {material.certificate_number}
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      <Chip
                        label={getStatusText(material.status)}
                        color={getStatusColor(material.status)}
                        size="small"
                        variant="filled"
                      />
                    </TableCell>
                    
                    <TableCell>
                      <Typography variant="body2">
                        {format(new Date(material.created_at), 'dd.MM.yyyy', { locale: ru })}
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      <Box display="flex" gap={0.5}>
                        <Tooltip title="Просмотр">
                          <IconButton 
                            size="small"
                            onClick={() => navigate(`/materials/${material.id}`)}
                          >
                            <Visibility />
                          </IconButton>
                        </Tooltip>
                        
                        {hasPermission('materials.edit') && (
                          <Tooltip title="Редактировать">
                            <IconButton 
                              size="small"
                              onClick={() => navigate(`/materials/${material.id}/edit`)}
                            >
                              <Edit />
                            </IconButton>
                          </Tooltip>
                        )}
                        
                        {material.qr_code && (
                          <Tooltip title="QR код">
                            <IconButton 
                              size="small"
                              onClick={() => window.open(material.qr_code, '_blank')}
                            >
                              <QrCode />
                            </IconButton>
                          </Tooltip>
                        )}
                        
                        <Tooltip title="Экспорт">
                          <IconButton 
                            size="small"
                            onClick={() => window.open(`/api/v1/materials/${material.id}/export/`, '_blank')}
                          >
                            <Download />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        
        {/* Пагинация */}
        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div"
          count={totalCount}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          labelRowsPerPage="Строк на странице:"
          labelDisplayedRows={({ from, to, count }) => 
            `${from}-${to} из ${count !== -1 ? count : `более чем ${to}`}`
          }
        />
      </Card>
    </Box>
  );
};

export default MaterialsPage;