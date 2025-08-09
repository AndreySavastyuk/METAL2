/**
 * Material-UI тема для MetalQMS
 */
import { createTheme, ThemeOptions } from '@mui/material/styles';
import { ruRU } from '@mui/material/locale';

// Цветовая палитра MetalQMS
const palette = {
  primary: {
    main: '#1976d2', // Синий цвет для основных элементов
    light: '#42a5f5',
    dark: '#1565c0',
    contrastText: '#ffffff',
  },
  secondary: {
    main: '#424242', // Серый цвет для металлургической тематики
    light: '#6d6d6d',
    dark: '#1b1b1b',
    contrastText: '#ffffff',
  },
  success: {
    main: '#388e3c', // Зеленый для одобренных материалов
    light: '#66bb6a',
    dark: '#2e7d32',
  },
  warning: {
    main: '#f57c00', // Оранжевый для ожидающих проверки
    light: '#ffb74d',
    dark: '#ef6c00',
  },
  error: {
    main: '#d32f2f', // Красный для отклоненных материалов
    light: '#ef5350',
    dark: '#c62828',
  },
  info: {
    main: '#0288d1', // Голубой для информационных сообщений
    light: '#03dac6',
    dark: '#0277bd',
  },
  grey: {
    50: '#fafafa',
    100: '#f5f5f5',
    200: '#eeeeee',
    300: '#e0e0e0',
    400: '#bdbdbd',
    500: '#9e9e9e',
    600: '#757575',
    700: '#616161',
    800: '#424242',
    900: '#212121',
  },
  background: {
    default: '#fafafa',
    paper: '#ffffff',
  },
  text: {
    primary: 'rgba(0, 0, 0, 0.87)',
    secondary: 'rgba(0, 0, 0, 0.6)',
    disabled: 'rgba(0, 0, 0, 0.38)',
  },
};

// Типография
const typography = {
  fontFamily: [
    '-apple-system',
    'BlinkMacSystemFont',
    '"Segoe UI"',
    'Roboto',
    '"Helvetica Neue"',
    'Arial',
    'sans-serif',
    '"Apple Color Emoji"',
    '"Segoe UI Emoji"',
    '"Segoe UI Symbol"',
  ].join(','),
  h1: {
    fontSize: '2.125rem',
    fontWeight: 500,
    lineHeight: 1.235,
  },
  h2: {
    fontSize: '1.875rem',
    fontWeight: 500,
    lineHeight: 1.2,
  },
  h3: {
    fontSize: '1.5rem',
    fontWeight: 500,
    lineHeight: 1.167,
  },
  h4: {
    fontSize: '1.25rem',
    fontWeight: 500,
    lineHeight: 1.235,
  },
  h5: {
    fontSize: '1.125rem',
    fontWeight: 500,
    lineHeight: 1.334,
  },
  h6: {
    fontSize: '1rem',
    fontWeight: 500,
    lineHeight: 1.6,
  },
  subtitle1: {
    fontSize: '1rem',
    fontWeight: 400,
    lineHeight: 1.75,
  },
  subtitle2: {
    fontSize: '0.875rem',
    fontWeight: 500,
    lineHeight: 1.57,
  },
  body1: {
    fontSize: '1rem',
    fontWeight: 400,
    lineHeight: 1.5,
  },
  body2: {
    fontSize: '0.875rem',
    fontWeight: 400,
    lineHeight: 1.43,
  },
  caption: {
    fontSize: '0.75rem',
    fontWeight: 400,
    lineHeight: 1.66,
  },
  overline: {
    fontSize: '0.75rem',
    fontWeight: 400,
    lineHeight: 2.66,
    textTransform: 'uppercase' as const,
  },
};

