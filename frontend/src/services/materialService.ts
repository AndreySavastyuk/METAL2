/**
 * API сервис для работы с материалами
 */
import axios, { AxiosProgressEvent } from 'axios';
import {
  Material,
  MaterialReceipt,
  MaterialFormData,
  MaterialListParams,
  PaginatedResponse,
  UploadProgress,
} from '../types/material';
import { config } from '../config/env';

const apiClient = axios.create({
  baseURL: `${config.apiUrl}/api`,
  timeout: config.apiTimeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor для добавления токена авторизации
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor для обработки ошибок
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export class MaterialService {
  /**
   * Получить список материалов с пагинацией и фильтрами
   */
  static async getMaterials(params: MaterialListParams = {}): Promise<PaginatedResponse<Material>> {
    const response = await apiClient.get('/warehouse/materials/', { params });
    return response.data;
  }

  /**
   * Получить материал по ID
   */
  static async getMaterial(id: number): Promise<Material> {
    const response = await apiClient.get(`/warehouse/materials/${id}/`);
    return response.data;
  }

  /**
   * Создать новый материал
   */
  static async createMaterial(
    data: MaterialFormData,
    onUploadProgress?: (progress: UploadProgress) => void
  ): Promise<Material> {
    const formData = new FormData();
    
    // Добавляем основные поля
    Object.entries(data).forEach(([key, value]) => {
      if (key !== 'certificate_file' && value !== undefined && value !== null) {
        formData.append(key, value.toString());
      }
    });

    // Добавляем файл сертификата если есть
    if (data.certificate_file) {
      formData.append('certificate_file', data.certificate_file);
    }

    const response = await apiClient.post('/warehouse/materials/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent: AxiosProgressEvent) => {
        if (onUploadProgress && progressEvent.total) {
          const progress: UploadProgress = {
            loaded: progressEvent.loaded,
            total: progressEvent.total,
            percentage: Math.round((progressEvent.loaded * 100) / progressEvent.total),
          };
          onUploadProgress(progress);
        }
      },
    });
    
    return response.data;
  }

  /**
   * Обновить материал
   */
  static async updateMaterial(
    id: number,
    data: Partial<MaterialFormData>,
    onUploadProgress?: (progress: UploadProgress) => void
  ): Promise<Material> {
    const formData = new FormData();
    
    Object.entries(data).forEach(([key, value]) => {
      if (key !== 'certificate_file' && value !== undefined && value !== null) {
        formData.append(key, value.toString());
      }
    });

    if (data.certificate_file) {
      formData.append('certificate_file', data.certificate_file);
    }

    const response = await apiClient.patch(`/warehouse/materials/${id}/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent: AxiosProgressEvent) => {
        if (onUploadProgress && progressEvent.total) {
          const progress: UploadProgress = {
            loaded: progressEvent.loaded,
            total: progressEvent.total,
            percentage: Math.round((progressEvent.loaded * 100) / progressEvent.total),
          };
          onUploadProgress(progress);
        }
      },
    });
    
    return response.data;
  }

  /**
   * Удалить материал
   */
  static async deleteMaterial(id: number): Promise<void> {
    await apiClient.delete(`/warehouse/materials/${id}/`);
  }

  /**
   * Получить список поступлений материалов
   */
  static async getMaterialReceipts(params: MaterialListParams = {}): Promise<PaginatedResponse<MaterialReceipt>> {
    const response = await apiClient.get('/warehouse/material-receipts/', { params });
    return response.data;
  }

  /**
   * Изменить статус поступления материала
   */
  static async changeReceiptStatus(
    id: number,
    status: string,
    comment?: string
  ): Promise<MaterialReceipt> {
    const response = await apiClient.post(`/warehouse/material-receipts/${id}/change_status/`, {
      status,
      comment,
    });
    return response.data;
  }

  /**
   * Получить QR код материала
   */
  static async generateQRCode(id: number): Promise<{ qr_code_url: string }> {
    const response = await apiClient.post(`/warehouse/materials/${id}/generate_qr/`);
    return response.data;
  }

  /**
   * Скачать QR код как изображение
   */
  static async downloadQRCode(id: number): Promise<Blob> {
    const response = await apiClient.get(`/warehouse/materials/${id}/download_qr/`, {
      responseType: 'blob',
    });
    return response.data;
  }

  /**
   * Получить статистику материалов
   */
  static async getMaterialStatistics(): Promise<Record<string, number>> {
    const response = await apiClient.get('/warehouse/materials/statistics/');
    return response.data;
  }

  /**
   * Поиск поставщиков для автодополнения
   */
  static async searchSuppliers(query: string): Promise<string[]> {
    const response = await apiClient.get('/warehouse/suppliers/search/', {
      params: { q: query },
    });
    return response.data.results || [];
  }

  /**
   * Поиск марок материалов для автодополнения
   */
  static async searchGrades(query: string): Promise<string[]> {
    const response = await apiClient.get('/warehouse/grades/search/', {
      params: { q: query },
    });
    return response.data.results || [];
  }

  /**
   * Экспорт материалов в Excel
   */
  static async exportMaterials(params: MaterialListParams = {}): Promise<Blob> {
    const response = await apiClient.get('/warehouse/materials/export/', {
      params,
      responseType: 'blob',
    });
    return response.data;
  }

  /**
   * Импорт материалов из Excel
   */
  static async importMaterials(
    file: File,
    onUploadProgress?: (progress: UploadProgress) => void
  ): Promise<{ success: number; errors: string[] }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/warehouse/materials/import/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent: AxiosProgressEvent) => {
        if (onUploadProgress && progressEvent.total) {
          const progress: UploadProgress = {
            loaded: progressEvent.loaded,
            total: progressEvent.total,
            percentage: Math.round((progressEvent.loaded * 100) / progressEvent.total),
          };
          onUploadProgress(progress);
        }
      },
    });
    
    return response.data;
  }
}

export default MaterialService;