"""
Сервисы для обработки PDF сертификатов
"""
import logging
import re
import hashlib
import io
import tempfile
from typing import Optional, Dict, Any, List
from pathlib import Path
from PIL import Image
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    fitz = None
import pypdf
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Q
from django.utils import timezone
from apps.warehouse.models import Certificate
from .models import CertificateSearchIndex, CertificatePreview, ProcessingLog

logger = logging.getLogger(__name__)


class CertificateProcessor:
    """Основной сервис для обработки PDF сертификатов"""
    
    # Регулярные выражения для извлечения данных
    GRADE_PATTERNS = [
        r'марка[:\s]+([А-Я0-9ХТ]+)',
        r'сталь[:\s]+([А-Я0-9ХТ]+)',
        r'grade[:\s]+([A-Z0-9]+)',
        r'материал[:\s]+([А-Я0-9ХТ]+)',
    ]
    
    HEAT_NUMBER_PATTERNS = [
        r'плавка[:\s№]+([А-Я0-9\-]+)',
        r'№\s*плавки[:\s]+([А-Я0-9\-]+)',
        r'heat\s*(?:no|number)[:\s]+([A-Z0-9\-]+)',
        r'плавка\s*№\s*([А-Я0-9\-]+)',
    ]
    
    CERTIFICATE_NUMBER_PATTERNS = [
        r'сертификат[:\s№]+([А-Я0-9\-/]+)',
        r'№\s*сертификата[:\s]+([А-Я0-9\-/]+)',
        r'certificate[:\s№]+([A-Z0-9\-/]+)',
        r'сертификат\s*№\s*([А-Я0-9\-/]+)',
    ]
    
    SUPPLIER_PATTERNS = [
        r'поставщик[:\s]+([А-Яа-я\s\"\-\.]+)',
        r'изготовитель[:\s]+([А-Яа-я\s\"\-\.]+)',
        r'предприятие[:\s]+([А-Яа-я\s\"\-\.]+)',
        r'supplier[:\s]+([A-Za-z\s\"\-\.]+)',
    ]
    
    # Элементы химического состава
    CHEMICAL_ELEMENTS = [
        'C', 'Si', 'Mn', 'P', 'S', 'Cr', 'Ni', 'Mo', 'Cu', 'Al', 'Ti', 'V', 'Nb', 'W', 'Co', 'B', 'N'
    ]
    
    def __init__(self):
        self.processing_timeout = 300  # 5 минут
    
    def extract_text_from_pdf(self, file_path: str) -> Optional[str]:
        """
        Извлечение текста из PDF файла с обработкой ошибок
        """
        log_entry = None
        try:
            # Создаем лог операции
            if hasattr(file_path, 'certificate'):
                certificate = file_path.certificate
            else:
                # Если передан путь к файлу, пытаемся найти сертификат
                certificate = Certificate.objects.filter(
                    pdf_file__icontains=Path(file_path).name
                ).first()
            
            if certificate:
                log_entry = ProcessingLog.objects.create(
                    certificate=certificate,
                    operation='text_extraction',
                    status='started'
                )
            
            # Сначала пробуем pypdf (быстрее)
            try:
                text = self._extract_with_pypdf(file_path)
                if text and len(text.strip()) > 50:  # Минимальная длина текста
                    if log_entry:
                        self._complete_log(log_entry, {'method': 'pypdf', 'text_length': len(text)})
                    return text
            except Exception as e:
                logger.warning(f"pypdf не смог извлечь текст: {e}")
            
            # Если pypdf не справился, используем PyMuPDF
            try:
                text = self._extract_with_pymupdf(file_path)
                if text:
                    if log_entry:
                        self._complete_log(log_entry, {'method': 'pymupdf', 'text_length': len(text)})
                    return text
            except Exception as e:
                logger.warning(f"PyMuPDF не смог извлечь текст: {e}")
            
            # Если ничего не помогло
            if log_entry:
                self._fail_log(log_entry, "Не удалось извлечь текст ни одним методом")
            
            return None
            
        except Exception as e:
            error_msg = f"Критическая ошибка извлечения текста: {e}"
            logger.error(error_msg)
            if log_entry:
                self._fail_log(log_entry, error_msg)
            return None
    
    def _extract_with_pypdf(self, file_path: str) -> str:
        """Извлечение текста с помощью pypdf"""
        with open(file_path, 'rb') as file:
            reader = pypdf.PdfReader(file)
            
            # Проверяем, что PDF не поврежден
            if reader.is_encrypted:
                raise ValueError("PDF зашифрован")
            
            text = ""
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Страница {page_num + 1} ---\n"
                        text += page_text
                except Exception as e:
                    logger.warning(f"Ошибка извлечения текста со страницы {page_num + 1}: {e}")
                    continue
            
            return text.strip()
    
    def _extract_with_pymupdf(self, file_path: str) -> str:
        """Извлечение текста с помощью PyMuPDF (fitz)"""
        if not HAS_PYMUPDF:
            raise ImportError("PyMuPDF не установлен")
        
        doc = fitz.open(file_path)
        text = ""
        
        for page_num in range(doc.page_count):
            try:
                page = doc[page_num]
                page_text = page.get_text()
                if page_text:
                    text += f"\n--- Страница {page_num + 1} ---\n"
                    text += page_text
            except Exception as e:
                logger.warning(f"Ошибка извлечения текста со страницы {page_num + 1}: {e}")
                continue
        
        doc.close()
        return text.strip()
    
    def parse_certificate_data(self, text: str) -> Dict[str, Any]:
        """
        Парсинг данных из текста сертификата
        """
        if not text:
            return {}
        
        # Нормализуем текст
        normalized_text = self._normalize_text(text)
        
        parsed_data = {
            'grade': self._extract_grade(normalized_text),
            'heat_number': self._extract_heat_number(normalized_text),
            'certificate_number': self._extract_certificate_number(normalized_text),
            'supplier': self._extract_supplier(normalized_text),
            'chemical_composition': self._extract_chemical_composition(normalized_text),
            'mechanical_properties': self._extract_mechanical_properties(normalized_text),
            'test_results': self._extract_test_results(normalized_text),
            'parsing_metadata': {
                'text_length': len(text),
                'normalized_length': len(normalized_text),
                'parsing_date': timezone.now().isoformat(),
                'patterns_used': len(self.GRADE_PATTERNS) + len(self.HEAT_NUMBER_PATTERNS)
            }
        }
        
        return parsed_data
    
    def _normalize_text(self, text: str) -> str:
        """Нормализация текста для лучшего парсинга"""
        # Убираем лишние пробелы и переносы
        text = re.sub(r'\s+', ' ', text)
        # Убираем служебные символы
        text = re.sub(r'[^\w\s\.\,\:\;\-\№\%\(\)\/]', ' ', text)
        # Приводим к нижнему регистру для поиска
        return text.lower().strip()
    
    def _extract_grade(self, text: str) -> Optional[str]:
        """Извлечение марки материала"""
        for pattern in self.GRADE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
            if match:
                grade = match.group(1).strip().upper()
                # Валидация марки
                if len(grade) >= 2 and len(grade) <= 20:
                    return grade
        return None
    
    def _extract_heat_number(self, text: str) -> Optional[str]:
        """Извлечение номера плавки"""
        for pattern in self.HEAT_NUMBER_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
            if match:
                heat_number = match.group(1).strip().upper()
                # Валидация номера плавки
                if len(heat_number) >= 3 and len(heat_number) <= 30:
                    return heat_number
        return None
    
    def _extract_certificate_number(self, text: str) -> Optional[str]:
        """Извлечение номера сертификата"""
        for pattern in self.CERTIFICATE_NUMBER_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
            if match:
                cert_number = match.group(1).strip().upper()
                # Валидация номера сертификата
                if len(cert_number) >= 3 and len(cert_number) <= 50:
                    return cert_number
        return None
    
    def _extract_supplier(self, text: str) -> Optional[str]:
        """Извлечение поставщика"""
        for pattern in self.SUPPLIER_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
            if match:
                supplier = match.group(1).strip()
                # Очистка и валидация
                supplier = re.sub(r'[\"\']+', '', supplier)
                if len(supplier) >= 3 and len(supplier) <= 200:
                    return supplier
        return None
    
    def _extract_chemical_composition(self, text: str) -> Dict[str, float]:
        """Извлечение химического состава"""
        composition = {}
        
        for element in self.CHEMICAL_ELEMENTS:
            # Паттерны для поиска элементов и их содержания
            patterns = [
                rf'{element}\s*[:\-\s]*(\d+[.,]\d+)',
                rf'{element}\s*=\s*(\d+[.,]\d+)',
                rf'{element}\s*(\d+[.,]\d+)\s*%',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        # Берем первое найденное значение
                        value_str = matches[0].replace(',', '.')
                        value = float(value_str)
                        if 0 <= value <= 100:  # Валидация процентного содержания
                            composition[element] = value
                            break
                    except ValueError:
                        continue
        
        return composition
    
    def _extract_mechanical_properties(self, text: str) -> Dict[str, float]:
        """Извлечение механических свойств"""
        properties = {}
        
        # Паттерны для основных механических свойств
        patterns = {
            'yield_strength': [
                r'предел\s+текучести[:\s]*(\d+[.,]?\d*)',
                r'σ[тт][:\s]*(\d+[.,]?\d*)',
                r'yield\s+strength[:\s]*(\d+[.,]?\d*)',
            ],
            'tensile_strength': [
                r'временное\s+сопротивление[:\s]*(\d+[.,]?\d*)',
                r'σ[вb][:\s]*(\d+[.,]?\d*)',
                r'tensile\s+strength[:\s]*(\d+[.,]?\d*)',
            ],
            'elongation': [
                r'относительное\s+удлинение[:\s]*(\d+[.,]?\d*)',
                r'δ[:\s]*(\d+[.,]?\d*)\s*%',
                r'elongation[:\s]*(\d+[.,]?\d*)',
            ],
            'hardness': [
                r'твердость[:\s]*(\d+[.,]?\d*)',
                r'hb[:\s]*(\d+[.,]?\d*)',
                r'hardness[:\s]*(\d+[.,]?\d*)',
            ]
        }
        
        for prop_name, prop_patterns in patterns.items():
            for pattern in prop_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        value_str = matches[0].replace(',', '.')
                        value = float(value_str)
                        properties[prop_name] = value
                        break
                    except ValueError:
                        continue
        
        return properties
    
    def _extract_test_results(self, text: str) -> Dict[str, Any]:
        """Извлечение результатов испытаний"""
        results = {}
        
        # Поиск типов испытаний
        test_types = {
            'impact_test': ['ударная вязкость', 'impact toughness', 'кcv', 'kcv'],
            'bending_test': ['испытание на изгиб', 'bending test'],
            'ultrasonic_test': ['узк', 'ультразвуковой контроль', 'ultrasonic'],
            'magnetic_test': ['магнитопорошковый', 'magnetic particle'],
        }
        
        for test_name, keywords in test_types.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    results[test_name] = {'performed': True, 'found_in_text': True}
                    break
        
        # Поиск температур испытаний
        temp_patterns = [
            r'при\s+температуре[:\s]*([+-]?\d+)[°\s]*c',
            r'at[:\s]*([+-]?\d+)[°\s]*c',
            r'([+-]?\d+)[°\s]*c',
        ]
        
        temperatures = []
        for pattern in temp_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    temp = int(match)
                    if -200 <= temp <= 1000:  # Разумный диапазон температур
                        temperatures.append(temp)
                except ValueError:
                    continue
        
        if temperatures:
            results['test_temperatures'] = list(set(temperatures))
        
        return results
    
    def generate_certificate_preview(self, pdf_file) -> Optional[str]:
        """
        Генерация превью первой страницы PDF как изображения
        """
        if not HAS_PYMUPDF:
            logger.error("PyMuPDF не установлен - генерация превью недоступна")
            return None
            
        certificate = None
        log_entry = None
        
        try:
            # Находим сертификат
            if hasattr(pdf_file, 'certificate'):
                certificate = pdf_file.certificate
            else:
                certificate = Certificate.objects.filter(pdf_file=pdf_file).first()
            
            if certificate:
                log_entry = ProcessingLog.objects.create(
                    certificate=certificate,
                    operation='preview_generation',
                    status='started'
                )
            
            # Получаем путь к файлу
            if hasattr(pdf_file, 'path'):
                file_path = pdf_file.path
            else:
                file_path = pdf_file
            
            # Генерируем превью с помощью PyMuPDF
            doc = fitz.open(file_path)
            
            if doc.page_count == 0:
                raise ValueError("PDF не содержит страниц")
            
            # Получаем первую страницу
            page = doc[0]
            
            # Конвертируем в изображение с высоким разрешением
            mat = fitz.Matrix(2.0, 2.0)  # Масштаб x2 для лучшего качества
            pix = page.get_pixmap(matrix=mat)
            
            # Конвертируем в PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # Создаем превью (большое изображение)
            preview_io = io.BytesIO()
            image.save(preview_io, format='PNG', quality=95, optimize=True)
            preview_content = ContentFile(preview_io.getvalue())
            
            # Создаем миниатюру
            thumbnail = image.copy()
            thumbnail.thumbnail((300, 400), Image.Resampling.LANCZOS)
            
            thumbnail_io = io.BytesIO()
            thumbnail.save(thumbnail_io, format='PNG', quality=85, optimize=True)
            thumbnail_content = ContentFile(thumbnail_io.getvalue())
            
            doc.close()
            
            # Сохраняем файлы
            if certificate:
                preview_obj, created = CertificatePreview.objects.get_or_create(
                    certificate=certificate,
                    defaults={'generation_status': 'generating'}
                )
                
                # Генерируем уникальные имена файлов
                base_name = f"cert_{certificate.id}_{int(timezone.now().timestamp())}"
                preview_name = f"{base_name}_preview.png"
                thumbnail_name = f"{base_name}_thumb.png"
                
                # Сохраняем файлы
                preview_obj.preview_image.save(preview_name, preview_content)
                preview_obj.thumbnail.save(thumbnail_name, thumbnail_content)
                preview_obj.generation_status = 'completed'
                preview_obj.save()
                
                if log_entry:
                    self._complete_log(log_entry, {
                        'preview_size': len(preview_io.getvalue()),
                        'thumbnail_size': len(thumbnail_io.getvalue()),
                        'image_dimensions': f"{image.width}x{image.height}"
                    })
                
                return preview_obj.preview_image.url
            
            if log_entry:
                self._complete_log(log_entry, {'status': 'completed_without_save'})
            
            return None
            
        except Exception as e:
            error_msg = f"Ошибка генерации превью: {e}"
            logger.error(error_msg)
            
            if certificate:
                preview_obj, created = CertificatePreview.objects.get_or_create(
                    certificate=certificate
                )
                preview_obj.generation_status = 'failed'
                preview_obj.error_message = error_msg
                preview_obj.save()
            
            if log_entry:
                self._fail_log(log_entry, error_msg)
            
            return None
    
    def search_in_certificates(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Полнотекстовый поиск в сертификатах
        """
        if not query or len(query.strip()) < 2:
            return []
        
        try:
            # Нормализуем запрос
            normalized_query = self._normalize_text(query)
            
            results = []
            
            # Поиск в индексированных данных
            search_indexes = CertificateSearchIndex.objects.filter(
                processing_status='completed'
            )
            
            # Фильтруем по различным полям
            q_objects = Q()
            
            # Поиск в извлеченном тексте
            q_objects |= Q(extracted_text__icontains=query)
            
            # Поиск в структурированных данных
            q_objects |= Q(grade__icontains=query)
            q_objects |= Q(heat_number__icontains=query)
            q_objects |= Q(certificate_number__icontains=query)
            q_objects |= Q(supplier__icontains=query)
            
            # Если есть поддержка PostgreSQL full-text search
            try:
                from django.contrib.postgres.search import SearchQuery, SearchRank
                search_query = SearchQuery(normalized_query, config='russian')
                q_objects |= Q(search_vector=search_query)
            except ImportError:
                # Fallback для SQLite
                pass
            
            matching_indexes = search_indexes.filter(q_objects)[:limit]
            
            for index in matching_indexes:
                try:
                    certificate = index.certificate
                    result = {
                        'certificate_id': certificate.id,
                        'material_id': certificate.material.id,
                        'grade': index.grade or certificate.material.material_grade,
                        'heat_number': index.heat_number or certificate.material.heat_number,
                        'certificate_number': index.certificate_number or certificate.material.certificate_number,
                        'supplier': index.supplier or certificate.material.supplier,
                        'file_url': certificate.pdf_file.url if certificate.pdf_file else None,
                        'preview_url': None,
                        'uploaded_at': certificate.uploaded_at,
                        'match_score': self._calculate_match_score(query, index),
                        'matched_fields': self._get_matched_fields(query, index)
                    }
                    
                    # Добавляем превью если есть
                    if hasattr(certificate, 'preview') and certificate.preview.thumbnail:
                        result['preview_url'] = certificate.preview.thumbnail.url
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Ошибка обработки результата поиска: {e}")
                    continue
            
            # Сортируем по релевантности
            results.sort(key=lambda x: x['match_score'], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка поиска в сертификатах: {e}")
            return []
    
    def _calculate_match_score(self, query: str, index: CertificateSearchIndex) -> float:
        """Вычисление релевантности результата"""
        score = 0.0
        query_lower = query.lower()
        
        # Точное совпадение в структурированных полях (высший приоритет)
        if index.grade and query_lower == index.grade.lower():
            score += 10.0
        if index.heat_number and query_lower == index.heat_number.lower():
            score += 10.0
        if index.certificate_number and query_lower == index.certificate_number.lower():
            score += 10.0
        
        # Частичное совпадение в структурированных полях
        if index.grade and query_lower in index.grade.lower():
            score += 5.0
        if index.heat_number and query_lower in index.heat_number.lower():
            score += 5.0
        if index.supplier and query_lower in index.supplier.lower():
            score += 3.0
        
        # Совпадение в тексте
        if index.extracted_text and query_lower in index.extracted_text.lower():
            # Количество вхождений
            occurrences = index.extracted_text.lower().count(query_lower)
            score += min(occurrences * 0.5, 3.0)  # Максимум 3 балла за текст
        
        return score
    
    def _get_matched_fields(self, query: str, index: CertificateSearchIndex) -> List[str]:
        """Определение полей, в которых найдено совпадение"""
        matched = []
        query_lower = query.lower()
        
        if index.grade and query_lower in index.grade.lower():
            matched.append('grade')
        if index.heat_number and query_lower in index.heat_number.lower():
            matched.append('heat_number')
        if index.certificate_number and query_lower in index.certificate_number.lower():
            matched.append('certificate_number')
        if index.supplier and query_lower in index.supplier.lower():
            matched.append('supplier')
        if index.extracted_text and query_lower in index.extracted_text.lower():
            matched.append('text')
        
        return matched
    
    def _complete_log(self, log_entry: ProcessingLog, metadata: Dict[str, Any] = None):
        """Завершение лога операции"""
        log_entry.status = 'completed'
        log_entry.completed_at = timezone.now()
        log_entry.duration_seconds = (log_entry.completed_at - log_entry.started_at).total_seconds()
        if metadata:
            log_entry.metadata.update(metadata)
        log_entry.save()
    
    def _fail_log(self, log_entry: ProcessingLog, error_message: str):
        """Отметка об ошибке в логе"""
        log_entry.status = 'failed'
        log_entry.completed_at = timezone.now()
        log_entry.duration_seconds = (log_entry.completed_at - log_entry.started_at).total_seconds()
        log_entry.error_message = error_message
        log_entry.save()


# Singleton instance
certificate_processor = CertificateProcessor()