from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Role(models.Model):
    """Custom roles created by business owners for their employees"""
    name = models.CharField(max_length=100, help_text="Role name e.g. Manager, HR, Senior")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_roles')
    description = models.TextField(blank=True, help_text="Brief description of this role")

    # Lead permissions
    can_view_leads = models.BooleanField(default=True, verbose_name="View Leads")
    can_add_leads = models.BooleanField(default=False, verbose_name="Add Leads")
    can_edit_leads = models.BooleanField(default=False, verbose_name="Edit Leads")
    can_delete_leads = models.BooleanField(default=False, verbose_name="Delete Leads")
    can_bulk_add_leads = models.BooleanField(default=False, verbose_name="Bulk Add Leads")
    can_csv_upload = models.BooleanField(default=False, verbose_name="CSV Upload")

    # Template & Custom Field permissions
    can_manage_templates = models.BooleanField(default=False, verbose_name="Manage Templates")
    can_manage_custom_fields = models.BooleanField(default=False, verbose_name="Manage Custom Fields")

    # Analytics & Reporting
    can_view_analytics = models.BooleanField(default=False, verbose_name="View Analytics")
    can_view_activity_log = models.BooleanField(default=False, verbose_name="View Activity Log")
    can_view_deleted_leads = models.BooleanField(default=False, verbose_name="View Deleted Leads")

    # Lead management
    can_assign_leads = models.BooleanField(default=False, verbose_name="Assign Leads")
    can_share_leads = models.BooleanField(default=False, verbose_name="Share Leads")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'owner')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

    @classmethod
    def get_permission_fields(cls):
        """Return list of all permission field names and their verbose names"""
        permission_fields = []
        for field in cls._meta.get_fields():
            if isinstance(field, models.BooleanField) and field.name.startswith('can_'):
                permission_fields.append({
                    'name': field.name,
                    'verbose_name': field.verbose_name,
                })
        return permission_fields

    def get_granted_permissions(self):
        """Return list of permission names that are granted"""
        return [f['name'] for f in self.get_permission_fields() if getattr(self, f['name'])]


class TeamMember(models.Model):
    boss = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_members')
    staff = models.OneToOneField(User, on_delete=models.CASCADE, related_name='team_boss')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    joined_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    previous_active_state = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)
    removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('boss', 'staff')

    def __str__(self):
        role_name = self.role.name if self.role else "No Role"
        return f"{self.staff.username} ({role_name}) -> {self.boss.username}"

    def mark_removed(self):
        """Permanently remove from active team management while retaining account record."""
        self.is_active = False
        self.is_removed = True
        self.removed_at = timezone.now()
        self.save(update_fields=['is_active', 'is_removed', 'removed_at'])

    def has_perm(self, permission_name):
        """Check if this team member has a specific permission"""
        if not self.role:
            return False
        return getattr(self.role, permission_name, False)
