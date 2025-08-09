/**
 * Страница формы материала (создание/редактирование)
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Divider,
  Paper
} from '@mui/material';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { Save, Cancel, Upload } from '@mui/icons-material';
import { useSnackbar } from 'notistack';

// Схема валидации
const materialSchema: yup.ObjectSchema<MaterialFormData> = yup.object({
  grade: yup.string().required('Марка материала обязательна'),
  size: yup.string().required('Размер обязателен'),
  supplier: yup.string().required('Поставщик обязателен'),
  order_number: yup.string().required('Номер заказа обязателен'),
  certificate_number: yup.string().required('Номер сертификата обязателен'),
  heat_number: yup.string().required('Номер плавки обязателен'),
  description: yup.string().optional(),
  requires_ppsd: yup.boolean().default(false),
  certificate_file: yup.mixed<File>().optional()
});

interface MaterialFormData {
  grade: string;
  size: string;
  supplier: string;
  order_number: string;
  certificate_number: string;
  heat_number: string;
  description?: string;
  requires_ppsd: boolean;
  certificate_file?: File;
}

const MaterialFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  
  const isEditing = !!id;
  const [certificateFile, setCertificateFile] = useState<File | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting }
  } = useForm<MaterialFormData>({
    resolver: yupResolver(materialSchema),
    defaultValues: {
      grade: '',
      size: '',
      supplier: '',
      order_number: '',
      certificate_number: '',
      heat_number: '',
      description: '',
      requires_ppsd: false
    }
  });

  // Загрузка данных материала для редактирования
  const { data: material, isLoading } = useQuery({
    queryKey: ['material', id],
    queryFn: async () => {
      const response = await fetch(`/api/v1/materials/${id}/`);
      if (!response.ok) {
        throw new Error('Материал не найден');
      }
      return response.json();
    },
    enabled: isEditing
  });

  // Загрузка справочных данных
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

  const { data: grades } = useQuery({
    queryKey: ['grades'],
    queryFn: async () => {
      const response = await fetch('/api/v1/grades/');
      if (!response.ok) {
        throw new Error('Ошибка загрузки марок');
      }
      return response.json();
    }
  });

  // Заполняем форму при редактировании
  useEffect(() => {
    if (material && isEditing) {
      reset({
        grade: material.grade,
        size: material.size,
        supplier: material.supplier,
        order_number: material.order_number,
        certificate_number: material.certificate_number,
        heat_number: material.heat_number,
        description: material.description || '',
        requires_ppsd: material.requires_ppsd
      });
    }
  }, [material, isEditing, reset]);

  // Мутация для сохранения материала
  const saveMaterialMutation = useMutation({
    mutationFn: async (data: MaterialFormData) => {
      const formData = new FormData();
      
      // Добавляем данные формы
      Object.entries(data).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          formData.append(key, value.toString());
        }
      });

      // Добавляем файл сертификата если есть
      if (certificateFile) {
        formData.append('certificate_file', certificateFile);
      }

      const url = isEditing ? `/api/v1/materials/${id}/` : '/api/v1/materials/';
      const method = isEditing ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Ошибка сохранения материала');
      }

      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['materials'] });
      queryClient.invalidateQueries({ queryKey: ['material', data.id] });
      
      enqueueSnackbar(
        isEditing ? 'Материал обновлен успешно' : 'Материал создан успешно',
        { variant: 'success' }
      );
      
      navigate(`/materials/${data.id}`);
    },
    onError: (error: Error) => {
      enqueueSnackbar(error.message, { variant: 'error' });
    }
  });

  const onSubmit = (data: MaterialFormData) => {
    saveMaterialMutation.mutate(data);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Проверяем тип файла
      if (file.type !== 'application/pdf') {
        enqueueSnackbar('Можно загружать только PDF файлы', { variant: 'error' });
        return;
      }
      
      // Проверяем размер файла (50MB)
      if (file.size > 50 * 1024 * 1024) {
        enqueueSnackbar('Размер файла не должен превышать 50MB', { variant: 'error' });
        return;
      }
      
      setCertificateFile(file);
    }
  };

  if (isLoading && isEditing) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Заголовок */}
      <Box mb={3}>
        <Typography variant="h4" component="h1">
          {isEditing ? 'Редактирование материала' : 'Новый материал'}
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {isEditing 
            ? 'Внесите изменения в данные материала' 
            : 'Заполните форму для регистрации нового материала'
          }
        </Typography>
      </Box>

      <form onSubmit={handleSubmit(onSubmit as any)}>
        <Grid container spacing={3}>
          {/* Основная информация */}
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Основная информация
                </Typography>
                
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <Controller
                      name="grade"
                      control={control}
                      render={({ field }) => (
                        <FormControl fullWidth error={!!errors.grade}>
                          <InputLabel>Марка материала</InputLabel>
                          <Select {...field} label="Марка материала">
                            {grades?.map((grade: any) => (
                              <MenuItem key={grade.id} value={grade.name}>
                                {grade.name}
                              </MenuItem>
                            ))}
                          </Select>
                          {errors.grade && (
                            <Typography variant="caption" color="error">
                              {errors.grade.message}
                            </Typography>
                          )}
                        </FormControl>
                      )}
                    />
                  </Grid>
                  
                  <Grid item xs={12} sm={6}>
                    <Controller
                      name="size"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          fullWidth
                          label="Размер"
                          error={!!errors.size}
                          helperText={errors.size?.message}
                          placeholder="⌀50, ⌀100, Лист 10мм"
                        />
                      )}
                    />
                  </Grid>
                  
                  <Grid item xs={12} sm={6}>
                    <Controller
                      name="supplier"
                      control={control}
                      render={({ field }) => (
                        <FormControl fullWidth error={!!errors.supplier}>
                          <InputLabel>Поставщик</InputLabel>
                          <Select {...field} label="Поставщик">
                            {suppliers?.map((supplier: any) => (
                              <MenuItem key={supplier.id} value={supplier.name}>
                                {supplier.name}
                              </MenuItem>
                            ))}
                          </Select>
                          {errors.supplier && (
                            <Typography variant="caption" color="error">
                              {errors.supplier.message}
                            </Typography>
                          )}
                        </FormControl>
                      )}
                    />
                  </Grid>
                  
                  <Grid item xs={12} sm={6}>
                    <Controller
                      name="order_number"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          fullWidth
                          label="Номер заказа"
                          error={!!errors.order_number}
                          helperText={errors.order_number?.message}
                        />
                      )}
                    />
                  </Grid>
                  
                  <Grid item xs={12} sm={6}>
                    <Controller
                      name="certificate_number"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          fullWidth
                          label="Номер сертификата"
                          error={!!errors.certificate_number}
                          helperText={errors.certificate_number?.message}
                        />
                      )}
                    />
                  </Grid>
                  
                  <Grid item xs={12} sm={6}>
                    <Controller
                      name="heat_number"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          fullWidth
                          label="Номер плавки"
                          error={!!errors.heat_number}
                          helperText={errors.heat_number?.message}
                        />
                      )}
                    />
                  </Grid>
                  
                  <Grid item xs={12}>
                    <Controller
                      name="description"
                      control={control}
                      render={({ field }) => (
                        <TextField
                          {...field}
                          fullWidth
                          label="Описание"
                          multiline
                          rows={3}
                          error={!!errors.description}
                          helperText={errors.description?.message}
                        />
                      )}
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          {/* Дополнительные настройки */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Сертификат качества
                </Typography>
                
                <input
                  accept="application/pdf"
                  style={{ display: 'none' }}
                  id="certificate-file-input"
                  type="file"
                  onChange={handleFileChange}
                />
                <label htmlFor="certificate-file-input">
                  <Button
                    variant="outlined"
                    component="span"
                    startIcon={<Upload />}
                    fullWidth
                    sx={{ mb: 2 }}
                  >
                    Загрузить PDF
                  </Button>
                </label>
                
                {certificateFile && (
                  <Alert severity="success" sx={{ mb: 2 }}>
                    Выбран файл: {certificateFile.name}
                  </Alert>
                )}
                
                {material?.certificate_file && !certificateFile && (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Сертификат уже загружен
                  </Alert>
                )}

                <Divider sx={{ my: 2 }} />

                <Typography variant="h6" gutterBottom>
                  Дополнительно
                </Typography>
                
                <Controller
                  name="requires_ppsd"
                  control={control}
                  render={({ field }) => (
                    <FormControl fullWidth>
                      <InputLabel>Требует ППСД</InputLabel>
                      <Select
                        {...field}
                        label="Требует ППСД"
                        value={field.value ? 'true' : 'false'}
                        onChange={(e) => field.onChange(e.target.value === 'true')}
                      >
                        <MenuItem value="false">Нет</MenuItem>
                        <MenuItem value="true">Да</MenuItem>
                      </Select>
                    </FormControl>
                  )}
                />
              </CardContent>
            </Card>
          </Grid>

          {/* Кнопки действий */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Box display="flex" justifyContent="space-between">
                <Button
                  variant="outlined"
                  startIcon={<Cancel />}
                  onClick={() => navigate(-1)}
                >
                  Отмена
                </Button>
                
                <Button
                  type="submit"
                  variant="contained"
                  startIcon={<Save />}
                  disabled={isSubmitting || saveMaterialMutation.isPending}
                >
                  {saveMaterialMutation.isPending ? (
                    <CircularProgress size={20} />
                  ) : (
                    isEditing ? 'Сохранить изменения' : 'Создать материал'
                  )}
                </Button>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      </form>
    </Box>
  );
};

export default MaterialFormPage;