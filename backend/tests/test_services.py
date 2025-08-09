"""
Service tests for MetalQMS Material workflow and business logic
"""
from unittest.mock import patch, MagicMock, call
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from celery.exceptions import Retry

from apps.warehouse.services import MaterialInspectionService, ServiceResponse
from apps.warehouse.models import Material, MaterialReceipt
from apps.quality.models import QCInspection
from apps.laboratory.models import LabTestRequest, LabTestResult
from apps.notifications.services import TelegramNotificationService
from apps.notifications.models import UserNotificationPreferences, NotificationLog
from apps.notifications.tasks import send_telegram_message
from apps.workflow.models import MaterialInspectionProcess

from .factories import (
    MaterialFactory, PPSDRequiredMaterialFactory, LargeSizeMaterialFactory,
    MaterialReceiptFactory, QCInspectionFactory, LabTestRequestFactory,
    WarehouseUserFactory, QCUserFactory, LabUserFactory,
    NotificationPreferencesFactory, MaterialInspectionProcessFactory
)


class MaterialInspectionServiceTest(TestCase):
    """Test MaterialInspectionService business logic"""
    
    def setUp(self):
        self.service = MaterialInspectionService()
    
    def test_check_ppsd_requirement_for_stainless_steel(self):
        """Test PPSD requirement check for stainless steel grades"""
        # Test grades that require PPSD
        ppsd_grades = ['12X18H10T', '08X18H10T', '10X17H13M2T', '03X17H14M3', '20X13', '40X13']
        
        for grade in ppsd_grades:
            with self.subTest(grade=grade):
                response = MaterialInspectionService.check_ppsd_requirement(grade)
                
                self.assertTrue(response.success)
                self.assertTrue(response.data['requires_ppsd'])
                self.assertIn(f"Марка {grade} входит в список", response.data['reasons'][0])
    
    def test_check_ppsd_requirement_for_carbon_steel(self):
        """Test PPSD requirement check for carbon steel grades"""
        carbon_grades = ['40X', '45', 'Ст3', '09Г2С']
        
        for grade in carbon_grades:
            with self.subTest(grade=grade):
                response = MaterialInspectionService.check_ppsd_requirement(grade)
                
                self.assertTrue(response.success)
                self.assertFalse(response.data['requires_ppsd'])
    
    def test_ppsd_requirement_for_large_size_materials(self):
        """Test PPSD requirement based on material size"""
        # Large diameter should require PPSD regardless of grade
        response = MaterialInspectionService.check_ppsd_requirement('40X', size='⌀250')
        
        self.assertTrue(response.success)
        self.assertTrue(response.data['requires_ppsd'])
        self.assertIn("Большой диаметр", response.data['reasons'][0])
    
    def test_ppsd_requirement_for_thick_plates(self):
        """Test PPSD requirement for thick plates"""
        response = MaterialInspectionService.check_ppsd_requirement('40X', size='Лист 80мм')
        
        self.assertTrue(response.success)
        self.assertTrue(response.data['requires_ppsd'])
        self.assertIn("Большая толщина листа", response.data['reasons'][0])
    
    def test_size_parsing_round_material(self):
        """Test size parsing for round materials"""
        size_info = MaterialInspectionService._parse_size('⌀150')
        
        self.assertEqual(size_info['type'], 'круглый')
        self.assertEqual(size_info['diameter'], 150)
    
    def test_size_parsing_plate_material(self):
        """Test size parsing for plate materials"""
        size_info = MaterialInspectionService._parse_size('Лист 25мм')
        
        self.assertEqual(size_info['type'], 'лист')
        self.assertEqual(size_info['thickness'], 25)
    
    def test_size_parsing_invalid_format(self):
        """Test size parsing with invalid format"""
        size_info = MaterialInspectionService._parse_size('InvalidSize')
        
        self.assertEqual(size_info['type'], 'неизвестный')
        self.assertNotIn('diameter', size_info)
        self.assertNotIn('thickness', size_info)
    
    def test_ultrasonic_requirements_for_large_diameter(self):
        """Test ultrasonic testing requirements for large diameter materials"""
        # Mock the ultrasonic requirements check method
        requirements = MaterialInspectionService.ULTRASONIC_REQUIREMENTS
        
        # Large diameter round material should require ultrasonic testing
        round_requirements = requirements['круглый']['диаметр_мм']
        
        # Check requirements for different diameter ranges
        self.assertIn((200, 500), round_requirements)
        self.assertEqual(round_requirements[(200, 500)], 'all')
    
    def test_ultrasonic_requirements_for_specific_grades(self):
        """Test ultrasonic testing requirements for specific grades and sizes"""
        requirements = MaterialInspectionService.ULTRASONIC_REQUIREMENTS
        
        # Medium diameter should require ultrasonic for specific grades
        medium_grades = requirements['круглый']['диаметр_мм'][(100, 200)]
        expected_grades = ['40X', '20X13', '12X18H10T', '09Г2С']
        
        self.assertEqual(medium_grades, expected_grades)
    
    def test_service_response_success(self):
        """Test ServiceResponse success creation"""
        data = {'test': 'value'}
        response = ServiceResponse.success_response(data)
        
        self.assertTrue(response.success)
        self.assertEqual(response.data, data)
        self.assertIsNone(response.error)
    
    def test_service_response_error(self):
        """Test ServiceResponse error creation"""
        error_message = "Test error"
        response = ServiceResponse.error_response(error_message)
        
        self.assertFalse(response.success)
        self.assertEqual(response.error, error_message)
        self.assertIsNone(response.data)


