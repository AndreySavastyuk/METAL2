from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CertificateProcessingViewSet

app_name = 'certificates'

router = DefaultRouter()
router.register(r'processing', CertificateProcessingViewSet, basename='processing')

urlpatterns = [
    path('', include(router.urls)),
] 