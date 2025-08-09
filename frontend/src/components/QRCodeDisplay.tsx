/**
 * Компонент для отображения QR кода материала с функциями печати и скачивания
 */
import React, { useRef, useCallback, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableRow,
  CircularProgress,
  // Alert,
  Switch,
  FormControlLabel,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Download as DownloadIcon,
  Print as PrintIcon,
  Fullscreen as FullscreenIcon,
  Close as CloseIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import QRCode from 'qrcode.react';
import { useQuery } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { Material, QRCodeData } from '../types/material';
import { MaterialService } from '../services/materialService';

interface QRCodeDisplayProps {
  material: Material;
  size?: number;
  showMaterialInfo?: boolean;
  showControls?: boolean;
  onClose?: () => void;
}

interface QRCodeSettings {
  size: number;
  errorCorrectionLevel: 'L' | 'M' | 'Q' | 'H';
  includeMargin: boolean;
  fgColor: string;
  bgColor: string;
  showMaterialInfo: boolean;
  showLogo: boolean;
}

const QRCodeDisplay: React.FC<QRCodeDisplayProps> = ({
  material,
  size = 256,
  showMaterialInfo = true,
  showControls = true,
  onClose,
}) => {
  const { enqueueSnackbar } = useSnackbar();
  const qrRef = useRef<HTMLDivElement>(null);
  const printRef = useRef<HTMLDivElement>(null);

  // State для настроек QR кода
  const [settings, setSettings] = useState<QRCodeSettings>({
    size: size,
    errorCorrectionLevel: 'M',
    includeMargin: true,
    fgColor: '#000000',
    bgColor: '#FFFFFF',
    showMaterialInfo: showMaterialInfo,
    showLogo: false,
  });

  const [fullscreenOpen, setFullscreenOpen] = useState(false);
  // const [printPreviewOpen, setPrintPreviewOpen] = useState(false);

  // Формирование данных для QR кода
  const qrCodeData: QRCodeData = {
    id: material.external_id,
    grade: material.material_grade,
    supplier: material.supplier,
    certificate: material.certificate_number,
    heat: material.heat_number,
    quantity: material.quantity.toString(),
    unit: material.unit,
  };

  // JSON строка для QR кода
  const qrValue = JSON.stringify(qrCodeData);

  // Человекочитаемый текст для QR кода (альтернативный формат)
  // const qrTextValue = [
  //   `ID: ${qrCodeData.id}`,
  //   `Марка: ${qrCodeData.grade}`,
  //   `Поставщик: ${qrCodeData.supplier}`,
  //   `Сертификат: ${qrCodeData.certificate}`,
  //   `Плавка: ${qrCodeData.heat}`,
  //   `Количество: ${qrCodeData.quantity} ${qrCodeData.unit}`,
  // ].join('\n');

  // Запрос для получения сгенерированного QR кода с сервера
  const { 
    // data: serverQRCode, 
    isLoading: isGenerating, 
    refetch: regenerateQR 
  } = useQuery({
    queryKey: ['material-qr', material.id],
    queryFn: () => MaterialService.generateQRCode(material.id),
    staleTime: Infinity, // QR код не изменяется
  });

  // Mutation для скачивания QR кода
  /*
  const downloadMutation = useMutation({
    mutationFn: () => MaterialService.downloadQRCode(material.id),
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `qr-code-${material.material_grade}-${material.heat_number}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      enqueueSnackbar('QR код скачан', { variant: 'success' });
    },
    onError: () => {
      enqueueSnackbar('Ошибка скачивания QR кода', { variant: 'error' });
    },
  });
  */

  // Скачивание как изображение (клиентское)
  const handleDownloadClient = useCallback(() => {
    if (!qrRef.current) return;

    const canvas = qrRef.current.querySelector('canvas');
    if (!canvas) return;

    try {
      // Создаем новый canvas с информацией о материале
      const finalCanvas = document.createElement('canvas');
      const ctx = finalCanvas.getContext('2d');
      if (!ctx) return;

      const padding = 40;
      const infoHeight = settings.showMaterialInfo ? 200 : 0;
      const canvasSize = settings.size + padding * 2;
      
      finalCanvas.width = canvasSize;
      finalCanvas.height = canvasSize + infoHeight;

      // Белый фон
      ctx.fillStyle = settings.bgColor;
      ctx.fillRect(0, 0, finalCanvas.width, finalCanvas.height);

      // Рисуем QR код
      ctx.drawImage(canvas, padding, padding);

      // Добавляем информацию о материале
      if (settings.showMaterialInfo) {
        ctx.fillStyle = '#000000';
        ctx.font = '14px Arial';
        ctx.textAlign = 'center';

        const textY = canvasSize + 30;
        const lines = [
          `Марка: ${material.material_grade}`,
          `Поставщик: ${material.supplier}`,
          `Сертификат: ${material.certificate_number}`,
          `Плавка: ${material.heat_number}`,
          `Количество: ${material.quantity} ${material.unit}`,
          `Размер: ${material.size}`,
        ];

        lines.forEach((line, index) => {
          ctx.fillText(line, finalCanvas.width / 2, textY + index * 20);
        });
      }

      // Скачиваем
      const link = document.createElement('a');
      link.download = `qr-${material.material_grade}-${material.heat_number}.png`;
      link.href = finalCanvas.toDataURL();
      link.click();

      enqueueSnackbar('QR код скачан', { variant: 'success' });
    } catch (error) {
      enqueueSnackbar('Ошибка создания изображения', { variant: 'error' });
    }
  }, [material, settings, enqueueSnackbar]);

  // Печать QR кода
  const handlePrint = useCallback(() => {
    if (!printRef.current) return;

    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    const printContent = printRef.current.innerHTML;
    
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>QR код - ${material.material_grade}</title>
          <style>
            body {
              font-family: Arial, sans-serif;
              text-align: center;
              padding: 20px;
              background: white;
            }
            .qr-container {
              display: inline-block;
              border: 2px solid #000;
              padding: 20px;
              background: white;
            }
            .material-info {
              margin-top: 20px;
              text-align: left;
            }
            .material-info table {
              margin: 0 auto;
              border-collapse: collapse;
            }
            .material-info td {
              padding: 5px 10px;
              border-bottom: 1px solid #eee;
            }
            .material-info td:first-child {
              font-weight: bold;
            }
            @media print {
              body { margin: 0; }
              .no-print { display: none; }
            }
          </style>
        </head>
        <body>
          <div class="qr-container">
            ${printContent}
          </div>
        </body>
      </html>
    `);

    printWindow.document.close();
    printWindow.focus();
    
    setTimeout(() => {
      printWindow.print();
      printWindow.close();
    }, 250);
  }, [material]);

  // Компонент QR кода
  const QRCodeComponent = () => (
    <Box ref={qrRef} display="inline-block">
      <QRCode
        value={qrValue}
        size={settings.size}
        level={settings.errorCorrectionLevel}
        includeMargin={settings.includeMargin}
        fgColor={settings.fgColor}
        bgColor={settings.bgColor}
      />
    </Box>
  );

  return (
    <Box>
      <Paper sx={{ p: 3 }}>
        {/* Заголовок */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h6">
            QR код материала
          </Typography>
          {onClose && (
            <IconButton onClick={onClose} size="small">
              <CloseIcon />
            </IconButton>
          )}
        </Box>

        <Grid container spacing={3}>
          {/* QR код */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <Box mb={2}>
                  {isGenerating ? (
                    <Box py={4}>
                      <CircularProgress />
                      <Typography variant="body2" mt={2}>
                        Генерация QR кода...
                      </Typography>
                    </Box>
                  ) : (
                    <QRCodeComponent />
                  )}
                </Box>

                {showControls && (
                  <Box display="flex" gap={1} justifyContent="center">
                    <Tooltip title="Скачать QR код">
                      <Button
                        startIcon={<DownloadIcon />}
                        onClick={handleDownloadClient}
                        variant="outlined"
                        size="small"
                      >
                        Скачать
                      </Button>
                    </Tooltip>

                    <Tooltip title="Печать QR кода">
                      <Button
                        startIcon={<PrintIcon />}
                        onClick={handlePrint}
                        variant="outlined"
                        size="small"
                      >
                        Печать
                      </Button>
                    </Tooltip>

                    <Tooltip title="Полноэкранный режим">
                      <IconButton 
                        onClick={() => setFullscreenOpen(true)}
                        size="small"
                      >
                        <FullscreenIcon />
                      </IconButton>
                    </Tooltip>

                    <Tooltip title="Обновить QR код">
                      <IconButton 
                        onClick={() => regenerateQR()}
                        size="small"
                        disabled={isGenerating}
                      >
                        <RefreshIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Информация о материале */}
          {settings.showMaterialInfo && (
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle1" gutterBottom>
                    Информация о материале
                  </Typography>
                  
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell><strong>ID:</strong></TableCell>
                        <TableCell>{material.external_id}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Марка:</strong></TableCell>
                        <TableCell>{material.material_grade}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Поставщик:</strong></TableCell>
                        <TableCell>{material.supplier}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Сертификат:</strong></TableCell>
                        <TableCell>{material.certificate_number}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Плавка:</strong></TableCell>
                        <TableCell>{material.heat_number}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Размер:</strong></TableCell>
                        <TableCell>{material.size}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell><strong>Количество:</strong></TableCell>
                        <TableCell>{material.quantity} {material.unit}</TableCell>
                      </TableRow>
                      {material.location && (
                        <TableRow>
                          <TableCell><strong>Местоположение:</strong></TableCell>
                          <TableCell>{material.location}</TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </Grid>
          )}

          {/* Настройки QR кода */}
          {showControls && (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle1" gutterBottom>
                    Настройки QR кода
                  </Typography>
                  
                  <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} sm={4}>
                      <Typography gutterBottom>Размер: {settings.size}px</Typography>
                      <Slider
                        value={settings.size}
                        onChange={(_, value) => setSettings(prev => ({ ...prev, size: value as number }))}
                        min={128}
                        max={512}
                        step={32}
                      />
                    </Grid>

                    <Grid item xs={12} sm={4}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Уровень коррекции</InputLabel>
                        <Select
                          value={settings.errorCorrectionLevel}
                          onChange={(e) => setSettings(prev => ({ 
                            ...prev, 
                            errorCorrectionLevel: e.target.value as 'L' | 'M' | 'Q' | 'H'
                          }))}
                          label="Уровень коррекции"
                        >
                          <MenuItem value="L">Низкий (7%)</MenuItem>
                          <MenuItem value="M">Средний (15%)</MenuItem>
                          <MenuItem value="Q">Высокий (25%)</MenuItem>
                          <MenuItem value="H">Максимальный (30%)</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>

                    <Grid item xs={12} sm={4}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={settings.showMaterialInfo}
                            onChange={(e) => setSettings(prev => ({ 
                              ...prev, 
                              showMaterialInfo: e.target.checked 
                            }))}
                          />
                        }
                        label="Показать информацию"
                      />
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>

        {/* Скрытый контейнер для печати */}
        <Box ref={printRef} sx={{ display: 'none' }}>
          <QRCodeComponent />
          {settings.showMaterialInfo && (
            <div className="material-info">
              <h3>Материал: {material.material_grade}</h3>
              <table>
                <tbody>
                  <tr><td>Поставщик:</td><td>{material.supplier}</td></tr>
                  <tr><td>Сертификат:</td><td>{material.certificate_number}</td></tr>
                  <tr><td>Плавка:</td><td>{material.heat_number}</td></tr>
                  <tr><td>Размер:</td><td>{material.size}</td></tr>
                  <tr><td>Количество:</td><td>{material.quantity} {material.unit}</td></tr>
                  {material.location && (
                    <tr><td>Местоположение:</td><td>{material.location}</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Box>
      </Paper>

      {/* Полноэкранный диалог */}
      <Dialog
        open={fullscreenOpen}
        onClose={() => setFullscreenOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          QR код - {material.material_grade}
          <IconButton
            onClick={() => setFullscreenOpen(false)}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        
        <DialogContent sx={{ textAlign: 'center' }}>
          <QRCode
            value={qrValue}
            size={400}
            level={settings.errorCorrectionLevel}
            includeMargin={settings.includeMargin}
            fgColor={settings.fgColor}
            bgColor={settings.bgColor}
          />
          
          <Box mt={3}>
            <Typography variant="h6" gutterBottom>
              {material.material_grade}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {material.supplier} • {material.heat_number} • {material.quantity} {material.unit}
            </Typography>
          </Box>
        </DialogContent>

        <DialogActions>
          <Button onClick={handleDownloadClient} startIcon={<DownloadIcon />}>
            Скачать
          </Button>
          <Button onClick={handlePrint} startIcon={<PrintIcon />}>
            Печать
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default QRCodeDisplay;