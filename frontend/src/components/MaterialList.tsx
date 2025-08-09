/**
 * Компонент списка материалов с таблицей, фильтрацией и пагинацией
 */
import React, { useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TableSortLabel,
  TextField,
  InputAdornment,
  IconButton,
  Button,
  Chip,
  Typography,
  Skeleton,
  Alert,
  Tooltip,
  Menu,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Grid,

} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  QrCode as QrCodeIcon,
  FileDownload as DownloadIcon,
  Refresh as RefreshIcon,
  MoreVert as MoreVertIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { 
  Material, 
  MaterialListParams, 
  MaterialListFilters,
  MATERIAL_STATUS_CHOICES,
  UNIT_CHOICES,
} from '../types/material';
import { MaterialService } from '../services/materialService';

interface MaterialListProps {
  onEdit?: (material: Material) => void;
  onDelete?: (material: Material) => void;
  onCreate?: () => void;
  onViewQR?: (material: Material) => void;
  showActions?: boolean;
  selectable?: boolean;
  onSelectionChange?: (selectedIds: number[]) => void;
}

type SortOrder = 'asc' | 'desc';

interface SortConfig {
  field: keyof Material | '';
  order: SortOrder;
}

const MaterialList: React.FC<MaterialListProps> = ({
  onEdit,
  onDelete,
  onCreate,
  onViewQR,
  showActions = true,
  selectable = false,
  onSelectionChange,
}) => {
  // const { enqueueSnackbar } = useSnackbar();
  // const queryClient = useQueryClient();

  // State для параметров запроса
  const [params, setParams] = useState<MaterialListParams>({
    page: 1,
    page_size: 25,
    ordering: '-created_at',
  });

  // State для фильтров
  const [filters, setFilters] = useState<MaterialListFilters>({});
  const [showFilters, setShowFilters] = useState(false);

  // State для поиска
  const [searchTerm, setSearchTerm] = useState('');
  const [searchTimeout, setSearchTimeout] = useState<NodeJS.Timeout | null>(null);

  // State для сортировки
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: 'created_at',
    order: 'desc',
  });

  // State для выбора строк
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  // State для меню действий
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedMaterial, setSelectedMaterial] = useState<Material | null>(null);

  // Запрос данных
  const {
    data: materialsData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['materials', params],
    queryFn: () => MaterialService.getMaterials(params),
    // keepPreviousData: true, // deprecated in newer versions
  });

  // Обработка поиска с дебаунсом
  const handleSearch = useCallback((value: string) => {
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }

    const timeout = setTimeout(() => {
      setParams(prev => ({
        ...prev,
        page: 1,
        search: value || undefined,
      }));
    }, 500);

    setSearchTimeout(timeout);
  }, [searchTimeout]);

  // Обработка изменения поискового запроса
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setSearchTerm(value);
    handleSearch(value);
  };

  // Обработка сортировки
  const handleSort = (field: keyof Material) => {
    const newOrder = sortConfig.field === field && sortConfig.order === 'asc' ? 'desc' : 'asc';
    const ordering = newOrder === 'desc' ? `-${field}` : field;
    
    setSortConfig({ field, order: newOrder });
    setParams(prev => ({
      ...prev,
      page: 1,
      ordering,
    }));
  };

  // Обработка пагинации
  const handlePageChange = (_event: unknown, newPage: number) => {
    setParams(prev => ({
      ...prev,
      page: newPage + 1,
    }));
  };

  const handleRowsPerPageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setParams(prev => ({
      ...prev,
      page: 1,
      page_size: parseInt(event.target.value, 10),
    }));
  };

  // Применение фильтров
  const applyFilters = () => {
    setParams(prev => ({
      ...prev,
      page: 1,
      ...filters,
    }));
    setShowFilters(false);
  };

  // Очистка фильтров
  const clearFilters = () => {
    setFilters({});
    setSearchTerm('');
    setParams({
      page: 1,
      page_size: 25,
      ordering: '-created_at',
    });
    setShowFilters(false);
  };

  // Обработка выбора строк
  const handleRowSelect = (id: number, selected: boolean) => {
    if (!selectable) return;

    const newSelected = selected
      ? [...selectedIds, id]
      : selectedIds.filter(selectedId => selectedId !== id);

    setSelectedIds(newSelected);
    onSelectionChange?.(newSelected);
  };

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!selectable || !materialsData) return;

    const newSelected = event.target.checked
      ? (materialsData as any).results?.map((material: any) => material.id)
      : [];

    setSelectedIds(newSelected);
    onSelectionChange?.(newSelected);
  };

  // Меню действий
  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, material: Material) => {
    setAnchorEl(event.currentTarget);
    setSelectedMaterial(material);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedMaterial(null);
  };

  // Действия с материалами
  const handleEdit = () => {
    if (selectedMaterial && onEdit) {
      onEdit(selectedMaterial);
    }
    handleMenuClose();
  };

  const handleDelete = () => {
    if (selectedMaterial && onDelete) {
      onDelete(selectedMaterial);
    }
    handleMenuClose();
  };

  const handleViewQR = () => {
    if (selectedMaterial && onViewQR) {
      onViewQR(selectedMaterial);
    }
    handleMenuClose();
  };

  // Получение статуса с цветом
  const getStatusChip = (_material: Material) => {
    // Предполагаем, что у нас есть связанный receipt
    const status = 'approved'; // Заглушка, должен быть реальный статус
    const statusInfo = MATERIAL_STATUS_CHOICES.find(s => s.value === status);
    
    return (
      <Chip
        label={statusInfo?.label || status}
        size="small"
        sx={{
          backgroundColor: statusInfo?.color || '#grey',
          color: 'white',
          fontWeight: 'bold',
        }}
      />
    );
  };

  // Мемоизированные значения
  const isSelected = useCallback((id: number) => selectedIds.includes(id), [selectedIds]);
  const selectedCount = selectedIds.length;
  const isIndeterminate = selectedCount > 0 && selectedCount < ((materialsData as any)?.results?.length || 0);

  if (error) {
    return (
      <Alert severity="error" action={
        <Button color="inherit" size="small" onClick={() => refetch()}>
          Повторить
        </Button>
      }>
        Ошибка загрузки материалов: {error.message}
      </Alert>
    );
  }

  return (
    <Box>
      {/* Панель инструментов */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <TextField
              placeholder="Поиск по сертификату, плавке, марке..."
              value={searchTerm}
              onChange={handleSearchChange}
              size="small"
              fullWidth
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Box display="flex" gap={1} justifyContent="flex-end">
              <Button
                startIcon={<FilterIcon />}
                onClick={() => setShowFilters(!showFilters)}
                variant={showFilters ? "contained" : "outlined"}
                size="small"
              >
                Фильтры
              </Button>
              
              <Button
                startIcon={<RefreshIcon />}
                onClick={() => refetch()}
                variant="outlined"
                size="small"
              >
                Обновить
              </Button>
              
              {onCreate && (
                <Button
                  startIcon={<AddIcon />}
                  onClick={onCreate}
                  variant="contained"
                  size="small"
                >
                  Добавить
                </Button>
              )}
            </Box>
          </Grid>
        </Grid>

        {/* Панель фильтров */}
        {showFilters && (
          <Box mt={2} p={2} bgcolor="grey.50" borderRadius={1}>
            <Grid container spacing={2}>
              <Grid item xs={12} md={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>Марка материала</InputLabel>
                  <Select
                    value={filters.material_grade || ''}
                    onChange={(e) => setFilters(prev => ({ ...prev, material_grade: e.target.value }))}
                    label="Марка материала"
                  >
                    <MenuItem value="">Все</MenuItem>
                    <MenuItem value="40X">40X</MenuItem>
                    <MenuItem value="20X13">20X13</MenuItem>
                    <MenuItem value="12X18H10T">12X18H10T</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} md={3}>
                <TextField
                  fullWidth
                  size="small"
                  label="Поставщик"
                  value={filters.supplier || ''}
                  onChange={(e) => setFilters(prev => ({ ...prev, supplier: e.target.value }))}
                />
              </Grid>
              
              <Grid item xs={12} md={3}>
                <TextField
                  fullWidth
                  size="small"
                  label="Дата от"
                  type="date"
                  value={filters.date_from || ''}
                  onChange={(e) => setFilters(prev => ({ ...prev, date_from: e.target.value }))}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              
              <Grid item xs={12} md={3}>
                <TextField
                  fullWidth
                  size="small"
                  label="Дата до"
                  type="date"
                  value={filters.date_to || ''}
                  onChange={(e) => setFilters(prev => ({ ...prev, date_to: e.target.value }))}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
            </Grid>
            
            <Box mt={2} display="flex" gap={1}>
              <Button variant="contained" size="small" onClick={applyFilters}>
                Применить
              </Button>
              <Button variant="outlined" size="small" onClick={clearFilters}>
                Очистить
              </Button>
            </Box>
          </Box>
        )}

        {/* Информация о выборе */}
        {selectable && selectedCount > 0 && (
          <Box mt={2}>
            <Alert severity="info">
              Выбрано {selectedCount} материалов
            </Alert>
          </Box>
        )}
      </Paper>

      {/* Таблица */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              {selectable && (
                <TableCell padding="checkbox">
                  <input
                    type="checkbox"
                    ref={(input) => {
                      if (input) input.indeterminate = isIndeterminate;
                    }}
                    checked={selectedCount === ((materialsData as any)?.results?.length || 0) && selectedCount > 0}
                    onChange={handleSelectAll}
                  />
                </TableCell>
              )}
              
              <TableCell>
                <TableSortLabel
                  active={sortConfig.field === 'material_grade'}
                  direction={sortConfig.field === 'material_grade' ? sortConfig.order : 'asc'}
                  onClick={() => handleSort('material_grade')}
                >
                  Марка материала
                </TableSortLabel>
              </TableCell>
              
              <TableCell>
                <TableSortLabel
                  active={sortConfig.field === 'supplier'}
                  direction={sortConfig.field === 'supplier' ? sortConfig.order : 'asc'}
                  onClick={() => handleSort('supplier')}
                >
                  Поставщик
                </TableSortLabel>
              </TableCell>
              
              <TableCell>Сертификат</TableCell>
              <TableCell>Плавка</TableCell>
              <TableCell>Размер</TableCell>
              
              <TableCell>
                <TableSortLabel
                  active={sortConfig.field === 'quantity'}
                  direction={sortConfig.field === 'quantity' ? sortConfig.order : 'asc'}
                  onClick={() => handleSort('quantity')}
                >
                  Количество
                </TableSortLabel>
              </TableCell>
              
              <TableCell>Статус</TableCell>
              <TableCell>Местоположение</TableCell>
              
              <TableCell>
                <TableSortLabel
                  active={sortConfig.field === 'created_at'}
                  direction={sortConfig.field === 'created_at' ? sortConfig.order : 'asc'}
                  onClick={() => handleSort('created_at')}
                >
                  Дата создания
                </TableSortLabel>
              </TableCell>
              
              {showActions && <TableCell>Действия</TableCell>}
            </TableRow>
          </TableHead>
          
          <TableBody>
            {isLoading ? (
              // Скелетон загрузки
              [...Array(5)].map((_, index) => (
                <TableRow key={index}>
                  {selectable && <TableCell><Skeleton /></TableCell>}
                  <TableCell><Skeleton /></TableCell>
                  <TableCell><Skeleton /></TableCell>
                  <TableCell><Skeleton /></TableCell>
                  <TableCell><Skeleton /></TableCell>
                  <TableCell><Skeleton /></TableCell>
                  <TableCell><Skeleton /></TableCell>
                  <TableCell><Skeleton /></TableCell>
                  <TableCell><Skeleton /></TableCell>
                  <TableCell><Skeleton /></TableCell>
                  {showActions && <TableCell><Skeleton /></TableCell>}
                </TableRow>
              ))
            ) : (materialsData as any)?.results?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={selectable ? 11 : 10} align="center">
                  <Typography variant="body2" color="text.secondary">
                    Материалы не найдены
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              (materialsData as any)?.results?.map((material: any) => (
                <TableRow 
                  key={material.id}
                  selected={isSelected(material.id)}
                  hover
                >
                  {selectable && (
                    <TableCell padding="checkbox">
                      <input
                        type="checkbox"
                        checked={isSelected(material.id)}
                        onChange={(e) => handleRowSelect(material.id, e.target.checked)}
                      />
                    </TableCell>
                  )}
                  
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      {material.material_grade}
                    </Typography>
                  </TableCell>
                  
                  <TableCell>{material.supplier}</TableCell>
                  
                  <TableCell>
                    <Tooltip title={`Заказ: ${material.order_number}`}>
                      <Typography variant="body2">
                        {material.certificate_number}
                      </Typography>
                    </Tooltip>
                  </TableCell>
                  
                  <TableCell>{material.heat_number}</TableCell>
                  <TableCell>{material.size}</TableCell>
                  
                  <TableCell>
                    {material.quantity} {UNIT_CHOICES.find(u => u.value === material.unit)?.label}
                  </TableCell>
                  
                  <TableCell>{getStatusChip(material)}</TableCell>
                  <TableCell>{material.location || '—'}</TableCell>
                  
                  <TableCell>
                    {new Date(material.created_at).toLocaleDateString('ru-RU')}
                  </TableCell>
                  
                  {showActions && (
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={(e) => handleMenuOpen(e, material)}
                      >
                        <MoreVertIcon />
                      </IconButton>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        
        {/* Пагинация */}
        {materialsData && (
          <TablePagination
            component="div"
            count={(materialsData as any)?.count || 0}
            page={(params.page || 1) - 1}
            onPageChange={handlePageChange}
            rowsPerPage={params.page_size || 25}
            onRowsPerPageChange={handleRowsPerPageChange}
            rowsPerPageOptions={[10, 25, 50, 100]}
            labelRowsPerPage="Строк на странице:"
            labelDisplayedRows={({ from, to, count }) => 
              `${from}–${to} из ${count !== -1 ? count : `более ${to}`}`
            }
          />
        )}
      </TableContainer>

      {/* Меню действий */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        {onEdit && (
          <MenuItem onClick={handleEdit}>
            <EditIcon sx={{ mr: 1 }} fontSize="small" />
            Редактировать
          </MenuItem>
        )}
        
        {onViewQR && (
          <MenuItem onClick={handleViewQR}>
            <QrCodeIcon sx={{ mr: 1 }} fontSize="small" />
            QR код
          </MenuItem>
        )}
        
        <MenuItem onClick={() => {}}>
          <DownloadIcon sx={{ mr: 1 }} fontSize="small" />
          Скачать сертификат
        </MenuItem>
        
        {onDelete && (
          <MenuItem onClick={handleDelete}>
            <DeleteIcon sx={{ mr: 1 }} fontSize="small" />
            Удалить
          </MenuItem>
        )}
      </Menu>
    </Box>
  );
};

export default MaterialList;