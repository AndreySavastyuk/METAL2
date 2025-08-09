"""
URL Configuration for MetalQMS project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from .views import home_view, health_check
from apps.common import monitoring_urls
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Home and Health Check
    path('', home_view, name='home'),
    path('health/', health_check, name='health'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # Auth (JWT)
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Monitoring
    path('metrics/', include((monitoring_urls.urlpatterns, 'monitoring'), namespace='monitoring')),

    # API Test Endpoints
    path('api/', include('apps.api.urls')),
    
    # API Endpoints (v1)
    path('api/v1/warehouse/', include('apps.warehouse.urls')),
    path('api/v1/quality/', include('apps.quality.urls')),
    path('api/v1/laboratory/', include('apps.laboratory.urls')),
    path('api/v1/production/', include('apps.production.urls')),
    path('api/v1/certificates/', include('apps.certificates.urls')),
    path('api/v1/workflow/', include('apps.workflow.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 