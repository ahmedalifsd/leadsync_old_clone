from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ActivityLog(models.Model):
    """Model to track user activities throughout the system"""
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('import', 'Import'),
        ('export', 'Export'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target_model = models.CharField(max_length=50, help_text="Model name being acted upon")
    target_id = models.IntegerField(help_text="ID of the object being acted upon", null=True, blank=True)
    target_name = models.CharField(max_length=200, help_text="Name/description of the target object", blank=True)
    details = models.TextField(help_text="Additional details about the action", blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        # Only keep indexes that match actual query patterns
        indexes = [
            models.Index(fields=['user', '-timestamp']),      # activity_log view: filter by user, order by -timestamp
            models.Index(fields=['action', '-timestamp']),     # filter by action
            models.Index(fields=['target_model', '-timestamp']),  # filter by model
            models.Index(fields=['-timestamp']),               # default ordering
        ]

    def __str__(self):
        return f"{self.user.username} - {self.action} {self.target_model} - {self.timestamp}"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Source(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class OwnerCategory(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owner_categories')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('owner', 'name')

    def __str__(self):
        return f"{self.name} ({self.owner.username})"


class OwnerSource(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owner_sources')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('owner', 'name')

    def __str__(self):
        return f"{self.name} ({self.owner.username})"


class Lead(models.Model):
    STATUS_CHOICES = (
        ('new', 'New'),
        ('not_contacted', 'Not Contacted'),
        ('contacted', 'Contacted'),
        ('no_response', 'No Response'),
        ('interested', 'Interested'),
        ('not_interested', 'Not Interested'),
        ('qualified', 'Qualified'),
        ('proposal', 'Proposal Sent'),
        ('negotiation', 'Negotiation'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    )

    # ForeignKey fields get automatic db_index from Django
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_leads')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_leads')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    category_other = models.TextField(blank=True, null=True)
    source = models.ForeignKey(Source, on_delete=models.SET_NULL, null=True, blank=True)
    source_other = models.TextField(blank=True, null=True)
    client_name = models.CharField(max_length=200, db_index=True)  # searched frequently
    contact_number = models.CharField(max_length=20, blank=True, null=True, db_index=True)  # searched frequently
    email = models.EmailField(blank=True, null=True, db_index=True)  # searched frequently
    requirement = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    follow_up_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Soft delete fields
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_leads')
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Assignment fields
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')
    assignment_date = models.DateTimeField(null=True, blank=True)

    # Lead scoring fields
    lead_score = models.IntegerField(default=0, help_text="Score based on lead quality criteria")
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Estimated budget of the lead")
    timeline = models.DateField(null=True, blank=True, help_text="Expected timeline for decision")
    decision_maker = models.BooleanField(default=False, help_text="Is the contact the decision maker?")

    # Conversion tracking
    converted_to_customer = models.BooleanField(default=False)
    conversion_date = models.DateTimeField(null=True, blank=True)

    # Number of times this lead has been explicitly marked as contacted.
    contact_attempts = models.PositiveIntegerField(default=0)

    # Tracks how many times the current status has been explicitly applied.
    # 1 = first time (show plain label), >1 = show label with count suffix.
    status_repeat_count = models.PositiveIntegerField(default=1)

    # Custom fields
    custom_fields = models.JSONField(default=dict, blank=True, help_text="Additional custom fields as key-value pairs")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Compound indexes aligned to actual query patterns
            models.Index(fields=['owner', 'status', '-created_at']),  # get_user_leads + filter
            models.Index(fields=['owner', '-created_at']),            # owner's leads ordered
            models.Index(fields=['created_by', '-created_at']),       # staff leads
            models.Index(fields=['assigned_to', '-created_at']),      # assigned leads
            models.Index(fields=['follow_up_date', 'status']),        # follow-up queries
            models.Index(fields=['converted_to_customer', '-created_at']),  # analytics
            models.Index(fields=['deleted_by', 'owner']),             # soft-delete queries
            models.Index(fields=['-created_at']),                     # default ordering
        ]

    def __str__(self):
        return f"{self.client_name} - {self.get_status_display()}"

    def get_category_display_name(self):
        if self.category:
            return self.category.name
        elif self.category_other:
            return self.category_other
        return "Not Specified"

    def get_source_display_name(self):
        if self.source:
            return self.source.name
        elif self.source_other:
            return self.source_other
        return "Not Specified"

    def is_deleted_for_user(self, user):
        """Check if this lead is soft deleted for the given user"""
        if self.deleted_by:
            # If deleted by someone with lower role, hide from them but show to higher roles
            user_profile = getattr(user, 'profile', None)
            deleted_by_profile = getattr(self.deleted_by, 'profile', None)

            # Super admin can see everything
            if user_profile and user_profile.role == 'super_admin':
                return False

            # Staff can't see leads deleted by owner or super admin
            if user_profile and user_profile.role == 'staff':
                if deleted_by_profile and deleted_by_profile.role in ['owner', 'super_admin']:
                    return True
                elif self.deleted_by == user:
                    return True  # Staff can't see what they deleted themselves
                return False

            # Owner can see what staff deleted, but not what they deleted themselves
            if user_profile and user_profile.role == 'owner':
                if self.deleted_by == user:
                    return True  # Owner can't see what they deleted themselves
                return False

        return False

    def calculate_lead_score(self):
        """Calculate lead score based on various criteria"""
        score = 0

        # Budget contributes to score (higher budget = higher score)
        if self.budget:
            budget_score_map = [
                (100000, 25),
                (50000, 20),
                (10000, 15),
                (1000, 10)
            ]
            for threshold, points in budget_score_map:
                if self.budget >= threshold:
                    score += points
                    break

        # Timeline contributes to score (shorter timeline = higher score)
        if self.timeline:
            from django.utils import timezone
            days_until_decision = (self.timeline - timezone.now().date()).days
            timeline_score_map = [
                (30, 20),
                (60, 15),
                (90, 10)
            ]
            for threshold, points in timeline_score_map:
                if days_until_decision <= threshold:
                    score += points
                    break

        # Decision maker contributes to score
        if self.decision_maker:
            score += 15

        # Status contributes to score
        status_scores = {
            'new': 5,
            'contacted': 10,
            'qualified': 15,
            'proposal': 20,
            'negotiation': 25,
            'won': 30
        }
        score += status_scores.get(self.status, 0)

        return score

    @classmethod
    def get_deleted_leads_for_owner(cls, owner_user):
        """Get leads that were deleted by staff members of this owner"""
        from team.models import TeamMember
        staff_ids = TeamMember.objects.filter(boss=owner_user).values_list('staff_id', flat=True)
        return cls.objects.filter(
            deleted_by__in=staff_ids,
            owner=owner_user
        ).select_related('created_by', 'owner', 'category', 'source', 'deleted_by')

    @classmethod
    def get_deleted_leads_for_admin(cls):
        """Get all leads that were deleted by any user"""
        return cls.objects.filter(deleted_by__isnull=False).select_related('created_by', 'owner', 'category', 'source', 'deleted_by')


class LeadAssignmentHistory(models.Model):
    """Model to track assignment history of leads"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='assignment_history')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assignments_made')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assignments_received')
    assigned_at = models.DateTimeField(auto_now_add=True)
    previous_assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='previous_assignments')
    reason = models.TextField(blank=True, help_text="Reason for assignment")

    class Meta:
        ordering = ['-assigned_at']
        verbose_name = 'Lead Assignment History'
        verbose_name_plural = 'Lead Assignment Histories'

    def __str__(self):
        return f"Lead {self.lead.client_name} assigned from {self.previous_assigned_to} to {self.assigned_to} on {self.assigned_at}"


class LeadActivity(models.Model):
    """Model to track all activities related to a lead"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=50, choices=[
        ('note', 'Note'),
        ('call', 'Call'),
        ('meeting', 'Meeting'),
        ('email', 'Email'),
        ('conversion', 'Conversion'),
        ('assignment', 'Assignment'),
        ('status_update', 'Status Update'),
    ])
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Lead Activity'
        verbose_name_plural = 'Lead Activities'

    def __str__(self):
        return f"{self.activity_type.title()} for {self.lead.client_name} on {self.timestamp}"

class CustomField(models.Model):
    """Model to define custom fields for leads"""
    FIELD_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('boolean', 'Boolean'),
        ('choice', 'Choice'),
        ('textarea', 'Text Area'),
    ]

    SCOPE_CHOICES = [
        ('all', 'Apply to all leads (bulk)'),
        ('each', 'Per individual lead'),
    ]

    name = models.CharField(max_length=100, help_text="Name of the custom field")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text', help_text="Type of the field")
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default='all',
                             help_text="Whether this field applies to all leads or per individual lead")
    choices = models.TextField(blank=True, help_text="Available choices for choice fields (comma separated)")
    required = models.BooleanField(default=False, help_text="Is this field required?")
    is_active = models.BooleanField(default=True, help_text="Whether this field is active and visible on forms")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_fields')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['name', 'owner']
        ordering = ['name']

    def __str__(self):
        return f"{self.owner.username} - {self.name}"

    def has_lead_data(self):
        """Check if any leads have data stored for this custom field"""
        leads_with_data = Lead.objects.filter(
            owner=self.owner,
            custom_fields__has_key=self.name
        ).exclude(custom_fields__exact={})
        return leads_with_data.exists()

    def lead_data_count(self):
        """Count how many leads have data for this custom field"""
        return Lead.objects.filter(
            owner=self.owner,
            custom_fields__has_key=self.name
        ).exclude(custom_fields__exact={}).count()


