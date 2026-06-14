from django.urls import path
from . import views

urlpatterns = [
    path('check-availability/', views.check_availability, name='check_availability'),
    path('profile/', views.profile, name='profile'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('approve-owner/<int:user_id>/', views.approve_owner, name='approve_owner'),
    path('toggle-owner-approval/<int:user_id>/', views.toggle_owner_approval, name='toggle_owner_approval'),
    path('reject-owner/<int:user_id>/', views.reject_owner, name='reject_owner'),
    path('manage-staff/', views.manage_staff_requests, name='manage_staff_requests'),
    path('approve-staff/<int:user_id>/', views.approve_staff, name='approve_staff'),
    path('toggle-staff-approval/<int:user_id>/', views.toggle_staff_approval, name='toggle_staff_approval'),
    path('reject-staff/<int:user_id>/', views.reject_staff, name='reject_staff'),
]