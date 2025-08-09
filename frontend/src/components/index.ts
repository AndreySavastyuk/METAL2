/**
 * Центральный экспорт всех компонентов MetalQMS
 */

// Layout компоненты
export { default as Layout } from './layout/Layout';
export { default as Breadcrumbs } from './layout/Breadcrumbs';

// Auth компоненты
export { default as ProtectedRoute } from './auth/ProtectedRoute';

// Common компоненты
export { default as LoadingSpinner } from './common/LoadingSpinner';
export { default as ErrorBoundary } from './common/ErrorBoundary';

// Material компоненты (существующие)
export { default as MaterialForm } from './MaterialForm';
export { default as MaterialList } from './MaterialList';
export { default as QRCodeDisplay } from './QRCodeDisplay';

// Error Boundary компоненты для форм
import ErrorBoundaryComponent from './common/ErrorBoundary';
export const AppErrorBoundary = ErrorBoundaryComponent;
export const FormErrorBoundary = ErrorBoundaryComponent;

// Re-export типов
export type { Material } from '../types/material';