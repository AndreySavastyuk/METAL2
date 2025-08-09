/**
 * Error Boundary компонент для обработки ошибок React
 */
import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  AlertTitle,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
} from '@mui/material';
import {
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  BugReport as BugReportIcon,
} from '@mui/icons-material';
import { ErrorBoundary as ReactErrorBoundary } from 'react-error-boundary';

interface ErrorFallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
  errorInfo?: string;
}

const ErrorFallback: React.FC<ErrorFallbackProps> = ({
  error,
  resetErrorBoundary,
  errorInfo,
}) => {
  const handleReportError = () => {
    // Здесь можно добавить отправку ошибки в систему мониторинга
    console.error('Error reported:', error, errorInfo);
    
    // Например, отправка в Sentry, LogRocket и т.д.
    // Sentry.captureException(error);
  };

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="400px"
      p={3}
    >
      <Paper sx={{ p: 4, maxWidth: 600, width: '100%' }}>
        <Box textAlign="center" mb={3}>
          <ErrorIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            Что-то пошло не так
          </Typography>
          <Typography variant="body1" color="text.secondary" mb={3}>
            Произошла неожиданная ошибка. Мы автоматически получили уведомление об этой проблеме.
          </Typography>
        </Box>

        <Alert severity="error" sx={{ mb: 3 }}>
          <AlertTitle>Детали ошибки</AlertTitle>
          <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
            {error.message}
          </Typography>
        </Alert>

        {/* Подробная информация об ошибке (для разработчиков) */}
        <Accordion sx={{ mb: 3 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="body2">
              Техническая информация
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box
              component="pre"
              sx={{
                fontSize: '0.75rem',
                fontFamily: 'monospace',
                bgcolor: 'grey.100',
                p: 2,
                borderRadius: 1,
                overflow: 'auto',
                maxHeight: 200,
              }}
            >
              {error.stack}
            </Box>
            {errorInfo && (
              <Box
                component="pre"
                sx={{
                  fontSize: '0.75rem',
                  fontFamily: 'monospace',
                  bgcolor: 'grey.100',
                  p: 2,
                  borderRadius: 1,
                  overflow: 'auto',
                  maxHeight: 200,
                  mt: 1,
                }}
              >
                {errorInfo}
              </Box>
            )}
          </AccordionDetails>
        </Accordion>

        <Box display="flex" gap={2} justifyContent="center">
          <Button
            variant="contained"
            onClick={resetErrorBoundary}
            startIcon={<RefreshIcon />}
          >
            Попробовать снова
          </Button>
          
          <Button
            variant="outlined"
            onClick={handleReportError}
            startIcon={<BugReportIcon />}
          >
            Сообщить об ошибке
          </Button>
          
          <Button
            variant="text"
            onClick={() => window.location.reload()}
          >
            Перезагрузить страницу
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<ErrorFallbackProps>;
  onError?: (error: Error, errorInfo: string) => void;
}

export const AppErrorBoundary: React.FC<ErrorBoundaryProps> = ({
  children,
  fallback: FallbackComponent = ErrorFallback,
  onError,
}) => {
  const handleError = (error: Error, errorInfo: any) => {
    // Логирование ошибки
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    // Вызов callback если предоставлен
    onError?.(error, errorInfo.componentStack || '');
    
    // Отправка в систему мониторинга
    // Здесь можно добавить интеграцию с Sentry, LogRocket и т.д.
  };

  return (
    <ReactErrorBoundary
      FallbackComponent={FallbackComponent}
      onError={handleError}
    >
      {children}
    </ReactErrorBoundary>
  );
};

// HOC для оборачивания компонентов в ErrorBoundary
export const withErrorBoundary = <P extends object>(
  Component: React.ComponentType<P>,
  errorFallback?: React.ComponentType<ErrorFallbackProps>
) => {
  const WrappedComponent = (props: P) => (
    <AppErrorBoundary fallback={errorFallback}>
      <Component {...props} />
    </AppErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
};

// Специализированный ErrorBoundary для форм
interface FormErrorFallbackProps extends ErrorFallbackProps {
  formName?: string;
}

const FormErrorFallback: React.FC<FormErrorFallbackProps> = ({
  error,
  resetErrorBoundary,
  formName = 'форме',
}) => (
  <Alert 
    severity="error" 
    action={
      <IconButton
        color="inherit"
        size="small"
        onClick={resetErrorBoundary}
      >
        <RefreshIcon />
      </IconButton>
    }
  >
    <AlertTitle>Ошибка в {formName}</AlertTitle>
    <Typography variant="body2">
      {error.message}
    </Typography>
    <Button size="small" onClick={resetErrorBoundary} sx={{ mt: 1 }}>
      Попробовать снова
    </Button>
  </Alert>
);

export const FormErrorBoundary: React.FC<{
  children: React.ReactNode;
  formName?: string;
}> = ({ children, formName }) => (
  <ReactErrorBoundary
    FallbackComponent={(props) => (
      <FormErrorFallback {...props} formName={formName} />
    )}
  >
    {children}
  </ReactErrorBoundary>
);

// Компонент для отображения ошибок API
interface ApiErrorProps {
  error: any;
  retry?: () => void;
  fallbackMessage?: string;
}

export const ApiError: React.FC<ApiErrorProps> = ({
  error,
  retry,
  fallbackMessage = 'Произошла ошибка при загрузке данных',
}) => {
  const getMessage = () => {
    if (error?.response?.data?.detail) {
      return error.response.data.detail;
    }
    if (error?.response?.data?.message) {
      return error.response.data.message;
    }
    if (error?.message) {
      return error.message;
    }
    return fallbackMessage;
  };

  const getStatusCode = () => {
    return error?.response?.status;
  };

  return (
    <Alert 
      severity="error"
      action={
        retry && (
          <Button color="inherit" size="small" onClick={retry}>
            Повторить
          </Button>
        )
      }
    >
      <AlertTitle>
        Ошибка {getStatusCode() && `(${getStatusCode()})`}
      </AlertTitle>
      {getMessage()}
    </Alert>
  );
};

export default AppErrorBoundary;