import logging
from datetime import datetime
from functools import wraps
from django.db.models import Q
from django.shortcuts import render
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Lead, ActivityLog, Notification, CustomField
from team.models import TeamMember

logger = logging.getLogger(__name__)


def get_table_page_size(request, table_key, default=10, allowed_sizes=None):
    """Return persisted rows-per-page for a table and update it when user selects a new value."""
    if allowed_sizes is None:
        allowed_sizes = [10, 15, 25, 50, 100]

    allowed_set = set(allowed_sizes)
    session_key = f'table_per_page_{table_key}'

    raw_value = request.GET.get('per_page')
    if raw_value is not None:
        try:
            parsed_value = int(raw_value)
        except (TypeError, ValueError):
            parsed_value = None

        if parsed_value in allowed_set:
            request.session[session_key] = parsed_value
            return parsed_value

    saved_value = request.session.get(session_key)
    if saved_value in allowed_set:
        return saved_value

    return default if default in allowed_set else min(allowed_sizes)


def log_activity(user, action, target_model, target_id=None, target_name='', details='', request=None):
    """
    Log user activity to the ActivityLog model with enhanced details
    """
    ip_address = None
    user_agent = None
    session_key = None

    if request:
        # Get IP address from request
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        # Get user agent from request
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Get session key if available
        session_key = request.session.session_key

    # Create activity log with enhanced details
    activity_log = ActivityLog.objects.create(
        user=user,
        action=action,
        target_model=target_model,
        target_id=target_id,
        target_name=target_name,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )

    # Optionally store session key in a separate field if needed
    # This would require adding a session_key field to the ActivityLog model

    return activity_log


def get_custom_fields_for_user(user, **extra_filters):
    """
    Get active custom fields for the appropriate owner based on user role.
    For staff, includes both boss's and their own custom fields.
    Extra filters (e.g. scope='all') can be passed as keyword args.
    """
    profile = user.profile
    if profile.role == 'owner':
        return CustomField.objects.filter(owner=user, is_active=True, **extra_filters).order_by('name')
    elif profile.role == 'staff':
        try:
            team_member = TeamMember.objects.get(staff=user)
            return CustomField.objects.filter(
                Q(owner=team_member.boss) | Q(owner=user),
                is_active=True, **extra_filters
            ).order_by('name')
        except TeamMember.DoesNotExist:
            return CustomField.objects.filter(owner=user, is_active=True, **extra_filters).order_by('name')
    elif profile.role == 'super_admin':
        return CustomField.objects.filter(is_active=True, **extra_filters).order_by('name')
    return CustomField.objects.none()


def get_user_leads(user):
    """
    Get leads based on user role with optimized queries
    """
    profile = user.profile

    if profile.role == 'super_admin':
        # Super admin sees all leads, including soft deleted ones
        leads = Lead.objects.select_related('created_by', 'owner', 'category', 'source', 'assigned_to')
    elif profile.role == 'owner' and profile.is_approved:
        # Owner sees their own leads and their staff's leads - excluding those soft deleted by the owner
        staff_ids = TeamMember.objects.filter(boss=user).values_list('staff_id', flat=True)
        all_user_ids = [user.id] + list(staff_ids)
        leads = Lead.objects.filter(owner_id__in=all_user_ids).select_related('created_by', 'owner', 'category', 'source', 'assigned_to')
        # Filter out leads that were soft deleted by the owner themselves
        leads = leads.exclude(deleted_by=user)
    elif profile.role == 'staff' and profile.is_approved:
        # Staff sees leads assigned to them AND their own created leads that haven't been soft deleted by owner or super admin
        leads = Lead.objects.filter(
            Q(assigned_to=user) | Q(created_by=user)
        ).select_related('created_by', 'owner', 'category', 'source', 'assigned_to')
        # Exclude leads deleted by owner/super_admin using a fast subquery (avoids JOINing profile table)
        from accounts.models import UserProfile
        higher_role_ids = UserProfile.objects.filter(
            role__in=['owner', 'super_admin']
        ).values_list('user_id', flat=True)
        leads = leads.exclude(deleted_by_id__in=higher_role_ids).exclude(deleted_by=user)
    else:
        leads = Lead.objects.none().select_related('created_by', 'owner', 'category', 'source', 'assigned_to')

    return leads


def staff_has_permission(user, permission_name):
    """
    Check if a staff user has a specific permission through their assigned role.
    Returns True for owners and super admins (they have all permissions).
    Returns False for staff without a role or without that permission.
    """
    profile = user.profile

    # Super admin and owner have all permissions
    if profile.role in ('super_admin', 'owner'):
        return True

    # Staff must have an approved account
    if profile.role != 'staff' or not profile.is_approved:
        return False

    # Check team membership and role
    try:
        team_member = TeamMember.objects.select_related('role').get(staff=user, is_active=True)
        if team_member.role:
            return getattr(team_member.role, permission_name, False)
    except TeamMember.DoesNotExist:
        pass

    return False


def send_email(to_email, subject, template_name, context=None):
    """
    Send an HTML email using a Django template.
    - to_email: Recipient email address (string or list)
    - subject: Email subject line
    - template_name: Path to the HTML template (e.g. 'emails/registration_pending.html')
    - context: Dictionary of context variables for the template
    """
    if context is None:
        context = {}

    # Add common context
    context['year'] = datetime.now().year
    context['subject'] = subject
    # Add currency symbol for email templates
    try:
        from billing.models import get_currency_symbol
        context['currency_symbol'] = get_currency_symbol()
    except Exception:
        context['currency_symbol'] = 'Rs.'

    try:
        # Render the HTML template
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)  # Fallback plain text

        # Ensure to_email is a list
        if isinstance(to_email, str):
            to_email = [to_email]

        # Create and send the email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to_email,
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        logger.info(f"Email sent successfully to {to_email} - Subject: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email} - Subject: {subject} - Error: {e}")
        return False


def notify(recipient, notification_type, title, message, url='', sender=None):
    """
    Create a notification for a user.
    - recipient: User who receives the notification
    - notification_type: One of Notification.NOTIFICATION_TYPES
    - title: Short title
    - message: Detailed message
    - url: Optional URL to redirect to on click
    - sender: Optional User who triggered the notification
    """
    return Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        title=title,
        message=message,
        url=url,
    )


def notify_team(owner, notification_type, title, message, url='', sender=None, exclude_user=None):
    """
    Send notification to all active team members of an owner.
    Optionally exclude a specific user (e.g., the person who performed the action).
    """
    staff_ids = TeamMember.objects.filter(boss=owner, is_active=True).values_list('staff_id', flat=True)
    notifications = []
    for staff_id in staff_ids:
        if exclude_user and staff_id == exclude_user.id:
            continue
        notifications.append(Notification(
            recipient_id=staff_id,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            url=url,
        ))
    if notifications:
        Notification.objects.bulk_create(notifications)


def require_permission(permission_name):
    """
    Decorator to check if the logged-in user has a specific permission.
    Works for all roles:
    - Super Admin & Owner: always pass
    - Staff: checked via their assigned Role
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.shortcuts import redirect
                return redirect('login')

            if staff_has_permission(request.user, permission_name):
                return view_func(request, *args, **kwargs)

            # Permission denied
            messages.error(request, 'You do not have permission to access this feature. Contact your manager.')
            return render(request, 'core/permission_denied.html', {
                'permission_name': permission_name
            }, status=403)

        return _wrapped_view
    return decorator