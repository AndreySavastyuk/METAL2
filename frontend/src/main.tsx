/**
 * Точка входа React приложения MetalQMS
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { SnackbarProvider } from 'notistack';
import { ErrorBoundary } from 'react-error-boundary';

import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import theme from './theme/materialTheme';
import './index.css';

// Создание клиента React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 5 * 60 * 1000, // 5 минут
      gcTime: 10 * 60 * 1000, // 10 минут
    },
    mutations: {
      retry: 1,
    },
  },
});

// Компонент для обработки ошибок
const ErrorFallback: React.FC<{ error: Error; resetErrorBoundary: () => void }> = ({ 
  error, 
  resetErrorBoundary 
}) => (
  <div style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    flexDirection: 'column',
    fontFamily: 'Roboto, sans-serif',
    color: '#d32f2f',
    padding: '20px',
    textAlign: 'center'
  }}>
    <h1>🚨 Произошла ошибка</h1>
    <p>Что-то пошло не так в приложении MetalQMS</p>
    <details style={{ margin: '20px 0', textAlign: 'left' }}>
      <summary>Детали ошибки</summary>
      <pre style={{ fontSize: '12px', color: '#666' }}>{error.message}</pre>
    </details>
    <button 
      onClick={resetErrorBoundary}
      style={{
        padding: '10px 20px',
        backgroundColor: '#1976d2',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer'
      }}
    >
      Попробовать снова
    </button>
  </div>
);

// Убираем loading экран когда React готов
document.body.classList.add('loaded');

console.log('🚀 MetalQMS Frontend starting...');

// Проверяем поддержку современных браузеров
if (!window.Promise || !window.fetch || !window.Map || !window.Set) {
  const errorMsg = 'Ваш браузер не поддерживает современные JavaScript функции. Пожалуйста, обновите браузер.';
  console.error(errorMsg);
  alert(errorMsg);
}

// Инициализация React приложения
const container = document.getElementById('root');
if (!container) {
  throw new Error('Root container not found');
}

const root = ReactDOM.createRoot(container);

// Render приложения с обработкой ошибок
try {
  console.log('📦 Rendering React application...');
  
  root.render(
    <React.StrictMode>
      <ErrorBoundary FallbackComponent={ErrorFallback}>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <ThemeProvider theme={theme}>
              <CssBaseline />
              <SnackbarProvider 
                maxSnack={3}
                anchorOrigin={{
                  vertical: 'bottom',
                  horizontal: 'right',
                }}
              >
                <AuthProvider>
                  <App />
                </AuthProvider>
              </SnackbarProvider>
            </ThemeProvider>
          </BrowserRouter>
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
      </ErrorBoundary>
    </React.StrictMode>
  );
  
  console.log('✅ React application rendered successfully');
} catch (error) {
  console.error('❌ Failed to render React application:', error);
  
  // Fallback UI при критической ошибке
  root.render(
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      flexDirection: 'column',
      fontFamily: 'Roboto, sans-serif',
      color: '#d32f2f',
      padding: '20px',
      textAlign: 'center'
    }}>
      <h1>🚨 Критическая ошибка</h1>
      <p>Не удалось запустить приложение MetalQMS</p>
      <p style={{ fontSize: '14px', color: '#666', marginTop: '20px' }}>
        Попробуйте перезагрузить страницу или обратитесь к администратору
      </p>
      <button 
        onClick={() => {
          console.log('🔄 Manual page reload requested');
          window.location.reload();
        }}
        style={{
          marginTop: '20px',
          padding: '10px 20px',
          backgroundColor: '#1976d2',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        Перезагрузить страницу
      </button>
    </div>
  );
}

// Hot Module Replacement для development
if (import.meta.hot) {
  import.meta.hot.accept();
  console.log('🔥 HMR enabled');
}

// Логирование версии и окружения
const appInfo = {
  version: import.meta.env.VITE_APP_VERSION || '1.0.0',
  environment: import.meta.env.MODE,
  apiUrl: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001',
  buildTime: new Date().toISOString()
};

console.log(`
🏭 MetalQMS Frontend
📦 Версия: ${appInfo.version}
🌍 Окружение: ${appInfo.environment}
🔗 API URL: ${appInfo.apiUrl}
⏰ Время запуска: ${appInfo.buildTime}
`);

// Глобальная обработка неперехваченных ошибок JavaScript
window.addEventListener('error', (event) => {
  console.error('❌ Global JavaScript error:', {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    error: event.error?.stack
  });
});

// Глобальная обработка неперехваченных Promise отклонений
window.addEventListener('unhandledrejection', (event) => {
  console.error('❌ Unhandled Promise rejection:', {
    reason: event.reason,
    promise: event.promise
  });
});