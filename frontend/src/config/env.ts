/**
 * Конфигурация окружения для MetalQMS Frontend
 */

export interface Config {
  apiUrl: string;
  apiTimeout: number;
  isDevelopment: boolean;
  isProduction: boolean;
}

const config: Config = {
  apiUrl: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001',
  apiTimeout: Number(import.meta.env.VITE_API_TIMEOUT) || 30000,
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD,
};

export { config };