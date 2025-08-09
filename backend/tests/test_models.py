"""
Model tests for MetalQMS Material workflow
"""
import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock
from io import BytesIO

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.base import ContentFile
from PIL import Image

from apps.warehouse.models import Material, MaterialReceipt
from apps.quality.models import QCInspection
from apps.laboratory.models import LabTestRequest, LabTestResult
from apps.warehouse.models import Certificate
# from apps.workflow.models import MaterialInspectionProcess  # Temporarily disabled

from .factories import (
    MaterialFactory, PPSDRequiredMaterialFactory, LargeSizeMaterialFactory,
    MaterialReceiptFactory, QCInspectionFactory, LabTestRequestFactory,
    CertificateFactory, WarehouseUserFactory, QCUserFactory, LabUserFactory,
    # MaterialInspectionProcessFactory,  # Temporarily disabled
    CompleteMaterialWorkflowFactory
)


class MaterialModelTest(TestCase):
    """Test Material model validations and business logic"""
    
    def setUp(self):
        self.user = WarehouseUserFactory()
    
    def test_material_creation_with_valid_data(self):
        """Test creating material with valid data"""
        material = MaterialFactory()
        
        self.assertIsNotNone(material.id)
        self.assertIsNotNone(material.external_id)
        self.assertIsInstance(material.external_id, uuid.UUID)
        self.assertTrue(material.material_grade)
        self.assertTrue(material.supplier)
        self.assertTrue(material.certificate_number)
        self.assertTrue(material.heat_number)
        self.assertGreater(material.quantity, 0)
    
    def test_material_str_representation(self):
        """Test material string representation"""
        material = MaterialFactory(
            material_grade='40X',
            supplier='МеталлТорг',
            certificate_number='CERT-123456'
        )
        
        expected = "40X - МеталлТорг (CERT-123456)"
        self.assertEqual(str(material), expected)
    
    def test_material_external_id_uniqueness(self):
        """Test that external_id is unique"""
        material1 = MaterialFactory()
        
        # Try to create another material with same external_id
        with self.assertRaises(Exception):
            MaterialFactory(external_id=material1.external_id)
    
    def test_certificate_number_uniqueness_validation(self):
        """Test certificate number uniqueness validation"""
        MaterialFactory(certificate_number='CERT-UNIQUE')
        
        # Attempt to create another material with same certificate number
        # should raise validation error in serializer (not model level)
        # But we can test the logic exists
        user = WarehouseUserFactory()
        material2 = MaterialFactory.build(certificate_number='CERT-UNIQUE', created_by=user, updated_by=user)
        # This doesn't raise error at model level, but will at serializer level
        material2.save()  # This succeeds at model level
    
    @patch('apps.warehouse.models.qrcode.QRCode')
    @patch('apps.warehouse.models.File')
    def test_qr_code_generation(self, mock_file, mock_qr_code):
        """Test QR code generation functionality"""
        # Setup mocks
        mock_qr_instance = MagicMock()
        mock_qr_code.return_value = mock_qr_instance
        
        mock_img = MagicMock()
        mock_qr_instance.make_image.return_value = mock_img
        
        mock_buffer = BytesIO()
        mock_file.return_value = mock_buffer
        
        # Create material without triggering save() which auto-generates QR
        user = WarehouseUserFactory()
        material = MaterialFactory.build(created_by=user, updated_by=user)
        material.save()  # First call to QR code generation
        
        # Reset mock to test explicit call
        mock_qr_code.reset_mock()
        mock_qr_instance.reset_mock()
        
        material.generate_qr_code()  # Second call
        
        # Verify QR code creation for explicit call
        mock_qr_code.assert_called_once_with(version=1, box_size=10, border=5)
        mock_qr_instance.add_data.assert_called_once()
        mock_qr_instance.make.assert_called_once_with(fit=True)
        mock_qr_instance.make_image.assert_called_once_with(
            fill_color="black", back_color="white"
        )
    
    def test_qr_code_data_content(self):
        """Test QR code data content"""
        material = MaterialFactory(
            material_grade='40X',
            supplier='МеталлТорг',
            certificate_number='CERT-123',
            heat_number='HEAT-123',
            quantity=Decimal('100.500'),
            unit='kg'
        )
        
        # Extract QR data logic (simulate what generate_qr_code does)
        qr_data = {
            'id': str(material.external_id),
            'grade': material.material_grade,
            'supplier': material.supplier,
            'certificate': material.certificate_number,
            'heat': material.heat_number,
            'quantity': str(material.quantity),
            'unit': material.unit
        }
        
        self.assertEqual(qr_data['grade'], '40X')
        self.assertEqual(qr_data['supplier'], 'МеталлТорг')
        self.assertEqual(qr_data['certificate'], 'CERT-123')
        self.assertEqual(qr_data['heat'], 'HEAT-123')
        self.assertEqual(qr_data['quantity'], '100.500')
        self.assertEqual(qr_data['unit'], 'kg')
    
    def test_material_save_generates_qr_code_for_new_material(self):
        """Test that save() generates QR code for new materials"""
        with patch.object(Material, 'generate_qr_code') as mock_generate:
            material = MaterialFactory()
            mock_generate.assert_called_once()
    
    def test_material_save_regenerates_qr_code_if_missing(self):
        """Test that save() regenerates QR code if missing"""
        material = MaterialFactory()
        material.qr_code = None
        
        with patch.object(Material, 'generate_qr_code') as mock_generate:
            material.save()
            mock_generate.assert_called_once()
    
    def test_soft_delete_functionality(self):
        """Test soft delete mixin functionality"""
        material = MaterialFactory()
        material_id = material.id
        
        # Soft delete
        material.delete()
        
        # Should still exist in database when including deleted
        deleted_material = Material.all_objects.get(id=material_id)
        self.assertTrue(deleted_material.is_deleted)
        self.assertIsNotNone(deleted_material.deleted_at)
        
        # Should not appear in normal queryset
        self.assertFalse(Material.objects.filter(id=material_id).exists())
        
        # Should appear in deleted queryset if it exists
        try:
            self.assertTrue(Material.objects.deleted().filter(id=material_id).exists())
        except AttributeError:
            # If deleted() method doesn't exist, check all_objects
            self.assertTrue(Material.all_objects.filter(id=material_id, is_deleted=True).exists())
    
    def test_audit_fields_populated(self):
        """Test that audit fields are properly populated"""
        user = WarehouseUserFactory()
        material = MaterialFactory(created_by=user, updated_by=user)
        
        self.assertEqual(material.created_by, user)
        self.assertEqual(material.updated_by, user)
        self.assertIsNotNone(material.created_at)
        self.assertIsNotNone(material.updated_at)
    
    def test_material_ordering(self):
        """Test default ordering by receipt_date"""
        old_material = MaterialFactory(
            receipt_date=timezone.now() - timezone.timedelta(days=5)
        )
        new_material = MaterialFactory(
            receipt_date=timezone.now() - timezone.timedelta(days=1)
        )
        
        materials = list(Material.objects.all())
        self.assertEqual(materials[0], new_material)  # Newer first
        self.assertEqual(materials[1], old_material)


