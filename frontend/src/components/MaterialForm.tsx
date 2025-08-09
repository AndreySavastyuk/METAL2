/**
 * Компонент формы для создания/редактирования материала
 */
import React, { useState, useRef, useCallback } from 'react';
import {
  Box,
  Paper,
  Grid,
  TextField,
  Button,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormHelperText,
  LinearProgress,
  Alert,
  Autocomplete,
  Card,
  CardContent,
  IconButton,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  Cancel as CancelIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { Document, Page, pdfjs } from 'react-pdf';
import {
  Material,
  MaterialFormData,
  UploadProgress,
  UNIT_CHOICES,
} from '../types/material';
import { MaterialService } from '../services/materialService';

// Настройка PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/legacy/build/pdf.worker.min.js`;

interface MaterialFormProps {
  material?: Material;
  onSuccess?: (material: Material) => void;
  onCancel?: () => void;
  readOnly?: boolean;
}

// Схема валидации
const validationSchema = yup.object({
  material_grade: yup
    .string()
    .required('Марка материала обязательна')
    .min(2, 'Минимум 2 символа')
    .max(100, 'Максимум 100 символов'),
  supplier: yup
    .string()
    .required('Поставщик обязателен')
    .min(3, 'Минимум 3 символа')
    .max(200, 'Максимум 200 символов'),
  order_number: yup
    .string()
    .required('Номер заказа обязателен')
    .max(100, 'Максимум 100 символов'),
  certificate_number: yup
    .string()
    .required('Номер сертификата обязателен')
    .max(100, 'Максимум 100 символов'),
  heat_number: yup
    .string()
    .required('Номер плавки обязателен')
    .max(100, 'Максимум 100 символов'),
  size: yup
    .string()
    .required('Размер обязателен')
    .max(100, 'Максимум 100 символов'),
  quantity: yup
    .number()
    .required('Количество обязательно')
    .positive('Количество должно быть положительным')
    .max(1000000, 'Максимальное количество: 1,000,000'),
  unit: yup
    .string()
    .required('Единица измерения обязательна')
    .oneOf(['kg', 'pcs', 'meters'], 'Некорректная единица измерения'),
  location: yup
    .string()
    .max(200, 'Максимум 200 символов'),
});

const MaterialForm: React.FC<MaterialFormProps> = ({
  material,
  onSuccess,
  onCancel,
  readOnly = false,
}) => {
  const { enqueueSnackbar } = useSnackbar();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // State для загрузки файла
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [pdfNumPages, setPdfNumPages] = useState<number | null>(null);

  // Form state
  const {
    control,
    handleSubmit,
    watch,
    formState: { errors },
    reset,
  } = useForm<MaterialFormData>({
    resolver: yupResolver(validationSchema) as any,
    defaultValues: material ? {
      material_grade: material.material_grade,
      supplier: material.supplier,
      order_number: material.order_number,
      certificate_number: material.certificate_number,
      heat_number: material.heat_number,
      size: material.size,
      quantity: material.quantity,
      unit: material.unit,
      location: material.location || '',
    } : {
      material_grade: '',
      supplier: '',
      order_number: '',
      certificate_number: '',
      heat_number: '',
      size: '',
      quantity: 0,
      unit: 'kg',
      location: '',
    },
  });

  // Queries для автодополнения
  const supplierQuery = watch('supplier');
  const gradeQuery = watch('material_grade');

  const { data: suppliers = [] } = useQuery({
    queryKey: ['suppliers', supplierQuery],
    queryFn: () => MaterialService.searchSuppliers(supplierQuery),
    enabled: supplierQuery.length >= 2,
    staleTime: 5 * 60 * 1000, // 5 минут
  });

  const { data: grades = [] } = useQuery({
    queryKey: ['grades', gradeQuery],
    queryFn: () => MaterialService.searchGrades(gradeQuery),
    enabled: gradeQuery.length >= 1,
    staleTime: 5 * 60 * 1000,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: MaterialFormData) => 
      MaterialService.createMaterial(data, setUploadProgress),
    onSuccess: (newMaterial) => {
      enqueueSnackbar('Материал успешно создан', { variant: 'success' });
      queryClient.invalidateQueries({ queryKey: ['materials'] });
      onSuccess?.(newMaterial);
      reset();
      setSelectedFile(null);
      setUploadProgress(null);
    },
    onError: (error: any) => {
      enqueueSnackbar(
        error.response?.data?.detail || 'Ошибка создания материала',
        { variant: 'error' }
      );
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: MaterialFormData) => 
      MaterialService.updateMaterial(material!.id, data, setUploadProgress),
    onSuccess: (updatedMaterial) => {
      enqueueSnackbar('Материал успешно обновлен', { variant: 'success' });
      queryClient.invalidateQueries({ queryKey: ['materials'] });
      onSuccess?.(updatedMaterial);
      setUploadProgress(null);
    },
    onError: (error: any) => {
      enqueueSnackbar(
        error.response?.data?.detail || 'Ошибка обновления материала',
        { variant: 'error' }
      );
    },
  });

  // Обработка отправки формы
  const onSubmit = useCallback((data: MaterialFormData) => {
    const formData = {
      ...data,
      certificate_file: selectedFile || undefined,
    };

    if (material) {
      updateMutation.mutate(formData);
    } else {
      createMutation.mutate(formData);
    }
  }, [material, selectedFile, createMutation, updateMutation]);

  // Обработка выбора файла
  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Проверка типа файла
    if (file.type !== 'application/pdf') {
      enqueueSnackbar('Можно загружать только PDF файлы', { variant: 'error' });
      return;
    }

    // Проверка размера файла (50MB)
    if (file.size > 50 * 1024 * 1024) {
      enqueueSnackbar('Размер файла не должен превышать 50MB', { variant: 'error' });
      return;
    }

    setSelectedFile(file);
    enqueueSnackbar('Файл сертификата выбран', { variant: 'success' });
  }, [enqueueSnackbar]);

  // Удаление выбранного файла
  const handleFileRemove = useCallback(() => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // Открытие файлового диалога
  const handleFileClick = useCallback(() => {
    if (!readOnly) {
      fileInputRef.current?.click();
    }
  }, [readOnly]);

  // Обработка PDF
  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setPdfNumPages(numPages);
  }, []);

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        {material ? 'Редактирование материала' : 'Добавление материала'}
      </Typography>

      <Box component="form" onSubmit={handleSubmit(onSubmit)}>
        <Grid container spacing={3}>
          {/* Основная информация */}
          <Grid item xs={12}>
            <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 'bold' }}>
              Основная информация
            </Typography>
          </Grid>

          <Grid item xs={12} md={6}>
            <Controller
              name="material_grade"
              control={control}
              render={({ field }) => (
                <Autocomplete
                  {...field}
                  options={grades}
                  freeSolo
                  disabled={readOnly}
                  onChange={(_, value) => field.onChange(value || '')}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Марка материала *"
                      error={!!errors.material_grade}
                      helperText={errors.material_grade?.message}
                      placeholder="Например: 40X, 20X13"
                    />
                  )}
                />
              )}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <Controller
              name="supplier"
              control={control}
              render={({ field }) => (
                <Autocomplete
                  {...field}
                  options={suppliers}
                  freeSolo
                  disabled={readOnly}
                  onChange={(_, value) => field.onChange(value || '')}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Поставщик *"
                      error={!!errors.supplier}
                      helperText={errors.supplier?.message}
                      placeholder="Название компании поставщика"
                    />
                  )}
                />
              )}
            />
          </Grid>

          <Grid item xs={12} md={4}>
            <Controller
              name="order_number"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="Номер заказа *"
                  disabled={readOnly}
                  error={!!errors.order_number}
                  helperText={errors.order_number?.message}
                  placeholder="Номер заказа"
                />
              )}
            />
          </Grid>

          <Grid item xs={12} md={4}>
            <Controller
              name="certificate_number"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="Номер сертификата *"
                  disabled={readOnly}
                  error={!!errors.certificate_number}
                  helperText={errors.certificate_number?.message}
                  placeholder="Номер сертификата качества"
                />
              )}
            />
          </Grid>

          <Grid item xs={12} md={4}>
            <Controller
              name="heat_number"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="Номер плавки *"
                  disabled={readOnly}
                  error={!!errors.heat_number}
                  helperText={errors.heat_number?.message}
                  placeholder="Номер плавки металла"
                />
              )}
            />
          </Grid>

          {/* Характеристики материала */}
          <Grid item xs={12}>
            <Typography variant="subtitle1" sx={{ mb: 2, mt: 2, fontWeight: 'bold' }}>
              Характеристики
            </Typography>
          </Grid>

          <Grid item xs={12} md={4}>
            <Controller
              name="size"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="Размер *"
                  disabled={readOnly}
                  error={!!errors.size}
                  helperText={errors.size?.message}
                  placeholder="Например: ⌀50, Лист 10мм"
                />
              )}
            />
          </Grid>

          <Grid item xs={12} md={4}>
            <Controller
              name="quantity"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="Количество *"
                  type="number"
                  disabled={readOnly}
                  error={!!errors.quantity}
                  helperText={errors.quantity?.message}
                  inputProps={{ min: 0, step: 0.01 }}
                />
              )}
            />
          </Grid>

          <Grid item xs={12} md={4}>
            <Controller
              name="unit"
              control={control}
              render={({ field }) => (
                <FormControl fullWidth error={!!errors.unit} disabled={readOnly}>
                  <InputLabel>Единица измерения *</InputLabel>
                  <Select {...field} label="Единица измерения *">
                    {UNIT_CHOICES.map((unit) => (
                      <MenuItem key={unit.value} value={unit.value}>
                        {unit.label}
                      </MenuItem>
                    ))}
                  </Select>
                  {errors.unit && (
                    <FormHelperText>{errors.unit.message}</FormHelperText>
                  )}
                </FormControl>
              )}
            />
          </Grid>

          <Grid item xs={12}>
            <Controller
              name="location"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="Местоположение на складе"
                  disabled={readOnly}
                  error={!!errors.location}
                  helperText={errors.location?.message}
                  placeholder="Стеллаж, секция, ячейка"
                />
              )}
            />
          </Grid>

          {/* Загрузка сертификата */}
          <Grid item xs={12}>
            <Typography variant="subtitle1" sx={{ mb: 2, mt: 2, fontWeight: 'bold' }}>
              Сертификат качества
            </Typography>
            
            <Card variant="outlined">
              <CardContent>
                <Box 
                  sx={{
                    border: '2px dashed',
                    borderColor: selectedFile ? 'success.main' : 'grey.300',
                    borderRadius: 2,
                    p: 3,
                    textAlign: 'center',
                    cursor: readOnly ? 'default' : 'pointer',
                    bgcolor: selectedFile ? 'success.50' : 'grey.50',
                    '&:hover': readOnly ? {} : {
                      borderColor: 'primary.main',
                      bgcolor: 'primary.50',
                    },
                  }}
                  onClick={handleFileClick}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    style={{ display: 'none' }}
                    onChange={handleFileSelect}
                    disabled={readOnly}
                  />
                  
                  {selectedFile ? (
                    <Box>
                      <Typography variant="h6" color="success.main" gutterBottom>
                        Файл выбран
                      </Typography>
                      <Chip
                        label={selectedFile.name}
                        color="success"
                        deleteIcon={readOnly ? undefined : <DeleteIcon />}
                        onDelete={readOnly ? undefined : handleFileRemove}
                        sx={{ mb: 2 }}
                      />
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Размер: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                        </Typography>
                      </Box>
                      {!readOnly && (
                        <Box mt={2}>
                          <Button
                            startIcon={<ViewIcon />}
                            onClick={(e) => {
                              e.stopPropagation();
                              setPreviewOpen(true);
                            }}
                            variant="outlined"
                            size="small"
                          >
                            Предпросмотр
                          </Button>
                        </Box>
                      )}
                    </Box>
                  ) : (
                    <Box>
                      <UploadIcon sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
                      <Typography variant="h6" color="text.secondary" gutterBottom>
                        {readOnly ? 'Сертификат не загружен' : 'Нажмите для выбора PDF файла'}
                      </Typography>
                      {!readOnly && (
                        <Typography variant="body2" color="text.secondary">
                          Поддерживаются PDF файлы до 50MB
                        </Typography>
                      )}
                    </Box>
                  )}
                </Box>

                {/* Прогресс загрузки */}
                {uploadProgress && (
                  <Box mt={2}>
                    <Typography variant="body2" gutterBottom>
                      Загрузка: {uploadProgress.percentage}%
                    </Typography>
                    <LinearProgress 
                      variant="determinate" 
                      value={uploadProgress.percentage} 
                    />
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Кнопки действий */}
          {!readOnly && (
            <Grid item xs={12}>
              <Box display="flex" gap={2} justifyContent="flex-end" mt={3}>
                {onCancel && (
                  <Button
                    startIcon={<CancelIcon />}
                    onClick={onCancel}
                    disabled={isLoading}
                  >
                    Отмена
                  </Button>
                )}
                
                <Button
                  type="submit"
                  variant="contained"
                  startIcon={isLoading ? <CircularProgress size={20} /> : <SaveIcon />}
                  disabled={isLoading}
                >
                  {isLoading ? 'Сохранение...' : (material ? 'Обновить' : 'Создать')}
                </Button>
              </Box>
            </Grid>
          )}
        </Grid>
      </Box>

      {/* Диалог предпросмотра PDF */}
      <Dialog
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Предпросмотр сертификата
          <IconButton
            onClick={() => setPreviewOpen(false)}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CancelIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {selectedFile && (
            <Box sx={{ textAlign: 'center' }}>
              <Document
                file={selectedFile}
                onLoadSuccess={onDocumentLoadSuccess}
                loading={
                  <Box py={4}>
                    <CircularProgress />
                    <Typography variant="body2" mt={2}>
                      Загрузка PDF...
                    </Typography>
                  </Box>
                }
                error={
                  <Alert severity="error">
                    Ошибка загрузки PDF файла
                  </Alert>
                }
              >
                <Page pageNumber={1} scale={1.0} />
              </Document>
              {pdfNumPages && pdfNumPages > 1 && (
                <Typography variant="caption" display="block" mt={1}>
                  Страница 1 из {pdfNumPages}
                </Typography>
              )}
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </Paper>
  );
};

export default MaterialForm;