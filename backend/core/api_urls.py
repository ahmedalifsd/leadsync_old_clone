from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'leads', api_views.LeadViewSet, basename='lead')
router.register(r'categories', api_views.CategoryViewSet, basename='category')
router.register(r'sources', api_views.SourceViewSet, basename='source')
router.register(r'owner-categories', api_views.OwnerCategoryViewSet, basename='owner-category')
router.register(r'owner-sources', api_views.OwnerSourceViewSet, basename='owner-source')
router.register(r'activity-logs', api_views.ActivityLogViewSet, basename='activity-log')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/stats/', api_views.dashboard_stats, name='dashboard_stats'),
    path('leads/status-distribution/', api_views.lead_status_distribution, name='lead_status_distribution'),
]