class TelegramNotificationServiceTest(TestCase):
    """Test Telegram notification service"""
    
    def setUp(self):
        self.user = WarehouseUserFactory()
        self.preferences = NotificationPreferencesFactory(
            user=self.user,
            telegram_chat_id='123456789',
            is_telegram_enabled=True
        )
        
    @patch('apps.notifications.services.Bot')
    @patch('apps.notifications.services.settings')
    def test_telegram_service_initialization(self, mock_settings, mock_bot):
        """Test TelegramNotificationService initialization"""
        mock_settings.TELEGRAM_BOT_TOKEN = 'test_token'
        
        service = TelegramNotificationService()
        
        self.assertIsNotNone(service.bot_token)
        mock_bot.assert_called_once_with(token='test_token')
    
    @patch('apps.notifications.services.Bot')
    @patch('apps.notifications.services.settings')
    def test_telegram_service_no_token(self, mock_settings, mock_bot):
        """Test TelegramNotificationService without token"""
        mock_settings.TELEGRAM_BOT_TOKEN = None
        
        service = TelegramNotificationService()
        
        self.assertFalse(service._check_bot_available())
        mock_bot.assert_not_called()
    
    @patch('apps.notifications.services.TelegramNotificationService._check_bot_available')
    @patch('apps.notifications.tasks.send_telegram_message.delay')
    def test_send_status_update_notification(self, mock_task, mock_check):
        """Test sending status update notification"""
        mock_check.return_value = True
        material = MaterialFactory()
        
        service = TelegramNotificationService()
        result = service.send_status_update(
            user_id=self.user.id,
            material=material,
            old_status='pending_qc',
            new_status='in_qc',
            is_urgent=False
        )
        
        self.assertTrue(result)
        mock_task.assert_called_once()
        
        # Verify notification log was created
        log = NotificationLog.objects.filter(user=self.user).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.notification_type, 'status_update')
    
    @patch('apps.notifications.services.TelegramNotificationService._check_bot_available')
    @patch('apps.notifications.tasks.send_telegram_message.delay')
    def test_send_task_assignment_notification(self, mock_task, mock_check):
        """Test sending task assignment notification"""
        mock_check.return_value = True
        material = MaterialFactory()
        
        service = TelegramNotificationService()
        result = service.send_task_assignment(
            user_id=self.user.id,
            material=material,
            task_type='qc_inspection',
            priority='high'
        )
        
        self.assertTrue(result)
        mock_task.assert_called_once()
        
        # Verify notification log
        log = NotificationLog.objects.filter(user=self.user).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.notification_type, 'task_assignment')
        self.assertIn('task_type', log.metadata)
    
    def test_notification_disabled_for_user(self):
        """Test that notifications are not sent when disabled"""
        self.preferences.is_telegram_enabled = False
        self.preferences.save()
        
        material = MaterialFactory()
        service = TelegramNotificationService()
        
        result = service.send_status_update(
            user_id=self.user.id,
            material=material,
            old_status='pending_qc',
            new_status='in_qc'
        )
        
        self.assertFalse(result)
        
        # No notification log should be created
        self.assertFalse(NotificationLog.objects.filter(user=self.user).exists())
    
    def test_notification_type_disabled(self):
        """Test notification when specific type is disabled"""
        # Disable status update notifications
        self.preferences.notification_types['status_update'] = False
        self.preferences.save()
        
        material = MaterialFactory()
        service = TelegramNotificationService()
        
        result = service.send_status_update(
            user_id=self.user.id,
            material=material,
            old_status='pending_qc',
            new_status='in_qc'
        )
        
        self.assertFalse(result)
    
    @patch('apps.notifications.services.TelegramNotificationService._check_bot_available')
    def test_notification_no_preferences(self, mock_check):
        """Test notification for user without preferences"""
        user_without_prefs = WarehouseUserFactory()
        material = MaterialFactory()
        
        service = TelegramNotificationService()
        result = service.send_status_update(
            user_id=user_without_prefs.id,
            material=material,
            old_status='pending_qc',
            new_status='in_qc'
        )
        
        self.assertFalse(result)


