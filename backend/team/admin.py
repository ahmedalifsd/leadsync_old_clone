from django.contrib import admin
from .models import TeamMember, Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'can_view_leads', 'can_add_leads', 'can_edit_leads', 'can_delete_leads', 'created_at')
    list_filter = ('owner', 'can_view_leads', 'can_add_leads', 'can_edit_leads', 'can_delete_leads')
    search_fields = ('name', 'owner__username')
    ordering = ('owner', 'name')


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('staff', 'boss', 'role', 'joined_date', 'is_active', 'is_removed', 'removed_at')
    list_filter = ('is_active', 'is_removed', 'joined_date', 'role')
    search_fields = ('staff__username', 'staff__email', 'boss__username', 'boss__email')
    ordering = ('-joined_date',)
    date_hierarchy = 'joined_date'
