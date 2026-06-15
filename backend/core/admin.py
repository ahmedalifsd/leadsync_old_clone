from django.contrib import admin
from .models import Category, Source, Lead, ProfileLink, Notification, DirectMessage, ChatTypingStatus, ChatGroup, ChatGroupMember, ChatGroupMessage, ChatGroupMessageReceipt, ChatPresence

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'contact_number', 'email', 'status', 'get_category_display_name', 'get_source_display_name', 'follow_up_date', 'created_at')
    list_filter = ('status', 'category', 'source', 'follow_up_date', 'created_at', 'updated_at')
    search_fields = ('client_name', 'contact_number', 'email', 'requirement', 'owner__username', 'created_by__username', 'category_other', 'source_other')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('client_name', 'contact_number', 'email')
        }),
        ('Lead Details', {
            'fields': ('requirement', 'status', 'follow_up_date', 'notes', 'category', 'category_other', 'source', 'source_other')
        }),
        ('System Information', {
            'fields': ('owner', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.profile.role == 'super_admin':
            return qs
        elif request.user.profile.role == 'owner':
            return qs.filter(owner=request.user)
        else:  # staff
            return qs.filter(created_by=request.user)


@admin.register(ProfileLink)
class ProfileLinkAdmin(admin.ModelAdmin):
    list_display = ('lead', 'get_platform_display_name', 'url', 'created_at')
    list_filter = ('platform', 'created_at')
    search_fields = ('lead__client_name', 'url', 'custom_platform')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.profile.role == 'super_admin':
            return qs
        elif request.user.profile.role == 'owner':
            return qs.filter(lead__owner=request.user)
        else:  # staff
            return qs.filter(lead__created_by=request.user)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__username', 'title', 'message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'created_at', 'read_at')
    list_filter = ('created_at', 'read_at')
    search_fields = ('sender__username', 'recipient__username', 'body')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(ChatTypingStatus)
class ChatTypingStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'peer', 'is_typing', 'updated_at')
    list_filter = ('is_typing', 'updated_at')
    search_fields = ('user__username', 'peer__username')
    readonly_fields = ('updated_at',)
    ordering = ('-updated_at',)


@admin.register(ChatGroup)
class ChatGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at')
    search_fields = ('name', 'owner__username')
    list_filter = ('created_at',)
    ordering = ('-created_at',)


@admin.register(ChatGroupMember)
class ChatGroupMemberAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'joined_at')
    search_fields = ('group__name', 'user__username')
    list_filter = ('joined_at',)
    ordering = ('-joined_at',)


@admin.register(ChatGroupMessage)
class ChatGroupMessageAdmin(admin.ModelAdmin):
    list_display = ('group', 'sender', 'created_at')
    search_fields = ('group__name', 'sender__username', 'body')
    list_filter = ('created_at',)
    ordering = ('-created_at',)


@admin.register(ChatGroupMessageReceipt)
class ChatGroupMessageReceiptAdmin(admin.ModelAdmin):
    list_display = ('message', 'recipient', 'delivered_at', 'seen_at')
    search_fields = ('message__group__name', 'recipient__username', 'message__body')
    list_filter = ('delivered_at', 'seen_at')
    ordering = ('-delivered_at',)


@admin.register(ChatPresence)
class ChatPresenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'last_seen_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    list_filter = ('last_seen_at',)
    ordering = ('-last_seen_at',)