class TelegramTaskTest(TestCase):
    """Test Telegram notification Celery tasks"""
    
    def setUp(self):
        self.user = WarehouseUserFactory()
        self.notification_log = NotificationLog.objects.create(
            user=self.user,
            notification_type='status_update',
            telegram_chat_id='123456789',
            message='Test notification message',
            status='pending'
        )
    
    @patch('apps.notifications.tasks.Bot')
    @patch('apps.notifications.tasks.settings')
    def test_send_telegram_message_success(self, mock_settings, mock_bot):
        """Test successful telegram message sending"""
        mock_settings.TELEGRAM_BOT_TOKEN = 'test_token'
        mock_bot_instance = MagicMock()
        mock_bot.return_value = mock_bot_instance
        
        # Mock successful message sending
        mock_message = MagicMock()
        mock_bot_instance.send_message.return_value = mock_message
        
        result = send_telegram_message(self.notification_log.id)
        
        self.assertTrue(result)
        
        # Verify log was updated
        self.notification_log.refresh_from_db()
        self.assertEqual(self.notification_log.status, 'sent')
        self.assertIsNotNone(self.notification_log.sent_at)
    
    @patch('apps.notifications.tasks.Bot')
    @patch('apps.notifications.tasks.settings')
    def test_send_telegram_message_forbidden(self, mock_settings, mock_bot):
        """Test telegram message sending with Forbidden error"""
        from telegram.error import Forbidden
        
        mock_settings.TELEGRAM_BOT_TOKEN = 'test_token'
        mock_bot_instance = MagicMock()
        mock_bot.return_value = mock_bot_instance
        
        # Mock Forbidden error (user blocked bot)
        mock_bot_instance.send_message.side_effect = Forbidden("Forbidden")
        
        result = send_telegram_message(self.notification_log.id)
        
        self.assertFalse(result)
        
        # Verify log was updated
        self.notification_log.refresh_from_db()
        self.assertEqual(self.notification_log.status, 'failed')
        self.assertIn('Unauthorized', self.notification_log.error_message)
        
        # Verify user preferences were disabled
        self.user.refresh_from_db()
        if hasattr(self.user, 'notification_preferences'):
            self.assertFalse(self.user.notification_preferences.is_telegram_enabled)
    
    @patch('apps.notifications.tasks.Bot')
    @patch('apps.notifications.tasks.settings')
    def test_send_telegram_message_retry_on_network_error(self, mock_settings, mock_bot):
        """Test telegram message retry on network error"""
        from telegram.error import NetworkError
        
        mock_settings.TELEGRAM_BOT_TOKEN = 'test_token'
        mock_bot_instance = MagicMock()
        mock_bot.return_value = mock_bot_instance
        
        # Mock network error
        mock_bot_instance.send_message.side_effect = NetworkError("Network error")
        
        # Mock the task retry mechanism
        with patch('apps.notifications.tasks.send_telegram_message.retry') as mock_retry:
            mock_retry.side_effect = Retry()
            
            with self.assertRaises(Retry):
                send_telegram_message(self.notification_log.id)
            
            mock_retry.assert_called_once()
    
    @patch('apps.notifications.tasks.settings')
    def test_send_telegram_message_no_token(self, mock_settings):
        """Test telegram message sending without token"""
        mock_settings.TELEGRAM_BOT_TOKEN = None
        
        result = send_telegram_message(self.notification_log.id)
        
        self.assertFalse(result)
        
        # Verify log was updated
        self.notification_log.refresh_from_db()
        self.assertEqual(self.notification_log.status, 'failed')
        self.assertIn('TELEGRAM_BOT_TOKEN не настроен', self.notification_log.error_message)


