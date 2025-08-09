/**
 * Система логирования для MetalQMS Frontend
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  data?: any;
  component?: string;
  userId?: string;
  sessionId: string;
}

class Logger {
  private sessionId: string;
  private isDevelopment: boolean;
  private logLevel: LogLevel;

  constructor() {
    this.sessionId = this.generateSessionId();
    this.isDevelopment = import.meta.env.MODE === 'development';
    this.logLevel = this.getLogLevel();
    
    this.info('Logger initialized', {
      sessionId: this.sessionId,
      environment: import.meta.env.MODE,
      logLevel: this.logLevel
    });
  }

  private generateSessionId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private getLogLevel(): LogLevel {
    const envLevel = import.meta.env.VITE_LOG_LEVEL?.toLowerCase();
    if (['debug', 'info', 'warn', 'error'].includes(envLevel)) {
      return envLevel as LogLevel;
    }
    return this.isDevelopment ? 'debug' : 'info';
  }

  private shouldLog(level: LogLevel): boolean {
    const levels: Record<LogLevel, number> = {
      debug: 0,
      info: 1,
      warn: 2,
      error: 3
    };
    return levels[level] >= levels[this.logLevel];
  }

  private formatMessage(level: LogLevel, message: string, data?: any, component?: string): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      message,
      data,
      component,
      userId: this.getCurrentUserId(),
      sessionId: this.sessionId
    };
  }

  private getCurrentUserId(): string | undefined {
    try {
      const user = localStorage.getItem('currentUser');
      return user ? JSON.parse(user).id : undefined;
    } catch {
      return undefined;
    }
  }

  private writeLog(logEntry: LogEntry): void {
    if (!this.shouldLog(logEntry.level)) return;

    // Console output с цветами
    const colors = {
      debug: '#6B7280',
      info: '#3B82F6', 
      warn: '#F59E0B',
      error: '#EF4444'
    };

    const style = `color: ${colors[logEntry.level]}; font-weight: bold;`;
    const prefix = `[${logEntry.timestamp}] [${logEntry.level.toUpperCase()}]`;
    
    if (logEntry.component) {
      console.group(`%c${prefix} ${logEntry.component}`, style);
    } else {
      console.group(`%c${prefix}`, style);
    }

    console.log(logEntry.message);
    
    if (logEntry.data) {
      console.log('Data:', logEntry.data);
    }
    
    console.groupEnd();

    // Отправка на сервер в production
    if (!this.isDevelopment && ['warn', 'error'].includes(logEntry.level)) {
      this.sendToServer(logEntry);
    }

    // Сохранение в localStorage для отладки
    this.saveToLocalStorage(logEntry);
  }

  private async sendToServer(logEntry: LogEntry): Promise<void> {
    try {
      await fetch(`${import.meta.env.VITE_API_URL}/api/logs/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(logEntry)
      });
    } catch (error) {
      console.error('Failed to send log to server:', error);
    }
  }

  private saveToLocalStorage(logEntry: LogEntry): void {
    try {
      const logs = JSON.parse(localStorage.getItem('appLogs') || '[]');
      logs.push(logEntry);
      
      // Ограничиваем количество логов в localStorage
      const maxLogs = 100;
      if (logs.length > maxLogs) {
        logs.splice(0, logs.length - maxLogs);
      }
      
      localStorage.setItem('appLogs', JSON.stringify(logs));
    } catch (error) {
      console.error('Failed to save log to localStorage:', error);
    }
  }

  // Public методы для логирования
  debug(message: string, data?: any, component?: string): void {
    this.writeLog(this.formatMessage('debug', message, data, component));
  }

  info(message: string, data?: any, component?: string): void {
    this.writeLog(this.formatMessage('info', message, data, component));
  }

  warn(message: string, data?: any, component?: string): void {
    this.writeLog(this.formatMessage('warn', message, data, component));
  }

  error(message: string, error?: any, component?: string): void {
    const errorData = error instanceof Error ? {
      name: error.name,
      message: error.message,
      stack: error.stack
    } : error;
    
    this.writeLog(this.formatMessage('error', message, errorData, component));
  }

  // Специальные методы
  apiCall(method: string, url: string, data?: any, component?: string): void {
    this.debug(`API Call: ${method} ${url}`, data, component || 'API');
  }

  apiResponse(method: string, url: string, status: number, data?: any, component?: string): void {
    const level = status >= 400 ? 'error' : status >= 300 ? 'warn' : 'debug';
    this[level](`API Response: ${method} ${url} - ${status}`, data, component || 'API');
  }

  userAction(action: string, data?: any, component?: string): void {
    this.info(`User Action: ${action}`, data, component || 'USER');
  }

  pageView(path: string, component?: string): void {
    this.info(`Page View: ${path}`, { path }, component || 'NAVIGATION');
  }

  // Утилиты для отладки
  getLogs(): LogEntry[] {
    try {
      return JSON.parse(localStorage.getItem('appLogs') || '[]');
    } catch {
      return [];
    }
  }

  clearLogs(): void {
    localStorage.removeItem('appLogs');
    this.info('Logs cleared');
  }

  downloadLogs(): void {
    const logs = this.getLogs();
    const blob = new Blob([JSON.stringify(logs, null, 2)], { 
      type: 'application/json' 
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `metalqms-logs-${this.sessionId}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    this.info('Logs downloaded');
  }
}

// Создаем глобальный экземпляр логгера
export const logger = new Logger();

// Перехват глобальных ошибок
window.addEventListener('error', (event) => {
  logger.error('Global Error', {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    error: event.error
  }, 'GLOBAL');
});

window.addEventListener('unhandledrejection', (event) => {
  logger.error('Unhandled Promise Rejection', {
    reason: event.reason,
    promise: event.promise
  }, 'GLOBAL');
});

// Добавляем logger в глобальный объект для отладки
if (import.meta.env.MODE === 'development') {
  (window as any).logger = logger;
}

export default logger;