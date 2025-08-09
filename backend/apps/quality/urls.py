from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    QCInspectionViewSet, 
    QCChecklistViewSet, 
    QCInspectionResultViewSet
)

app_name = 'quality'

router = DefaultRouter()
router.register('inspections', QCInspectionViewSet, basename='qc-inspection')
router.register('checklists', QCChecklistViewSet, basename='qc-checklist')
router.register('inspection-results', QCInspectionResultViewSet, basename='qc-inspection-result')

urlpatterns = [
    path('', include(router.urls)),
] 