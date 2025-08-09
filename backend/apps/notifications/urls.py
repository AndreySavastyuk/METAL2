from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'notifications'

router = DefaultRouter()
# TODO: Добавить ViewSets здесь
# router.register('notifications', NotificationViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 