// Компоненты
const components = {
  // Кнопки
  MuiButton: {
    styleOverrides: {
      root: {
        textTransform: 'none' as const,
        borderRadius: 6,
        fontWeight: 500,
        boxShadow: 'none',
        '&:hover': {
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        },
      },
      containedPrimary: {
        '&:hover': {
          backgroundColor: palette.primary.dark,
        },
      },
    },
  },
  
  // Карточки
  MuiCard: {
    styleOverrides: {
      root: {
        borderRadius: 8,
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        '&:hover': {
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        },
      },
    },
  },
  
  // Paper
  MuiPaper: {
    styleOverrides: {
      root: {
        borderRadius: 8,
      },
      elevation1: {
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      },
    },
  },
  
  // Таблицы
  MuiTableHead: {
    styleOverrides: {
      root: {
        backgroundColor: palette.grey[50],
        '& .MuiTableCell-head': {
          fontWeight: 600,
          color: palette.text.primary,
        },
      },
    },
  },
  
  MuiTableRow: {
    styleOverrides: {
      root: {
        '&:hover': {
          backgroundColor: palette.grey[50],
        },
        '&.Mui-selected': {
          backgroundColor: `${palette.primary.main}08`,
          '&:hover': {
            backgroundColor: `${palette.primary.main}12`,
          },
        },
      },
    },
  },
  
  // Чипы для статусов
  MuiChip: {
    styleOverrides: {
      root: {
        borderRadius: 6,
        fontWeight: 500,
      },
      colorSuccess: {
        backgroundColor: palette.success.main,
        color: '#ffffff',
      },
      colorWarning: {
        backgroundColor: palette.warning.main,
        color: '#ffffff',
      },
      colorError: {
        backgroundColor: palette.error.main,
        color: '#ffffff',
      },
    },
  },
  
  // Поля ввода
  MuiTextField: {
    styleOverrides: {
      root: {
        '& .MuiOutlinedInput-root': {
          borderRadius: 6,
        },
      },
    },
  },
  
  // Диалоги
  MuiDialog: {
    styleOverrides: {
      paper: {
        borderRadius: 12,
      },
    },
  },
  
  // Аккордеоны
  MuiAccordion: {
    styleOverrides: {
      root: {
        borderRadius: 8,
        '&:before': {
          display: 'none',
        },
        '&.Mui-expanded': {
          margin: 0,
        },
      },
    },
  },
  
  // Алерты
  MuiAlert: {
    styleOverrides: {
      root: {
        borderRadius: 8,
      },
    },
  },
  
  // Загрузочные индикаторы
  MuiLinearProgress: {
    styleOverrides: {
      root: {
        borderRadius: 4,
        height: 6,
      },
    },
  },
  
  // Меню
  MuiMenu: {
    styleOverrides: {
      paper: {
        borderRadius: 8,
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      },
    },
  },
};

// Базовая тема
const themeOptions: ThemeOptions = {
  palette,
  typography,
  components,
  spacing: 8,
  shape: {
    borderRadius: 8,
  },
  breakpoints: {
    values: {
      xs: 0,
      sm: 600,
      md: 900,
      lg: 1200,
      xl: 1536,
    },
  },
  transitions: {
    easing: {
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
      easeOut: 'cubic-bezier(0.0, 0, 0.2, 1)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      sharp: 'cubic-bezier(0.4, 0, 0.6, 1)',
    },
    duration: {
      shortest: 150,
      shorter: 200,
      short: 250,
      standard: 300,
      complex: 375,
      enteringScreen: 225,
      leavingScreen: 195,
    },
  },
};

// Создаем тему с русской локализацией
export const materialTheme = createTheme(themeOptions, ruRU);

// Дополнительные стили для состояний материалов
export const materialStatusColors = {
  pending_qc: {
    color: palette.warning.main,
    backgroundColor: `${palette.warning.main}20`,
    borderColor: palette.warning.main,
  },
  in_qc: {
    color: palette.info.main,
    backgroundColor: `${palette.info.main}20`,
    borderColor: palette.info.main,
  },
  approved: {
    color: palette.success.main,
    backgroundColor: `${palette.success.main}20`,
    borderColor: palette.success.main,
  },
  rejected: {
    color: palette.error.main,
    backgroundColor: `${palette.error.main}20`,
    borderColor: palette.error.main,
  },
} as const;

// Общие стили для компонентов
export const commonStyles = {
  // Анимации
  fadeIn: {
    animation: 'fadeIn 0.3s ease-in-out',
    '@keyframes fadeIn': {
      from: { opacity: 0, transform: 'translateY(10px)' },
      to: { opacity: 1, transform: 'translateY(0)' },
    },
  },
  
  // Карточка с hover эффектом
  hoverCard: {
    transition: 'all 0.2s ease-in-out',
    cursor: 'pointer',
    '&:hover': {
      transform: 'translateY(-2px)',
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
    },
  },
  
  // Скроллбар
  scrollbar: {
    '&::-webkit-scrollbar': {
      width: 8,
      height: 8,
    },
    '&::-webkit-scrollbar-track': {
      backgroundColor: palette.grey[200],
      borderRadius: 4,
    },
    '&::-webkit-scrollbar-thumb': {
      backgroundColor: palette.grey[400],
      borderRadius: 4,
      '&:hover': {
        backgroundColor: palette.grey[500],
      },
    },
  },
  
  // Градиентные фоны
  gradients: {
    primary: `linear-gradient(135deg, ${palette.primary.main} 0%, ${palette.primary.dark} 100%)`,
    success: `linear-gradient(135deg, ${palette.success.main} 0%, ${palette.success.dark} 100%)`,
    warning: `linear-gradient(135deg, ${palette.warning.main} 0%, ${palette.warning.dark} 100%)`,
    error: `linear-gradient(135deg, ${palette.error.main} 0%, ${palette.error.dark} 100%)`,
  },
};

export default materialTheme;