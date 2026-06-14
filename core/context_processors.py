from django.conf import settings
from django.core.cache import cache


def stripe_context(request):
    """
    Adds Stripe configuration to the context
    """
    return {
        'STRIPE_PUBLISHABLE_KEY': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''),
    }


def google_analytics_context(request):
    """Adds GA4 measurement ID to templates."""
    return {
        'GA_MEASUREMENT_ID': getattr(settings, 'GA_MEASUREMENT_ID', ''),
    }


def currency_context(request):
    """
    Adds site settings and currency info to every template context.
    Cached to avoid DB hit on every request.
    """
    cached = cache.get('site_settings_context')
    if cached:
        return cached

    try:
        from billing.models import SiteSettings
        s = SiteSettings.objects.first()
        if s:
            result = {
                'currency_symbol': s.currency_symbol,
                'currency_code': s.currency_code,
                'site_settings': s,
            }
        else:
            result = {'currency_symbol': 'Rs.', 'currency_code': 'pkr', 'site_settings': None}
    except Exception:
        result = {'currency_symbol': 'Rs.', 'currency_code': 'pkr', 'site_settings': None}

    cache.set('site_settings_context', result, 300)  # 5 min cache
    return result


# All permissions dict for super_admin and owner (no DB needed)
_ALL_PERMS = {
    'can_view_leads': True,
    'can_add_leads': True,
    'can_edit_leads': True,
    'can_delete_leads': True,
    'can_bulk_add_leads': True,
    'can_csv_upload': True,
    'can_manage_templates': True,
    'can_manage_custom_fields': True,
    'can_view_analytics': True,
    'can_view_activity_log': True,
    'can_view_deleted_leads': True,
    'can_assign_leads': True,
    'can_share_leads': True,
}

_EMPTY_PERMS = {'user_perms': {}, 'user_role_name': 'No Role'}


def user_permissions_context(request):
    """
    Adds user permissions to the template context.
    Uses per-request caching to avoid DB hits on every template render.
    Staff permissions are cached in Django cache for 5 min (invalidated on role change).
    """
    if not request.user.is_authenticated:
        return {'user_perms': {}}

    # Per-request cache: avoid recomputing within the same request
    if hasattr(request, '_cached_user_perms'):
        return request._cached_user_perms

    profile = getattr(request.user, 'profile', None)
    if not profile:
        result = {'user_perms': {}}
        request._cached_user_perms = result
        return result

    # Super admin and owner: no DB query needed, return static dict
    if profile.role in ('super_admin', 'owner'):
        result = {
            'user_perms': _ALL_PERMS,
            'user_role_name': profile.get_role_display(),
        }
        request._cached_user_perms = result
        return result

    # Staff: use cache to avoid DB query on every request
    if profile.role == 'staff' and profile.is_approved:
        cache_key = f'user_perms_{request.user.id}'
        cached = cache.get(cache_key)
        if cached:
            request._cached_user_perms = cached
            return cached

        from team.models import TeamMember
        try:
            team_member = TeamMember.objects.select_related('role').get(staff=request.user, is_active=True)
            role = team_member.role
            if role:
                result = {
                    'user_perms': {
                        'can_view_leads': role.can_view_leads,
                        'can_add_leads': role.can_add_leads,
                        'can_edit_leads': role.can_edit_leads,
                        'can_delete_leads': role.can_delete_leads,
                        'can_bulk_add_leads': role.can_bulk_add_leads,
                        'can_csv_upload': role.can_csv_upload,
                        'can_manage_templates': role.can_manage_templates,
                        'can_manage_custom_fields': role.can_manage_custom_fields,
                        'can_view_analytics': role.can_view_analytics,
                        'can_view_activity_log': role.can_view_activity_log,
                        'can_view_deleted_leads': role.can_view_deleted_leads,
                        'can_assign_leads': role.can_assign_leads,
                        'can_share_leads': role.can_share_leads,
                    },
                    'user_role_name': role.name,
                }
                cache.set(cache_key, result, 300)  # Cache for 5 minutes
                request._cached_user_perms = result
                return result
        except TeamMember.DoesNotExist:
            pass

    request._cached_user_perms = _EMPTY_PERMS
    return _EMPTY_PERMS


