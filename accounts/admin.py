from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_approved', 'phone_number', 'company_name', 'created_at')
    list_filter = ('role', 'is_approved', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'phone_number', 'company_name', 'pending_boss_username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
