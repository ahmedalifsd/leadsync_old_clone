from django.urls import path
from . import views

urlpatterns = [
    path('manage/', views.manage_team, name='manage_team'),
    path('manage/create-employee/', views.create_employee, name='create_employee'),
    path('manage/import-employees/', views.import_employees, name='import_employees'),
    path('manage/employees-template.xlsx', views.download_employees_template, name='download_employees_template'),
    path('toggle-status/<int:staff_id>/', views.toggle_staff_status, name='toggle_staff_status'),
    path('remove/<int:staff_id>/', views.remove_staff, name='remove_staff'),
    path('bulk-remove/', views.bulk_remove_staff, name='bulk_remove_staff'),
    path('bulk-deactivate/', views.bulk_deactivate_staff, name='bulk_deactivate_staff'),
    path('employees/', views.admin_manage_employees, name='admin_manage_employees'),
    path('business-owners/', views.admin_manage_business_owners, name='admin_manage_business_owners'),
    path('business-owners/toggle-status/<int:user_id>/', views.toggle_business_owner_status, name='toggle_business_owner_status'),
    path('business-owner/<int:user_id>/', views.admin_view_business_owner, name='admin_view_business_owner'),

    # Role management (Business Owner only)
    path('roles/', views.manage_roles, name='manage_roles'),
    path('roles/create/', views.create_role, name='create_role'),
    path('roles/edit/<int:role_id>/', views.edit_role, name='edit_role'),
    path('roles/delete/<int:role_id>/', views.delete_role, name='delete_role'),
    path('roles/permissions/<int:role_id>/', views.view_role_permissions, name='view_role_permissions'),
    path('assign-role/<int:staff_id>/', views.assign_role, name='assign_role'),
]