class LeadSharing(models.Model):
    """Model to track sharing of leads between team members"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='shared_with')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shares_created')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shares_received')
    shared_at = models.DateTimeField(auto_now_add=True)
    permissions = models.CharField(max_length=20, choices=[
        ('view', 'View Only'),
        ('edit', 'Edit'),
        ('full', 'Full Access'),
    ], default='view')
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When sharing access expires")

    class Meta:
        unique_together = ['lead', 'shared_with']
        ordering = ['-shared_at']

    def __str__(self):
        return f"Lead {self.lead.client_name} shared from {self.shared_by} to {self.shared_with}"

    @classmethod
    def get_deleted_leads_for_admin(cls):
        """Get all leads that were deleted by any user"""
        return cls.objects.filter(deleted_by__isnull=False).select_related('created_by', 'owner', 'category', 'source', 'deleted_by')


class ProfileLink(models.Model):
    PLATFORM_CHOICES = (
        ('linkedin', 'LinkedIn'),
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter'),
        ('youtube', 'YouTube'),
        ('website', 'Website'),
        ('other', 'Other'),
    )

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='profile_links')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='other')
    custom_platform = models.CharField(max_length=100, blank=True, null=True, help_text="Specify platform name if 'Other' selected")
    url = models.URLField(help_text="Profile URL")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['platform']

    def __str__(self):
        platform_name = self.get_platform_display()
        if self.platform == 'other' and self.custom_platform:
            platform_name = self.custom_platform
        return f"{platform_name}: {self.url}"

    def get_platform_display_name(self):
        if self.platform == 'other' and self.custom_platform:
            return self.custom_platform
        return self.get_platform_display()


class LeadTemplate(models.Model):
    """Model to store lead template presets"""
    name = models.CharField(max_length=100, help_text="Name for this template preset")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lead_templates')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    source = models.ForeignKey(Source, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Lead.STATUS_CHOICES, default='new')
    notes = models.TextField(blank=True, help_text="Default notes for all leads using this template")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Soft delete fields
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_templates')
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        unique_together = ['owner', 'name']  # Each user can have unique template names

    def __str__(self):
        return f"{self.owner.username} - {self.name}"

    def is_deleted_for_user(self, user):
        """Check if this template is soft deleted for the given user"""
        if self.deleted_by:
            # If deleted by someone with lower role, hide from them but show to higher roles
            user_profile = getattr(user, 'profile', None)
            deleted_by_profile = getattr(self.deleted_by, 'profile', None)

            # Super admin can see everything
            if user_profile and user_profile.role == 'super_admin':
                return False

            # Staff can't see templates deleted by owner or super admin
            if user_profile and user_profile.role == 'staff':
                if deleted_by_profile and deleted_by_profile.role in ['owner', 'super_admin']:
                    return True
                elif self.deleted_by == user:
                    return True  # Staff can't see what they deleted themselves
                return False

            # Owner can see what staff deleted, but not what they deleted themselves
            if user_profile and user_profile.role == 'owner':
                if self.deleted_by == user:
                    return True  # Owner can't see what they deleted themselves
                return False

        return False

    @classmethod
    def get_deleted_templates_for_owner(cls, owner_user):
        """Get templates that were deleted by staff members of this owner"""
        from team.models import TeamMember
        staff_ids = TeamMember.objects.filter(boss=owner_user).values_list('staff_id', flat=True)
        return cls.objects.filter(
            deleted_by__in=staff_ids,
            owner=owner_user
        ).select_related('deleted_by')

    @classmethod
    def get_deleted_templates_for_admin(cls):
        """Get all templates that were deleted by any user"""
        return cls.objects.filter(deleted_by__isnull=False).select_related('deleted_by')


class Notification(models.Model):
    """Model to store in-app notifications for users"""
    NOTIFICATION_TYPES = [
        ('lead_added', 'Lead Added'),
        ('lead_updated', 'Lead Updated'),
        ('lead_deleted', 'Lead Deleted'),
        ('lead_assigned', 'Lead Assigned'),
        ('lead_shared', 'Lead Shared'),
        ('lead_converted', 'Lead Converted'),
        ('lead_imported', 'Leads Imported'),
        ('staff_approved', 'Staff Approved'),
        ('staff_rejected', 'Staff Rejected'),
        ('staff_removed', 'Staff Removed'),
        ('owner_approved', 'Owner Approved'),
        ('role_assigned', 'Role Assigned'),
        ('role_created', 'Role Created'),
        ('plan_upgraded', 'Plan Upgraded'),
        ('payment_received', 'Payment Received'),
        ('followup_due', 'Follow-up Due'),
        ('followup_overdue', 'Follow-up Overdue'),
        ('template_created', 'Template Created'),
        ('custom_field_created', 'Custom Field Created'),
        ('system', 'System'),
    ]

    ICON_MAP = {
        'lead_added': 'fa-solid fa-user-plus text-success',
        'lead_updated': 'fa-solid fa-pen-to-square text-primary',
        'lead_deleted': 'fa-solid fa-trash text-danger',
        'lead_assigned': 'fa-solid fa-user-tag text-info',
        'lead_shared': 'fa-solid fa-share-nodes text-warning',
        'lead_converted': 'fa-solid fa-trophy text-success',
        'lead_imported': 'fa-solid fa-file-import text-primary',
        'staff_approved': 'fa-solid fa-user-check text-success',
        'staff_rejected': 'fa-solid fa-user-xmark text-danger',
        'staff_removed': 'fa-solid fa-user-minus text-danger',
        'owner_approved': 'fa-solid fa-building-circle-check text-success',
        'role_assigned': 'fa-solid fa-user-shield text-info',
        'role_created': 'fa-solid fa-shield-halved text-primary',
        'plan_upgraded': 'fa-solid fa-arrow-up-right-dots text-success',
        'payment_received': 'fa-solid fa-credit-card text-success',
        'followup_due': 'fa-solid fa-clock text-warning',
        'followup_overdue': 'fa-solid fa-clock text-danger',
        'template_created': 'fa-solid fa-file-circle-plus text-primary',
        'custom_field_created': 'fa-solid fa-sliders text-info',
        'system': 'fa-solid fa-bell text-secondary',
    }

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', db_index=True)
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='system', db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    url = models.CharField(max_length=500, blank=True, help_text="URL to redirect when notification is clicked")
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),       # navbar: latest 5
            models.Index(fields=['recipient', 'is_read', '-created_at']),  # unread count
        ]

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"

    @property
    def icon_class(self):
        return self.ICON_MAP.get(self.notification_type, 'fa-solid fa-bell text-secondary')

    @property
    def time_ago(self):
        """Return human-readable time difference"""
        from django.utils import timezone
        now = timezone.now()
        diff = now - self.created_at
        seconds = diff.total_seconds()

        if seconds < 60:
            return 'Just now'
        elif seconds < 3600:
            mins = int(seconds // 60)
            return f'{mins} min{"s" if mins > 1 else ""} ago'
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f'{hours} hr{"s" if hours > 1 else ""} ago'
        elif seconds < 604800:
            days = int(seconds // 86400)
            return f'{days} day{"s" if days > 1 else ""} ago'
        else:
            return self.created_at.strftime('%b %d, %Y')


class DirectMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_direct_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_direct_messages')
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['sender', 'recipient', '-created_at']),
            models.Index(fields=['recipient', 'read_at', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
        constraints = [
            models.CheckConstraint(condition=~models.Q(sender=models.F('recipient')), name='dm_sender_not_recipient'),
        ]

    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username}"


class ChatTypingStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='typing_statuses')
    peer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='peer_typing_statuses')
    is_typing = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'peer']
        indexes = [
            models.Index(fields=['peer', 'is_typing', '-updated_at']),
            models.Index(fields=['user', 'peer']),
        ]
        constraints = [
            models.CheckConstraint(condition=~models.Q(user=models.F('peer')), name='typing_user_not_peer'),
        ]

    def __str__(self):
        return f"typing:{self.user.username}->{self.peer.username}:{self.is_typing}"


class ChatGroup(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_chat_groups')
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', '-created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.owner.username})"


class ChatGroupMember(models.Model):
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_group_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['group', 'user']
        indexes = [
            models.Index(fields=['user', 'group']),
            models.Index(fields=['group', 'user']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"


class ChatGroupMessage(models.Model):
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_group_messages')
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['group', '-created_at']),
            models.Index(fields=['sender', '-created_at']),
        ]

    def __str__(self):
        return f"{self.sender.username} in {self.group.name}"


class ChatGroupMessageReceipt(models.Model):
    message = models.ForeignKey(ChatGroupMessage, on_delete=models.CASCADE, related_name='receipts')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_message_receipts')
    delivered_at = models.DateTimeField(default=timezone.now)
    seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['message', 'recipient']
        indexes = [
            models.Index(fields=['message', 'recipient']),
            models.Index(fields=['recipient', 'seen_at']),
            models.Index(fields=['recipient', 'delivered_at']),
        ]

    def __str__(self):
        return f"{self.message_id} -> {self.recipient.username}"


class ChatPresence(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_presence')
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['last_seen_at']),
        ]

    def __str__(self):
        return f"{self.user.username} @ {self.last_seen_at}"