def plan_alert_context(request):
    """
    Provides plan status alerts for owners and employees.
    Shows:
      - "No plan active" if free/no subscription
      - "Plan expiring in X days" if <= 3 days remaining
      - "Plan expired" if end_date passed
    For staff: looks up the boss's subscription.
    """
    empty = {'plan_alert': None}
    if not request.user.is_authenticated:
        return empty

    if hasattr(request, '_cached_plan_alert'):
        return request._cached_plan_alert

    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role == 'super_admin':
        request._cached_plan_alert = empty
        return empty

    from billing.models import Subscription, Plan
    from datetime import date

    subscription = None
    is_staff = profile.role == 'staff'
    boss_name = ''

    if profile.role == 'owner':
        try:
            subscription = Subscription.objects.select_related('plan').get(owner=request.user)
        except Subscription.DoesNotExist:
            pass
    elif is_staff:
        from team.models import TeamMember
        try:
            tm = TeamMember.objects.select_related('boss').get(staff=request.user, is_active=True)
            boss_name = tm.boss.get_full_name() or tm.boss.username
            try:
                subscription = Subscription.objects.select_related('plan').get(owner=tm.boss)
            except Subscription.DoesNotExist:
                pass
        except TeamMember.DoesNotExist:
            request._cached_plan_alert = empty
            return empty

    if not subscription or not subscription.is_active:
        alert = {
            'type': 'no_plan',
            'color': 'info',
            'icon': 'fas fa-info-circle',
            'is_staff': is_staff,
            'boss_name': boss_name,
        }
        if is_staff:
            alert['message'] = f"Your business owner ({boss_name}) has no active plan. Some features may be limited."
        else:
            alert['message'] = "You don't have an active plan. Upgrade now to unlock all features!"
            alert['show_upgrade'] = True
        result = {'plan_alert': alert}
        request._cached_plan_alert = result
        return result

    is_free = subscription.plan.monthly_price <= 0 and not subscription.is_custom_plan
    today = date.today()

    # Free plan — nudge to upgrade
    if is_free:
        alert = {
            'type': 'free_plan',
            'color': 'info',
            'icon': 'fas fa-gift',
            'is_staff': is_staff,
            'boss_name': boss_name,
            'plan_name': subscription.plan.name,
        }
        if is_staff:
            alert['message'] = f"Your team is on the free {subscription.plan.name} plan. Ask {boss_name} to upgrade for more features."
        else:
            alert['message'] = f"You're on the free {subscription.plan.name} plan. Upgrade to unlock more employees, leads and features!"
            alert['show_upgrade'] = True
        result = {'plan_alert': alert}
        request._cached_plan_alert = result
        return result

    # Expired plan
    if subscription.end_date and subscription.end_date < today:
        alert = {
            'type': 'expired',
            'color': 'danger',
            'icon': 'fas fa-exclamation-circle',
            'is_staff': is_staff,
            'boss_name': boss_name,
            'plan_name': subscription.plan.name if not subscription.is_custom_plan else 'Custom Plan',
        }
        if is_staff:
            alert['message'] = f"Your team's plan has expired! Please inform {boss_name} to renew immediately."
        else:
            alert['message'] = "Your plan has expired! Renew now to continue using all features."
            alert['show_upgrade'] = True
        result = {'plan_alert': alert}
        request._cached_plan_alert = result
        return result

    # Expiring soon (3 days or less)
    if subscription.end_date:
        remaining = (subscription.end_date - today).days
        if remaining <= 3:
            alert = {
                'type': 'expiring',
                'color': 'warning',
                'icon': 'fas fa-clock',
                'is_staff': is_staff,
                'boss_name': boss_name,
                'remaining_days': remaining,
                'plan_name': subscription.plan.name if not subscription.is_custom_plan else 'Custom Plan',
            }
            if is_staff:
                day_text = 'today' if remaining == 0 else (f'in {remaining} day' + ('s' if remaining != 1 else ''))
                alert['message'] = f"Your team's plan expires {day_text}! Please inform {boss_name} to renew."
            else:
                day_text = 'today' if remaining == 0 else (f'in {remaining} day' + ('s' if remaining != 1 else ''))
                alert['message'] = f"Your plan expires {day_text}! Renew now to avoid service interruption."
                alert['show_upgrade'] = True
            result = {'plan_alert': alert}
            request._cached_plan_alert = result
            return result

    # Active paid plan — no alert needed
    request._cached_plan_alert = empty
    return empty


_EMPTY_NOTIFICATIONS = {'notifications': [], 'unread_notifications_count': 0}


def notifications_context(request):
    """
    Provides notification data for the navbar dropdown.
    Optimized: single query with annotation, per-request cached.
    """
    if not request.user.is_authenticated:
        return _EMPTY_NOTIFICATIONS

    # Per-request cache
    if hasattr(request, '_cached_notifications'):
        return request._cached_notifications

    from .models import Notification
    from django.db.models import Sum, Case, When, IntegerField

    # Single query: fetch latest 5 notifications + unread count via annotation
    recent = list(
        Notification.objects.filter(recipient=request.user)
        .order_by('-created_at')[:5]
    )
    # Separate lightweight count query for unread badge
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    result = {
        'notifications': recent,
        'unread_notifications_count': unread_count,
    }
    request._cached_notifications = result
    return result


_EMPTY_CHAT = {'unread_chat_count': 0}


def chat_unread_context(request):
    """Provides unread direct-message count for sidebar chat badge."""
    if not request.user.is_authenticated:
        return _EMPTY_CHAT

    if hasattr(request, '_cached_unread_chat_count'):
        return {'unread_chat_count': request._cached_unread_chat_count}

    from .models import DirectMessage

    unread_count = DirectMessage.objects.filter(
        recipient=request.user,
        read_at__isnull=True,
    ).count()

    request._cached_unread_chat_count = unread_count
    return {'unread_chat_count': unread_count}