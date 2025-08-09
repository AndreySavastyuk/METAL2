/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_APP_VERSION: string;
  readonly VITE_APP_ENVIRONMENT: string;
  readonly VITE_LOG_LEVEL: string;
  readonly VITE_QUERY_STALE_TIME: string;
  readonly VITE_QUERY_CACHE_TIME: string;
  readonly VITE_MAX_FILE_SIZE: string;
  readonly VITE_ALLOWED_FILE_TYPES: string;
  readonly VITE_QR_CODE_SIZE: string;
  readonly VITE_QR_ERROR_CORRECTION: string;
  readonly VITE_NOTIFICATION_DURATION: string;
  readonly VITE_MAX_NOTIFICATIONS: string;
  readonly VITE_ENABLE_DEVTOOLS: string;
  readonly VITE_ENABLE_ANALYTICS: string;
  readonly VITE_ENABLE_PWA: string;
  readonly VITE_DEBUG_MODE: string;
  readonly VITE_SHOW_CONSOLE_LOGS: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}