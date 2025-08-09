"""
API tests for MetalQMS Material workflow
"""
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock
from io import BytesIO

from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from apps.warehouse.models import Material, MaterialReceipt
from apps.quality.models import QCInspection
from apps.laboratory.models import LabTestRequest, LabTestResult
from apps.warehouse.models import Certificate

from .factories import (
    MaterialFactory, PPSDRequiredMaterialFactory, MaterialReceiptFactory,
    QCInspectionFactory, LabTestRequestFactory, LabTestResultFactory, CertificateFactory,
    WarehouseUserFactory, QCUserFactory, LabUserFactory, UserFactory,
    CompleteMaterialWorkflowFactory
)


class BaseAPITest(TestCase):
    """Base class for API tests with common setup"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create users with different roles
        self.warehouse_user = WarehouseUserFactory()
        self.qc_user = QCUserFactory() 
        self.lab_user = LabUserFactory()
        self.regular_user = UserFactory()
        
        # Create tokens for authentication
        self.warehouse_token = Token.objects.create(user=self.warehouse_user)
        self.qc_token = Token.objects.create(user=self.qc_user)
        self.lab_token = Token.objects.create(user=self.lab_user)
        self.regular_token = Token.objects.create(user=self.regular_user)
    
    def authenticate_as(self, user_type='warehouse'):
        """Helper to authenticate as different user types"""
        token_map = {
            'warehouse': self.warehouse_token,
            'qc': self.qc_token,
            'lab': self.lab_token,
            'regular': self.regular_token
        }
        
        token = token_map.get(user_type)
        if token:
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        else:
            self.client.credentials()  # Clear credentials
    
    def create_test_file(self, filename='test.pdf', content=b'test content'):
        """Helper to create test file for upload"""
        return SimpleUploadedFile(
            filename,
            content,
            content_type='application/pdf'
        )


class MaterialAPITest(BaseAPITest):
    """Test Material API endpoints"""
    
    def test_list_materials_authenticated(self):
        """Test listing materials as authenticated user"""
        MaterialFactory.create_batch(3)
        self.authenticate_as('regular')
        
        url = reverse('warehouse:material-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)
    
    def test_list_materials_unauthenticated(self):
        """Test listing materials without authentication"""
        MaterialFactory.create_batch(3)
        
        url = reverse('warehouse:material-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_material_as_warehouse_user(self):
        """Test creating material with warehouse user permissions"""
        self.authenticate_as('warehouse')
        
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
        
        url = reverse('warehouse:material-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify material was created
        material = Material.objects.get(id=response.data['id'])
        self.assertEqual(material.material_grade, '40X')
        self.assertEqual(material.supplier, 'МеталлТорг')
        self.assertEqual(material.created_by, self.warehouse_user)
    
    def test_create_material_as_non_warehouse_user(self):
        """Test creating material without warehouse permissions"""
        self.authenticate_as('regular')
        
        data = {
            'material_grade': '40X',
            'supplier': 'МеталлТорг',
            'order_number': 'ORD-123456',
            'certificate_number': 'CERT-123456',
            'heat_number': 'HEAT-123456',
            'size': '⌀100',
            'quantity': '250.500',
            'unit': 'kg'
        }
        
        url = reverse('warehouse:material-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_create_material_with_invalid_data(self):
        """Test creating material with invalid data"""
        self.authenticate_as('warehouse')
        
        data = {
            'material_grade': '',  # Required field empty
            'supplier': 'МеталлТорг',
            'quantity': '-10.0',  # Negative quantity
            'unit': 'invalid_unit'  # Invalid unit choice
        }
        
        url = reverse('warehouse:material-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('material_grade', response.data)
    
    def test_update_material_as_warehouse_user(self):
        """Test updating material with warehouse permissions"""
        material = MaterialFactory(created_by=self.warehouse_user)
        self.authenticate_as('warehouse')
        
        data = {
            'material_grade': material.material_grade,
            'supplier': 'Updated Supplier',
            'order_number': material.order_number,
            'certificate_number': material.certificate_number,
            'heat_number': material.heat_number,
            'size': material.size,
            'quantity': str(material.quantity),
            'unit': material.unit
        }
        
        url = reverse('warehouse:material-detail', kwargs={'pk': material.id})
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        material.refresh_from_db()
        self.assertEqual(material.supplier, 'Updated Supplier')
        self.assertEqual(material.updated_by, self.warehouse_user)
    
    def test_delete_material_as_warehouse_user(self):
        """Test soft deleting material"""
        material = MaterialFactory(created_by=self.warehouse_user)
        self.authenticate_as('warehouse')
        
        url = reverse('warehouse:material-detail', kwargs={'pk': material.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify soft delete
        material.refresh_from_db()
        self.assertTrue(material.is_deleted)
        
        # Verify not in normal queryset
        self.assertFalse(Material.objects.filter(id=material.id).exists())
    
    def test_retrieve_material_detail(self):
        """Test retrieving material detail with related data"""
        material = CompleteMaterialWorkflowFactory()
        self.authenticate_as('regular')
        
        url = reverse('warehouse:material-detail', kwargs={'pk': material.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], material.id)
        self.assertIn('qr_code_url', response.data)
        self.assertIn('certificate', response.data)
    
    def test_material_qr_code_endpoint(self):
        """Test QR code generation endpoint"""
        material = MaterialFactory()
        self.authenticate_as('warehouse')
        
        url = reverse('warehouse:material-qr-code', kwargs={'pk': material.id})
        
        with patch('apps.warehouse.models.Material.generate_qr_code') as mock_generate:
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_generate.assert_called_once()
    
    def test_material_filtering_by_grade(self):
        """Test filtering materials by grade"""
        MaterialFactory(material_grade='40X')
        MaterialFactory(material_grade='20X13')
        MaterialFactory(material_grade='40X')
        
        self.authenticate_as('regular')
        
        url = reverse('warehouse:material-list')
        response = self.client.get(url, {'material_grade': '40X'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        for material in response.data['results']:
            self.assertEqual(material['material_grade'], '40X')
    
    def test_material_search(self):
        """Test searching materials"""
        MaterialFactory(
            material_grade='40X',
            supplier='МеталлТорг',
            certificate_number='CERT-SEARCH-001'
        )
        MaterialFactory(
            material_grade='20X13',
            supplier='СпецСталь',
            certificate_number='CERT-OTHER-002'
        )
        
        self.authenticate_as('regular')
        
        url = reverse('warehouse:material-list')
        response = self.client.get(url, {'search': 'МеталлТорг'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['supplier'], 'МеталлТорг')
    
    def test_material_ordering(self):
        """Test material ordering"""
        old_material = MaterialFactory(material_grade='AAA')
        new_material = MaterialFactory(material_grade='ZZZ')
        
        self.authenticate_as('regular')
        
        # Test ascending order
        url = reverse('warehouse:material-list')
        response = self.client.get(url, {'ordering': 'material_grade'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(results[0]['id'], old_material.id)
        self.assertEqual(results[1]['id'], new_material.id)
    
    def test_material_pagination(self):
        """Test material list pagination"""
        MaterialFactory.create_batch(25)
        self.authenticate_as('regular')
        
        url = reverse('warehouse:material-list')
        response = self.client.get(url, {'page_size': 10})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIn('next', response.data)
        self.assertIsNotNone(response.data['next'])


class MaterialReceiptAPITest(BaseAPITest):
    """Test MaterialReceipt API endpoints"""
    
    def test_create_material_receipt(self):
        """Test creating material receipt"""
        material = MaterialFactory()
        self.authenticate_as('warehouse')
        
        data = {
            'material': material.id,
            'document_number': 'RCP-123456',
            'supplier_delivery_note': 'DEL-123456',
            'notes': 'Test receipt notes'
        }
        
        url = reverse('warehouse:materialreceipt-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        receipt = MaterialReceipt.objects.get(id=response.data['id'])
        self.assertEqual(receipt.material, material)
        self.assertEqual(receipt.received_by, self.warehouse_user)
    
    def test_update_receipt_status_as_qc_user(self):
        """Test updating receipt status with QC permissions"""
        receipt = MaterialReceiptFactory()
        self.authenticate_as('qc')
        
        data = {
            'status': 'in_qc',
            'material': receipt.material.id,
            'document_number': receipt.document_number
        }
        
        url = reverse('warehouse:materialreceipt-detail', kwargs={'pk': receipt.id})
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, 'in_qc')


class QCInspectionAPITest(BaseAPITest):
    """Test QC Inspection API endpoints"""
    
    def test_create_qc_inspection(self):
        """Test creating QC inspection"""
        receipt = MaterialReceiptFactory()
        self.authenticate_as('qc')
        
        data = {
            'material_receipt': receipt.id,
            'visual_inspection_passed': True,
            'dimensional_check_passed': True,
            'marking_check_passed': True,
            'documentation_check_passed': True,
            'requires_ppsd': False,
            'comments': 'Test inspection comments'
        }
        
        url = reverse('quality:qcinspection-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        inspection = QCInspection.objects.get(id=response.data['id'])
        self.assertEqual(inspection.inspector, self.qc_user)
        self.assertTrue(inspection.visual_inspection_passed)
    
    def test_qc_inspection_permission_denied(self):
        """Test QC inspection creation denied for non-QC users"""
        receipt = MaterialReceiptFactory()
        self.authenticate_as('warehouse')
        
        data = {
            'material_receipt': receipt.id,
            'visual_inspection_passed': True
        }
        
        url = reverse('quality:qcinspection-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class LaboratoryTestAPITest(BaseAPITest):
    """Test Laboratory Test API endpoints"""
    
    def test_create_laboratory_test_request(self):
        """Test creating laboratory test request"""
        receipt = MaterialReceiptFactory()
        self.authenticate_as('lab')
        
        data = {
            'material_receipt': receipt.id,
            'test_type': 'chemical_analysis',
            'test_requirements': 'Определить химический состав',
            'priority': 'normal'
        }
        
        url = reverse('laboratory:labtestrequest-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        test_request = LabTestRequest.objects.get(id=response.data['id'])
        self.assertEqual(test_request.requested_by, self.lab_user)
        self.assertEqual(test_request.test_type, 'chemical_analysis')
    
    def test_laboratory_test_permission_denied(self):
        """Test laboratory test creation denied for non-lab users"""
        receipt = MaterialReceiptFactory()
        self.authenticate_as('warehouse')
        
        data = {
            'material_receipt': receipt.id,
            'test_type': 'chemical_analysis'
        }
        
        url = reverse('laboratory:labtestrequest-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CertificateAPITest(BaseAPITest):
    """Test Certificate API endpoints"""
    
    def test_upload_certificate_file(self):
        """Test uploading certificate file"""
        material = MaterialFactory()
        self.authenticate_as('warehouse')
        
        # Create test PDF file
        test_file = self.create_test_file('certificate.pdf', b'PDF content')
        
        data = {
            'material': material.id,
            'certificate_number': material.certificate_number,
            'issued_date': '2024-01-01',
            'expiry_date': '2025-01-01',
            'issuer': 'Test Certificate Authority',
            'file': test_file
        }
        
        url = reverse('warehouse:certificate-list')
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        certificate = Certificate.objects.get(id=response.data['id'])
        self.assertEqual(certificate.material, material)
        self.assertTrue(certificate.is_valid)


class APIPermissionTest(BaseAPITest):
    """Test API permission classes"""
    
    def test_warehouse_specific_endpoints(self):
        """Test endpoints that require warehouse permissions"""
        material = MaterialFactory()
        
        warehouse_endpoints = [
            ('post', reverse('warehouse:material-list'), {}),
            ('put', reverse('warehouse:material-detail', kwargs={'pk': material.id}), {}),
            ('delete', reverse('warehouse:material-detail', kwargs={'pk': material.id}), {}),
        ]
        
        for method, url, data in warehouse_endpoints:
            with self.subTest(method=method, url=url):
                # Test with non-warehouse user
                self.authenticate_as('regular')
                response = getattr(self.client, method)(url, data, format='json')
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                
                # Test with warehouse user
                self.authenticate_as('warehouse')
                response = getattr(self.client, method)(url, data, format='json')
                self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_read_only_endpoints_for_all_authenticated(self):
        """Test that read-only endpoints are accessible to all authenticated users"""
        material = MaterialFactory()
        
        read_endpoints = [
            reverse('warehouse:material-list'),
            reverse('warehouse:material-detail', kwargs={'pk': material.id}),
        ]
        
        for url in read_endpoints:
            with self.subTest(url=url):
                # Test with different user types
                for user_type in ['warehouse', 'qc', 'lab', 'regular']:
                    self.authenticate_as(user_type)
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, status.HTTP_200_OK)


class APIValidationTest(BaseAPITest):
    """Test API validation and error handling"""
    
    def test_unique_certificate_number_validation(self):
        """Test that duplicate certificate numbers are rejected"""
        existing_material = MaterialFactory(certificate_number='CERT-UNIQUE')
        self.authenticate_as('warehouse')
        
        data = {
            'material_grade': '40X',
            'supplier': 'МеталлТорг',
            'order_number': 'ORD-NEW',
            'certificate_number': 'CERT-UNIQUE',  # Duplicate
            'heat_number': 'HEAT-NEW',
            'size': '⌀100',
            'quantity': '100.0',
            'unit': 'kg'
        }
        
        url = reverse('warehouse:material-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('certificate_number', response.data)
    
    def test_invalid_quantity_format(self):
        """Test validation of invalid quantity formats"""
        self.authenticate_as('warehouse')
        
        data = {
            'material_grade': '40X',
            'supplier': 'МеталлТорг',
            'order_number': 'ORD-123',
            'certificate_number': 'CERT-123',
            'heat_number': 'HEAT-123',
            'size': '⌀100',
            'quantity': 'invalid_number',
            'unit': 'kg'
        }
        
        url = reverse('warehouse:material-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('quantity', response.data)
    
    def test_missing_required_fields(self):
        """Test validation of missing required fields"""
        self.authenticate_as('warehouse')
        
        data = {
            'material_grade': '',  # Required but empty
            'supplier': 'МеталлТорг'
            # Missing other required fields
        }
        
        url = reverse('warehouse:material-list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Check that all required fields are mentioned in errors
        required_fields = ['material_grade', 'order_number', 'certificate_number', 'heat_number', 'size', 'quantity', 'unit']
        for field in required_fields:
            self.assertIn(field, response.data)


class APIIntegrationTest(BaseAPITest):
    """Integration tests for API workflows"""
    
    def test_complete_material_workflow_via_api(self):
        """Test complete workflow from material creation to approval via API"""
        self.authenticate_as('warehouse')
        
        # 1. Create material
        material_data = {
            'material_grade': '12X18H10T',  # PPSD required grade
            'supplier': 'МеталлТорг',
            'order_number': 'ORD-WORKFLOW',
            'certificate_number': 'CERT-WORKFLOW',
            'heat_number': 'HEAT-WORKFLOW',
            'size': '⌀150',
            'quantity': '500.0',
            'unit': 'kg'
        }
        
        material_url = reverse('warehouse:material-list')
        material_response = self.client.post(material_url, material_data, format='json')
        self.assertEqual(material_response.status_code, status.HTTP_201_CREATED)
        material_id = material_response.data['id']
        
        # 2. Create material receipt
        receipt_data = {
            'material': material_id,
            'document_number': 'RCP-WORKFLOW',
            'supplier_delivery_note': 'DEL-WORKFLOW'
        }
        
        receipt_url = reverse('warehouse:materialreceipt-list')
        receipt_response = self.client.post(receipt_url, receipt_data, format='json')
        self.assertEqual(receipt_response.status_code, status.HTTP_201_CREATED)
        receipt_id = receipt_response.data['id']
        
        # 3. Create QC inspection
        self.authenticate_as('qc')
        inspection_data = {
            'material_receipt': receipt_id,
            'visual_inspection_passed': True,
            'dimensional_check_passed': True,
            'marking_check_passed': True,
            'documentation_check_passed': True,
            'requires_ppsd': True,  # Based on material grade
            'comments': 'All checks passed, PPSD required'
        }
        
        inspection_url = reverse('quality:qcinspection-list')
        inspection_response = self.client.post(inspection_url, inspection_data, format='json')
        self.assertEqual(inspection_response.status_code, status.HTTP_201_CREATED)
        
        # 4. Create laboratory test requests for PPSD
        self.authenticate_as('lab')
        
        # Chemical analysis test request
        chem_request_data = {
            'material_receipt': receipt_id,
            'test_type': 'chemical_analysis',
            'test_requirements': 'Определить химический состав согласно ГОСТ',
            'priority': 'high'
        }
        
        request_url = reverse('laboratory:labtestrequest-list')
        chem_response = self.client.post(request_url, chem_request_data, format='json')
        self.assertEqual(chem_response.status_code, status.HTTP_201_CREATED)
        
        # Create test result for chemical analysis
        chem_result_data = {
            'test_request': chem_response.data['id'],
            'results': {
                'carbon': 0.12,
                'chromium': 18.0,
                'nickel': 10.0,
                'manganese': 2.0
            },
            'conclusion': 'passed',
            'certificate_number': 'PROT-CHEM-001',
            'sample_description': 'Образец материала для химанализа',
            'test_method': 'ГОСТ 7565-81'
        }
        
        result_url = reverse('laboratory:labtestresult-list')
        chem_result_response = self.client.post(result_url, chem_result_data, format='json')
        self.assertEqual(chem_result_response.status_code, status.HTTP_201_CREATED)
        
        # Mechanical properties test request
        mech_request_data = {
            'material_receipt': receipt_id,
            'test_type': 'mechanical_properties',
            'test_requirements': 'Определить механические свойства',
            'priority': 'high'
        }
        
        mech_response = self.client.post(request_url, mech_request_data, format='json')
        self.assertEqual(mech_response.status_code, status.HTTP_201_CREATED)
        
        # 5. Verify workflow completion
        self.authenticate_as('regular')
        
        # Check that all related objects were created
        material_detail_url = reverse('warehouse:material-detail', kwargs={'pk': material_id})
        detail_response = self.client.get(material_detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        
        # Verify material exists and has expected data
        material = Material.objects.get(id=material_id)
        self.assertEqual(material.material_grade, '12X18H10T')
        
        # Verify related objects exist
        self.assertTrue(MaterialReceipt.objects.filter(material=material).exists())
        receipt = MaterialReceipt.objects.get(material=material)
        self.assertTrue(QCInspection.objects.filter(material_receipt=receipt).exists())
        self.assertEqual(LabTestRequest.objects.filter(material_receipt=receipt).count(), 2)