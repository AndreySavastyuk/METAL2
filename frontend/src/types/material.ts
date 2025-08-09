/**
 * TypeScript интерфейсы для работы с материалами
 */

export interface Material {
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

export interface MaterialReceipt {
  id: number;
  material: Material;
  received_by: number;
  receipt_date: string;
  document_number: string;
  status: 'pending_qc' | 'in_qc' | 'approved' | 'rejected';
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface Certificate {
  id: number;
  material: number;
  pdf_file: string;
  uploaded_at: string;
  parsed_data: Record<string, unknown>;
  file_size?: number;
  file_hash?: string;
}

export interface MaterialFormData {
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

export interface MaterialListFilters {
  search?: string;
  material_grade?: string;
  supplier?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
}

export interface MaterialListParams {
  page?: number;
  page_size?: number;
  ordering?: string;
  search?: string;
  [key: string]: unknown;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiError {
  detail?: string;
  message?: string;
  errors?: Record<string, string[]>;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface QRCodeData {
  id: string;
  grade: string;
  supplier: string;
  certificate: string;
  heat: string;
  quantity: string;
  unit: string;
}

// Константы для статусов
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

// Utility types
export type MaterialStatus = typeof MATERIAL_STATUS_CHOICES[number]['value'];
export type MaterialUnit = typeof UNIT_CHOICES[number]['value'];