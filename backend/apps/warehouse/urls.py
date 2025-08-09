from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MaterialViewSet, 
    MaterialReceiptViewSet, 
    CertificateViewSet,
    WarehouseReportsViewSet
)

app_name = 'warehouse'

router = DefaultRouter()
router.register('materials', MaterialViewSet, basename='material')
router.register('receipts', MaterialReceiptViewSet, basename='materialreceipt')
router.register('certificates', CertificateViewSet, basename='certificate')
router.register('reports', WarehouseReportsViewSet, basename='warehouse-reports')

urlpatterns = [
    path('', include(router.urls)),
] 