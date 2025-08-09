from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'production'

router = DefaultRouter()
# TODO: Добавить ViewSets здесь
# router.register('orders', ProductionOrderViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 