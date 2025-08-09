"""
Pytest configuration and fixtures for MetalQMS tests
"""
import pytest
import os
import django
from unittest.mock import patch, MagicMock

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.test_settings')

try:
    django.setup()
except Exception:
    pass

from django.conf import settings
from django.test import override_settings
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from .factories import (
    UserFactory, WarehouseUserFactory, QCUserFactory, LabUserFactory,
    MaterialFactory, MaterialReceiptFactory, QCInspectionFactory,
    LabTestRequestFactory, NotificationPreferencesFactory
)


@pytest.fixture
def api_client():
    """Provide API client for tests"""
    return APIClient()


@pytest.fixture
def warehouse_user():
    """Create warehouse user with group"""
    return WarehouseUserFactory()


@pytest.fixture
def qc_user():
    """Create QC user with group"""
    return QCUserFactory()


@pytest.fixture
def lab_user():
    """Create lab user with group"""
    return LabUserFactory()


@pytest.fixture
def regular_user():
    """Create regular user without special groups"""
    return UserFactory()


@pytest.fixture
def authenticated_client(api_client, warehouse_user):
    """Provide authenticated API client"""
    token, created = Token.objects.get_or_create(user=warehouse_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return api_client


@pytest.fixture
def material():
    """Create test material"""
    return MaterialFactory()


@pytest.fixture
def ppsd_material():
    """Create material that requires PPSD"""
    return MaterialFactory(material_grade='12X18H10T')


@pytest.fixture
def material_receipt(material):
    """Create material receipt"""
    return MaterialReceiptFactory(material=material)


@pytest.fixture
def qc_inspection(material_receipt):
    """Create QC inspection"""
    return QCInspectionFactory(material_receipt=material_receipt)


@pytest.fixture
def lab_test(material_receipt):
    """Create laboratory test"""
    return LaboratoryTestFactory(material_receipt=material_receipt)


@pytest.fixture(autouse=True)
def mock_external_services():
    """Mock external services for all tests"""
    with patch('apps.warehouse.models.qrcode.QRCode') as mock_qr, \
         patch('apps.notifications.services.Bot') as mock_bot, \
         patch('apps.notifications.tasks.Bot') as mock_task_bot:
        
        # Setup QR code mock
        mock_qr_instance = MagicMock()
        mock_qr.return_value = mock_qr_instance
        mock_img = MagicMock()
        mock_qr_instance.make_image.return_value = mock_img
        
        # Setup Telegram bot mock
        mock_bot_instance = MagicMock()
        mock_bot.return_value = mock_bot_instance
        mock_task_bot.return_value = mock_bot_instance
        
        yield {
            'qr_code': mock_qr,
            'telegram_bot': mock_bot,
            'telegram_task_bot': mock_task_bot
        }


@pytest.fixture
def mock_telegram_settings():
    """Mock Telegram settings"""
    with override_settings(
        TELEGRAM_BOT_TOKEN='test_token_123',
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True
    ):
        yield


@pytest.fixture
def notification_user():
    """Create user with notification preferences"""
    user = UserFactory()
    NotificationPreferencesFactory(
        user=user,
        telegram_chat_id='123456789',
        is_telegram_enabled=True
    )
    return user


@pytest.fixture
def test_database():
    """Ensure tests use test database"""
    with override_settings(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        }
    ):
        yield


@pytest.fixture(scope='session')
def django_db_setup():
    """Setup test database"""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }


@pytest.fixture
def mock_file_upload():
    """Mock file upload for tests"""
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    def _create_test_file(filename='test.pdf', content=b'test content', content_type='application/pdf'):
        return SimpleUploadedFile(filename, content, content_type=content_type)
    
    return _create_test_file


@pytest.fixture
def sample_test_results():
    """Provide sample test results data"""
    return {
        'chemical_analysis': {
            'carbon': 0.25,
            'manganese': 1.2,
            'silicon': 0.8,
            'chromium': 18.0,
            'nickel': 10.0
        },
        'mechanical_properties': {
            'tensile_strength': 650,
            'yield_strength': 450,
            'elongation': 25,
            'hardness': 180
        },
        'ultrasonic': {
            'defects_found': False,
            'scan_coverage': 100,
            'equipment_calibration': '2024-01-01'
        }
    }


# Pytest markers
pytest_plugins = ['pytest_django']

# Custom markers
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API tests"
    )
    config.addinivalue_line(
        "markers", "workflow: marks tests as workflow tests"
    )


@pytest.fixture
def transactional_db(db):
    """Provide transactional database access"""
    pass  # This fixture allows tests to use database transactions