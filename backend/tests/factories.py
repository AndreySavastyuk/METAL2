"""
Factory Boy factories for generating test data
"""
import factory
import uuid
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import timedelta
import random

from apps.warehouse.models import Material, MaterialReceipt
from apps.quality.models import QCInspection
from apps.laboratory.models import LabTestRequest, LabTestResult
from apps.warehouse.models import Certificate
from apps.notifications.models import UserNotificationPreferences
# from apps.workflow.models import MaterialInspectionProcess  # Temporarily disabled due to viewflow dependency


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for Django User model"""
    
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@metalqms.test")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    is_staff = False
    date_joined = factory.LazyFunction(timezone.now)


class WarehouseUserFactory(UserFactory):
    """Factory for warehouse users"""
    
    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        
        warehouse_group, created = Group.objects.get_or_create(name='warehouse')
        self.groups.add(warehouse_group)


class QCUserFactory(UserFactory):
    """Factory for QC users"""
    
    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        
        qc_group, created = Group.objects.get_or_create(name='qc')
        self.groups.add(qc_group)


class LabUserFactory(UserFactory):
    """Factory for lab users"""
    
    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        
        lab_group, created = Group.objects.get_or_create(name='lab')
        self.groups.add(lab_group)


class MaterialFactory(factory.django.DjangoModelFactory):
    """Factory for Material model"""
    
    class Meta:
        model = Material
    
    material_grade = factory.Iterator([
        '40X', '20X13', '12X18H10T', '09Г2С', '08X18H10T', 
        '10X17H13M2T', '03X17H14M3', '40X13'
    ])
    supplier = factory.Iterator([
        'МеталлТорг', 'СпецСталь', 'УралМет', 'СибирьМеталл', 'РосМеталл'
    ])
    order_number = factory.Sequence(lambda n: f"ORD-{n:06d}")
    certificate_number = factory.Sequence(lambda n: f"CERT-{n:06d}")
    heat_number = factory.Sequence(lambda n: f"HEAT-{n:06d}")
    size = factory.Iterator([
        '⌀50', '⌀100', '⌀150', '⌀200', 'Лист 10мм', 'Лист 20мм', 'Лист 50мм'
    ])
    quantity = factory.LazyFunction(lambda: Decimal(str(random.uniform(10.0, 1000.0))))
    unit = factory.Iterator(['kg', 'pcs', 'meters'])
    receipt_date = factory.LazyFunction(
        lambda: timezone.now() - timedelta(days=random.randint(0, 365))
    )
    location = factory.Iterator([
        'Секция А-1', 'Секция А-2', 'Секция Б-1', 'Секция Б-2', 'Склад №3'
    ])
    external_id = factory.LazyFunction(uuid.uuid4)
    created_by = factory.SubFactory(WarehouseUserFactory)
    updated_by = factory.SelfAttribute('created_by')


class PPSDRequiredMaterialFactory(MaterialFactory):
    """Factory for materials that require PPSD testing"""
    
    material_grade = factory.Iterator([
        '12X18H10T', '08X18H10T', '10X17H13M2T', '03X17H14M3', '20X13', '40X13'
    ])


class LargeSizeMaterialFactory(MaterialFactory):
    """Factory for large size materials that may require additional testing"""
    
    size = factory.Iterator(['⌀250', '⌀300', 'Лист 80мм', 'Лист 100мм'])


class CertificateFactory(factory.django.DjangoModelFactory):
    """Factory for Certificate model"""
    
    class Meta:
        model = Certificate
    
    material = factory.SubFactory(MaterialFactory)
    pdf_file = factory.django.FileField(filename='certificate.pdf')
    uploaded_at = factory.LazyFunction(timezone.now)
    parsed_data = factory.LazyFunction(lambda: {})
    file_size = factory.LazyFunction(lambda: random.randint(1024, 10*1024*1024))
    file_hash = factory.Sequence(lambda n: f"hash{n:032x}")
    created_by = factory.SubFactory(WarehouseUserFactory)
    updated_by = factory.SelfAttribute('created_by')


# DocumentFactory removed - Document model doesn't exist in the project


class MaterialReceiptFactory(factory.django.DjangoModelFactory):
    """Factory for MaterialReceipt model"""
    
    class Meta:
        model = MaterialReceipt
    
    material = factory.SubFactory(MaterialFactory)
    document_number = factory.Sequence(lambda n: f"RCP-{n:06d}")
    receipt_date = factory.LazyFunction(timezone.now)
    received_by = factory.SubFactory(WarehouseUserFactory)
    notes = factory.Faker('text', max_nb_chars=200)
    status = 'pending_qc'
    created_by = factory.SelfAttribute('received_by')
    updated_by = factory.SelfAttribute('received_by')


class QCInspectionFactory(factory.django.DjangoModelFactory):
    """Factory for QCInspection model"""
    
    class Meta:
        model = QCInspection
    
    material_receipt = factory.SubFactory(MaterialReceiptFactory)
    inspector = factory.SubFactory(QCUserFactory)
    inspection_date = factory.LazyFunction(timezone.now)
    status = factory.Iterator(['draft', 'in_progress', 'completed', 'rejected'])
    requires_ppsd = factory.LazyAttribute(
        lambda obj: obj.material_receipt.material.material_grade in [
            '12X18H10T', '08X18H10T', '10X17H13M2T', '03X17H14M3', '20X13', '40X13'
        ]
    )
    requires_ultrasonic = factory.Iterator([True, False])
    comments = factory.Faker('text', max_nb_chars=500)
    created_by = factory.SelfAttribute('inspector')
    updated_by = factory.SelfAttribute('inspector')


class LabTestRequestFactory(factory.django.DjangoModelFactory):
    """Factory for LabTestRequest model"""
    
    class Meta:
        model = LabTestRequest
    
    material_receipt = factory.SubFactory(MaterialReceiptFactory)
    test_type = factory.Iterator(['chemical_analysis', 'mechanical_properties', 'ultrasonic'])
    requested_by = factory.SubFactory(LabUserFactory)
    assigned_to = factory.SubFactory(LabUserFactory)
    priority = factory.Iterator(['low', 'normal', 'high', 'urgent'])
    status = factory.Iterator(['pending', 'assigned', 'in_progress', 'completed'])
    test_requirements = factory.Faker('text', max_nb_chars=200)
    estimated_duration_hours = factory.LazyFunction(lambda: random.randint(2, 24))
    created_by = factory.SelfAttribute('requested_by')


class LabTestResultFactory(factory.django.DjangoModelFactory):
    """Factory for LabTestResult model"""
    
    class Meta:
        model = LabTestResult
    
    test_request = factory.SubFactory(LabTestRequestFactory)
    performed_by = factory.SubFactory(LabUserFactory)
    test_date = factory.LazyFunction(timezone.now)
    results = factory.LazyFunction(
        lambda: {
            'carbon': round(random.uniform(0.1, 0.5), 3),
            'manganese': round(random.uniform(0.5, 2.0), 3),
            'silicon': round(random.uniform(0.1, 1.0), 3),
            'tensile_strength': random.randint(400, 800),
            'yield_strength': random.randint(200, 600)
        }
    )
    conclusion = factory.Iterator(['passed', 'failed', 'conditional', 'retest_required'])
    certificate_number = factory.Sequence(lambda n: f"PROT-{n:06d}")
    sample_description = factory.Faker('text', max_nb_chars=200)
    test_method = factory.Iterator(['ГОСТ 7565-81', 'ГОСТ 1497-84', 'ГОСТ 14782-86'])
    created_by = factory.SelfAttribute('performed_by')


class NotificationPreferencesFactory(factory.django.DjangoModelFactory):
    """Factory for UserNotificationPreferences"""
    
    class Meta:
        model = UserNotificationPreferences
    
    user = factory.SubFactory(UserFactory)
    telegram_chat_id = factory.Sequence(lambda n: str(100000 + n))
    is_telegram_enabled = True
    notification_types = factory.LazyFunction(
        lambda: {
            'status_update': True,
            'task_assignment': True,
            'daily_summary': False,
            'urgent_alert': True,
            'sla_warning': True,
            'quality_alert': True,
            'workflow_complete': False
        }
    )


# class MaterialInspectionProcessFactory(factory.django.DjangoModelFactory):
#     """Factory for MaterialInspectionProcess workflow"""
#     
#     class Meta:
#         model = MaterialInspectionProcess
#     
#     material_receipt = factory.SubFactory(MaterialReceiptFactory)
#     priority = factory.Iterator(['low', 'normal', 'high', 'urgent'])
#     requires_ppsd = factory.LazyAttribute(
#         lambda obj: obj.material_receipt.material.material_grade in [
#             '12X18H10T', '08X18H10T', '10X17H13M2T', '03X17H14M3', '20X13', '40X13'
#         ]
#     )
#     requires_ultrasonic = factory.LazyFunction(lambda: random.choice([True, False]))
#     created_by = factory.SubFactory(UserFactory)


# Trait factories for specific scenarios
class UrgentMaterialFactory(MaterialFactory):
    """Factory for urgent materials"""
    
    @factory.post_generation
    def create_urgent_process(self, create, extracted, **kwargs):
        if not create:
            return
            
        receipt = MaterialReceiptFactory(material=self)
        MaterialInspectionProcessFactory(
            material_receipt=receipt,
            priority='urgent',
            requires_ppsd=True
        )


class CompleteMaterialWorkflowFactory(MaterialFactory):
    """Factory that creates a complete workflow for a material"""
    
    @factory.post_generation
    def create_complete_workflow(self, create, extracted, **kwargs):
        if not create:
            return
        
        # Create certificate (without PDF processing to avoid Celery issues)
        with patch('apps.certificates.tasks.process_uploaded_certificate'):
            CertificateFactory(material=self)
        
        # Create receipt
        receipt = MaterialReceiptFactory(material=self, status='pending_qc')
        
        # Create QC inspection
        qc_inspection = QCInspectionFactory(
            material_receipt=receipt,
            status='completed'
        )
        
        # Create lab tests if PPSD required
        if qc_inspection.requires_ppsd:
            chem_request = LabTestRequestFactory(
                material_receipt=receipt,
                test_type='chemical_analysis',
                status='completed'
            )
            LabTestResultFactory(
                test_request=chem_request,
                conclusion='passed'
            )
            
            mech_request = LabTestRequestFactory(
                material_receipt=receipt,
                test_type='mechanical_properties',
                status='completed'
            )
            LabTestResultFactory(
                test_request=mech_request,
                conclusion='passed'
            )
        
        # Create workflow process
        # MaterialInspectionProcessFactory(
        #     material_receipt=receipt,
        #     requires_ppsd=qc_inspection.requires_ppsd
        # )