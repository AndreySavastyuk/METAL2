# React TypeScript компоненты для MetalQMS

## Обзор

Набор React TypeScript компонентов для управления материалами в системе MetalQMS с использованием Material-UI, react-hook-form, и современных практик разработки.

## Созданные компоненты

### 📋 MaterialList
Компонент таблицы материалов с полным функционалом:

**Возможности:**
- Сортировка по всем колонкам
- Фильтрация и поиск в реальном времени
- Пагинация с настраиваемым размером страницы
- Выбор строк (single/multiple)
- Меню действий для каждого материала
- Статусные badges с цветовой кодировкой
- Responsive дизайн

**Использование:**
```tsx
import { MaterialList } from '../components';

<MaterialList
  onEdit={(material) => console.log('Edit:', material)}
  onDelete={(material) => console.log('Delete:', material)}
  onCreate={() => console.log('Create new material')}
  onViewQR={(material) => console.log('View QR:', material)}
  showActions={true}
  selectable={false}
  onSelectionChange={(selectedIds) => console.log('Selected:', selectedIds)}
/>
```

### 📝 MaterialForm
Форма создания/редактирования материала с валидацией:

**Возможности:**
- React Hook Form + Yup валидация
- Автодополнение для поставщиков и марок
- Drag & Drop загрузка PDF сертификатов
- Progress индикатор загрузки
- Предпросмотр PDF файлов
- Responsive layout
- TypeScript типизация

**Использование:**
```tsx
import { MaterialForm } from '../components';

<MaterialForm
  material={existingMaterial} // Для редактирования
  onSuccess={(material) => console.log('Saved:', material)}
  onCancel={() => console.log('Cancelled')}
  readOnly={false}
/>
```

### 🔲 QRCodeDisplay
Компонент отображения и управления QR кодами:

**Возможности:**
- Генерация QR кодов с данными материала
- Настройка размера и уровня коррекции ошибок
- Скачивание как PNG изображение
- Печать с дополнительной информацией
- Полноэкранный режим просмотра
- Кастомизируемые настройки

**Использование:**
```tsx
import { QRCodeDisplay } from '../components';

<QRCodeDisplay
  material={material}
  size={256}
  showMaterialInfo={true}
  showControls={true}
  onClose={() => setQrDialogOpen(false)}
/>
```

## Дополнительные компоненты

### 🔄 Loading States
```tsx
import { LoadingSpinner, TableLoading, CardLoading } from '../components';

// Общий спиннер
<LoadingSpinner message="Загрузка..." variant="circular" />

// Скелетон для таблицы
<TableLoading rows={5} columns={6} />

// Скелетон для карточек
<CardLoading count={3} />
```

### ⚠️ Error Boundaries
```tsx
import { 
  AppErrorBoundary, 
  FormErrorBoundary, 
  ApiError,
  withErrorBoundary 
} from '../components';

// Общий error boundary
<AppErrorBoundary>
  <YourComponent />
</AppErrorBoundary>

// Error boundary для форм
<FormErrorBoundary formName="создания материала">
  <MaterialForm />
</FormErrorBoundary>

// HOC для оборачивания компонентов
const SafeComponent = withErrorBoundary(YourComponent);

// Компонент для API ошибок
<ApiError 
  error={error} 
  retry={() => refetch()} 
  fallbackMessage="Ошибка загрузки данных" 
/>
```

## TypeScript интерфейсы

### Основные типы
```tsx
interface Material {
  id: number;
  material_grade: string;
  supplier: string;
  order_number: string;
  certificate_number: string;
  heat_number: string;
  size: string;
  quantity: number;
  unit: 'kg' | 'pcs' | 'meters';
  location?: string;
  qr_code?: string;
  external_id: string;
  created_at: string;
  updated_at: string;
  created_by: number;
  updated_by: number;
}

interface MaterialFormData {
  material_grade: string;
  supplier: string;
  order_number: string;
  certificate_number: string;
  heat_number: string;
  size: string;
  quantity: number;
  unit: 'kg' | 'pcs' | 'meters';
  location?: string;
  certificate_file?: File;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
```