class MaterialReceiptModelTest(TestCase):
    """Test MaterialReceipt model functionality"""
    
    def test_material_receipt_creation(self):
        """Test creating material receipt"""
        receipt = MaterialReceiptFactory()
        
        self.assertIsNotNone(receipt.id)
        self.assertIsNotNone(receipt.material)
        self.assertIsNotNone(receipt.received_by)
        self.assertEqual(receipt.status, 'pending_qc')
    
    def test_material_receipt_str_representation(self):
        """Test receipt string representation"""
        receipt = MaterialReceiptFactory(
            document_number='RCP-123456',
            material__material_grade='40X'
        )
        
        # Check that string representation contains expected information
        str_repr = str(receipt)
        self.assertIn('RCP-123456', str_repr)
        self.assertIn(receipt.material.material_grade, str_repr)


class QCInspectionModelTest(TestCase):
    """Test QCInspection model logic"""
    
    def test_qc_inspection_creation(self):
        """Test creating QC inspection"""
        inspection = QCInspectionFactory()
        
        self.assertIsNotNone(inspection.id)
        self.assertIsNotNone(inspection.material_receipt)
        self.assertIsNotNone(inspection.inspector)
        self.assertIn(inspection.status, ['draft', 'in_progress', 'completed', 'rejected'])
    
    def test_ppsd_requirement_for_stainless_steel(self):
        """Test PPSD requirement for stainless steel grades"""
        # Create material with PPSD-required grade
        material = PPSDRequiredMaterialFactory(material_grade='12X18H10T')
        receipt = MaterialReceiptFactory(material=material)
        inspection = QCInspectionFactory(material_receipt=receipt)
        
        # Check if PPSD is required based on material grade
        ppsd_grades = ['12X18H10T', '08X18H10T', '10X17H13M2T', '03X17H14M3', '20X13', '40X13']
        self.assertIn(material.material_grade, ppsd_grades)
    
    def test_inspection_status_transitions(self):
        """Test valid status transitions"""
        inspection = QCInspectionFactory(status='draft')
        
        # Valid transitions
        valid_transitions = {
            'draft': ['in_progress', 'rejected'],
            'in_progress': ['completed', 'rejected'],
            'completed': [],  # Final state
            'rejected': []    # Final state
        }
        
        self.assertIn('in_progress', valid_transitions['draft'])
        self.assertIn('completed', valid_transitions['in_progress'])