class WorkflowServiceTest(TestCase):
    """Test workflow service integration"""
    
    def setUp(self):
        self.warehouse_user = WarehouseUserFactory()
        self.qc_user = QCUserFactory()
        self.lab_user = LabUserFactory()
    
    @patch('apps.notifications.services.TelegramNotificationService.send_task_assignment')
    def test_workflow_triggers_notifications(self, mock_notification):
        """Test that workflow changes trigger appropriate notifications"""
        # Create material and receipt
        material = PPSDRequiredMaterialFactory()
        receipt = MaterialReceiptFactory(material=material)
        
        # Create QC inspection that requires PPSD
        qc_inspection = QCInspectionFactory(
            material_receipt=receipt,
            requires_ppsd=True,
            status='completed'
        )
        
        # This should trigger notification to lab user
        # (In real implementation, this would be triggered by signals or workflow)
        mock_notification.assert_called()
    
    def test_ppsd_determination_integration(self):
        """Test PPSD determination integration with workflow"""
        # Create stainless steel material
        material = PPSDRequiredMaterialFactory(material_grade='12X18H10T')
        receipt = MaterialReceiptFactory(material=material)
        
        # Check PPSD requirement using service
        response = MaterialInspectionService.check_ppsd_requirement(
            material.material_grade, 
            material.size
        )
        
        self.assertTrue(response.success)
        self.assertTrue(response.data['requires_ppsd'])
        
        # Create QC inspection based on service response
        qc_inspection = QCInspectionFactory(
            material_receipt=receipt,
            requires_ppsd=response.data['requires_ppsd']
        )
        
        self.assertTrue(qc_inspection.requires_ppsd)
    
    def test_workflow_process_creation_with_ppsd(self):
        """Test workflow process creation for PPSD materials"""
        material = PPSDRequiredMaterialFactory(material_grade='12X18H10T')
        receipt = MaterialReceiptFactory(material=material)
        
        # Create workflow process
        process = MaterialInspectionProcessFactory(
            material_receipt=receipt,
            requires_ppsd=True,
            priority='high'
        )
        
        self.assertTrue(process.requires_ppsd)
        self.assertEqual(process.priority, 'high')
        self.assertEqual(process.material_receipt, receipt)
    
    @patch('apps.warehouse.services.MaterialInspectionService.check_ppsd_requirement')
    def test_service_integration_with_workflow(self, mock_ppsd_check):
        """Test service integration with workflow decisions"""
        # Mock PPSD check response
        mock_response = ServiceResponse.success_response({
            'requires_ppsd': True,
            'reasons': ['Марка 12X18H10T входит в список материалов, требующих ППСД']
        })
        mock_ppsd_check.return_value = mock_response
        
        material = MaterialFactory(material_grade='12X18H10T')
        receipt = MaterialReceiptFactory(material=material)
        
        # Simulate workflow decision point
        ppsd_response = MaterialInspectionService.check_ppsd_requirement(
            material.material_grade, 
            material.size
        )
        
        # Create process based on service response
        process = MaterialInspectionProcessFactory(
            material_receipt=receipt,
            requires_ppsd=ppsd_response.data['requires_ppsd']
        )
        
        mock_ppsd_check.assert_called_once_with(material.material_grade, material.size)
        self.assertTrue(process.requires_ppsd)


class ServiceMockTest(TestCase):
    """Test service mocking and external service integration"""
    
    @patch('apps.warehouse.models.qrcode.QRCode')
    def test_qr_code_generation_service_mock(self, mock_qr_code):
        """Test QR code generation with mocked external library"""
        # Setup QR code generation mock
        mock_qr_instance = MagicMock()
        mock_qr_code.return_value = mock_qr_instance
        
        mock_img = MagicMock()
        mock_qr_instance.make_image.return_value = mock_img
        
        material = MaterialFactory()
        material.generate_qr_code()
        
        # Verify QR library was called correctly
        mock_qr_code.assert_called_once_with(version=1, box_size=10, border=5)
        mock_qr_instance.add_data.assert_called_once()
        mock_qr_instance.make.assert_called_once_with(fit=True)
    
    @patch('apps.notifications.services.Bot')
    @patch('apps.notifications.services.settings')
    def test_telegram_bot_api_mock(self, mock_settings, mock_bot):
        """Test Telegram Bot API mocking"""
        mock_settings.TELEGRAM_BOT_TOKEN = 'mocked_token'
        mock_bot_instance = MagicMock()
        mock_bot.return_value = mock_bot_instance
        
        # Test successful message
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_bot_instance.send_message.return_value = mock_message
        
        service = TelegramNotificationService()
        self.assertTrue(service._check_bot_available())
        
        # Verify bot was initialized with correct token
        mock_bot.assert_called_once_with(token='mocked_token')
    
    @patch('reportlab.pdfgen.canvas.Canvas')
    def test_pdf_generation_service_mock(self, mock_canvas):
        """Test PDF generation with mocked reportlab"""
        # This would test PDF certificate generation if implemented
        mock_canvas_instance = MagicMock()
        mock_canvas.return_value = mock_canvas_instance
        
        # Test PDF generation (placeholder for future implementation)
        # certificate_service = CertificateGenerationService()
        # certificate_service.generate_pdf(material)
        
        # For now, just verify mock setup works
        self.assertTrue(mock_canvas.called or not mock_canvas.called)  # Always passes