### Статусы и константы
```tsx
export const MATERIAL_STATUS_CHOICES = [
  { value: 'pending_qc', label: 'Ожидает ОТК', color: '#f57c00' },
  { value: 'in_qc', label: 'В ОТК', color: '#1976d2' },
  { value: 'approved', label: 'Одобрено', color: '#388e3c' },
  { value: 'rejected', label: 'Отклонено', color: '#d32f2f' },
] as const;

export const UNIT_CHOICES = [
  { value: 'kg', label: 'Килограммы' },
  { value: 'pcs', label: 'Штуки' },
  { value: 'meters', label: 'Метры' },
] as const;
```

## API сервис

### MaterialService
```tsx
import { MaterialService } from '../services/materialService';

// Получение списка материалов
const materials = await MaterialService.getMaterials({
  page: 1,
  page_size: 25,
  search: 'поисковый запрос',
  ordering: '-created_at'
});

// Создание материала
const newMaterial = await MaterialService.createMaterial(
  formData,
  (progress) => console.log(`Загрузка: ${progress.percentage}%`)
);

// Автодополнение поставщиков
const suppliers = await MaterialService.searchSuppliers('МеталлТорг');

// Генерация QR кода
const qrData = await MaterialService.generateQRCode(materialId);

// Скачивание QR кода
const qrBlob = await MaterialService.downloadQRCode(materialId);
```

## Material-UI тема

### Кастомная тема MetalQMS
```tsx
import { materialTheme, materialStatusColors } from '../theme/materialTheme';

// Использование темы
<ThemeProvider theme={materialTheme}>
  <YourApp />
</ThemeProvider>

// Цвета статусов
const statusColor = materialStatusColors.approved.color;
```

### Общие стили
```tsx
import { commonStyles } from '../theme/materialTheme';

// Анимация появления
<Box sx={commonStyles.fadeIn}>Content</Box>

// Карточка с hover эффектом
<Card sx={commonStyles.hoverCard}>Content</Card>

// Кастомный скроллбар
<Box sx={commonStyles.scrollbar}>Scrollable content</Box>
```

## React Query интеграция

### Хуки для работы с данными
```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Запрос списка материалов
const { data: materials, isLoading, error } = useQuery({
  queryKey: ['materials', params],
  queryFn: () => MaterialService.getMaterials(params),
  keepPreviousData: true,
});

// Мутация создания материала
const createMutation = useMutation({
  mutationFn: MaterialService.createMaterial,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['materials'] });
    enqueueSnackbar('Материал создан', { variant: 'success' });
  },
});
```

## Примеры страниц

### MaterialsPage
Полнофункциональная страница управления материалами:

```tsx
import MaterialsPage from '../pages/MaterialsPage';

// Включает:
// - MaterialList с полным функционалом
// - Диалоги создания/редактирования
// - QR код менеджмент
// - Error boundaries
// - Loading states
// - Breadcrumbs навигация
```

### App.tsx
Основное приложение с провайдерами:

```tsx
import App from './App';

// Настройки:
// - ThemeProvider с кастомной темой
// - QueryClientProvider для React Query
// - SnackbarProvider для уведомлений
// - Router для навигации
// - Error boundaries
// - React Query DevTools
```

## Валидация форм

### Yup схемы
```tsx
import * as yup from 'yup';

const validationSchema = yup.object({
  material_grade: yup
    .string()
    .required('Марка материала обязательна')
    .min(2, 'Минимум 2 символа'),
  supplier: yup
    .string()
    .required('Поставщик обязателен')
    .min(3, 'Минимум 3 символа'),
  quantity: yup
    .number()
    .required('Количество обязательно')
    .positive('Количество должно быть положительным'),
});
```

### React Hook Form
```tsx
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';

const { control, handleSubmit, formState: { errors } } = useForm({
  resolver: yupResolver(validationSchema),
  defaultValues: { /* ... */ },
});
```

## Обработка файлов

### Загрузка PDF сертификатов
```tsx
// Валидация файлов
const validateFile = (file: File) => {
  if (file.type !== 'application/pdf') {
    throw new Error('Только PDF файлы разрешены');
  }
  if (file.size > 50 * 1024 * 1024) {
    throw new Error('Файл слишком большой (макс. 50MB)');
  }
};

// Обработка загрузки с progress
const handleUpload = (file: File, onProgress: (progress: UploadProgress) => void) => {
  MaterialService.createMaterial(formData, onProgress);
};
```