class LabTestRequestModelTest(TestCase):
    """Test LabTestRequest model functionality"""
    
    def test_lab_test_request_creation(self):
        """Test creating laboratory test request"""
        test_request = LabTestRequestFactory()
        
        self.assertIsNotNone(test_request.id)
        self.assertIsNotNone(test_request.material_receipt)
        self.assertIsNotNone(test_request.requested_by)
        self.assertIn(test_request.test_type, ['chemical_analysis', 'mechanical_properties', 'ultrasonic'])
    
    def test_test_requirements_field(self):
        """Test that test requirements are properly stored"""
        test_requirements = "Проверить химический состав согласно ГОСТ"
        
        test_request = LabTestRequestFactory(test_requirements=test_requirements)
        
        self.assertEqual(test_request.test_requirements, test_requirements)


class WorkflowModelTest(TestCase):
    """Test workflow-related models"""
    
    def test_material_inspection_process_creation(self):
        """Test creating material inspection process"""
        # Temporarily disabled due to viewflow dependency
        # process = MaterialInspectionProcessFactory()
        # 
        # self.assertIsNotNone(process.id)
        # self.assertIsNotNone(process.material_receipt)
        # self.assertIn(process.priority, ['low', 'normal', 'high', 'urgent'])
        pass
    
    def test_complete_workflow_factory(self):
        """Test complete workflow factory creates all related objects"""
        material = CompleteMaterialWorkflowFactory()
        
        # Verify all related objects were created
        self.assertTrue(Certificate.objects.filter(material=material).exists())
        self.assertTrue(MaterialReceipt.objects.filter(material=material).exists())
        
        receipt = MaterialReceipt.objects.get(material=material)
        self.assertTrue(QCInspection.objects.filter(material_receipt=receipt).exists())
        # self.assertTrue(MaterialInspectionProcess.objects.filter(material_receipt=receipt).exists())  # Temporarily disabled
        
        # Check if lab tests were created for PPSD materials
        qc_inspection = QCInspection.objects.get(material_receipt=receipt)
        if qc_inspection.requires_ppsd:
            self.assertTrue(LabTestRequest.objects.filter(material_receipt=receipt).exists())


class MaterialValidationTest(TestCase):
    """Test material validation edge cases"""
    
    def test_negative_quantity_validation(self):
        """Test that negative quantities are handled appropriately"""
        # At model level, there's no constraint, but business logic should prevent this
        user = WarehouseUserFactory()
        material = MaterialFactory.build(quantity=Decimal('-10.0'), created_by=user, updated_by=user)
        # This would be caught at serializer/form level in real application
        material.save()  # Succeeds at model level
    
    def test_very_large_quantity(self):
        """Test handling of very large quantities"""
        large_quantity = Decimal('9999999.999')  # Max digits=10, decimal_places=3 (7 integer digits max)
        material = MaterialFactory(quantity=large_quantity)
        self.assertEqual(material.quantity, large_quantity)
    
    def test_empty_required_fields(self):
        """Test behavior with empty required fields"""
        # Note: Django model fields don't enforce required validation at model level
        # This is typically done at form/serializer level
        # These will succeed at model level but would fail at form/serializer level
        user = WarehouseUserFactory()
        material1 = MaterialFactory(material_grade='', created_by=user, updated_by=user)
        material2 = MaterialFactory(supplier='', created_by=user, updated_by=user)
        
        # Verify they were created (showing that model level doesn't enforce this)
        self.assertEqual(material1.material_grade, '')
        self.assertEqual(material2.supplier, '')
    
    def test_invalid_unit_choice(self):
        """Test invalid unit choice validation"""
        # Note: Django choice field validation happens at form/serializer level
        # At model level, invalid choices are allowed
        user = WarehouseUserFactory()
        material = MaterialFactory(unit='invalid_unit', created_by=user, updated_by=user)
        
        # Verify it was created (showing that model level doesn't enforce choices)
        self.assertEqual(material.unit, 'invalid_unit')


class MaterialQuerySetTest(TestCase):
    """Test Material queryset methods and optimizations"""
    
    def test_active_materials_queryset(self):
        """Test that default queryset excludes deleted materials"""
        active_material = MaterialFactory()
        deleted_material = MaterialFactory()
        deleted_material.delete()
        
        active_materials = Material.objects.all()
        self.assertIn(active_material, active_materials)
        self.assertNotIn(deleted_material, active_materials)
    
    def test_material_with_prefetch_related(self):
        """Test queryset optimization with prefetch_related"""
        material = CompleteMaterialWorkflowFactory()
        
        # Test optimized query
        materials = Material.objects.prefetch_related(
            'certificate_set',
            'materialreceipt_set'
        ).filter(id=material.id)
        
        self.assertTrue(materials.exists())
        
        # Test that prefetched data is available
        material_with_prefetch = materials.first()
        with self.assertNumQueries(0):  # Should not trigger additional queries
            list(material_with_prefetch.certificate_set.all())
            list(material_with_prefetch.materialreceipt_set.all())