from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'workflow'

router = DefaultRouter()
# TODO: Добавить ViewSets здесь
# router.register('processes', WorkflowProcessViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 