### Предпросмотр PDF
```tsx
import { Document, Page, pdfjs } from 'react-pdf';

// Настройка worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/legacy/build/pdf.worker.min.js`;

// Компонент предпросмотра
<Document
  file={selectedFile}
  onLoadSuccess={({ numPages }) => setNumPages(numPages)}
>
  <Page pageNumber={1} scale={1.0} />
</Document>
```

## QR код функциональность

### Генерация QR кодов
```tsx
import QRCode from 'qrcode.react';

const qrData = {
  id: material.external_id,
  grade: material.material_grade,
  supplier: material.supplier,
  certificate: material.certificate_number,
  heat: material.heat_number,
  quantity: material.quantity.toString(),
  unit: material.unit,
};

<QRCode
  value={JSON.stringify(qrData)}
  size={256}
  level="M"
  includeMargin={true}
/>
```

### Печать QR кодов
```tsx
const handlePrint = () => {
  const printWindow = window.open('', '_blank');
  printWindow.document.write(`
    <html>
      <head><title>QR код - ${material.material_grade}</title></head>
      <body>
        <div style="text-align: center;">
          ${qrElement.innerHTML}
          <div>
            <h3>${material.material_grade}</h3>
            <p>Поставщик: ${material.supplier}</p>
            <p>Плавка: ${material.heat_number}</p>
          </div>
        </div>
      </body>
    </html>
  `);
  printWindow.print();
};
```

## Производительность

### Оптимизации
- React.memo для компонентов
- useMemo для вычислений
- useCallback для функций
- React Query кэширование
- Виртуализация для больших списков
- Lazy loading компонентов

### Мемоизация
```tsx
// Мемоизированные вычисления
const filteredMaterials = useMemo(() => {
  return materials?.results.filter(material => 
    material.material_grade.toLowerCase().includes(searchTerm.toLowerCase())
  );
}, [materials, searchTerm]);

// Мемоизированные callbacks
const handleRowSelect = useCallback((id: number, selected: boolean) => {
  setSelectedIds(prev => 
    selected ? [...prev, id] : prev.filter(selectedId => selectedId !== id)
  );
}, []);
```

## Тестирование

### Unit тесты
```tsx
// Пример теста компонента
import { render, screen, fireEvent } from '@testing-library/react';
import { MaterialList } from '../components';

test('renders material list', () => {
  render(<MaterialList />);
  expect(screen.getByText('Марка материала')).toBeInTheDocument();
});

test('handles search input', () => {
  render(<MaterialList />);
  const searchInput = screen.getByPlaceholderText('Поиск по сертификату...');
  fireEvent.change(searchInput, { target: { value: '40X' } });
  expect(searchInput.value).toBe('40X');
});
```

### Integration тесты
```tsx
// Тест API интеграции
import { MaterialService } from '../services/materialService';

jest.mock('axios');

test('creates material successfully', async () => {
  const mockMaterial = { id: 1, material_grade: '40X' };
  axios.post.mockResolvedValue({ data: mockMaterial });
  
  const result = await MaterialService.createMaterial(formData);
  expect(result).toEqual(mockMaterial);
});
```

## Развертывание

### Build команды
```bash
# Разработка
npm run dev

# Сборка для продакшена
npm run build

# Линтинг
npm run lint

# Форматирование
npm run format
```

### Environment Variables
```env
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_ENVIRONMENT=development
```

## Best Practices

### Структура компонентов
1. Всегда используйте TypeScript интерфейсы
2. Применяйте Error Boundaries
3. Используйте loading states
4. Мемоизируйте тяжелые вычисления
5. Следуйте принципам SOLID

### API интеграция
1. Используйте React Query для кэширования
2. Обрабатывайте все типы ошибок
3. Показывайте progress для загрузок
4. Реализуйте retry логику
5. Валидируйте данные на клиенте

### UX/UI
1. Показывайте состояния загрузки
2. Предоставляйте понятные сообщения об ошибках
3. Используйте consistent цветовую схему
4. Реализуйте responsive дизайн
5. Добавляйте keyboard navigation

---

*Последнее обновление: 2024-01-15*