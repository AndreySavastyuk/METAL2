"""
Test mixins and utilities for MetalQMS tests
"""
from unittest.mock import patch, MagicMock
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User, Group

from .factories import (
    UserFactory, WarehouseUserFactory, QCUserFactory, LabUserFactory
)


class MockExternalServicesMixin:
    """Mixin to mock external services"""
    
    def setUp(self):
        super().setUp()
        self.setup_mocks()
    
    def setup_mocks(self):
        """Setup all external service mocks"""
        self.qr_code_patcher = patch('apps.warehouse.models.qrcode.QRCode')
        self.telegram_bot_patcher = patch('apps.notifications.services.Bot')
        self.telegram_task_patcher = patch('apps.notifications.tasks.Bot')
        self.reportlab_patcher = patch('reportlab.pdfgen.canvas.Canvas')
        
        self.mock_qr_code = self.qr_code_patcher.start()
        self.mock_telegram_bot = self.telegram_bot_patcher.start()
        self.mock_telegram_task = self.telegram_task_patcher.start()
        self.mock_reportlab = self.reportlab_patcher.start()
        
        self.setup_qr_code_mock()
        self.setup_telegram_mock()
        self.setup_pdf_mock()
    
    def setup_qr_code_mock(self):
        """Setup QR code generation mock"""
        mock_qr_instance = MagicMock()
        self.mock_qr_code.return_value = mock_qr_instance
        
        mock_img = MagicMock()
        mock_qr_instance.make_image.return_value = mock_img
        
        # Mock QR code methods
        mock_qr_instance.add_data = MagicMock()
        mock_qr_instance.make = MagicMock()
    
    def setup_telegram_mock(self):
        """Setup Telegram bot mock"""
        mock_bot_instance = MagicMock()
        self.mock_telegram_bot.return_value = mock_bot_instance
        self.mock_telegram_task.return_value = mock_bot_instance
        
        # Mock successful message sending
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_bot_instance.send_message.return_value = mock_message
    
    def setup_pdf_mock(self):
        """Setup PDF generation mock"""
        mock_canvas_instance = MagicMock()
        self.mock_reportlab.return_value = mock_canvas_instance
    
    def tearDown(self):
        super().tearDown()
        self.qr_code_patcher.stop()
        self.telegram_bot_patcher.stop()
        self.telegram_task_patcher.stop()
        self.reportlab_patcher.stop()


class AuthenticatedAPITestMixin:
    """Mixin for API tests with authentication"""
    
    def setUp(self):
        super().setUp()
        self.setup_users()
        self.setup_tokens()
    
    def setup_users(self):
        """Create users with different roles"""
        self.warehouse_user = WarehouseUserFactory()
        self.qc_user = QCUserFactory()
        self.lab_user = LabUserFactory()
        self.regular_user = UserFactory()
        
        # Create admin user
        self.admin_user = UserFactory(
            is_staff=True,
            is_superuser=True,
            username='admin_test'
        )
    
    def setup_tokens(self):
        """Create authentication tokens"""
        self.warehouse_token = Token.objects.create(user=self.warehouse_user)
        self.qc_token = Token.objects.create(user=self.qc_user)
        self.lab_token = Token.objects.create(user=self.lab_user)
        self.regular_token = Token.objects.create(user=self.regular_user)
        self.admin_token = Token.objects.create(user=self.admin_user)
    
    def authenticate_as(self, user_type='warehouse'):
        """Authenticate client as specific user type"""
        token_map = {
            'warehouse': self.warehouse_token,
            'qc': self.qc_token,
            'lab': self.lab_token,
            'regular': self.regular_token,
            'admin': self.admin_token
        }
        
        token = token_map.get(user_type)
        if token:
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        else:
            self.client.credentials()  # Clear credentials
    
    def get_user_by_type(self, user_type):
        """Get user instance by type"""
        user_map = {
            'warehouse': self.warehouse_user,
            'qc': self.qc_user,
            'lab': self.lab_user,
            'regular': self.regular_user,
            'admin': self.admin_user
        }
        return user_map.get(user_type)


