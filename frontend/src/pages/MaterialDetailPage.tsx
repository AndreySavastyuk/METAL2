/**
 * Страница детального просмотра материала
 */
import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Divider,
  Tab,
  Tabs,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  TextField,
  DialogActions,

  Paper,

} from '@mui/material';
import {
  Edit,
  Download,
  Visibility,
  Assignment,
  Science,
  CheckCircle,

  Add,
  Comment
} from '@mui/icons-material';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';
import { Document, Page, pdfjs } from 'react-pdf';
import { useAuth } from '../contexts/AuthContext';

// Настройка worker для react-pdf
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

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

const MaterialDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  
  const [activeTab, setActiveTab] = useState(0);
  const [commentDialogOpen, setCommentDialogOpen] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [pdfNumPages, setPdfNumPages] = useState<number | null>(null);
  const [pdfPageNumber, setPdfPageNumber] = useState(1);

  // Загрузка данных материала
  const { data: material, isLoading, error } = useQuery({
    queryKey: ['material', id],
    queryFn: async () => {
      const response = await fetch(`/api/v1/materials/${id}/`);
      if (!response.ok) {
        throw new Error('Материал не найден');
      }
      return response.json();
    },
    enabled: !!id
  });

  // Мутация для добавления комментария
  const addCommentMutation = useMutation({
    mutationFn: async (comment: string) => {
      const response = await fetch(`/api/v1/materials/${id}/comments/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: comment }),
      });
      if (!response.ok) {
        throw new Error('Ошибка добавления комментария');
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['material', id] });
      setCommentDialogOpen(false);
      setNewComment('');
    },
  });

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleAddComment = () => {
    if (newComment.trim()) {
      addCommentMutation.mutate(newComment);
    }
  };

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setPdfNumPages(numPages);
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error || !material) {
    return (
      <Alert severity="error">
        Материал не найден или произошла ошибка при загрузке данных
      </Alert>
    );
  }

  // Определяем статус и его цвет
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

  return (
    <Box>
      {/* Заголовок и действия */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Материал #{material.id}
        </Typography>
        <Box display="flex" gap={1}>
          {hasPermission('materials.edit') && (
            <Button
              variant="outlined"
              startIcon={<Edit />}
              onClick={() => navigate(`/materials/${id}/edit`)}
            >
              Редактировать
            </Button>
          )}
          <Button
            variant="contained"
            startIcon={<Download />}
            onClick={() => window.open(`/api/v1/materials/${id}/download/`, '_blank')}
          >
            Скачать данные
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Основная информация */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">
                  {material.grade} - {material.size}
                </Typography>
                <Chip
                  label={getStatusText(material.status)}
                  color={getStatusColor(material.status)}
                  variant="filled"
                />
              </Box>

              <Tabs value={activeTab} onChange={handleTabChange}>
                <Tab label="Детали" icon={<Visibility />} />
                <Tab label="Сертификат" icon={<Assignment />} />
                <Tab label="История" icon={<CheckCircle />} />
                <Tab label="Комментарии" icon={<Comment />} />
              </Tabs>

              <TabPanel value={activeTab} index={0}>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2" color="textSecondary">
                      Поставщик
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {material.supplier}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2" color="textSecondary">
                      Номер заказа
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {material.order_number}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2" color="textSecondary">
                      Номер сертификата
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {material.certificate_number}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle2" color="textSecondary">
                      Номер плавки
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {material.heat_number}
                    </Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="subtitle2" color="textSecondary">
                      Описание
                    </Typography>
                    <Typography variant="body1" gutterBottom>
                      {material.description || 'Описание отсутствует'}
                    </Typography>
                  </Grid>
                </Grid>
              </TabPanel>

              <TabPanel value={activeTab} index={1}>
                {material.certificate_file ? (
                  <Box>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                      <Typography variant="h6">
                        Сертификат качества
                      </Typography>
                      <Button
                        variant="outlined"
                        startIcon={<Download />}
                        onClick={() => window.open(material.certificate_file, '_blank')}
                      >
                        Скачать PDF
                      </Button>
                    </Box>
                    <Paper 
                      sx={{ 
                        p: 2, 
                        textAlign: 'center',
                        backgroundColor: '#f5f5f5',
                        minHeight: '600px'
                      }}
                    >
                      <Document
                        file={material.certificate_file}
                        onLoadSuccess={onDocumentLoadSuccess}
                        loading={<CircularProgress />}
                        error={
                          <Alert severity="error">
                            Ошибка загрузки PDF документа
                          </Alert>
                        }
                      >
                        <Page 
                          pageNumber={pdfPageNumber} 
                          width={Math.min(600, window.innerWidth - 100)}
                        />
                      </Document>
                      {pdfNumPages && pdfNumPages > 1 && (
                        <Box mt={2} display="flex" justifyContent="center" gap={1}>
                          <Button
                            size="small"
                            disabled={pdfPageNumber <= 1}
                            onClick={() => setPdfPageNumber(pdfPageNumber - 1)}
                          >
                            Предыдущая
                          </Button>
                          <Typography variant="body2" sx={{ alignSelf: 'center' }}>
                            Страница {pdfPageNumber} из {pdfNumPages}
                          </Typography>
                          <Button
                            size="small"
                            disabled={pdfPageNumber >= pdfNumPages}
                            onClick={() => setPdfPageNumber(pdfPageNumber + 1)}
                          >
                            Следующая
                          </Button>
                        </Box>
                      )}
                    </Paper>
                  </Box>
                ) : (
                  <Alert severity="warning">
                    Сертификат не загружен
                  </Alert>
                )}
              </TabPanel>

              <TabPanel value={activeTab} index={2}>
                <Box>
                  {material.history?.map((item: any, index: number) => (
                    <Paper key={index} sx={{ p: 2, mb: 2 }}>
                      <Box display="flex" justifyContent="between" alignItems="center" mb={1}>
                        <Typography variant="h6" component="span">
                          {getStatusText(item.status)}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {format(new Date(item.created_at), 'dd.MM.yyyy HH:mm', { locale: ru })}
                        </Typography>
                      </Box>
                      <Typography variant="body2">{item.comment}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {item.user}
                      </Typography>
                    </Paper>
                  )) || (
                    <Typography variant="body2" color="text.secondary">
                      История изменений пуста
                    </Typography>
                  )}
                </Box>
              </TabPanel>

              <TabPanel value={activeTab} index={3}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">
                    Внутренние комментарии
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<Add />}
                    onClick={() => setCommentDialogOpen(true)}
                  >
                    Добавить
                  </Button>
                </Box>
                
                {material.comments?.length > 0 ? (
                  material.comments.map((comment: any) => (
                    <Paper key={comment.id} sx={{ p: 2, mb: 2 }}>
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                        <Typography variant="subtitle2">
                          {comment.user}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {format(new Date(comment.created_at), 'dd.MM.yyyy HH:mm', { locale: ru })}
                        </Typography>
                      </Box>
                      <Typography variant="body1">
                        {comment.text}
                      </Typography>
                    </Paper>
                  ))
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Комментарии отсутствуют
                  </Typography>
                )}
              </TabPanel>
            </CardContent>
          </Card>
        </Grid>

        {/* Боковая панель */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Быстрые действия
              </Typography>
              <Box display="flex" flexDirection="column" gap={1}>
                {hasPermission('inspections.create') && material.status === 'received' && (
                  <Button
                    variant="contained"
                    startIcon={<Assignment />}
                    fullWidth
                    onClick={() => navigate(`/qc/inspections/new?material=${id}`)}
                  >
                    Создать инспекцию
                  </Button>
                )}
                {hasPermission('tests.create') && ['qc_approved', 'lab_testing'].includes(material.status) && (
                  <Button
                    variant="contained"
                    startIcon={<Science />}
                    fullWidth
                    onClick={() => navigate(`/lab/tests/new?material=${id}`)}
                  >
                    Создать тест
                  </Button>
                )}
              </Box>
              
              <Divider sx={{ my: 2 }} />
              
              <Typography variant="h6" gutterBottom>
                Информация
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Создан: {format(new Date(material.created_at), 'dd.MM.yyyy HH:mm', { locale: ru })}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Обновлен: {format(new Date(material.updated_at), 'dd.MM.yyyy HH:mm', { locale: ru })}
              </Typography>
              {material.qr_code && (
                <Box textAlign="center" mt={2}>
                  <img 
                    src={material.qr_code} 
                    alt="QR Code" 
                    style={{ maxWidth: '150px', height: 'auto' }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    QR код материала
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Диалог добавления комментария */}
      <Dialog open={commentDialogOpen} onClose={() => setCommentDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Добавить комментарий</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Комментарий"
            fullWidth
            multiline
            rows={4}
            variant="outlined"
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCommentDialogOpen(false)}>
            Отмена
          </Button>
          <Button 
            onClick={handleAddComment} 
            variant="contained"
            disabled={!newComment.trim() || addCommentMutation.isPending}
          >
            {addCommentMutation.isPending ? <CircularProgress size={20} /> : 'Добавить'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MaterialDetailPage;