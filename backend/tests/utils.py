"""
Test utilities and helper functions
"""
import json
import tempfile
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient


class TestDataHelper:
    """Helper class for creating test data"""
    
    @staticmethod
    def create_material_data(**overrides) -> Dict[str, Any]:
        """Create material data dictionary"""
        data = {
            'material_grade': '40X',
            'supplier': 'МеталлТорг',
            'order_number': 'ORD-123456',
            'certificate_number': 'CERT-123456',
            'heat_number': 'HEAT-123456',
            'size': '⌀100',
            'quantity': '250.500',
            'unit': 'kg',
            'location': 'Секция А-1'
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_qc_inspection_data(**overrides) -> Dict[str, Any]:
        """Create QC inspection data dictionary"""
        data = {
            'visual_inspection_passed': True,
            'dimensional_check_passed': True,
            'marking_check_passed': True,
            'documentation_check_passed': True,
            'requires_ppsd': False,
            'comments': 'Test inspection'
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_lab_test_data(**overrides) -> Dict[str, Any]:
        """Create laboratory test data dictionary"""
        data = {
            'test_type': 'chemical_analysis',
            'test_results': {
                'carbon': 0.25,
                'manganese': 1.2,
                'silicon': 0.8
            },
            'equipment_used': 'Спектрометр АRL-01',
            'status': 'completed'
        }
        data.update(overrides)
        return data


class MockHelper:
    """Helper class for creating mocks"""
    
    @staticmethod
    def mock_qr_code_generation():
        """Create QR code generation mock"""
        with patch('apps.warehouse.models.qrcode.QRCode') as mock_qr:
            mock_qr_instance = MagicMock()
            mock_qr.return_value = mock_qr_instance
            
            mock_img = MagicMock()
            mock_qr_instance.make_image.return_value = mock_img
            
            yield mock_qr
    
    @staticmethod
    def mock_telegram_bot():
        """Create Telegram bot mock"""
        with patch('apps.notifications.services.Bot') as mock_bot:
            mock_bot_instance = MagicMock()
            mock_bot.return_value = mock_bot_instance
            
            # Mock successful message sending
            mock_message = MagicMock()
            mock_message.message_id = 123
            mock_bot_instance.send_message.return_value = mock_message
            
            yield mock_bot
    
    @staticmethod
    def mock_pdf_generation():
        """Create PDF generation mock"""
        with patch('reportlab.pdfgen.canvas.Canvas') as mock_canvas:
            mock_canvas_instance = MagicMock()
            mock_canvas.return_value = mock_canvas_instance
            yield mock_canvas


class FileHelper:
    """Helper class for file operations in tests"""
    
    @staticmethod
    def create_test_pdf(filename='test.pdf', content=None):
        """Create test PDF file"""
        if content is None:
            # Minimal valid PDF structure
            content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
        
        return SimpleUploadedFile(
            filename,
            content,
            content_type='application/pdf'
        )
    
    @staticmethod
    def create_test_image(filename='test.jpg', format='JPEG'):
        """Create test image file"""
        from PIL import Image
        from io import BytesIO
        
        # Create simple colored image
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format=format)
        buffer.seek(0)
        
        content_type = f'image/{format.lower()}'
        if format.lower() == 'jpeg':
            content_type = 'image/jpeg'
        
        return SimpleUploadedFile(
            filename,
            buffer.read(),
            content_type=content_type
        )
    
    @staticmethod
    def create_test_document(filename='test.docx'):
        """Create test document file"""
        content = b'PK\x03\x04' + b'test document content'  # ZIP-like header for Office docs
        return SimpleUploadedFile(
            filename,
            content,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )


class APITestHelper:
    """Helper class for API testing"""
    
    @staticmethod
    def get_paginated_response_data(response):
        """Extract data from paginated API response"""
        if 'results' in response.data:
            return response.data['results']
        return response.data
    
    @staticmethod
    def assert_paginated_response(test_case, response, expected_count=None):
        """Assert paginated response structure"""
        test_case.assertIn('results', response.data)
        test_case.assertIn('count', response.data)
        test_case.assertIn('next', response.data)
        test_case.assertIn('previous', response.data)
        
        if expected_count is not None:
            test_case.assertEqual(len(response.data['results']), expected_count)
    
    @staticmethod
    def assert_api_error(test_case, response, status_code, error_field=None):
        """Assert API error response"""
        test_case.assertEqual(response.status_code, status_code)
        
        if error_field:
            test_case.assertIn(error_field, response.data)


class WorkflowTestHelper:
    """Helper class for workflow testing"""
    
    @staticmethod
    def create_complete_workflow_data():
        """Create data for complete workflow test"""
        return {
            'material': TestDataHelper.create_material_data(
                material_grade='12X18H10T'  # PPSD required
            ),
            'receipt': {
                'document_number': 'RCP-WORKFLOW',
                'supplier_delivery_note': 'DEL-WORKFLOW'
            },
            'qc_inspection': TestDataHelper.create_qc_inspection_data(
                requires_ppsd=True
            ),
            'lab_tests': [
                TestDataHelper.create_lab_test_data(
                    test_type='chemical_analysis'
                ),
                TestDataHelper.create_lab_test_data(
                    test_type='mechanical_properties',
                    test_results={
                        'tensile_strength': 650,
                        'yield_strength': 450,
                        'elongation': 25
                    }
                )
            ]
        }
    
    @staticmethod
    def assert_workflow_completion(test_case, material):
        """Assert that complete workflow was executed"""
        from apps.warehouse.models import MaterialReceipt
        from apps.quality.models import QCInspection
        from apps.laboratory.models import LaboratoryTest
        
        # Check material receipt exists
        test_case.assertTrue(
            MaterialReceipt.objects.filter(material=material).exists(),
            "Material receipt should exist"
        )
        
        receipt = MaterialReceipt.objects.get(material=material)
        
        # Check QC inspection exists
        test_case.assertTrue(
            QCInspection.objects.filter(material_receipt=receipt).exists(),
            "QC inspection should exist"
        )
        
        qc_inspection = QCInspection.objects.get(material_receipt=receipt)
        
        # Check lab tests if PPSD required
        if qc_inspection.requires_ppsd:
            test_case.assertTrue(
                LaboratoryTest.objects.filter(material_receipt=receipt).exists(),
                "Laboratory tests should exist for PPSD materials"
            )


class ValidationTestHelper:
    """Helper class for validation testing"""
    
    @staticmethod
    def test_required_fields(test_case, url, method, required_fields, auth_client):
        """Test that required fields are properly validated"""
        for field in required_fields:
            with test_case.subTest(field=field):
                data = TestDataHelper.create_material_data()
                data[field] = ''  # Empty required field
                
                response = getattr(auth_client, method.lower())(url, data, format='json')
                test_case.assertEqual(response.status_code, 400)
                test_case.assertIn(field, response.data)
    
    @staticmethod
    def test_invalid_choices(test_case, url, method, choice_fields, auth_client):
        """Test validation of choice fields"""
        for field, invalid_value in choice_fields.items():
            with test_case.subTest(field=field):
                data = TestDataHelper.create_material_data()
                data[field] = invalid_value
                
                response = getattr(auth_client, method.lower())(url, data, format='json')
                test_case.assertEqual(response.status_code, 400)
                test_case.assertIn(field, response.data)


class PerformanceTestHelper:
    """Helper class for performance testing"""
    
    @staticmethod
    def measure_query_count(test_case, func, expected_max_queries=None):
        """Measure and assert query count"""
        from django.test.utils import override_settings
        from django.db import connection
        
        with override_settings(DEBUG=True):
            initial_query_count = len(connection.queries)
            func()
            final_query_count = len(connection.queries)
            
            actual_queries = final_query_count - initial_query_count
            
            if expected_max_queries is not None:
                test_case.assertLessEqual(
                    actual_queries, 
                    expected_max_queries,
                    f"Expected max {expected_max_queries} queries, got {actual_queries}"
                )
            
            return actual_queries
    
    @staticmethod
    def assert_no_n_plus_one(test_case, queryset_func, iteration_func):
        """Assert that there's no N+1 query problem"""
        from django.test.utils import override_settings
        from django.db import connection
        
        with override_settings(DEBUG=True):
            # Get baseline query count for first item
            connection.queries_log.clear()
            queryset = queryset_func()
            first_item = queryset.first()
            if first_item:
                iteration_func(first_item)
            baseline_queries = len(connection.queries)
            
            # Test with multiple items
            connection.queries_log.clear()
            items = list(queryset[:5])  # Get 5 items
            for item in items:
                iteration_func(item)
            
            multi_queries = len(connection.queries)
            
            # Should not scale linearly with number of items
            test_case.assertLessEqual(
                multi_queries,
                baseline_queries + 2,  # Allow small variance
                f"Possible N+1 query problem: {multi_queries} queries for 5 items vs {baseline_queries} for 1 item"
            )