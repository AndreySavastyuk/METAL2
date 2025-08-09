from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'laboratory'

router = DefaultRouter()
# TODO: Добавить ViewSets здесь
# router.register('tests', TestViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 