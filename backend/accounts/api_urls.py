from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'users', api_views.UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', api_views.register, name='register'),
    path('login/', api_views.login_view, name='login'),
    path('logout/', api_views.logout_view, name='logout'),
    path('user/', api_views.current_user, name='current_user'),
    path('profile/', api_views.update_profile, name='update_profile'),
    path('password/change/', api_views.change_password, name='change_password'),
    path('check-username/', api_views.check_username, name='check_username'),
    path('check-email/', api_views.check_email, name='check_email'),
]