class WorkflowTestMixin:
    """Mixin for workflow-related tests"""
    
    def setup_workflow_mocks(self):
        """Setup workflow-specific mocks"""
        self.workflow_patcher = patch('apps.workflow.signals.auto_start_workflow_on_material_receipt')
        self.notification_patcher = patch('apps.notifications.services.TelegramNotificationService.send_task_assignment')
        
        self.mock_workflow = self.workflow_patcher.start()
        self.mock_notification = self.notification_patcher.start()
        
        # Configure workflow mock behavior
        self.mock_workflow.return_value = True
        self.mock_notification.return_value = True
    
    def teardown_workflow_mocks(self):
        """Cleanup workflow mocks"""
        if hasattr(self, 'workflow_patcher'):
            self.workflow_patcher.stop()
        if hasattr(self, 'notification_patcher'):
            self.notification_patcher.stop()
    
    def assert_workflow_started(self, material_receipt=None):
        """Assert that workflow was started"""
        self.mock_workflow.assert_called()
        if material_receipt:
            # Check if specific material receipt was used
            call_args = self.mock_workflow.call_args
            self.assertIn(material_receipt, str(call_args))
    
    def assert_notification_sent(self, user=None, notification_type=None):
        """Assert that notification was sent"""
        self.mock_notification.assert_called()
        if user or notification_type:
            call_args = self.mock_notification.call_args
            if user:
                self.assertIn(user.id, str(call_args))
            if notification_type:
                self.assertIn(notification_type, str(call_args))


class FileUploadTestMixin:
    """Mixin for file upload tests"""
    
    def create_test_file(self, filename='test.pdf', content=b'test content', content_type='application/pdf'):
        """Create test file for upload"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(filename, content, content_type=content_type)
    
    def create_test_pdf(self, filename='test.pdf'):
        """Create test PDF file"""
        # Simple PDF header
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
        return self.create_test_file(filename, pdf_content, 'application/pdf')
    
    def create_test_image(self, filename='test.jpg'):
        """Create test image file"""
        from PIL import Image
        from io import BytesIO
        
        # Create simple test image
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        
        return self.create_test_file(filename, buffer.read(), 'image/jpeg')


class DatabaseTestMixin:
    """Mixin for database-related test utilities"""
    
    def assert_object_created(self, model_class, **kwargs):
        """Assert that object was created with specific attributes"""
        obj = model_class.objects.filter(**kwargs).first()
        self.assertIsNotNone(obj, f"Object {model_class.__name__} with {kwargs} was not created")
        return obj
    
    def assert_object_not_exists(self, model_class, **kwargs):
        """Assert that object does not exist"""
        exists = model_class.objects.filter(**kwargs).exists()
        self.assertFalse(exists, f"Object {model_class.__name__} with {kwargs} should not exist")
    
    def assert_object_count(self, model_class, expected_count, **filter_kwargs):
        """Assert object count"""
        actual_count = model_class.objects.filter(**filter_kwargs).count()
        self.assertEqual(actual_count, expected_count, 
                        f"Expected {expected_count} {model_class.__name__} objects, got {actual_count}")
    
    def refresh_objects(self, *objects):
        """Refresh multiple objects from database"""
        for obj in objects:
            obj.refresh_from_db()


class PermissionTestMixin:
    """Mixin for permission testing utilities"""
    
    def assert_permission_required(self, url, method='get', user_type=None, expected_status=403):
        """Assert that specific permission is required for endpoint"""
        if user_type:
            self.authenticate_as(user_type)
        else:
            self.client.credentials()  # No authentication
        
        response = getattr(self.client, method.lower())(url)
        self.assertEqual(response.status_code, expected_status)
    
    def assert_permission_granted(self, url, method='get', user_type='admin'):
        """Assert that permission is granted for endpoint"""
        self.authenticate_as(user_type)
        response = getattr(self.client, method.lower())(url)
        self.assertNotEqual(response.status_code, 403)
    
    def test_endpoint_permissions(self, endpoint_configs):
        """Test multiple endpoint permissions
        
        Args:
            endpoint_configs: List of dicts with 'url', 'method', 'allowed_roles', 'denied_roles'
        """
        for config in endpoint_configs:
            url = config['url']
            method = config.get('method', 'get')
            allowed_roles = config.get('allowed_roles', [])
            denied_roles = config.get('denied_roles', [])
            
            # Test allowed roles
            for role in allowed_roles:
                with self.subTest(url=url, method=method, role=role, permission='allowed'):
                    self.assert_permission_granted(url, method, role)
            
            # Test denied roles
            for role in denied_roles:
                with self.subTest(url=url, method=method, role=role, permission='denied'):
                    self.assert_permission_required(url, method, role)


class ComprehensiveTestMixin(
    MockExternalServicesMixin,
    AuthenticatedAPITestMixin,
    WorkflowTestMixin,
    FileUploadTestMixin,
    DatabaseTestMixin,
    PermissionTestMixin
):
    """Combined mixin with all testing utilities"""
    
    def setUp(self):
        super().setUp()
        self.setup_workflow_mocks()
    
    def tearDown(self):
        super().tearDown()
        self.teardown_workflow_mocks()