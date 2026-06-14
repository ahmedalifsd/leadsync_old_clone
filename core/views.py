from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count, Prefetch, Avg
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from email.utils import parseaddr
from .models import Lead, Category, Source, OwnerCategory, OwnerSource, LeadTemplate, ActivityLog, LeadAssignmentHistory, LeadActivity, CustomField, LeadSharing, ProfileLink, Notification, DirectMessage, ChatTypingStatus, ChatGroup, ChatGroupMember, ChatGroupMessage, ChatGroupMessageReceipt, ChatPresence
from .forms import LeadForm, LeadFilterForm, ProfileLinkFormSet, BulkLeadForm, LeadEntryFormSet, LeadEntryCustomFieldsFormSet, LeadTemplateForm, CSVUploadForm, LeadAssignmentForm, CustomFieldForm
from team.models import TeamMember
from .utils import log_activity, get_user_leads, require_permission, notify, notify_team, get_custom_fields_for_user, get_table_page_size
import json
import csv
import io
from datetime import datetime, timedelta, date
import logging
from decimal import Decimal


logger = logging.getLogger(__name__)


CHAT_ONLINE_WINDOW_SECONDS = 45


def _get_query_choice(request, key, allowed_values, default):
    value = (request.GET.get(key) or '').strip()
    return value if value in allowed_values else default


def _get_best_campaign_discount(plan, base_amount, check_date=None):
    """Return best active campaign and discount amount for a plan amount."""
    from billing.models import PlanDiscount

    check_date = check_date or date.today()
    campaigns = PlanDiscount.objects.filter(
        is_active=True,
        start_date__lte=check_date,
        end_date__gte=check_date,
    )
    campaigns = (campaigns.filter(applies_to_all_plans=True) | campaigns.filter(plans=plan)).distinct()

    best_campaign = None
    best_discount = Decimal('0.00')
    amount = Decimal(str(base_amount)).quantize(Decimal('0.01'))
    for campaign in campaigns:
        discount_amount = campaign.get_discount_amount(amount)
        if discount_amount > best_discount:
            best_discount = discount_amount
            best_campaign = campaign

    return best_campaign, best_discount


def _attach_public_plan_pricing(plans):
    """Attach campaign-adjusted monthly/yearly display prices for public pages."""
    for plan in plans:
        monthly_campaign, monthly_discount = _get_best_campaign_discount(plan, plan.monthly_price)
        yearly_campaign, yearly_discount = _get_best_campaign_discount(plan, plan.yearly_price)

        yearly_base_price = (plan.monthly_price * Decimal('12')).quantize(Decimal('0.01'))
        yearly_base_discount_amount = max(Decimal('0.00'), yearly_base_price - plan.yearly_price).quantize(Decimal('0.01'))

        plan.display_monthly_price = max(Decimal('0.00'), plan.monthly_price - monthly_discount).quantize(Decimal('0.01'))
        plan.display_yearly_price = max(Decimal('0.00'), plan.yearly_price - yearly_discount).quantize(Decimal('0.01'))
        plan.monthly_campaign_discount = monthly_discount
        plan.yearly_campaign_discount = yearly_discount
        plan.yearly_base_price = yearly_base_price
        plan.yearly_base_discount_amount = yearly_base_discount_amount

        active_campaign = monthly_campaign or yearly_campaign
        plan.active_campaign_name = active_campaign.name if active_campaign else ''


def _can_access_lead(user, lead):
    """Check whether a user can access or modify a lead record."""
    return (
        user.profile.role == 'super_admin' or
        lead.owner == user or
        lead.created_by == user or
        lead.assigned_to == user
    )


def _get_effective_owner(user):
    if user.profile.role == 'owner':
        return user
    if user.profile.role == 'staff':
        tm = TeamMember.objects.filter(staff=user, is_active=True).select_related('boss').first()
        return tm.boss if tm else None
    return None


def _build_visible_category_options(user):
    options = [{'id': str(c.id), 'name': c.name, 'scope': 'global'} for c in Category.objects.all()]
    owner_user = _get_effective_owner(user)
    if owner_user:
        private_categories = OwnerCategory.objects.filter(owner=owner_user).order_by('name')
        options.extend(
            {'id': f'owner_{c.id}', 'name': f'{c.name} (Private)', 'scope': 'private'}
            for c in private_categories
        )
    return options


def _build_visible_source_options(user):
    options = [{'id': str(s.id), 'name': s.name, 'scope': 'global'} for s in Source.objects.all()]
    owner_user = _get_effective_owner(user)
    if owner_user:
        private_sources = OwnerSource.objects.filter(owner=owner_user).order_by('name')
        options.extend(
            {'id': f'owner_{s.id}', 'name': f'{s.name} (Private)', 'scope': 'private'}
            for s in private_sources
        )
    return options


def _resolve_category_selection(user, category_choice, category_other):
    category_choice = (category_choice or '').strip()
    category_other = (category_other or '').strip()

    if not category_choice:
        return None, '', None

    if category_choice == 'other':
        return None, category_other, None

    if category_choice.startswith('owner_'):
        owner_user = _get_effective_owner(user)
        if not owner_user:
            return None, '', 'Private category is not available for this account.'
        owner_id = category_choice.split('owner_', 1)[1]
        private_category = OwnerCategory.objects.filter(owner=owner_user, id=owner_id).first()
        if not private_category:
            return None, '', 'Selected private category is invalid.'
        return None, private_category.name, None

    try:
        global_category = Category.objects.get(id=int(category_choice))
        return global_category, '', None
    except (ValueError, Category.DoesNotExist):
        return None, '', 'Selected category is invalid.'


def _resolve_source_selection(user, source_choice, source_other):
    source_choice = (source_choice or '').strip()
    source_other = (source_other or '').strip()

    if not source_choice:
        return None, '', None

    if source_choice == 'other':
        return None, source_other, None

    if source_choice.startswith('owner_'):
        owner_user = _get_effective_owner(user)
        if not owner_user:
            return None, '', 'Private source is not available for this account.'
        owner_id = source_choice.split('owner_', 1)[1]
        private_source = OwnerSource.objects.filter(owner=owner_user, id=owner_id).first()
        if not private_source:
            return None, '', 'Selected private source is invalid.'
        return None, private_source.name, None

    try:
        global_source = Source.objects.get(id=int(source_choice))
        return global_source, '', None
    except (ValueError, Source.DoesNotExist):
        return None, '', 'Selected source is invalid.'


TEAM_STATUS_COLORS = [
    '#0d6efd',
    '#20c997',
    '#ffc107',
    '#fd7e14',
    '#6f42c1',
    '#dc3545',
    '#198754',
    '#6c757d',
]


def _build_team_status_metrics(qs):
    aggregates = {'total': Count('id')}
    for status_key, _ in Lead.STATUS_CHOICES:
        aggregates[status_key] = Count('id', filter=Q(status=status_key))

    status_counts = qs.aggregate(**aggregates)
    metrics = {status_key: status_counts.get(status_key) or 0 for status_key, _ in Lead.STATUS_CHOICES}
    return {
        'total': status_counts.get('total') or 0,
        'statuses': metrics,
    }


def _team_stacked_status_payload(qs, name):
    metrics = _build_team_status_metrics(qs)
    payload = {
        'name': name,
        'total': metrics['total'],
        'statuses': metrics['statuses'],
    }
    payload.update(metrics['statuses'])
    return payload


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    from billing.models import Plan
    plans = list(Plan.objects.filter(is_active=True))
    _attach_public_plan_pricing(plans)
    return render(request, 'core/home.html', {'plans': plans})


def my_plans_page(request):
    from billing.models import Plan
    plans = list(Plan.objects.filter(is_active=True))
    _attach_public_plan_pricing(plans)
    return render(request, 'core/my_plans_public.html', {'plans': plans})


def privacy_policy(request):
    return render(request, 'core/privacy_policy.html')


def terms_and_conditions(request):
    return render(request, 'core/terms_and_conditions.html')


def support(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()

        if not all([name, email, subject, message_text]):
            messages.error(request, 'Please fill all support form fields.')
            return redirect('support')

        support_subject = f"[LeadSync Support] {subject}"
        support_body = (
            f"Support request from LeadSync website\n\n"
            f"Name: {name}\n"
            f"Email: {email}\n\n"
            f"Message:\n{message_text}\n"
        )

        default_from = (getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip()
        smtp_user_email = (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()

        to_email = smtp_user_email
        try:
            validate_email(to_email)
        except ValidationError:
            to_email = ''

        if not to_email:
            _, parsed_default_email = parseaddr(default_from)
            try:
                validate_email(parsed_default_email)
                to_email = parsed_default_email
            except ValidationError:
                to_email = email

        _, parsed_from_email = parseaddr(default_from)
        try:
            validate_email(parsed_from_email)
            from_email = default_from
        except ValidationError:
            from_email = to_email

        try:
            send_mail(
                subject=support_subject,
                message=support_body,
                from_email=from_email,
                recipient_list=[to_email],
                fail_silently=False,
            )
            messages.success(request, 'Support request sent successfully. Our team will contact you soon.')
        except Exception:
            logger.exception('Support request email failed to send.')
            messages.error(request, 'Support request could not be sent right now. Please try again shortly.')

        return redirect('support')

    return render(request, 'core/support.html')


def _get_staff_team_member(user):
    if getattr(user.profile, 'role', '') != 'staff':
        return None

    return (
        TeamMember.objects
        .filter(staff=user, is_removed=False)
        .select_related('boss', 'boss__profile')
        .first()
    )


def _get_chat_access_blocked_reason(user):
    profile = getattr(user, 'profile', None)
    if not profile:
        return 'Chat is not available for this account.'

    if profile.role == 'super_admin':
        return ''

    if not profile.is_approved:
        if profile.role == 'staff':
            return 'Your employee account is pending approval. Chat will be available after approval.'
        if profile.role == 'owner':
            return 'Your business owner account is pending approval. Chat will be available after approval.'
        return 'Chat is not available for this account.'

    if profile.role != 'staff':
        return ''

    team_member = _get_staff_team_member(user)
    if not team_member:
        return 'Your employee account is not linked to an active business owner.'

    if not team_member.is_active:
        return 'Chat is unavailable because your employee account is inactive.'

    from billing.models import Subscription

    owner_subscription = Subscription.objects.filter(owner=team_member.boss, is_active=True).first()
    if not owner_subscription:
        return 'Chat is unavailable because your business owner does not have an active plan.'

    return ''


def _touch_chat_presence(user):
    if not getattr(user, 'is_authenticated', False):
        return
    ChatPresence.objects.update_or_create(user=user, defaults={})


def _get_online_user_ids(user_ids):
    user_ids = [uid for uid in set(user_ids) if uid]
    if not user_ids:
        return set()

    threshold = timezone.now() - timedelta(seconds=CHAT_ONLINE_WINDOW_SECONDS)
    return set(
        ChatPresence.objects.filter(
            user_id__in=user_ids,
            last_seen_at__gte=threshold,
        ).values_list('user_id', flat=True)
    )


def _display_user_name(user):
    return user.get_full_name().strip() or user.username


def _build_direct_presence_payload(contact):
    is_online = contact.id in _get_online_user_ids([contact.id])
    return {
        'is_online': is_online,
        'label': 'Online' if is_online else 'Offline',
    }


def _build_group_presence_payload(group):
    memberships = list(group.memberships.all())
    member_ids = [membership.user_id for membership in memberships]
    online_ids = _get_online_user_ids(member_ids)
    online_members = [
        _display_user_name(membership.user)
        for membership in memberships
        if membership.user_id in online_ids
    ]
    return {
        'online_count': len(online_members),
        'member_count': len(member_ids),
        'online_members': online_members,
        'label': f'{len(online_members)}/{len(member_ids)} online' if member_ids else '0 online',
    }


def _build_group_receipt_summary(receipts):
    receipt_list = list(receipts)
    recipient_count = len(receipt_list)
    delivered_names = [_display_user_name(receipt.recipient) for receipt in receipt_list if receipt.delivered_at]
    seen_names = [_display_user_name(receipt.recipient) for receipt in receipt_list if receipt.seen_at]
    return {
        'recipient_count': recipient_count,
        'delivered_count': len(delivered_names),
        'delivered_names': delivered_names,
        'seen_count': len(seen_names),
        'seen_names': seen_names,
    }


def _serialize_group_message(message, current_user):
    payload = {
        'id': message.id,
        'sender_id': message.sender_id,
        'sender_name': _display_user_name(message.sender),
        'body': message.body,
        'created_at': timezone.localtime(message.created_at).strftime('%I:%M %p'),
    }

    if message.sender_id == current_user.id:
        payload.update(_build_group_receipt_summary(message.receipts.all()))

    return payload


def _attach_group_receipt_summary(messages, current_user):
    for message in messages:
        summary = _build_group_receipt_summary(message.receipts.all()) if message.sender_id == current_user.id else {}
        message.recipient_count = summary.get('recipient_count', 0)
        message.delivered_count = summary.get('delivered_count', 0)
        message.delivered_names = summary.get('delivered_names', [])
        message.seen_count = summary.get('seen_count', 0)
        message.seen_names = summary.get('seen_names', [])


def _mark_group_messages_seen(group, user):
    seen_at = timezone.now()
    ChatGroupMessageReceipt.objects.filter(
        message__group=group,
        recipient=user,
        seen_at__isnull=True,
    ).exclude(
        message__sender=user,
    ).update(seen_at=seen_at)


def _create_group_message_with_receipts(group, sender, body):
    message = ChatGroupMessage.objects.create(
        group=group,
        sender=sender,
        body=body,
    )

    recipient_ids = list(
        group.memberships.exclude(user=sender).values_list('user_id', flat=True)
    )
    ChatGroupMessageReceipt.objects.bulk_create([
        ChatGroupMessageReceipt(message=message, recipient_id=recipient_id)
        for recipient_id in recipient_ids
    ])
    return message


def _get_chat_contacts(user):
    profile = getattr(user, 'profile', None)
    if not profile:
        return User.objects.none()

    if profile.role == 'super_admin':
        return User.objects.filter(
            profile__role='owner',
            profile__is_approved=True,
            is_active=True,
        ).exclude(id=user.id).order_by('first_name', 'username')

    if profile.role == 'owner':
        super_admins = User.objects.filter(
            profile__role='super_admin',
            is_active=True,
        ).exclude(id=user.id)
        # Include all non-removed employees so a newly added employee appears immediately.
        owner_staff = User.objects.filter(
            team_boss__boss=user,
            team_boss__is_removed=False,
            is_active=True,
        ).exclude(id=user.id)
        return (super_admins | owner_staff).distinct().order_by('first_name', 'username')

    if profile.role == 'staff' and not _get_chat_access_blocked_reason(user):
        team_member = _get_staff_team_member(user)
        if not team_member:
            return User.objects.none()

        owner_qs = User.objects.filter(id=team_member.boss_id, is_active=True)
        active_staff = User.objects.filter(
            team_boss__boss=team_member.boss,
            team_boss__is_active=True,
            team_boss__is_removed=False,
            is_active=True,
        ).exclude(id=user.id)
        return (owner_qs | active_staff).distinct().order_by('first_name', 'username')

    return User.objects.none()


def _get_direct_notice(current_user, contact):
    current_profile = getattr(current_user, 'profile', None)
    contact_profile = getattr(contact, 'profile', None)
    if not current_profile or not contact_profile:
        return ''

    if current_profile.role == 'owner' and contact_profile.role == 'staff':
        relation = TeamMember.objects.filter(
            boss=current_user,
            staff=contact,
            is_removed=False,
        ).first()
        if relation and not relation.is_active:
            return 'This employee is inactive. They cannot view chat messages or reply.'

    return ''


def _build_contact_items(current_user, contacts):
    items = []
    online_user_ids = _get_online_user_ids([contact.id for contact in contacts])
    for contact in contacts:
        last_message = DirectMessage.objects.filter(
            Q(sender=current_user, recipient=contact) |
            Q(sender=contact, recipient=current_user)
        ).order_by('-created_at').first()

        unread_count = DirectMessage.objects.filter(
            sender=contact,
            recipient=current_user,
            read_at__isnull=True,
        ).count()

        display_name = contact.get_full_name().strip() or contact.username
        direct_notice = _get_direct_notice(current_user, contact)
        items.append({
            'user': contact,
            'display_name': display_name,
            'last_message': last_message,
            'unread_count': unread_count,
            'direct_notice': direct_notice,
            'is_online': contact.id in online_user_ids,
        })

    items.sort(
        key=lambda item: item['last_message'].created_at.timestamp() if item['last_message'] else -1,
        reverse=True,
    )
    return items


def _get_contact_map(user):
    contacts = list(_get_chat_contacts(user))
    return contacts, {u.id: u for u in contacts}


def _get_chat_groups(user):
    profile = getattr(user, 'profile', None)
    if not profile:
        return []

    if profile.role == 'owner':
        return list(
            ChatGroup.objects.filter(owner=user)
            .prefetch_related('memberships__user')
            .order_by('-created_at')
        )

    if profile.role == 'staff' and not _get_chat_access_blocked_reason(user):
        return list(
            ChatGroup.objects.filter(memberships__user=user).distinct()
            .prefetch_related('memberships__user')
            .order_by('-created_at')
        )

    return []


def _build_group_items(current_user, groups):
    items = []
    all_member_ids = []
    for group in groups:
        all_member_ids.extend(membership.user_id for membership in group.memberships.all())
    online_user_ids = _get_online_user_ids(all_member_ids)

    for group in groups:
        last_message = ChatGroupMessage.objects.filter(group=group).order_by('-created_at').first()
        memberships = list(group.memberships.all())
        member_ids = [membership.user_id for membership in memberships]
        items.append({
            'group': group,
            'display_name': group.name,
            'member_count': len(member_ids),
            'last_message': last_message,
            'online_member_count': sum(1 for member_id in member_ids if member_id in online_user_ids),
        })

    items.sort(
        key=lambda item: item['last_message'].created_at.timestamp() if item['last_message'] else -1,
        reverse=True,
    )
    return items


def _get_group_map(user):
    groups = _get_chat_groups(user)
    return groups, {g.id: g for g in groups}


@login_required
def chat_screen(request, user_id=None, group_id=None):
    _touch_chat_presence(request.user)

    contacts, contact_map = _get_contact_map(request.user)
    contact_ids = set(contact_map.keys())
    groups, group_map = _get_group_map(request.user)
    group_ids = set(group_map.keys())
    chat_access_blocked_reason = _get_chat_access_blocked_reason(request.user)

    selected_user = None
    selected_group = None
    direct_notice = ''
    selected_presence = {'label': ''}
    if user_id is not None:
        if user_id not in contact_ids:
            return HttpResponseForbidden('You are not allowed to chat with this user.')
        selected_user = contact_map.get(user_id)
        direct_notice = _get_direct_notice(request.user, selected_user)
        selected_presence = _build_direct_presence_payload(selected_user)
    if group_id is not None:
        if group_id not in group_ids:
            return HttpResponseForbidden('You are not allowed to access this group chat.')
        selected_group = group_map.get(group_id)
        selected_presence = _build_group_presence_payload(selected_group)

    if request.method == 'POST':
        if request.POST.get('chat_action') == 'create_group':
            return _handle_group_create(request)

        selected_id = request.POST.get('selected_user_id')
        selected_group_id = request.POST.get('selected_group_id')
        message_body = request.POST.get('message', '').strip()

        if chat_access_blocked_reason:
            messages.error(request, chat_access_blocked_reason)
            return redirect('chat_screen')

        if selected_group_id:
            if not selected_group_id.isdigit() or int(selected_group_id) not in group_ids:
                messages.error(request, 'Invalid group selected.')
                return redirect('chat_screen')

            selected_group_id_int = int(selected_group_id)
            if not message_body:
                messages.error(request, 'Please enter a message before sending.')
                return redirect('chat_with_group', group_id=selected_group_id_int)

            group = group_map.get(selected_group_id_int)
            _create_group_message_with_receipts(group, request.user, message_body)
            return redirect('chat_with_group', group_id=selected_group_id_int)

        if not selected_id or not selected_id.isdigit() or int(selected_id) not in contact_ids:
            messages.error(request, 'Invalid chat recipient.')
            return redirect('chat_screen')

        selected_id_int = int(selected_id)
        if not message_body:
            messages.error(request, 'Please enter a message before sending.')
            return redirect('chat_with_user', user_id=selected_id_int)

        recipient = contact_map.get(selected_id_int)
        if not recipient:
            return HttpResponseForbidden('You are not allowed to chat with this user.')

        DirectMessage.objects.create(
            sender=request.user,
            recipient=recipient,
            body=message_body,
        )
        return redirect('chat_with_user', user_id=recipient.id)

    messages_qs = DirectMessage.objects.none()
    group_messages_qs = ChatGroupMessage.objects.none()
    latest_seen_outgoing_id = None
    if selected_user:
        messages_qs = DirectMessage.objects.filter(
            Q(sender=request.user, recipient=selected_user) |
            Q(sender=selected_user, recipient=request.user)
        ).select_related('sender', 'recipient').order_by('created_at')

        DirectMessage.objects.filter(
            sender=selected_user,
            recipient=request.user,
            read_at__isnull=True,
        ).update(read_at=timezone.now())

        latest_seen_outgoing = DirectMessage.objects.filter(
            sender=request.user,
            recipient=selected_user,
            read_at__isnull=False,
        ).order_by('-id').first()
        latest_seen_outgoing_id = latest_seen_outgoing.id if latest_seen_outgoing else None

    if selected_group:
        _mark_group_messages_seen(selected_group, request.user)
        group_messages_qs = list(
            ChatGroupMessage.objects.filter(group=selected_group)
            .select_related('sender')
            .prefetch_related(
                Prefetch(
                    'receipts',
                    queryset=ChatGroupMessageReceipt.objects.select_related('recipient').order_by('recipient__first_name', 'recipient__username'),
                )
            )
            .order_by('created_at')
        )
        _attach_group_receipt_summary(group_messages_qs, request.user)

    available_group_members = []
    if getattr(request.user.profile, 'role', '') == 'owner':
        available_group_members = User.objects.filter(
            team_boss__boss=request.user,
            team_boss__is_active=True,
            team_boss__is_removed=False,
            is_active=True,
        ).exclude(id=request.user.id).order_by('first_name', 'username')

    context = {
        'chat_contacts': _build_contact_items(request.user, contacts),
        'chat_groups': _build_group_items(request.user, groups),
        'selected_user': selected_user,
        'selected_group': selected_group,
        'selected_chat_type': 'group' if selected_group else ('direct' if selected_user else ''),
        'chat_messages': messages_qs,
        'group_messages': group_messages_qs,
        'latest_seen_outgoing_id': latest_seen_outgoing_id,
        'direct_notice': direct_notice,
        'selected_presence_label': selected_presence['label'],
        'chat_access_blocked_reason': chat_access_blocked_reason,
        'available_group_members': available_group_members,
    }
    return render(request, 'core/chat_screen.html', context)


@login_required
@require_POST
def _handle_group_create(request):
    if getattr(request.user.profile, 'role', '') != 'owner':
        messages.error(request, 'Only business owners can create employee groups.')
        return redirect('chat_screen')

    group_name = (request.POST.get('group_name') or '').strip()
    member_ids = request.POST.getlist('member_ids')
    member_ids = [int(mid) for mid in member_ids if mid.isdigit()]

    if len(member_ids) < 2:
        messages.error(request, 'Select at least 2 active employees to create a group.')
        return redirect('chat_screen')

    employees = list(User.objects.filter(
        id__in=member_ids,
        team_boss__boss=request.user,
        team_boss__is_active=True,
        team_boss__is_removed=False,
        is_active=True,
    ).distinct())

    if len(employees) < 2:
        messages.error(request, 'Group members must be your active employees only.')
        return redirect('chat_screen')

    if not group_name:
        group_name = 'Team Group'

    group = ChatGroup.objects.create(owner=request.user, name=group_name)
    ChatGroupMember.objects.create(group=group, user=request.user)
    ChatGroupMember.objects.bulk_create([
        ChatGroupMember(group=group, user=employee)
        for employee in employees
    ])

    messages.success(request, 'Group created successfully.')
    return redirect('chat_with_group', group_id=group.id)


@login_required
def chat_thread_updates(request, user_id):
    _touch_chat_presence(request.user)

    blocked_reason = _get_chat_access_blocked_reason(request.user)
    if blocked_reason:
        return JsonResponse({'error': 'forbidden', 'reason': blocked_reason}, status=403)

    _, contact_map = _get_contact_map(request.user)
    selected_user = contact_map.get(user_id)
    if not selected_user:
        return JsonResponse({'error': 'forbidden'}, status=403)

    try:
        after_id = int(request.GET.get('after_id', '0'))
    except (TypeError, ValueError):
        after_id = 0

    DirectMessage.objects.filter(
        sender=selected_user,
        recipient=request.user,
        read_at__isnull=True,
    ).update(read_at=timezone.now())

    new_messages = DirectMessage.objects.filter(
        Q(sender=request.user, recipient=selected_user) |
        Q(sender=selected_user, recipient=request.user),
        id__gt=after_id,
    ).select_related('sender').order_by('id')

    latest_seen_outgoing = DirectMessage.objects.filter(
        sender=request.user,
        recipient=selected_user,
        read_at__isnull=False,
    ).order_by('-id').first()

    typing_window_start = timezone.now() - timedelta(seconds=8)
    peer_typing = ChatTypingStatus.objects.filter(
        user=selected_user,
        peer=request.user,
        is_typing=True,
        updated_at__gte=typing_window_start,
    ).exists()
    peer_is_online = selected_user.id in _get_online_user_ids([selected_user.id])

    payload = {
        'messages': [
            {
                'id': msg.id,
                'sender_id': msg.sender_id,
                'body': msg.body,
                'created_at': timezone.localtime(msg.created_at).strftime('%I:%M %p'),
            }
            for msg in new_messages
        ],
        'peer_typing': peer_typing,
        'latest_seen_outgoing_id': latest_seen_outgoing.id if latest_seen_outgoing else None,
        'direct_notice': _get_direct_notice(request.user, selected_user),
        'peer_online': peer_is_online,
        'presence_label': 'Online' if peer_is_online else 'Offline',
    }
    return JsonResponse(payload)


@login_required
def chat_group_updates(request, group_id):
    _touch_chat_presence(request.user)

    blocked_reason = _get_chat_access_blocked_reason(request.user)
    if blocked_reason:
        return JsonResponse({'error': 'forbidden', 'reason': blocked_reason}, status=403)

    _, group_map = _get_group_map(request.user)
    selected_group = group_map.get(group_id)
    if not selected_group:
        return JsonResponse({'error': 'forbidden'}, status=403)

    try:
        after_id = int(request.GET.get('after_id', '0'))
    except (TypeError, ValueError):
        after_id = 0

    _mark_group_messages_seen(selected_group, request.user)

    receipt_prefetch = Prefetch(
        'receipts',
        queryset=ChatGroupMessageReceipt.objects.select_related('recipient').order_by('recipient__first_name', 'recipient__username'),
    )
    new_messages = (
        ChatGroupMessage.objects.filter(
            group=selected_group,
            id__gt=after_id,
        )
        .select_related('sender')
        .prefetch_related(receipt_prefetch)
        .order_by('id')
    )
    receipt_updates = (
        ChatGroupMessage.objects.filter(
            group=selected_group,
            sender=request.user,
        )
        .select_related('sender')
        .prefetch_related(receipt_prefetch)
        .order_by('id')
    )
    group_presence = _build_group_presence_payload(selected_group)

    payload = {
        'messages': [_serialize_group_message(msg, request.user) for msg in new_messages],
        'receipt_updates': [_serialize_group_message(msg, request.user) for msg in receipt_updates],
        'presence_label': group_presence['label'],
        'online_member_count': group_presence['online_count'],
        'member_count': group_presence['member_count'],
    }
    return JsonResponse(payload)


@login_required
@require_POST
def chat_typing_status(request):
    _touch_chat_presence(request.user)

    blocked_reason = _get_chat_access_blocked_reason(request.user)
    if blocked_reason:
        return JsonResponse({'error': 'forbidden', 'reason': blocked_reason}, status=403)

    recipient_id = request.POST.get('recipient_id')
    if not recipient_id or not recipient_id.isdigit():
        return JsonResponse({'error': 'invalid recipient'}, status=400)

    recipient_id_int = int(recipient_id)
    _, contact_map = _get_contact_map(request.user)
    recipient = contact_map.get(recipient_id_int)
    if not recipient:
        return JsonResponse({'error': 'forbidden'}, status=403)

    raw_is_typing = (request.POST.get('is_typing') or '').strip().lower()
    is_typing = raw_is_typing in ('1', 'true', 'yes', 'on')

    ChatTypingStatus.objects.update_or_create(
        user=request.user,
        peer=recipient,
        defaults={'is_typing': is_typing},
    )
    return JsonResponse({'ok': True})


@login_required
@require_POST
def chat_send_message(request):
    _touch_chat_presence(request.user)

    blocked_reason = _get_chat_access_blocked_reason(request.user)
    if blocked_reason:
        return JsonResponse({'error': 'forbidden', 'reason': blocked_reason}, status=403)

    recipient_id = request.POST.get('recipient_id')
    message_body = (request.POST.get('message') or '').strip()

    if not recipient_id or not recipient_id.isdigit():
        return JsonResponse({'error': 'invalid recipient'}, status=400)

    if not message_body:
        return JsonResponse({'error': 'empty message'}, status=400)

    recipient_id_int = int(recipient_id)
    _, contact_map = _get_contact_map(request.user)
    recipient = contact_map.get(recipient_id_int)
    if not recipient:
        return JsonResponse({'error': 'forbidden'}, status=403)

    message = DirectMessage.objects.create(
        sender=request.user,
        recipient=recipient,
        body=message_body,
    )

    return JsonResponse({
        'message': {
            'id': message.id,
            'sender_id': message.sender_id,
            'sender_name': (request.user.get_full_name().strip() or request.user.username),
            'body': message.body,
            'created_at': timezone.localtime(message.created_at).strftime('%I:%M %p'),
            'status': 'Delivered',
        }
    })


@login_required
@require_POST
def chat_send_group_message(request):
    _touch_chat_presence(request.user)

    blocked_reason = _get_chat_access_blocked_reason(request.user)
    if blocked_reason:
        return JsonResponse({'error': 'forbidden', 'reason': blocked_reason}, status=403)

    group_id = request.POST.get('group_id')
    message_body = (request.POST.get('message') or '').strip()

    if not group_id or not group_id.isdigit():
        return JsonResponse({'error': 'invalid group'}, status=400)

    if not message_body:
        return JsonResponse({'error': 'empty message'}, status=400)

    group_id_int = int(group_id)
    _, group_map = _get_group_map(request.user)
    group = group_map.get(group_id_int)
    if not group:
        return JsonResponse({'error': 'forbidden'}, status=403)

    message = _create_group_message_with_receipts(group, request.user, message_body)
    message = (
        ChatGroupMessage.objects.filter(id=message.id)
        .select_related('sender')
        .prefetch_related(
            Prefetch(
                'receipts',
                queryset=ChatGroupMessageReceipt.objects.select_related('recipient').order_by('recipient__first_name', 'recipient__username'),
            )
        )
        .first()
    )

    return JsonResponse({
        'message': _serialize_group_message(message, request.user),
    })


@login_required
def dashboard(request):
    user = request.user
    profile = user.profile
    print_mode = request.GET.get('print') == '1'
    dashboard_line_tf = _get_query_choice(request, 'line_tf', {'all', 'today', 'week', '7d', '15d', '30d', '90d'}, '7d')
    dashboard_pie_tf = _get_query_choice(request, 'pie_tf', {'all', 'today', 'week', '7d', '15d', '30d', '90d'}, '7d')
    dashboard_col_tf = _get_query_choice(request, 'col_tf', {'all', 'today', 'week', '7d', '15d', '30d', '90d'}, '7d')
    status_sort_keys = {status_key for status_key, _ in Lead.STATUS_CHOICES}
    dashboard_col_sort = _get_query_choice(request, 'col_sort', {'total', 'name', *status_sort_keys}, 'total')

    # Get leads based on role with optimized queries
    leads = get_user_leads(user)

    # Apply filters
    form = LeadFilterForm(request.GET)
    if form.is_valid():
        category = form.cleaned_data.get('category')
        source = form.cleaned_data.get('source')
        status = form.cleaned_data.get('status')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

        if category:
            leads = leads.filter(category=category)
        if source:
            leads = leads.filter(source=source)
        if status:
            leads = leads.filter(status=status)
        if start_date:
            leads = leads.filter(created_at__date__gte=start_date)
        if end_date:
            leads = leads.filter(created_at__date__lte=end_date)

    # Get statistics with a single query
    stats = leads.aggregate(
        total=Count('id'),
        new=Count('id', filter=Q(status='new')),
        contacted=Count('id', filter=Q(status='contacted')),
        won=Count('id', filter=Q(status='won'))
    )

    # Get leads by status for chart with single query
    status_counts = leads.values('status').annotate(count=Count('id'))
    status_data = {item['status']: item['count'] for item in status_counts}

    today = timezone.now().date()

    # Main card values should always represent today's activity.
    today_total_leads = leads.filter(created_at__date=today).count()
    today_new_leads = leads.filter(created_at__date=today, status='new').count()
    today_won_leads = leads.filter(created_at__date=today, status='won').count()
    today_followups = leads.filter(follow_up_date=today).count()

    # Dropdown period values: total, last 7 days, last 30 days.
    last_7_start = today - timedelta(days=6)
    last_30_start = today - timedelta(days=29)

    stat_period_counts = {
        'total': {
            'total': stats['total'],
            '7d': leads.filter(created_at__date__gte=last_7_start, created_at__date__lte=today).count(),
            '30d': leads.filter(created_at__date__gte=last_30_start, created_at__date__lte=today).count(),
        },
        'new': {
            'total': leads.filter(status='new').count(),
            '7d': leads.filter(status='new', created_at__date__gte=last_7_start, created_at__date__lte=today).count(),
            '30d': leads.filter(status='new', created_at__date__gte=last_30_start, created_at__date__lte=today).count(),
        },
        'won': {
            'total': leads.filter(status='won').count(),
            '7d': leads.filter(status='won', created_at__date__gte=last_7_start, created_at__date__lte=today).count(),
            '30d': leads.filter(status='won', created_at__date__gte=last_30_start, created_at__date__lte=today).count(),
        },
        'followups': {
            'total': leads.filter(follow_up_date__isnull=False).count(),
            '7d': leads.filter(follow_up_date__gte=last_7_start, follow_up_date__lte=today).count(),
            '30d': leads.filter(follow_up_date__gte=last_30_start, follow_up_date__lte=today).count(),
        },
    }

    # Percentage change by selected period (7d/30d); keep 0 when previous window is empty.
    prev_7_start = today - timedelta(days=13)
    prev_7_end = today - timedelta(days=7)
    prev_30_start = today - timedelta(days=59)
    prev_30_end = today - timedelta(days=30)

    def _pct_change(curr, prev):
        if prev <= 0:
            return 0.0
        return round(((curr - prev) / prev) * 100, 1)

    prev_period_counts = {
        'total': {
            '7d': leads.filter(created_at__date__gte=prev_7_start, created_at__date__lte=prev_7_end).count(),
            '30d': leads.filter(created_at__date__gte=prev_30_start, created_at__date__lte=prev_30_end).count(),
        },
        'new': {
            '7d': leads.filter(status='new', created_at__date__gte=prev_7_start, created_at__date__lte=prev_7_end).count(),
            '30d': leads.filter(status='new', created_at__date__gte=prev_30_start, created_at__date__lte=prev_30_end).count(),
        },
        'won': {
            '7d': leads.filter(status='won', created_at__date__gte=prev_7_start, created_at__date__lte=prev_7_end).count(),
            '30d': leads.filter(status='won', created_at__date__gte=prev_30_start, created_at__date__lte=prev_30_end).count(),
        },
        'followups': {
            '7d': leads.filter(follow_up_date__gte=prev_7_start, follow_up_date__lte=prev_7_end).count(),
            '30d': leads.filter(follow_up_date__gte=prev_30_start, follow_up_date__lte=prev_30_end).count(),
        },
    }

    stat_period_pcts = {
        metric: {
            'total': 0.0,
            '7d': _pct_change(stat_period_counts[metric]['7d'], prev_period_counts[metric]['7d']),
            '30d': _pct_change(stat_period_counts[metric]['30d'], prev_period_counts[metric]['30d']),
        }
        for metric in stat_period_counts.keys()
    }

    # Mini-stats for cards: Today, Week, Month values for each metric
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=6)
    month_start = today - timedelta(days=29)

    # Total Leads mini-stats
    total_today = leads.filter(created_at__date=today).count()
    total_week = leads.filter(created_at__date__gte=week_start, created_at__date__lte=today).count()
    total_month = leads.filter(created_at__date__gte=month_start, created_at__date__lte=today).count()
    total_all = leads.count()

    # New Leads mini-stats
    new_today = leads.filter(created_at__date=today, status='new').count()
    new_week = leads.filter(created_at__date__gte=week_start, created_at__date__lte=today, status='new').count()
    new_month = leads.filter(created_at__date__gte=month_start, created_at__date__lte=today, status='new').count()
    new_all = leads.filter(status='new').count()

    # Won Leads mini-stats
    won_today = leads.filter(created_at__date=today, status='won').count()
    won_week = leads.filter(created_at__date__gte=week_start, created_at__date__lte=today, status='won').count()
    won_month = leads.filter(created_at__date__gte=month_start, created_at__date__lte=today, status='won').count()
    won_all = leads.filter(status='won').count()

    # Follow-ups mini-stats
    followup_today = leads.filter(follow_up_date=today).count()
    followup_week = leads.filter(follow_up_date__gte=week_start, follow_up_date__lte=today).count()
    followup_month = leads.filter(follow_up_date__gte=month_start, follow_up_date__lte=today).count()
    followup_all = leads.filter(follow_up_date__isnull=False).count()

    # Social Media Stats: each card should only track its own platform.
    # Match against source/category names and "other" text fields so custom entries also work.
    platform_terms = {
        'facebook': ['facebook', 'fb'],
        'instagram': ['instagram', 'insta'],
        'whatsapp': ['whatsapp', 'wa'],
        'linkedin': ['linkedin', 'linked in'],
    }

    social_stats = {}
    for platform, terms in platform_terms.items():
        platform_filter = Q()
        for term in terms:
            platform_filter |= Q(source__name__icontains=term)
            platform_filter |= Q(source_other__icontains=term)
            platform_filter |= Q(category__name__icontains=term)
            platform_filter |= Q(category_other__icontains=term)

        platform_leads = leads.filter(platform_filter).distinct()
        social_stats[platform] = {
            'today': platform_leads.filter(created_at__date=today).count(),
            'week': platform_leads.filter(created_at__date__gte=week_start, created_at__date__lte=today).count(),
            'month': platform_leads.filter(created_at__date__gte=month_start, created_at__date__lte=today).count(),
            'total': platform_leads.count(),
            'engagement_today': platform_leads.filter(created_at__date=today, status='contacted').count(),
            'engagement_week': platform_leads.filter(created_at__date__gte=week_start, created_at__date__lte=today, status='contacted').count(),
            'engagement_month': platform_leads.filter(created_at__date__gte=month_start, created_at__date__lte=today, status='contacted').count(),
        }

    # Donut Chart: Leads this week (Mon-Sun)
    week_start_donut = today - timedelta(days=today.weekday())
    week_day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    week_leads_data = []
    week_day_labels = []
    for i in range(7):
        d = week_start_donut + timedelta(days=i)
        count = leads.filter(created_at__date=d).count() if d <= today else 0
        week_leads_data.append(count)
        week_day_labels.append(week_day_names[i])

    context = {
        'leads': leads[:10],
        'form': form,
        'user_role': profile.role,
        # Stat cards
        'today_total_leads': today_total_leads,
        'today_new_leads': today_new_leads,
        'today_won_leads': today_won_leads,
        'today_followups': today_followups,
        # Mini-stats for cards
        'total_mini_stats': {'today': total_today, 'week': total_week, 'month': total_month, 'total': total_all},
        'new_mini_stats': {'today': new_today, 'week': new_week, 'month': new_month, 'total': new_all},
        'won_mini_stats': {'today': won_today, 'week': won_week, 'month': won_month, 'total': won_all},
        'followup_mini_stats': {'today': followup_today, 'week': followup_week, 'month': followup_month, 'total': followup_all},
        # Social media stats
        'fb_stats': social_stats.get('facebook', {'today': 0, 'week': 0, 'month': 0, 'total': 0}),
        'insta_stats': social_stats.get('instagram', {'today': 0, 'week': 0, 'month': 0, 'total': 0}),
        'whatsapp_stats': social_stats.get('whatsapp', {'today': 0, 'week': 0, 'month': 0, 'total': 0}),
        'linkedin_stats': social_stats.get('linkedin', {'today': 0, 'week': 0, 'month': 0, 'total': 0}),
        'stat_period_counts_json': json.dumps(stat_period_counts),
        'stat_period_pcts_json': json.dumps(stat_period_pcts),
        # Donut chart
        'week_day_labels_json': json.dumps(week_day_labels),
        'week_leads_data_json': json.dumps(week_leads_data),
        'print_mode': print_mode,
        'dashboard_line_tf': dashboard_line_tf,
        'dashboard_pie_tf': dashboard_pie_tf,
        'dashboard_col_tf': dashboard_col_tf,
        'dashboard_col_sort': dashboard_col_sort,
    }

    return render(request, 'core/dashboard.html', context)


@login_required
def dashboard_chart_data(request):
    """AJAX endpoint: returns chart data for any timeframe."""
    timeframe = request.GET.get('timeframe', '7d')
    today = timezone.now().date()

    leads = get_user_leads(request.user)

    if timeframe == 'all':
        first_created = leads.order_by('created_at').values_list('created_at', flat=True).first()
        start = first_created.date() if first_created else today
    elif timeframe == 'today':
        start = today
        days = 0
    elif timeframe == 'week':
        start = today - timedelta(days=today.weekday())  # Monday
        days = (today - start).days
    else:
        days_map = {'7d': 7, '15d': 15, '30d': 30, '90d': 90}
        days = days_map.get(timeframe, 7)
        start = today - timedelta(days=days)

    leads = leads.filter(created_at__date__gte=start)

    dates = []
    lead_counts = []
    conversion_counts = []
    new_counts = []
    contacted_counts = []

    if timeframe == 'today':
        # Hourly buckets (6am-11pm)
        for hour in range(24):
            dates.append(f'{today.strftime("%Y-%m-%d")}T{hour:02d}:00:00')
            lead_counts.append(leads.filter(created_at__hour=hour).count())
            conversion_counts.append(leads.filter(created_at__hour=hour, status='won').count())
            new_counts.append(leads.filter(created_at__hour=hour, status='new').count())
            contacted_counts.append(leads.filter(created_at__hour=hour, status='contacted').count())
        x_format = 'HH:mm'
    else:
        actual_days = (today - start).days
        for i in range(actual_days, -1, -1):
            d = today - timedelta(days=i)
            dates.append(d.strftime('%Y-%m-%d'))
            lead_counts.append(leads.filter(created_at__date=d).count())
            conversion_counts.append(leads.filter(created_at__date=d, status='won').count())
            new_counts.append(leads.filter(created_at__date=d, status='new').count())
            contacted_counts.append(leads.filter(created_at__date=d, status='contacted').count())
        x_format = 'dd MMM'

    total = sum(lead_counts)
    won = sum(conversion_counts)
    new_total = sum(new_counts)
    contacted_total = sum(contacted_counts)

    status_keys = [status_key for status_key, _ in Lead.STATUS_CHOICES]
    status_labels = dict(Lead.STATUS_CHOICES)
    status_breakdown = []
    for status_key in status_keys:
        status_breakdown.append({
            'key': status_key,
            'label': status_labels.get(status_key, status_key.title()),
            'count': leads.filter(status=status_key).count(),
        })

    label_map = {
        'all': 'All Time', 'today': 'Today', 'week': 'This Week', '7d': 'Last 7 Days',
        '15d': 'Last 15 Days', '30d': 'Last 30 Days', '90d': 'Last 90 Days',
    }
    label = label_map.get(timeframe, 'Last 7 Days')

    return JsonResponse({
        'dates': dates,
        'leads': lead_counts,
        'conversions': conversion_counts,
        'new_leads': new_counts,
        'contacted_leads': contacted_counts,
        'total': total,
        'won': won,
        'new_total': new_total,
        'contacted_total': contacted_total,
        'status_breakdown': status_breakdown,
        'label': label,
        'xFormat': x_format,
    })


@login_required
def dashboard_chart_export(request):
    """Export detailed lead data as CSV for the selected timeframe."""
    timeframe = request.GET.get('timeframe', '30d')
    today = timezone.now().date()

    leads = get_user_leads(request.user)

    if timeframe == 'all':
        start = None
    elif timeframe == 'today':
        start = today
    elif timeframe == 'week':
        start = today - timedelta(days=today.weekday())
    else:
        days_map = {'7d': 7, '15d': 15, '30d': 30, '90d': 90}
        days = days_map.get(timeframe, 7)
        start = today - timedelta(days=days)

    filtered = leads.select_related(
        'category', 'source', 'created_by'
    ).order_by('-created_at')
    if start is not None:
        filtered = filtered.filter(created_at__date__gte=start)

    label = {'all': 'AllTime', 'today': 'Today', 'week': 'ThisWeek', '7d': '7Days', '15d': '15Days', '30d': '30Days', '90d': '90Days'}.get(timeframe, '7Days')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="LeadSync_Leads_{label}_{today}.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Client Name', 'Email', 'Contact', 'Status', 'Category', 'Source',
        'Budget', 'Lead Score', 'Follow-up Date', 'Requirement',
        'Notes', 'Created By', 'Created Date',
    ])
    for lead in filtered:
        writer.writerow([
            lead.client_name,
            lead.email or '',
            lead.contact_number or '',
            lead.get_status_display(),
            lead.get_category_display_name(),
            lead.get_source_display_name(),
            lead.budget or '',
            lead.lead_score or '',
            lead.follow_up_date.strftime('%Y-%m-%d') if lead.follow_up_date else '',
            lead.requirement or '',
            lead.notes or '',
            lead.created_by.username if lead.created_by else '',
            lead.created_at.strftime('%Y-%m-%d %H:%M') if lead.created_at else '',
        ])
    return response


@login_required
def export_team_report(request):
    """Export detailed team performance report as CSV."""
    user = request.user
    profile = user.profile
    today = timezone.now().date()
    last_30 = today - timedelta(days=30)
    last_7 = today - timedelta(days=7)

    if profile.role not in ('owner', 'super_admin'):
        return HttpResponse('Permission denied', status=403)

    if profile.role == 'super_admin':
        leads = Lead.objects.filter(deleted_by__isnull=True)
        team_members = TeamMember.objects.filter(is_active=True).select_related('staff', 'staff__profile', 'role', 'boss')
    else:
        staff_ids = list(TeamMember.objects.filter(boss=user).values_list('staff_id', flat=True))
        all_user_ids = [user.id] + staff_ids
        leads = Lead.objects.filter(owner__in=all_user_ids, deleted_by__isnull=True)
        team_members = TeamMember.objects.filter(boss=user, is_active=True).select_related('staff', 'staff__profile', 'role')

    report_type = request.GET.get('type', 'summary')

    if report_type == 'detailed':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="Employee_Leads_Detail_{today}.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Employee', 'Role', 'Client Name', 'Email', 'Contact',
            'Status', 'Category', 'Source', 'Budget', 'Lead Score',
            'Follow-up Date', 'Requirement', 'Notes', 'Created Date',
        ])

        people = []
        if profile.role == 'owner':
            people.append({'user_obj': user, 'label': user.username, 'role': 'Owner'})
        for tm in team_members:
            people.append({'user_obj': tm.staff, 'label': tm.staff.username, 'role': tm.role.name if tm.role else 'Staff'})

        for p in people:
            emp_leads = leads.filter(created_by=p['user_obj']).select_related('category', 'source').order_by('-created_at')
            for lead in emp_leads:
                writer.writerow([
                    p['label'],
                    p['role'],
                    lead.client_name,
                    lead.email or '',
                    lead.contact_number or '',
                    lead.get_status_display(),
                    lead.get_category_display_name(),
                    lead.get_source_display_name(),
                    lead.budget or '',
                    lead.lead_score or '',
                    lead.follow_up_date.strftime('%Y-%m-%d') if lead.follow_up_date else '',
                    lead.requirement or '',
                    lead.notes or '',
                    lead.created_at.strftime('%Y-%m-%d %H:%M') if lead.created_at else '',
                ])
        return response

    # Default: summary report
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Team_Performance_{today}.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Employee', 'Role', 'Total Leads', 'New', 'Contacted', 'Qualified',
        'Won', 'Lost', 'Conversion Rate %', 'Leads (7 Days)',
        'Leads (30 Days)', 'Overdue Follow-ups', 'Today Follow-ups',
    ])

    people = []
    if profile.role == 'owner':
        people.append({'user_obj': user, 'label': user.username, 'role': 'Owner'})
    for tm in team_members:
        people.append({'user_obj': tm.staff, 'label': tm.staff.username, 'role': tm.role.name if tm.role else 'Staff'})

    grand = {'total': 0, 'new': 0, 'contacted': 0, 'qualified': 0, 'won': 0, 'lost': 0, 'l7': 0, 'l30': 0, 'overdue': 0, 'today_fu': 0}

    for p in people:
        u = p['user_obj']
        u_leads = leads.filter(created_by=u)
        s = u_leads.aggregate(
            total=Count('id'),
            new=Count('id', filter=Q(status='new')),
            contacted=Count('id', filter=Q(status='contacted')),
            qualified=Count('id', filter=Q(status='qualified')),
            won=Count('id', filter=Q(status='won')),
            lost=Count('id', filter=Q(status='lost')),
            last_7=Count('id', filter=Q(created_at__date__gte=last_7)),
            last_30=Count('id', filter=Q(created_at__date__gte=last_30)),
            overdue=Count('id', filter=Q(follow_up_date__lt=today, follow_up_date__isnull=False)),
            today_fu=Count('id', filter=Q(follow_up_date=today)),
        )
        t = s['total'] or 0
        w = s['won'] or 0
        cr = round(w / t * 100, 1) if t > 0 else 0
        writer.writerow([
            p['label'], p['role'], t, s['new'] or 0, s['contacted'] or 0,
            s['qualified'] or 0, w, s['lost'] or 0, cr,
            s['last_7'] or 0, s['last_30'] or 0, s['overdue'] or 0, s['today_fu'] or 0,
        ])
        for k in ['total', 'new', 'contacted', 'qualified', 'won', 'lost']:
            grand[k] += s[k] or 0
        grand['l7'] += s['last_7'] or 0
        grand['l30'] += s['last_30'] or 0
        grand['overdue'] += s['overdue'] or 0
        grand['today_fu'] += s['today_fu'] or 0

    gcr = round(grand['won'] / grand['total'] * 100, 1) if grand['total'] > 0 else 0
    writer.writerow([
        'TOTAL', '', grand['total'], grand['new'], grand['contacted'],
        grand['qualified'], grand['won'], grand['lost'], gcr,
        grand['l7'], grand['l30'], grand['overdue'], grand['today_fu'],
    ])

    return response


@login_required
def dashboard_team_data(request):
    """AJAX endpoint: paginated + sorted team performance data."""
    user = request.user
    profile = user.profile
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 5))
    sort_by = request.GET.get('sort', 'total')  # total, won, contacted, name

    leads = get_user_leads(user)
    members = []

    def _member_stats(name, qs):
        t = qs.count()
        w = qs.filter(status='won').count()
        return {
            'name': name,
            'total': t,
            'contacted': qs.filter(status='contacted').count(),
            'won': w,
            'conversion': round(w / t * 100, 1) if t > 0 else 0,
        }

    if profile.role == 'super_admin':
        for u in User.objects.filter(profile__role='owner', profile__is_approved=True):
            members.append(_member_stats(u.username, leads.filter(owner=u)))
    elif profile.role == 'owner':
        members.append(_member_stats(user.username + ' (You)', leads.filter(created_by=user)))
        for tm in TeamMember.objects.filter(boss=user, is_active=True).select_related('staff'):
            members.append(_member_stats(tm.staff.username, leads.filter(created_by=tm.staff)))
    else:
        members.append(_member_stats(user.username, leads.filter(created_by=user)))

    # Sort
    reverse = True
    if sort_by == 'name':
        members.sort(key=lambda x: x['name'].lower())
        reverse = False
    elif sort_by == 'won':
        members.sort(key=lambda x: x['won'], reverse=True)
    elif sort_by == 'contacted':
        members.sort(key=lambda x: x['contacted'], reverse=True)
    else:
        members.sort(key=lambda x: x['total'], reverse=True)

    total_members = len(members)
    total_pages = max(1, (total_members + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    page_members = members[start:start + per_page]

    return JsonResponse({
        'members': page_members,
        'page': page,
        'total_pages': total_pages,
        'total_members': total_members,
        'sort': sort_by,
    })


@login_required
def dashboard_team_stacked_data(request):
    """AJAX endpoint for stacked team status chart with timeframe + pagination + sorting."""
    user = request.user
    profile = user.profile
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 6))
    sort_by = request.GET.get('sort', 'total')  # total, new, contacted, won, lost, name
    timeframe = request.GET.get('timeframe', '7d')
    
    # Get filter parameters from the request
    category_id = request.GET.get('category', '')
    source_id = request.GET.get('source', '')
    status = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    search_query = request.GET.get('search', '')
    
    today = timezone.now().date()

    if timeframe == 'all':
        start = None
    elif timeframe == 'today':
        start = today
    elif timeframe == 'week':
        start = today - timedelta(days=today.weekday())
    else:
        days_map = {'7d': 7, '15d': 15, '30d': 30, '90d': 90}
        days = days_map.get(timeframe, 7)
        start = today - timedelta(days=days)

    leads = get_user_leads(user)
    
    # Apply filters
    if category_id:
        leads = leads.filter(category_id=category_id)
    if source_id:
        leads = leads.filter(source_id=source_id)
    if status:
        leads = leads.filter(status=status)
    if search_query:
        leads = leads.filter(
            Q(client_name__icontains=search_query) |
            Q(contact_number__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(requirement__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            leads = leads.filter(created_at__date__gte=start_date_obj)
        except ValueError:
            pass
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            leads = leads.filter(created_at__date__lte=end_date_obj)
        except ValueError:
            pass
    
    if start is not None:
        leads = leads.filter(created_at__date__gte=start)
    members = []

    status_options = [
        {'key': status_key, 'label': status_label, 'color': TEAM_STATUS_COLORS[index % len(TEAM_STATUS_COLORS)]}
        for index, (status_key, status_label) in enumerate(Lead.STATUS_CHOICES)
    ]

    if profile.role == 'super_admin':
        for owner_user in User.objects.filter(profile__role='owner', profile__is_approved=True):
            members.append(_team_stacked_status_payload(leads.filter(owner=owner_user), owner_user.username))
    elif profile.role == 'owner':
        members.append(_team_stacked_status_payload(leads.filter(created_by=user), user.username + ' (You)'))
        for tm in TeamMember.objects.filter(boss=user, is_active=True).select_related('staff'):
            members.append(_team_stacked_status_payload(leads.filter(created_by=tm.staff), tm.staff.username))
    else:
        members.append(_team_stacked_status_payload(leads.filter(created_by=user), user.username))

    if sort_by == 'name':
        members.sort(key=lambda x: x['name'].lower())
    elif sort_by in dict(Lead.STATUS_CHOICES):
        members.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
    else:
        members.sort(key=lambda x: x['total'], reverse=True)

    total_members = len(members)
    total_pages = max(1, (total_members + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    page_members = members[start_idx:start_idx + per_page]

    label_map = {
        'all': 'All Time',
        'today': 'Today',
        'week': 'This Week',
        '7d': 'Last 7 Days',
        '15d': 'Last 15 Days',
        '30d': 'Last 30 Days',
        '90d': 'Last 90 Days',
    }

    return JsonResponse({
        'members': page_members,
        'page': page,
        'total_pages': total_pages,
        'total_members': total_members,
        'sort': sort_by,
        'timeframe': timeframe,
        'label': label_map.get(timeframe, 'Last 7 Days'),
        'statuses': status_options,
    })


@login_required
def dashboard_team_stacked_export(request):
    """Export stacked team status chart data as CSV with timeframe + sorting."""
    user = request.user
    profile = user.profile
    sort_by = request.GET.get('sort', 'total')
    timeframe = request.GET.get('timeframe', '7d')
    today = timezone.now().date()

    if timeframe == 'all':
        start = None
    elif timeframe == 'today':
        start = today
    elif timeframe == 'week':
        start = today - timedelta(days=today.weekday())
    else:
        days_map = {'7d': 7, '15d': 15, '30d': 30, '90d': 90}
        days = days_map.get(timeframe, 7)
        start = today - timedelta(days=days)

    leads = get_user_leads(user)
    if start is not None:
        leads = leads.filter(created_at__date__gte=start)
    rows = []

    status_options = [
        {'key': status_key, 'label': status_label, 'color': TEAM_STATUS_COLORS[index % len(TEAM_STATUS_COLORS)]}
        for index, (status_key, status_label) in enumerate(Lead.STATUS_CHOICES)
    ]

    if profile.role == 'super_admin':
        for owner_user in User.objects.filter(profile__role='owner', profile__is_approved=True):
            rows.append(_team_stacked_status_payload(leads.filter(owner=owner_user), owner_user.username))
    elif profile.role == 'owner':
        rows.append(_team_stacked_status_payload(leads.filter(created_by=user), user.username + ' (You)'))
        for tm in TeamMember.objects.filter(boss=user, is_active=True).select_related('staff'):
            rows.append(_team_stacked_status_payload(leads.filter(created_by=tm.staff), tm.staff.username))
    else:
        rows.append(_team_stacked_status_payload(leads.filter(created_by=user), user.username))

    if sort_by == 'name':
        rows.sort(key=lambda x: x['name'].lower())
    elif sort_by in dict(Lead.STATUS_CHOICES):
        rows.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
    else:
        rows.sort(key=lambda x: x['total'], reverse=True)

    timeframe_label = {
        'all': 'AllTime',
        'today': 'Today',
        'week': 'ThisWeek',
        '7d': '7Days',
        '15d': '15Days',
        '30d': '30Days',
        '90d': '90Days',
    }.get(timeframe, '7Days')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Team_Status_Stacked_{timeframe_label}_{today}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Member', 'Total'] + [label for _, label in Lead.STATUS_CHOICES])

    for row in rows:
        writer.writerow([row['name'], row['total']] + [row.get(status_key, 0) for status_key, _ in Lead.STATUS_CHOICES])

    return response


@login_required
@require_permission('can_add_leads')
def add_lead(request):
    """
    Redirect single lead add to bulk add page as per requirement.
    Preserves query parameters (like ?template=id).
    """
    from django.urls import reverse
    url = reverse('bulk_add_leads')
    query_string = request.META.get('QUERY_STRING')
    if query_string:
        url = f"{url}?{query_string}"
    return redirect(url)


@login_required
@require_permission('can_edit_leads')
def edit_lead(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)

    # Check permission
    if not _can_access_lead(request.user, lead):
        messages.error(request, 'You do not have permission to edit this lead!')
        return redirect('dashboard')

    # Check if lead is soft deleted for the current user
    if lead.is_deleted_for_user(request.user):
        messages.error(request, 'This lead is not accessible.')
        return redirect('dashboard')

    # Initialize assignment_form for both POST and GET requests
    assignment_form = None
    if request.user.profile.role == 'owner':
        assignment_form = LeadAssignmentForm(user=request.user)

    if request.method == 'POST':
        # Capture original state for detailed activity logging
        try:
            orig = Lead.objects.get(id=lead.id)
        except Lead.DoesNotExist:
            orig = lead

        form = LeadForm(request.POST, instance=lead, user=request.user)
        profile_link_formset = ProfileLinkFormSet(request.POST, prefix='profile_links')
        if form.is_valid() and profile_link_formset.is_valid():
            # Save the lead with custom fields
            lead = form.save(commit=False)

            # Handle category and source from dropdown choices
            category_choice = form.cleaned_data.get('category_choice')
            category_other = form.cleaned_data.get('category_other', '')
            source_choice = form.cleaned_data.get('source_choice')
            source_other = form.cleaned_data.get('source_other', '')

            selected_category, selected_category_other, category_error = _resolve_category_selection(
                request.user,
                category_choice,
                category_other,
            )
            if category_error:
                messages.error(request, category_error)
                return redirect('edit_lead', lead_id=lead.id)

            selected_source, selected_source_other, source_error = _resolve_source_selection(
                request.user,
                source_choice,
                source_other,
            )
            if source_error:
                messages.error(request, source_error)
                return redirect('edit_lead', lead_id=lead.id)

            lead.category = selected_category
            lead.category_other = selected_category_other
            lead.source = selected_source
            lead.source_other = selected_source_other

            previous_status = lead.status

            # Handle profile links - delete existing and add new ones
            lead.profile_links.all().delete()  # Delete existing profile links

            # Save new profile links
            for profile_link_form in profile_link_formset:
                if profile_link_form.cleaned_data and not profile_link_form.cleaned_data.get('DELETE', False):
                    profile_link = profile_link_form.save(commit=False)
                    profile_link.lead = lead
                    profile_link.save()

            # Calculate lead score based on updated information
            lead.lead_score = lead.calculate_lead_score()
            
            # Track changes before saving
            change_details = []
            for field in form.changed_data:
                if field in form.fields and field not in ['category_choice', 'source_choice', 'category_other', 'source_other']:
                    label = form.fields[field].label or field
                    if field == 'status':
                        old_v = orig.get_status_display()
                        new_v = dict(form.fields['status'].choices).get(form.cleaned_data['status'], form.cleaned_data['status'])
                    else:
                        old_v = getattr(orig, field, 'None')
                        new_v = form.cleaned_data.get(field, 'None')
                    
                    if str(old_v) != str(new_v):
                        change_details.append(f"{label}: {old_v} → {new_v}")
            
            # Manual check for category/source
            old_cat = str(orig.category) if orig.category else orig.category_other
            new_cat = str(lead.category) if lead.category else lead.category_other
            if old_cat != new_cat:
                change_details.append(f"Category: {old_cat} → {new_cat}")
                
            old_src = str(orig.source) if orig.source else orig.source_other
            new_src = str(lead.source) if lead.source else lead.source_other
            if old_src != new_src:
                change_details.append(f"Source: {old_src} → {new_src}")

            lead.save()

            # Create a LeadActivity for the update to show in Lead timeline and Lead List
            if change_details:
                LeadActivity.objects.create(
                    lead=lead,
                    user=request.user,
                    activity_type='status_update' if 'status' in form.changed_data else 'note',
                    description="\n".join(change_details)
                )

            if lead.status == 'contacted' and previous_status != 'contacted':
                lead.contact_attempts = (lead.contact_attempts or 0) + 1
                lead.save(update_fields=['contact_attempts'])

                LeadActivity.objects.create(
                    lead=lead,
                    user=request.user,
                    activity_type='status_update',
                    description=f'Status changed from {previous_status} to contacted (attempt #{lead.contact_attempts})',
                )

            # Log the update activity
            details = "\n".join(change_details) if change_details else f"Updated lead: {lead.client_name}"
            log_activity(
                user=request.user,
                action='update',
                target_model='Lead',
                target_id=lead.id,
                target_name=lead.client_name,
                details=details,
                request=request
            )

            # Handle lead assignment
            assigned_to_id = request.POST.get('assigned_to')
            if assigned_to_id and assigned_to_id != str(lead.assigned_to_id if lead.assigned_to else ''):
                from team.models import TeamMember
                try:
                    new_assigned_to = User.objects.get(id=assigned_to_id)
                    # Check if user has permission to assign to this team member
                    # Verify that the staff member is active and approved
                    team_member = TeamMember.objects.filter(
                        boss=request.user,
                        staff=new_assigned_to,
                        is_active=True
                    ).first()

                    if (request.user.profile.role == 'owner' and
                        team_member and new_assigned_to.profile.is_approved):

                        # Create assignment history
                        LeadAssignmentHistory.objects.create(
                            lead=lead,
                            assigned_by=request.user,
                            assigned_to=new_assigned_to,
                            previous_assigned_to=lead.assigned_to,
                            reason=request.POST.get('assignment_reason', '')
                        )

                        # Update lead assignment
                        lead.assigned_to = new_assigned_to
                        lead.assignment_date = timezone.now()
                        lead.save()

                        # Add activity log
                        LeadActivity.objects.create(
                            lead=lead,
                            user=request.user,
                            activity_type='assignment',
                            description=f'Lead assigned to {new_assigned_to.username}'
                        )

                        messages.success(request, f'Lead assigned to {new_assigned_to.username}')
                    else:
                        messages.error(request, 'You do not have permission to assign to this user or the user is not an approved team member.')
                except User.DoesNotExist:
                    messages.error(request, 'Selected user does not exist.')

            messages.success(request, 'Lead updated successfully!')

            # Notify owner when staff updates a lead
            if request.user.profile.role == 'staff':
                try:
                    tm = TeamMember.objects.get(staff=request.user)
                    notify(
                        recipient=tm.boss,
                        notification_type='lead_updated',
                        title='Lead Updated',
                        message=f'{request.user.username} updated lead: {lead.client_name}',
                        url=f'/leads/edit/{lead.id}/',
                        sender=request.user,
                    )
                except TeamMember.DoesNotExist:
                    pass

            # Check if user wants to add another lead after editing
            if request.POST.get('action') == 'continue':
                # Redirect to bulk_add_leads to create new leads
                return redirect('bulk_add_leads')
            else:
                return redirect('lead_detail', lead_id=lead.id)
        else:
            messages.error(request, 'Please fix the errors below before saving.')
    else:
        # Log the view activity
        log_activity(
            user=request.user,
            action='view',
            target_model='Lead',
            target_id=lead.id,
            target_name=lead.client_name,
            details=f'Viewed lead: {lead.client_name}',
            request=request
        )

        # Initialize form with current values
        initial_data = {}
        owner_user = _get_effective_owner(request.user)

        if lead.category:
            initial_data['category_choice'] = lead.category.id
            initial_data['category_other'] = ''
        elif lead.category_other:
            private_category = None
            if owner_user:
                private_category = OwnerCategory.objects.filter(
                    owner=owner_user,
                    name__iexact=lead.category_other,
                ).first()

            if private_category:
                initial_data['category_choice'] = f'owner_{private_category.id}'
                initial_data['category_other'] = ''
            else:
                initial_data['category_choice'] = 'other'
                initial_data['category_other'] = lead.category_other
        else:
            initial_data['category_choice'] = ''
            initial_data['category_other'] = ''

        if lead.source:
            initial_data['source_choice'] = lead.source.id
            initial_data['source_other'] = ''
        elif lead.source_other:
            private_source = None
            if owner_user:
                private_source = OwnerSource.objects.filter(
                    owner=owner_user,
                    name__iexact=lead.source_other,
                ).first()

            if private_source:
                initial_data['source_choice'] = f'owner_{private_source.id}'
                initial_data['source_other'] = ''
            else:
                initial_data['source_choice'] = 'other'
                initial_data['source_other'] = lead.source_other
        else:
            initial_data['source_choice'] = ''
            initial_data['source_other'] = ''

        form = LeadForm(instance=lead, initial=initial_data, user=request.user)
        profile_link_formset = ProfileLinkFormSet(prefix='profile_links')

        # Create assignment form for owners
        assignment_form = None
        if request.user.profile.role == 'owner':
            assignment_form = LeadAssignmentForm(user=request.user)

    # Get all categories and sources for the template dropdowns
    categories = _build_visible_category_options(request.user)
    sources = _build_visible_source_options(request.user)

    return render(request, 'core/edit_lead.html', {
        'form': form,
        'profile_link_formset': profile_link_formset,
        'lead': lead,
        'categories': categories,
        'sources': sources,
        'assignment_form': assignment_form,
        'lead_activities': LeadActivity.objects.filter(lead=lead).order_by('-timestamp'),
        'assignment_history': LeadAssignmentHistory.objects.filter(lead=lead).order_by('-assigned_at')
    })


@login_required
@require_permission('can_delete_leads')
def delete_lead(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)

    # Check permission
    if not _can_access_lead(request.user, lead):
        messages.error(request, 'You do not have permission to delete this lead!')
        return redirect('dashboard')

    if request.method == 'POST':
        # Perform soft delete
        lead.deleted_by = request.user
        lead.deleted_at = timezone.now()
        lead.save()

        # Log the delete activity
        log_activity(
            user=request.user,
            action='delete',
            target_model='Lead',
            target_id=lead.id,
            target_name=lead.client_name,
            details=f'Deleted lead: {lead.client_name}',
            request=request
        )

        messages.success(request, 'Lead deleted successfully!')

        # Notify owner when staff deletes a lead
        if request.user.profile.role == 'staff':
            try:
                tm = TeamMember.objects.get(staff=request.user)
                notify(
                    recipient=tm.boss,
                    notification_type='lead_deleted',
                    title='Lead Deleted',
                    message=f'{request.user.username} deleted lead: {lead.client_name}',
                    url='/leads/deleted-leads/',
                    sender=request.user,
                )
            except TeamMember.DoesNotExist:
                pass

        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)

        return redirect('lead_list')

    return redirect('lead_list')


@login_required
@require_permission('can_view_leads')
def lead_detail(request, lead_id):
    """Display lead details in read-only mode."""
    lead = get_object_or_404(Lead, id=lead_id)

    # Check permission
    if not _can_access_lead(request.user, lead):
        messages.error(request, 'You do not have permission to view this lead!')
        return redirect('dashboard')

    # Check if lead is soft deleted for the current user
    if lead.is_deleted_for_user(request.user):
        messages.error(request, 'This lead is not accessible.')
        return redirect('dashboard')

    # Log the view activity
    log_activity(
        user=request.user,
        action='view',
        target_model='Lead',
        target_id=lead.id,
        target_name=lead.client_name,
        details=f'Viewed lead: {lead.client_name}',
        request=request
    )

    # Get related data
    categories = Category.objects.all()
    sources = Source.objects.all()
    profile_links = lead.profile_links.all()
    
    # Get all activity records for this lead (both LeadActivity and ActivityLog)
    lead_activities = LeadActivity.objects.filter(lead=lead).order_by('-timestamp')
    lead_action_logs = ActivityLog.objects.filter(target_model='Lead', target_id=lead.id).order_by('-timestamp')
    
    # Combine both activity types with source indicator
    all_activities = []
    for activity in lead_activities:
        all_activities.append({
            'type': 'lead_activity',
            'activity': activity,
            'timestamp': activity.timestamp
        })
    for log in lead_action_logs:
        all_activities.append({
            'type': 'activity_log',
            'log': log,
            'timestamp': log.timestamp
        })
    
    # Sort by timestamp, most recent first
    all_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    assignment_history = LeadAssignmentHistory.objects.filter(lead=lead).order_by('-assigned_at')

    return render(request, 'core/lead_detail.html', {
        'lead': lead,
        'categories': categories,
        'sources': sources,
        'profile_links': profile_links,
        'all_activities': all_activities[:50],  # Show last 50 activities
        'assignment_history': assignment_history,
    })


# from django_ratelimit.decorators import ratelimit

@login_required
@require_permission('can_bulk_add_leads')
# @ratelimit(key='ip', rate='10/m', method='POST', block=True)
def bulk_add_leads(request):
    if not request.user.profile.is_approved:
        messages.error(request, 'Your account needs to be approved first!')
        return redirect('dashboard')

    # Determine the owner for plan limit checks
    from billing.models import can_create_leads
    if request.user.profile.role == 'staff':
        try:
            _tm = TeamMember.objects.get(staff=request.user)
            _lead_owner = _tm.boss
        except TeamMember.DoesNotExist:
            _lead_owner = request.user
    else:
        _lead_owner = request.user

    custom_fields_all = get_custom_fields_for_user(request.user, scope='all')
    custom_fields_each = get_custom_fields_for_user(request.user, scope='each')
    categories_for_dropdown = _build_visible_category_options(request.user)
    sources_for_dropdown = _build_visible_source_options(request.user)

    # Prepare choices for each custom field for use in JavaScript
    custom_field_choices = {}
    for custom_field in custom_fields_each:
        if custom_field.field_type == 'choice':
            choices_list = [choice.strip() for choice in custom_field.choices.split(',')]
            custom_field_choices[custom_field.id] = choices_list

    if request.method == 'POST':
        bulk_form = BulkLeadForm(request.POST, user=request.user)
        lead_entries_formset = LeadEntryFormSet(request.POST, prefix='leads', user=request.user)
        lead_custom_fields_formset = LeadEntryCustomFieldsFormSet(
            request.POST,
            user=request.user,
            prefix='lead_custom_fields',
        )

        # For per-lead custom fields, we'll process them directly from POST data
        # since the template renders them as static HTML fields per lead entry
        custom_fields_formset_valid = True  # Always valid since we're processing directly from POST

        if bulk_form.is_valid() and lead_entries_formset.is_valid() and custom_fields_formset_valid:
            # Process shared data
            category_choice = bulk_form.cleaned_data.get('category_choice')
            category_other = bulk_form.cleaned_data.get('category_other')
            source_choice = bulk_form.cleaned_data.get('source_choice')
            source_other = bulk_form.cleaned_data.get('source_other')
            status = bulk_form.cleaned_data.get('status')
            follow_up_date = bulk_form.cleaned_data.get('follow_up_date')
            notes = bulk_form.cleaned_data.get('notes')

            # Determine category and source based on selection
            category, category_other_value, category_error = _resolve_category_selection(
                request.user,
                category_choice,
                category_other,
            )
            if category_error:
                messages.error(request, category_error)
                return render(request, 'core/bulk_add_leads.html', {
                    'bulk_form': bulk_form,
                    'lead_entries_formset': lead_entries_formset,
                    'lead_custom_fields_formset': lead_custom_fields_formset,
                    'categories': categories_for_dropdown,
                    'sources': sources_for_dropdown,
                    'custom_fields_all': custom_fields_all,
                    'custom_fields_each': custom_fields_each,
                    'custom_field_choices': custom_field_choices,
                })

            source, source_other_value, source_error = _resolve_source_selection(
                request.user,
                source_choice,
                source_other,
            )
            if source_error:
                messages.error(request, source_error)
                return render(request, 'core/bulk_add_leads.html', {
                    'bulk_form': bulk_form,
                    'lead_entries_formset': lead_entries_formset,
                    'lead_custom_fields_formset': lead_custom_fields_formset,
                    'categories': categories_for_dropdown,
                    'sources': sources_for_dropdown,
                    'custom_fields_all': custom_fields_all,
                    'custom_fields_each': custom_fields_each,
                    'custom_field_choices': custom_field_choices,
                })

            # Process individual leads
            created_count = 0
            created_leads = []  # Track created leads for logging

            # Process custom fields from bulk form (only 'all' scope fields)
            custom_fields_all_data = {}
            custom_fields_each_data = {}

            if hasattr(bulk_form, 'user_instance') and bulk_form.user_instance:
                # Separate custom fields by scope
                all_scope_fields = CustomField.objects.filter(owner=bulk_form.user_instance, scope='all', is_active=True)
                each_scope_fields = CustomField.objects.filter(owner=bulk_form.user_instance, scope='each', is_active=True)

                # Process 'all' scope fields (apply to all leads)
                for custom_field in all_scope_fields:
                    field_name = f"custom_{custom_field.id}"
                    if field_name in bulk_form.cleaned_data:
                        custom_fields_all_data[custom_field.name] = bulk_form.cleaned_data[field_name]

                # Process 'each' scope fields (would be handled per lead if implemented in formset)
                for custom_field in each_scope_fields:
                    field_name = f"custom_{custom_field.id}"
                    if field_name in bulk_form.cleaned_data:
                        custom_fields_each_data[custom_field.name] = bulk_form.cleaned_data[field_name]

            # First, collect all per-lead custom field values
            per_lead_custom_fields = {}
            for key, value in request.POST.items():
                # Look for keys in the format: lead_{index}_custom_{field_id}
                if value and key.startswith('lead_') and '_custom_' in key:
                    try:
                        # Extract lead index and custom field ID
                        # Format: lead_{index}_custom_{field_id}
                        parts = key.split('_custom_')
                        if len(parts) == 2:
                            lead_part = parts[0]  # This should be "lead_{index}"
                            custom_field_id = parts[1]  # This should be the field ID

                            # Extract the lead index
                            lead_idx_part = lead_part[5:]  # Remove "lead_" prefix
                            lead_idx = int(lead_idx_part)

                            # Initialize the dictionary for this lead if not already done
                            if lead_idx not in per_lead_custom_fields:
                                per_lead_custom_fields[lead_idx] = {}

                            # Get the custom field object and store the value
                            custom_field_obj = CustomField.objects.get(id=custom_field_id, owner=request.user)
                            per_lead_custom_fields[lead_idx][custom_field_obj.name] = value
                    except (ValueError, IndexError, CustomField.DoesNotExist):
                        # Skip if parsing fails
                        continue

            # Validate required per-lead custom fields
            required_each_fields = get_custom_fields_for_user(request.user, scope='each', required=True)
            missing_required = False
            if required_each_fields.exists():
                for i, form in enumerate(lead_entries_formset):
                    if form.cleaned_data and form.cleaned_data.get('client_name'):
                        for req_field in required_each_fields:
                            field_key = f"lead_{i}_custom_{req_field.id}"
                            val = request.POST.get(field_key, '').strip()
                            if not val:
                                messages.error(request, f'Lead #{i+1}: "{req_field.name}" is required.')
                                missing_required = True

            if missing_required:
                return render(request, 'core/bulk_add_leads.html', {
                    'bulk_form': bulk_form,
                    'lead_entries_formset': lead_entries_formset,
                    'lead_custom_fields_formset': lead_custom_fields_formset,
                    'categories': categories_for_dropdown,
                    'sources': sources_for_dropdown,
                    'custom_fields_all': custom_fields_all,
                    'custom_fields_each': custom_fields_each,
                    'custom_field_choices': custom_field_choices,
                })

            # Check lead limit before creating
            leads_to_add = sum(1 for f in lead_entries_formset if f.cleaned_data and f.cleaned_data.get('client_name'))
            allowed, limit_msg = can_create_leads(_lead_owner, leads_to_add)
            if not allowed:
                messages.error(request, limit_msg)
                return render(request, 'core/bulk_add_leads.html', {
                    'bulk_form': bulk_form,
                    'lead_entries_formset': lead_entries_formset,
                    'lead_custom_fields_formset': lead_custom_fields_formset,
                    'categories': categories_for_dropdown,
                    'sources': sources_for_dropdown,
                    'custom_fields_all': custom_fields_all,
                    'custom_fields_each': custom_fields_each,
                    'custom_field_choices': custom_field_choices,
                })

            created_count = 0
            created_leads = []
            shared_assigned_user = bulk_form.cleaned_data.get('assigned_to')

            for i, form in enumerate(lead_entries_formset):
                if form.cleaned_data and form.cleaned_data.get('client_name'):
                    combined_custom_fields = custom_fields_all_data.copy()

                    # Add per-lead custom fields for this specific lead
                    if i in per_lead_custom_fields:
                        combined_custom_fields.update(per_lead_custom_fields[i])

                    row_status = form.cleaned_data.get('status') or status
                    row_follow_up_date = form.cleaned_data.get('follow_up_date') or follow_up_date
                    row_assigned_user = form.cleaned_data.get('assigned_to') if 'assigned_to' in form.fields else None
                    if not row_assigned_user:
                        row_assigned_user = shared_assigned_user

                    # Create lead with shared defaults and per-row overrides
                    lead = Lead.objects.create(
                        owner=request.user,
                        created_by=request.user,
                        category=category,
                        category_other=category_other_value,
                        source=source,
                        source_other=source_other_value,
                        client_name=form.cleaned_data['client_name'],
                        contact_number=form.cleaned_data.get('contact_number', ''),
                        email=form.cleaned_data.get('email', ''),
                        requirement=form.cleaned_data.get('requirement', ''),
                        status=row_status,
                        contact_attempts=1 if row_status == 'contacted' else 0,
                        follow_up_date=row_follow_up_date,
                        notes=notes,
                        custom_fields=combined_custom_fields  # Add custom fields data
                    )

                    # Set owner based on role
                    if request.user.profile.role == 'staff':
                        try:
                            team_member = TeamMember.objects.get(staff=request.user)
                            lead.owner = team_member.boss
                            lead.assigned_to = request.user
                            lead.assignment_date = timezone.now()
                            lead.save(update_fields=['owner', 'assigned_to', 'assignment_date'])

                            LeadAssignmentHistory.objects.create(
                                lead=lead,
                                assigned_by=team_member.boss,
                                assigned_to=request.user,
                                previous_assigned_to=None,
                                reason='Auto-assigned to creator'
                            )
                        except TeamMember.DoesNotExist:
                            messages.error(request, 'You are not assigned to any team!')
                            return redirect('dashboard')

                    # Handle assignment if owner assigned leads during bulk creation
                    assigned_user = row_assigned_user
                    if assigned_user:
                        # Verify that the assigned user is indeed an active and approved team member of this owner
                        team_member = TeamMember.objects.filter(
                            boss=request.user,
                            staff=assigned_user,
                            is_active=True
                        ).first()

                        if team_member and assigned_user.profile.is_approved:
                            lead.assigned_to = assigned_user
                            lead.assignment_date = timezone.now()
                            lead.save()

                            # Create assignment history
                            LeadAssignmentHistory.objects.create(
                                lead=lead,
                                assigned_by=request.user,
                                assigned_to=assigned_user,
                                previous_assigned_to=None,
                                reason="Bulk assignment during creation"
                            )

                            # Add activity log
                            LeadActivity.objects.create(
                                lead=lead,
                                user=request.user,
                                activity_type='assignment',
                                description=f'Lead assigned to {assigned_user.username} during bulk creation'
                            )

                    # Process profile links for this lead
                    # Find all profile link data associated with this specific lead
                    profile_link_data = {}

                    # Collect all profile link data for this specific lead
                    # Format: lead_{any_lead_index}_profile_links-{link_index}-{field_name}
                    for key, value in request.POST.items():
                        if key.startswith('lead_') and '_profile_links-' in key:
                            # Split the key to extract components
                            # Format: lead_{lead_index}_profile_links-{link_index}-{field_name}
                            parts = key.split('_profile_links-')
                            if len(parts) == 2:
                                # Get the lead index from the first part
                                lead_part = parts[0]  # This should be "lead_{index}"
                                if lead_part.startswith('lead_'):
                                    lead_idx_str = lead_part[5:]  # Remove "lead_" prefix

                                    # Now split the second part to get link index and field name
                                    remaining_part = parts[1]
                                    sub_parts = remaining_part.split('-')

                                    if len(sub_parts) >= 2:
                                        try:
                                            link_idx = int(sub_parts[0])  # The link index
                                            field_name = sub_parts[1]     # The field name (platform, url, etc.)

                                            # Check if this key belongs to the current lead (i)
                                            if lead_idx_str == str(i):
                                                # Initialize the link index dict if it doesn't exist
                                                if link_idx not in profile_link_data:
                                                    profile_link_data[link_idx] = {}

                                                # Store the field value
                                                profile_link_data[link_idx][field_name] = value
                                        except ValueError:
                                            # If conversion to int fails, skip this key
                                            continue

                    # Create profile links for this lead
                    for link_idx, link_info in profile_link_data.items():
                        if link_info.get('platform') and link_info.get('url'):
                            ProfileLink.objects.create(
                                lead=lead,
                                platform=link_info.get('platform', 'other'),
                                custom_platform=link_info.get('custom_platform', ''),
                                url=link_info.get('url', '')
                            )

                    created_count += 1
                    created_leads.append(lead)

            # Log the activity
            if created_count > 0:
                log_activity(
                    user=request.user,
                    action='create',
                    target_model='Lead',
                    target_name=f'{created_count} leads',
                    details=f'Bulk added {created_count} leads with shared properties',
                    request=request
                )

            messages.success(request, f'{created_count} leads added successfully!')

            # Notify: owner if staff added leads, self-notification for owners
            if created_count > 0:
                if request.user.profile.role == 'staff':
                    try:
                        tm = TeamMember.objects.get(staff=request.user)
                        notify(
                            recipient=tm.boss,
                            notification_type='lead_added',
                            title='New Leads Added',
                            message=f'{request.user.username} added {created_count} new lead(s).',
                            url='/leads/list/',
                            sender=request.user,
                        )
                    except TeamMember.DoesNotExist:
                        pass
                else:
                    notify(
                        recipient=request.user,
                        notification_type='lead_added',
                        title='Leads Added',
                        message=f'You successfully added {created_count} new lead(s).',
                        url='/leads/list/',
                        sender=request.user,
                    )

            if created_leads:
                return redirect('lead_list')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the errors in the form before submitting.')
    else:
        # Check if a template ID was passed in the URL
        template_id = request.GET.get('template')
        template_data = None
        if template_id:
            try:
                template = LeadTemplate.objects.get(id=template_id, owner=request.user)
                template_data = {
                    'category': template.category,
                    'source': template.source,
                    'status': template.status,
                    'notes': template.notes
                }
                # Pre-populate the form with template data
                initial_data = {}
                if template.category:
                    initial_data['category_choice'] = str(template.category.id)  # Convert to string
                if template.source:
                    initial_data['source_choice'] = str(template.source.id)  # Convert to string
                if template.status:
                    initial_data['status'] = template.status
                if template.notes:
                    initial_data['notes'] = template.notes
                bulk_form = BulkLeadForm(user=request.user, initial=initial_data)
            except LeadTemplate.DoesNotExist:
                bulk_form = BulkLeadForm(user=request.user)
        else:
            bulk_form = BulkLeadForm(user=request.user)

        lead_entries_formset = LeadEntryFormSet(prefix='leads', user=request.user)
        # Initialize the custom fields formset with 1 empty form for the initial lead entry
        lead_custom_fields_formset = LeadEntryCustomFieldsFormSet(
            user=request.user,
            prefix='lead_custom_fields',
            initial=[{}]  # One empty form for the initial lead
        )

    return render(request, 'core/bulk_add_leads.html', {
        'bulk_form': bulk_form,
        'lead_entries_formset': lead_entries_formset,
        'lead_custom_fields_formset': lead_custom_fields_formset,  # May be None if custom fields section is removed
        'categories': categories_for_dropdown,
        'sources': sources_for_dropdown,
        'custom_fields_all': custom_fields_all,
        'custom_fields_each': custom_fields_each,
        'custom_field_choices': custom_field_choices
    })


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import csv
import io


@login_required
@require_permission('can_manage_templates')
def manage_templates(request):
    """View for managing lead templates"""
    user_profile = getattr(request.user, 'profile', None)

    if user_profile and user_profile.role == 'super_admin':
        # Super admin sees all templates, including soft deleted ones
        templates = LeadTemplate.objects.all()
    elif user_profile and user_profile.role == 'owner':
        # Owner sees their templates, excluding those they soft deleted themselves
        templates = LeadTemplate.objects.filter(owner=request.user).exclude(deleted_by=request.user)
    elif user_profile and user_profile.role == 'staff':
        # Staff sees their templates, excluding those deleted by owner or super admin
        from accounts.models import UserProfile
        higher_role_ids = UserProfile.objects.filter(role__in=['owner', 'super_admin']).values_list('user_id', flat=True)
        templates = LeadTemplate.objects.filter(owner=request.user).exclude(deleted_by_id__in=higher_role_ids).exclude(deleted_by=request.user)
    else:
        templates = LeadTemplate.objects.filter(owner=request.user).exclude(deleted_by=request.user)

    if request.method == 'POST':
        form = LeadTemplateForm(request.POST, user=request.user)
        if form.is_valid():
            template = form.save(commit=False)
            template.owner = request.user
            template.save()

            # Log the create activity
            log_activity(
                user=request.user,
                action='create',
                target_model='LeadTemplate',
                target_id=template.id,
                target_name=template.name,
                details=f'Created lead template: {template.name}',
                request=request
            )

            messages.success(request, 'Template saved successfully!')
            return redirect('manage_templates')
        else:
            messages.error(request, 'Please fix the errors in the template form.')
    else:
        # Log the view activity
        log_activity(
            user=request.user,
            action='view',
            target_model='LeadTemplate',
            target_name='Manage Templates',
            details='Viewed manage templates page',
            request=request
        )
        form = LeadTemplateForm(user=request.user)

    # Get categories and sources for the template
    categories = Category.objects.all()
    sources = Source.objects.all()

    # Get deleted templates for owners and super admins
    deleted_templates = []
    if user_profile and user_profile.role == 'owner':
        deleted_templates = LeadTemplate.get_deleted_templates_for_owner(request.user)
    elif user_profile and user_profile.role == 'super_admin':
        deleted_templates = LeadTemplate.get_deleted_templates_for_admin()

    return render(request, 'core/manage_templates.html', {
        'form': form,
        'templates': templates,
        'categories': categories,
        'sources': sources,
        'deleted_templates': deleted_templates
    })


@login_required
@require_permission('can_manage_templates')
def edit_template(request, template_id):
    """Edit a lead template"""
    template = get_object_or_404(LeadTemplate, id=template_id, owner=request.user)

    if request.method == 'POST':
        form = LeadTemplateForm(request.POST, instance=template, user=request.user)
        if form.is_valid():
            form.save()

            # Log the update activity
            log_activity(
                user=request.user,
                action='update',
                target_model='LeadTemplate',
                target_id=template.id,
                target_name=template.name,
                details=f'Updated lead template: {template.name}',
                request=request
            )

            messages.success(request, f'Template "{template.name}" updated successfully!')
            return redirect('manage_templates')
        else:
            messages.error(request, 'Please fix the errors in the form.')

    return redirect('manage_templates')


@login_required
@require_permission('can_manage_templates')
def delete_template(request, template_id):
    """Soft delete a lead template"""
    template = get_object_or_404(LeadTemplate, id=template_id, owner=request.user)

    # Check permission - allow owner to delete their own templates
    if template.owner != request.user and request.user.profile.role != 'super_admin':
        messages.error(request, 'You do not have permission to delete this template!')
        return redirect('manage_templates')

    if request.method == 'POST':
        # Perform soft delete
        template.deleted_by = request.user
        template.deleted_at = timezone.now()
        template.save()

        # Log the delete activity
        log_activity(
            user=request.user,
            action='delete',
            target_model='LeadTemplate',
            target_id=template.id,
            target_name=template.name,
            details=f'Deleted lead template: {template.name}',
            request=request
        )

        messages.success(request, 'Template deleted successfully!')
        return redirect('manage_templates')

    messages.info(request, 'Confirm delete from the template modal to remove this template.')
    return redirect('manage_templates')


@login_required
@require_permission('can_manage_templates')
def apply_template(request, template_id):
    """API endpoint to apply a template to the bulk_add_leads form"""
    template = get_object_or_404(LeadTemplate, id=template_id, owner=request.user)

    # Return template data as JSON
    data = {
        'success': True,
        'template_data': {
            'category_id': template.category.id if template.category else None,
            'source_id': template.source.id if template.source else None,
            'status': template.status,
            'notes': template.notes
        }
    }
    return JsonResponse(data)


@login_required
@require_permission('can_csv_upload')
# @ratelimit(key='ip', rate='5/m', method='POST', block=True)
def csv_upload(request):
    """View for uploading CSV files to import leads"""
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            template = form.cleaned_data.get('template')

            # Read CSV content
            content = csv_file.read().decode('utf-8')
            csv_file.seek(0)  # Reset file pointer for any further processing

            # Parse CSV
            reader = csv.DictReader(io.StringIO(content))

            # Pre-cache global categories/sources and owner-private options.
            category_cache = {c.name.lower(): c for c in Category.objects.all()}
            source_cache = {s.name.lower(): s for s in Source.objects.all()}

            # Determine owner for staff
            owner_user = request.user
            if request.user.profile.role == 'staff':
                try:
                    team_member = TeamMember.objects.get(staff=request.user)
                    owner_user = team_member.boss
                except TeamMember.DoesNotExist:
                    messages.error(request, 'You are not assigned to any team!')
                    return redirect('csv_upload')

            owner_category_cache = {}
            owner_source_cache = {}
            if owner_user and hasattr(owner_user, 'profile') and owner_user.profile.role == 'owner':
                owner_category_cache = {
                    c.name.lower(): c.name
                    for c in OwnerCategory.objects.filter(owner=owner_user)
                }
                owner_source_cache = {
                    s.name.lower(): s.name
                    for s in OwnerSource.objects.filter(owner=owner_user)
                }

            # Get custom fields for the user to map CSV columns
            user_custom_fields = _get_custom_fields_for_user(request.user)
            # Build a lookup: lowercase custom field name -> CustomField object
            custom_field_lookup = {cf.name.lower().strip(): cf for cf in user_custom_fields}

            # Identify base columns to exclude from custom field matching
            base_columns = {
                'client_name', 'contact_number', 'email', 'requirement', 'status',
                'follow_up_date', 'notes', 'category', 'source',
                'budget', 'timeline', 'decision_maker', 'lead_score',
                'converted_to_customer',
                'linkedin', 'instagram', 'facebook', 'twitter', 'youtube', 'website',
            }

            # Profile link platform columns
            profile_link_columns = {'linkedin', 'instagram', 'facebook', 'twitter', 'youtube', 'website'}

            leads_to_create = []
            profile_links_data = []

            rows = list(reader)
            if rows and rows[0].get('client_name', '').strip().startswith('('):
                rows = rows[1:]

            # Check lead limit before processing CSV
            from billing.models import can_create_leads
            valid_row_count = sum(1 for r in rows if r.get('client_name', '').strip())
            allowed, limit_msg = can_create_leads(owner_user, valid_row_count)
            if not allowed:
                messages.error(request, limit_msg)
                return redirect('csv_upload')

            for row_idx, row in enumerate(rows):
                lead_data = {
                    'owner': owner_user,
                    'created_by': request.user,
                    'client_name': row.get('client_name', '').strip(),
                    'contact_number': row.get('contact_number', '').strip(),
                    'email': row.get('email', '').strip(),
                    'requirement': row.get('requirement', '').strip(),
                    'status': row.get('status', 'new').strip() or 'new',
                    'notes': row.get('notes', '').strip(),
                }
                lead_data['contact_attempts'] = 1 if lead_data['status'] == 'contacted' else 0

                if request.user.profile.role == 'staff':
                    lead_data['assigned_to'] = request.user
                    lead_data['assignment_date'] = timezone.now()

                # Handle dates
                follow_up_date = row.get('follow_up_date', '').strip()
                if follow_up_date:
                    try:
                        lead_data['follow_up_date'] = datetime.strptime(follow_up_date, '%Y-%m-%d').date()
                    except ValueError:
                        pass

                # Handle budget
                budget_val = row.get('budget', '').strip()
                if budget_val:
                    try:
                        lead_data['budget'] = float(budget_val)
                    except (ValueError, TypeError):
                        pass

                # Handle timeline (date field)
                timeline_val = row.get('timeline', '').strip()
                if timeline_val:
                    try:
                        lead_data['timeline'] = datetime.strptime(timeline_val, '%Y-%m-%d').date()
                    except ValueError:
                        pass

                # Handle decision_maker (boolean)
                decision_maker_val = row.get('decision_maker', '').strip()
                if decision_maker_val:
                    lead_data['decision_maker'] = decision_maker_val.lower() in ('true', 'yes', '1', 'on')

                # Handle lead_score (integer)
                lead_score_val = row.get('lead_score', '').strip()
                if lead_score_val:
                    try:
                        lead_data['lead_score'] = int(float(lead_score_val))
                    except (ValueError, TypeError):
                        pass

                # Handle converted_to_customer (boolean)
                converted_val = row.get('converted_to_customer', '').strip()
                if converted_val:
                    lead_data['converted_to_customer'] = converted_val.lower() in ('true', 'yes', '1', 'on')

                # Collect profile link URLs for this row
                for platform in profile_link_columns:
                    url_val = row.get(platform, '').strip()
                    if url_val:
                        profile_links_data.append((row_idx, platform, url_val))

                # Handle category:
                # 1) use global category if exists,
                # 2) else use owner-private category text,
                # 3) else store as lead-specific category_other (no global creation).
                category_name = row.get('category', '').strip()
                if category_name:
                    cat_key = category_name.lower()
                    if cat_key in category_cache:
                        lead_data['category'] = category_cache[cat_key]
                    elif cat_key in owner_category_cache:
                        lead_data['category_other'] = owner_category_cache[cat_key]
                    else:
                        lead_data['category_other'] = category_name
                elif template and template.category:
                    lead_data['category'] = template.category

                # Handle source with same rules as category.
                source_name = row.get('source', '').strip()
                if source_name:
                    src_key = source_name.lower()
                    if src_key in source_cache:
                        lead_data['source'] = source_cache[src_key]
                    elif src_key in owner_source_cache:
                        lead_data['source_other'] = owner_source_cache[src_key]
                    else:
                        lead_data['source_other'] = source_name
                elif template and template.source:
                    lead_data['source'] = template.source

                # Apply template defaults
                if template:
                    if 'category' not in lead_data and template.category:
                        lead_data['category'] = template.category
                    if 'source' not in lead_data and template.source:
                        lead_data['source'] = template.source
                    if not lead_data.get('status'):
                        lead_data['status'] = template.status
                    if not lead_data.get('notes'):
                        lead_data['notes'] = template.notes

                # Handle custom fields from CSV columns
                custom_data = {}
                for col_name, col_value in row.items():
                    if col_name and col_name.strip().lower() not in base_columns:
                        col_key = col_name.strip().lower()
                        if col_key in custom_field_lookup and col_value and col_value.strip():
                            cf = custom_field_lookup[col_key]
                            val = col_value.strip()
                            # Convert value based on field type
                            if cf.field_type == 'number':
                                try:
                                    val = float(val)
                                    if val == int(val):
                                        val = int(val)
                                except (ValueError, TypeError):
                                    val = val
                            elif cf.field_type == 'boolean':
                                val = val.lower() in ('true', 'yes', '1', 'on')
                            custom_data[cf.name] = val

                if custom_data:
                    lead_data['custom_fields'] = custom_data

                leads_to_create.append(Lead(**lead_data))

            # Bulk create in batches of 500 (much faster than individual creates)
            if leads_to_create:
                created_leads = Lead.objects.bulk_create(leads_to_create, batch_size=500)
            else:
                created_leads = []
            created_count = len(created_leads)

            # Create profile links for imported leads
            if profile_links_data and created_leads:
                links_to_create = []
                for row_idx, platform, url in profile_links_data:
                    if row_idx < len(created_leads):
                        links_to_create.append(ProfileLink(
                            lead=created_leads[row_idx],
                            platform=platform,
                            url=url,
                        ))
                if links_to_create:
                    ProfileLink.objects.bulk_create(links_to_create, batch_size=500)

            # Log the import activity
            log_activity(
                user=request.user,
                action='import',
                target_model='Lead',
                target_name=f'{created_count} leads',
                details=f'Imported {created_count} leads from CSV file',
                request=request
            )

            messages.success(request, f'Successfully imported {created_count} leads from CSV!')

            # Notify about CSV import
            if created_count > 0:
                if request.user.profile.role == 'staff':
                    try:
                        tm = TeamMember.objects.get(staff=request.user)
                        notify(
                            recipient=tm.boss,
                            notification_type='lead_imported',
                            title='CSV Leads Imported',
                            message=f'{request.user.username} imported {created_count} leads from CSV.',
                            url='/leads/list/',
                            sender=request.user,
                        )
                    except TeamMember.DoesNotExist:
                        pass
                else:
                    notify(
                        recipient=request.user,
                        notification_type='lead_imported',
                        title='CSV Import Complete',
                        message=f'Successfully imported {created_count} leads from CSV.',
                        url='/leads/list/',
                        sender=request.user,
                    )

            return redirect('dashboard')
        else:
            messages.error(request, 'Please upload a valid CSV file.')
    else:
        form = CSVUploadForm(user=request.user)

    # Get custom fields to display their names in the template
    user_custom_fields = _get_custom_fields_for_user(request.user)

    return render(request, 'core/csv_upload.html', {
        'form': form,
        'custom_fields': user_custom_fields,
    })


from django.http import HttpResponse
from django.core.paginator import Paginator


@login_required
@require_permission('can_view_activity_log')
def activity_log(request):
    """View to display user activity logs"""
    user_profile = getattr(request.user, 'profile', None)

    if user_profile and user_profile.role == 'super_admin':
        # Super admin can see all activities
        base_qs = ActivityLog.objects.select_related('user').all()
    elif user_profile and user_profile.role == 'owner':
        # Owner can see their own activities and their staff's activities
        staff_ids = list(TeamMember.objects.filter(boss=request.user).values_list('staff_id', flat=True))
        all_user_ids = [request.user.id] + staff_ids
        base_qs = ActivityLog.objects.filter(user_id__in=all_user_ids).select_related('user')
    else:
        # Regular user can only see their own activities
        base_qs = ActivityLog.objects.filter(user=request.user).select_related('user')

    # Get unique model names for filter dropdown (from role-scoped qs, not full table)
    all_models = base_qs.order_by('target_model').values_list('target_model', flat=True).distinct()
    # Get users available in this scope for user filter
    all_users = User.objects.filter(
        id__in=base_qs.values_list('user_id', flat=True).distinct()
    ).order_by('username')

    # Apply filters
    action_filter = request.GET.get('action')
    model_filter = request.GET.get('model')
    user_filter = request.GET.get('user')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    per_page = get_table_page_size(request, 'activity_log', default=25)

    activities = base_qs
    if action_filter:
        activities = activities.filter(action=action_filter)
    if model_filter:
        activities = activities.filter(target_model__icontains=model_filter)
    if user_filter:
        activities = activities.filter(user_id=user_filter)
    if date_from:
        activities = activities.filter(timestamp__date__gte=date_from)
    if date_to:
        activities = activities.filter(timestamp__date__lte=date_to)

    # Order by most recent
    activities = activities.order_by('-timestamp')

    # Paginate
    paginator = Paginator(activities, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    action_choices = ActivityLog.ACTION_CHOICES

    context = {
        'page_obj': page_obj,
        'action_choices': action_choices,
        'all_models': all_models,
        'all_users': all_users,
        'total_activity_count': activities.count(),
        'current_filters': {
            'action': action_filter,
            'model': model_filter,
            'user': user_filter,
            'date_from': date_from,
            'date_to': date_to,
            'per_page': per_page,
        }
    }

    return render(request, 'core/activity_log.html', context)


def _get_custom_fields_for_user(user):
    """Wrapper around shared utility for backward compatibility."""
    return get_custom_fields_for_user(user)


@login_required
@require_permission('can_csv_upload')
def download_sample_csv(request):
    """Download a sample CSV file for lead import, including user's custom fields"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_leads_template.csv"'

    writer = csv.writer(response)

    # Base columns (all importable Lead model fields)
    base_columns = [
        'client_name', 'contact_number', 'email', 'requirement', 'status',
        'follow_up_date', 'notes', 'category', 'source',
        'budget', 'timeline', 'decision_maker', 'lead_score',
        'converted_to_customer',
        'linkedin', 'instagram', 'facebook', 'twitter', 'youtube', 'website',
    ]

    # Get user's custom fields
    custom_fields_qs = _get_custom_fields_for_user(request.user)
    custom_field_names = list(custom_fields_qs.values_list('name', flat=True))

    # Header row
    writer.writerow(base_columns + custom_field_names)

    instructions = [
        '(Required) Full client name',
        '(Required) Contact number',
        '(Optional) Email address',
        '(Required) Lead requirement/details',
        '(Optional) new/contacted/qualified/proposal/negotiation/won/lost',
        '(Optional) Date YYYY-MM-DD',
        '(Optional) Any notes',
        '(Optional) Category name',
        '(Optional) Source name',
        '(Optional) Decimal/number',
        '(Optional) Date YYYY-MM-DD',
        '(Optional) true/false',
        '(Optional) Number 0-100',
        '(Optional) true/false',
        '(Optional) LinkedIn profile URL',
        '(Optional) Instagram profile URL',
        '(Optional) Facebook profile URL',
        '(Optional) Twitter/X profile URL',
        '(Optional) YouTube channel URL',
        '(Optional) Website URL',
    ]

    for cf in custom_fields_qs:
        if cf.field_type == 'text':
            hint = f'({"Required" if cf.required else "Optional"}) Text value'
        elif cf.field_type == 'number':
            hint = f'({"Required" if cf.required else "Optional"}) Number value'
        elif cf.field_type == 'date':
            hint = f'({"Required" if cf.required else "Optional"}) Date YYYY-MM-DD'
        elif cf.field_type == 'boolean':
            hint = f'({"Required" if cf.required else "Optional"}) true/false'
        elif cf.field_type == 'choice':
            choices_list = [c.strip() for c in cf.choices.split(',') if c.strip()]
            hint = f'({"Required" if cf.required else "Optional"}) Options: {"/".join(choices_list)}'
        elif cf.field_type == 'textarea':
            hint = f'({"Required" if cf.required else "Optional"}) Text value'
        else:
            hint = f'({"Required" if cf.required else "Optional"})'
        instructions.append(hint)
    writer.writerow(instructions)

    sample_rows = [
        ['John Doe', '123-456-7890', 'john@example.com', 'Need website development', 'new', '2026-02-01', 'Interested in web services', 'Development', 'Referral', '50000', '2026-06-01', 'true', '80', 'false', 'https://linkedin.com/in/johndoe', 'https://instagram.com/johndoe', '', '', '', 'https://johndoe.com'],
        ['Jane Smith', '098-765-4321', 'jane@example.com', 'Marketing campaign', 'contacted', '2026-02-05', 'Follow up next week', 'Marketing', 'Advertisement', '25000', '2026-04-15', 'false', '60', 'false', '', 'https://instagram.com/janesmith', 'https://facebook.com/janesmith', '', '', ''],
        ['Bob Johnson', '555-123-4567', 'bob@example.com', 'SEO consultation', 'qualified', '2026-02-10', 'High priority client', 'SEO', 'Online Search', '15000', '2026-03-20', 'true', '90', 'true', 'https://linkedin.com/in/bobjohnson', '', '', 'https://twitter.com/bobjohnson', 'https://youtube.com/@bobjohnson', 'https://bobjohnson.com'],
    ]

    for row in sample_rows:
        for cf in custom_fields_qs:
            if cf.field_type == 'text':
                row.append('Sample text')
            elif cf.field_type == 'number':
                row.append('100')
            elif cf.field_type == 'date':
                row.append('2026-03-01')
            elif cf.field_type == 'boolean':
                row.append('true')
            elif cf.field_type == 'choice':
                choices = [c.strip() for c in cf.choices.split(',') if c.strip()]
                row.append(choices[0] if choices else '')
            elif cf.field_type == 'textarea':
                row.append('Sample description text')
            else:
                row.append('')
        writer.writerow(row)

    return response


@login_required
@require_permission('can_view_leads')
def export_leads_csv(request):
    """Export all filtered leads as CSV including custom fields"""
    user = request.user
    profile = user.profile

    # Get leads based on role
    leads = get_user_leads(user)

    # Apply same filters as lead_list
    form = LeadFilterForm(request.GET)
    if form.is_valid():
        category = form.cleaned_data.get('category')
        source = form.cleaned_data.get('source')
        status = form.cleaned_data.get('status')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

        if category:
            leads = leads.filter(category=category)
        if source:
            leads = leads.filter(source=source)
        if status:
            leads = leads.filter(status=status)
        if start_date:
            leads = leads.filter(created_at__date__gte=start_date)
        if end_date:
            leads = leads.filter(created_at__date__lte=end_date)

    # Apply search filter
    search_query = request.GET.get('search', '').strip()
    if search_query:
        leads = leads.filter(
            Q(client_name__icontains=search_query) |
            Q(contact_number__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(requirement__icontains=search_query) |
            Q(notes__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(source__name__icontains=search_query)
        )

    # Apply analytics filters
    analytics_filter = request.GET.get('filter', '').strip()
    today = timezone.now().date()
    if analytics_filter == 'converted':
        leads = leads.filter(converted_to_customer=True)
    elif analytics_filter == 'overdue_followups':
        leads = leads.filter(follow_up_date__lt=today, follow_up_date__isnull=False)
    elif analytics_filter == 'today_followups':
        leads = leads.filter(follow_up_date=today)
    elif analytics_filter == 'upcoming_followups':
        leads = leads.filter(follow_up_date__gt=today)
    elif analytics_filter == 'has_score':
        leads = leads.filter(lead_score__gt=0).order_by('-lead_score')

    # Get custom fields for this user
    custom_fields_qs = _get_custom_fields_for_user(user)
    custom_field_names = list(custom_fields_qs.values_list('name', flat=True))

    # Build CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="leads_export_{timezone.now().strftime("%Y-%m-%d")}.csv"'

    writer = csv.writer(response)

    # Header row
    base_columns = [
        'Client Name', 'Contact Number', 'Email', 'Requirement', 'Status',
        'Follow-up Date', 'Notes', 'Category', 'Source',
        'Budget', 'Timeline', 'Decision Maker', 'Lead Score',
        'Converted to Customer',
        'LinkedIn', 'Instagram', 'Facebook', 'Twitter', 'YouTube', 'Website',
        'Added By', 'Created Date',
    ]
    header = base_columns + custom_field_names
    writer.writerow(header)

    # Prefetch profile links for all leads to avoid N+1 queries
    leads = leads.prefetch_related('profile_links')

    # Data rows
    export_count = 0
    for lead in leads:
        # Build profile link dict for this lead
        profile_links_dict = {}
        for pl in lead.profile_links.all():
            if pl.platform != 'other':
                profile_links_dict[pl.platform] = pl.url

        row = [
            lead.client_name,
            lead.contact_number,
            lead.email or '',
            lead.requirement,
            lead.get_status_display(),
            lead.follow_up_date.strftime('%Y-%m-%d') if lead.follow_up_date else '',
            lead.notes or '',
            lead.get_category_display_name(),
            lead.get_source_display_name(),
            lead.budget if lead.budget else '',
            lead.timeline.strftime('%Y-%m-%d') if lead.timeline else '',
            'Yes' if lead.decision_maker else 'No',
            lead.lead_score,
            'Yes' if lead.converted_to_customer else 'No',
            profile_links_dict.get('linkedin', ''),
            profile_links_dict.get('instagram', ''),
            profile_links_dict.get('facebook', ''),
            profile_links_dict.get('twitter', ''),
            profile_links_dict.get('youtube', ''),
            profile_links_dict.get('website', ''),
            lead.created_by.username if lead.created_by else '',
            lead.created_at.strftime('%Y-%m-%d %H:%M') if lead.created_at else '',
        ]

        # Add custom field values
        lead_custom = lead.custom_fields or {}
        for cf_name in custom_field_names:
            val = lead_custom.get(cf_name, '')
            if isinstance(val, bool):
                val = 'Yes' if val else 'No'
            row.append(val)

        writer.writerow(row)
        export_count += 1

    # Log the export activity
    log_activity(
        user=request.user,
        action='export',
        target_model='Lead',
        target_name=f'{export_count} leads',
        details=f'Exported {export_count} leads to CSV (with {len(custom_field_names)} custom fields)',
        request=request
    )

    return response


@login_required
@require_permission('can_edit_leads')
def update_lead_status(request, lead_id):
    """AJAX endpoint to quickly update lead status from the lead list table."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    lead = get_object_or_404(Lead, id=lead_id)

    if not _can_access_lead(request.user, lead):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if lead.is_deleted_for_user(request.user):
        return JsonResponse({'error': 'Lead not accessible'}, status=404)

    valid_statuses = dict(Lead.STATUS_CHOICES).keys()
    new_status = request.POST.get('status', '')
    if new_status not in valid_statuses:
        return JsonResponse({'error': 'Invalid status'}, status=400)

    old_status = lead.status
    lead.status = new_status

    update_fields = ['status']
    if old_status == new_status:
        lead.status_repeat_count = (lead.status_repeat_count or 1) + 1
    else:
        lead.status_repeat_count = 1
    update_fields.append('status_repeat_count')

    description = f'Status changed from {old_status} to {new_status}'
    details = f'Status updated: {old_status} -> {new_status}'

    if new_status == 'contacted':
        lead.contact_attempts = (lead.contact_attempts or 0) + 1
        update_fields.append('contact_attempts')
        if old_status == 'contacted':
            description = f'Contacted again (attempt #{lead.contact_attempts})'
            details = f'Contacted again. Total attempts: {lead.contact_attempts}'
        else:
            description = f'Status changed from {old_status} to contacted (attempt #{lead.contact_attempts})'
            details = f'Status updated: {old_status} -> contacted (attempt #{lead.contact_attempts})'

    lead.save(update_fields=update_fields)

    LeadActivity.objects.create(
        lead=lead,
        user=request.user,
        activity_type='status_update',
        description=description,
    )
    log_activity(
        user=request.user,
        action='update',
        target_model='Lead',
        target_id=lead.id,
        target_name=lead.client_name,
        details=details,
        request=request,
    )

    status_display = dict(Lead.STATUS_CHOICES).get(new_status, new_status)
    return JsonResponse({
        'success': True,
        'status': new_status,
        'status_display': status_display,
        'status_repeat_count': lead.status_repeat_count,
        'contact_attempts': lead.contact_attempts,
    })


@login_required
@require_permission('can_view_leads')
def lead_list(request):
    user = request.user
    profile = user.profile

    if request.method == 'POST':
        # Handle bulk delete
        lead_ids = request.POST.getlist('selected_leads')
        if 'bulk_delete' in request.POST and not lead_ids:
            messages.warning(request, 'Please select at least one lead to delete.')
            return redirect('lead_list')
        if lead_ids and 'bulk_delete' in request.POST:
            # Build permission filter in DB instead of Python loop
            now = timezone.now()
            perm_filter = Q(id__in=lead_ids, deleted_by__isnull=True)
            if profile.role == 'super_admin':
                pass  # Super admin can delete any
            elif profile.role == 'owner':
                perm_filter &= Q(owner=request.user)
            else:
                perm_filter &= (Q(created_by=request.user) | Q(assigned_to=request.user) | Q(owner=request.user))

            deleted_count = Lead.objects.filter(perm_filter).update(
                deleted_by=request.user,
                deleted_at=now,
            )

            if deleted_count:
                log_activity(
                    user=request.user,
                    action='delete',
                    target_model='Lead',
                    target_name=f'{deleted_count} leads',
                    details=f'Bulk deleted {deleted_count} leads',
                    request=request
                )

            messages.success(request, f'{deleted_count} lead(s) deleted successfully!')
            return redirect('lead_list')

    # Get leads based on role with optimized queries
    leads = get_user_leads(user).prefetch_related('activities')

    # Apply filters
    form = LeadFilterForm(request.GET)
    if form.is_valid():
        category = form.cleaned_data.get('category')
        source = form.cleaned_data.get('source')
        status = form.cleaned_data.get('status')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

        if category:
            leads = leads.filter(category=category)
        if source:
            leads = leads.filter(source=source)
        if status:
            leads = leads.filter(status=status)
        if start_date:
            leads = leads.filter(created_at__date__gte=start_date)
        if end_date:
            leads = leads.filter(created_at__date__lte=end_date)

    # Apply search filter
    search_query = request.GET.get('search', '').strip()
    if search_query:
        leads = leads.filter(
            Q(client_name__icontains=search_query) |
            Q(contact_number__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(requirement__icontains=search_query) |
            Q(notes__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(source__name__icontains=search_query)
        )

    # Apply analytics filters (from clickable analytics cards)
    analytics_filter = request.GET.get('filter', '').strip()
    today = timezone.now().date()
    if analytics_filter == 'converted':
        leads = leads.filter(converted_to_customer=True)
    elif analytics_filter == 'overdue_followups':
        leads = leads.filter(follow_up_date__lt=today, follow_up_date__isnull=False)
    elif analytics_filter == 'today_followups':
        leads = leads.filter(follow_up_date=today)
    elif analytics_filter == 'upcoming_followups':
        leads = leads.filter(follow_up_date__gt=today)
    elif analytics_filter == 'has_score':
        leads = leads.filter(lead_score__gt=0).order_by('-lead_score')

    # Build active filter label for display
    filter_labels = {
        'converted': 'Converted Leads',
        'overdue_followups': 'Overdue Follow-ups',
        'today_followups': "Today's Follow-ups",
        'upcoming_followups': 'Upcoming Follow-ups',
        'has_score': 'Leads with Score (High to Low)',
    }
    active_filter_label = filter_labels.get(analytics_filter, '')

    # Get deleted leads for owners and super admins
    deleted_leads = []
    if profile.role == 'owner':
        deleted_leads = Lead.get_deleted_leads_for_owner(user)
    elif profile.role == 'super_admin':
        deleted_leads = Lead.get_deleted_leads_for_admin()

    # Get custom fields for the user
    user_custom_fields = _get_custom_fields_for_user(user)
    custom_field_names = list(user_custom_fields.values_list('name', flat=True))

    # Calculate Summary Card Values
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timezone.timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    # Base queryset for stats (already filtered by user access)
    stats_qs = leads

    # Efficiently calculate all counts in fewer queries
    # NOTE: Q is already imported at module level; don't re-import it here
    # otherwise Python treats it as a local and breaks earlier Q(...) usage.
    from django.db.models import Count
    stats = stats_qs.aggregate(
        # Card 1: Total Leads (all statuses)
        today_total=Count('id', filter=Q(created_at__gte=today_start)),
        week_total=Count('id', filter=Q(created_at__gte=week_start)),
        month_total=Count('id', filter=Q(created_at__gte=month_start)),
        all_total=Count('id'),
        
        # Card 2: Won-related Leads (won, contacted, proposal statuses)
        today_won=Count('id', filter=Q(status='won', created_at__gte=today_start)),
        today_contacted=Count('id', filter=Q(status='contacted', created_at__gte=today_start)),
        today_proposal=Count('id', filter=Q(status='proposal', created_at__gte=today_start)),
        
        week_won=Count('id', filter=Q(status='won', created_at__gte=week_start)),
        week_contacted=Count('id', filter=Q(status='contacted', created_at__gte=week_start)),
        week_proposal=Count('id', filter=Q(status='proposal', created_at__gte=week_start)),
        
        month_won=Count('id', filter=Q(status='won', created_at__gte=month_start)),
        month_contacted=Count('id', filter=Q(status='contacted', created_at__gte=month_start)),
        month_proposal=Count('id', filter=Q(status='proposal', created_at__gte=month_start)),
        
        all_won=Count('id', filter=Q(status='won')),
        all_contacted=Count('id', filter=Q(status='contacted')),
        all_proposal=Count('id', filter=Q(status='proposal')),
        
        # Card 3: Lost-related Leads (lost, no_response, not_interested statuses)
        today_lost=Count('id', filter=Q(status='lost', created_at__gte=today_start)),
        today_no_response=Count('id', filter=Q(status='no_response', created_at__gte=today_start)),
        today_not_interested=Count('id', filter=Q(status='not_interested', created_at__gte=today_start)),
        
        week_lost=Count('id', filter=Q(status='lost', created_at__gte=week_start)),
        week_no_response=Count('id', filter=Q(status='no_response', created_at__gte=week_start)),
        week_not_interested=Count('id', filter=Q(status='not_interested', created_at__gte=week_start)),
        
        month_lost=Count('id', filter=Q(status='lost', created_at__gte=month_start)),
        month_no_response=Count('id', filter=Q(status='no_response', created_at__gte=month_start)),
        month_not_interested=Count('id', filter=Q(status='not_interested', created_at__gte=month_start)),
        
        all_lost=Count('id', filter=Q(status='lost')),
        all_no_response=Count('id', filter=Q(status='no_response')),
        all_not_interested=Count('id', filter=Q(status='not_interested')),
    )

    today_total_leads = stats['all_total']
    total_mini_stats = {
        'week': stats['week_total'],
        'month': stats['month_total'],
        'total': stats['all_total'],
    }

    # Card 2: Sum of won-related statuses for main display (TOTAL, not just today)
    today_new_leads = stats['all_won'] + stats['all_contacted'] + stats['all_proposal']
    new_mini_stats = {
        'week_won': stats['week_won'],
        'week_contacted': stats['week_contacted'],
        'week_proposal': stats['week_proposal'],
        'month_won': stats['month_won'],
        'month_contacted': stats['month_contacted'],
        'month_proposal': stats['month_proposal'],
        'total_won': stats['all_won'],
        'total_contacted': stats['all_contacted'],
        'total_proposal': stats['all_proposal'],
    }

    # Card 3: Sum of lost-related statuses for main display (TOTAL, not just today)
    today_won_leads = stats['all_lost'] + stats['all_no_response'] + stats['all_not_interested']
    won_mini_stats = {
        'week_lost': stats['week_lost'],
        'week_no_response': stats['week_no_response'],
        'week_not_interested': stats['week_not_interested'],
        'month_lost': stats['month_lost'],
        'month_no_response': stats['month_no_response'],
        'month_not_interested': stats['month_not_interested'],
        'total_lost': stats['all_lost'],
        'total_no_response': stats['all_no_response'],
        'total_not_interested': stats['all_not_interested'],
    }

    # Handle AJAX request for filtering/pagination
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Apply pagination to the filtered leads
        from django.core.paginator import Paginator
        per_page = get_table_page_size(request, 'lead_list', default=10)
        paginator = Paginator(leads, per_page)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        # Prepare leads data for AJAX response
        leads_data = []
        for lead in page_obj:
            latest_activity = lead.activities.first()
            if latest_activity:
                # Use description if available (it has the detailed changes), otherwise type display
                main_activity = latest_activity.description if latest_activity.description else latest_activity.get_activity_type_display()
            else:
                main_activity = 'None'
            
            lead_data = {
                'id': lead.id,
                'client_name': lead.client_name,
                'contact_number': lead.contact_number,
                'category': lead.get_category_display_name(),
                'source': lead.get_source_display_name(),
                'status': lead.status,
                'status_display': lead.get_status_display(),
                'status_repeat_count': lead.status_repeat_count,
                'contact_attempts': lead.contact_attempts,
                'follow_up_date': lead.follow_up_date.strftime('%Y-%m-%d') if lead.follow_up_date else None,
                'follow_up_display': f"{lead.follow_up_date} ({'Overdue' if lead.follow_up_date and lead.follow_up_date < timezone.now().date() else 'Today' if lead.follow_up_date and lead.follow_up_date == timezone.now().date() else ''})" if lead.follow_up_date else 'Not set',
                'created_by': lead.created_by.username if lead.created_by else '',
                'main_activity': main_activity,
                'created_at': lead.created_at.strftime('%b %d, %Y'),
                'email': lead.email or '',
                'is_overdue': lead.follow_up_date and lead.follow_up_date < timezone.now().date() if lead.follow_up_date else False,
                'is_today': lead.follow_up_date and lead.follow_up_date == timezone.now().date() if lead.follow_up_date else False,
            }
            # Add custom fields
            lead_custom = lead.custom_fields or {}
            custom_values = {}
            for cf_name in custom_field_names:
                val = lead_custom.get(cf_name, '')
                if isinstance(val, bool):
                    val = 'Yes' if val else 'No'
                custom_values[cf_name] = val
            lead_data['custom_fields'] = custom_values
            leads_data.append(lead_data)

        # Return JSON response
        from django.http import JsonResponse
        return JsonResponse({
            'leads': leads_data,
            'custom_field_names': custom_field_names,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': page_obj.paginator.num_pages,
            'total_count': paginator.count,
            'per_page': per_page,
        })

    # Apply pagination to the filtered leads
    from django.core.paginator import Paginator
    per_page = get_table_page_size(request, 'lead_list', default=10)
    paginator = Paginator(leads, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'leads': page_obj,
        'form': form,
        'deleted_leads': deleted_leads,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
        'active_filter_label': active_filter_label,
        'custom_field_names': custom_field_names,
        'custom_field_names_json': json.dumps(custom_field_names),
        'per_page': per_page,
        'today_total_leads': today_total_leads,
        'total_mini_stats': total_mini_stats,
        'today_new_leads': today_new_leads,
        'new_mini_stats': new_mini_stats,
        'today_won_leads': today_won_leads,
        'won_mini_stats': won_mini_stats,
    }

    return render(request, 'core/lead_list.html', context)


@login_required
@require_permission('can_view_deleted_leads')
def deleted_leads(request):
    """View to display deleted leads"""
    user = request.user
    profile = user.profile

    # Get deleted leads based on role
    if profile.role == 'super_admin':
        # Super admin sees all deleted leads
        deleted_leads = Lead.objects.filter(deleted_by__isnull=False).select_related('created_by', 'owner', 'category', 'source', 'deleted_by')
    elif profile.role == 'owner':
        # Owner sees deleted leads from their team
        from team.models import TeamMember
        staff_ids = TeamMember.objects.filter(boss=user).values_list('staff_id', flat=True)
        all_user_ids = [user.id] + list(staff_ids)
        deleted_leads = Lead.objects.filter(
            deleted_by_id__in=all_user_ids,
            owner_id__in=all_user_ids
        ).select_related('created_by', 'owner', 'category', 'source', 'deleted_by')
    else:
        # Regular user sees their own deleted leads
        deleted_leads = Lead.objects.filter(deleted_by=user).select_related('created_by', 'owner', 'category', 'source', 'deleted_by')

    # Apply filters
    form = LeadFilterForm(request.GET)
    if form.is_valid():
        category = form.cleaned_data.get('category')
        source = form.cleaned_data.get('source')
        status = form.cleaned_data.get('status')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

        if category:
            deleted_leads = deleted_leads.filter(category=category)
        if source:
            deleted_leads = deleted_leads.filter(source=source)
        if status:
            deleted_leads = deleted_leads.filter(status=status)
        if start_date:
            deleted_leads = deleted_leads.filter(created_at__date__gte=start_date)
        if end_date:
            deleted_leads = deleted_leads.filter(created_at__date__lte=end_date)

    # Apply search filter
    search_query = request.GET.get('search', '').strip()
    if search_query:
        deleted_leads = deleted_leads.filter(
            Q(client_name__icontains=search_query) |
            Q(contact_number__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(requirement__icontains=search_query) |
            Q(notes__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(source__name__icontains=search_query)
        )

    # Handle POST request for bulk delete
    if request.method == 'POST' and 'bulk_delete' in request.POST:
        lead_ids = request.POST.getlist('selected_leads')
        if lead_ids:
            # Only allow super admin to permanently delete leads
            if profile.role == 'super_admin':
                # Permanently delete the leads
                Lead.objects.filter(id__in=lead_ids, deleted_by__isnull=False).delete()
                messages.success(request, f'{len(lead_ids)} lead(s) permanently deleted!')
            else:
                messages.error(request, 'Only super admins can permanently delete leads.')

        return redirect('deleted_leads')

    # Handle AJAX request for filtering/pagination
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Apply pagination to the filtered leads
        from django.core.paginator import Paginator
        per_page = get_table_page_size(request, 'deleted_leads', default=10)
        paginator = Paginator(deleted_leads, per_page)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        # Prepare leads data for AJAX response
        leads_data = []
        for lead in page_obj:
            leads_data.append({
                'id': lead.id,
                'client_name': lead.client_name,
                'contact_number': lead.contact_number,
                'category': lead.get_category_display_name(),
                'source': lead.get_source_display_name(),
                'status': lead.status,
                'status_display': lead.get_status_display(),
                'follow_up_date': lead.follow_up_date.strftime('%Y-%m-%d') if lead.follow_up_date else None,
                'follow_up_display': f"{lead.follow_up_date} ({'Overdue' if lead.follow_up_date and lead.follow_up_date < timezone.now().date() else 'Today' if lead.follow_up_date and lead.follow_up_date == timezone.now().date() else ''})" if lead.follow_up_date else 'Not set',
                'created_by': lead.created_by.username if lead.created_by else '',
                'created_at': lead.created_at.strftime('%b %d, %Y'),
                'email': lead.email or '',
                'deleted_by': lead.deleted_by.username if lead.deleted_by else 'Unknown',
                'deleted_at': lead.deleted_at.strftime('%b %d, %Y %H:%M') if lead.deleted_at else 'Unknown',
                'is_overdue': lead.follow_up_date and lead.follow_up_date < timezone.now().date() if lead.follow_up_date else False,
                'is_today': lead.follow_up_date and lead.follow_up_date == timezone.now().date() if lead.follow_up_date else False,
            })

        # Return JSON response
        from django.http import JsonResponse
        return JsonResponse({
            'leads': leads_data,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': page_obj.paginator.num_pages,
            'total_count': paginator.count,
            'per_page': per_page,
        })

    # Apply pagination for regular request
    from django.core.paginator import Paginator
    per_page = get_table_page_size(request, 'deleted_leads', default=10)
    paginator = Paginator(deleted_leads, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'leads': page_obj,
        'form': form,
        'deleted_leads': [],  # Empty since this is the deleted leads page
        'is_deleted_leads_view': True,
        'per_page': per_page,
    }

    return render(request, 'core/deleted_leads.html', context)


@login_required
@require_permission('can_assign_leads')
def lead_assignment(request, lead_id):
    """View to assign leads to team members"""
    lead = get_object_or_404(Lead, id=lead_id)

    # Check permission
    if not (lead.owner == request.user or request.user.profile.role == 'super_admin'):
        messages.error(request, 'You do not have permission to assign this lead!')
        return redirect('dashboard')

    if request.method == 'POST':
        form = LeadAssignmentForm(request.POST, user=request.user)
        if form.is_valid():
            assigned_to = form.cleaned_data['assigned_to']
            reason = form.cleaned_data['reason']

            # Create assignment history
            LeadAssignmentHistory.objects.create(
                lead=lead,
                assigned_by=request.user,
                assigned_to=assigned_to,
                previous_assigned_to=lead.assigned_to,
                reason=reason
            )

            # Update lead assignment
            lead.assigned_to = assigned_to
            lead.assignment_date = timezone.now()
            lead.save()

            # Add activity log
            LeadActivity.objects.create(
                lead=lead,
                user=request.user,
                activity_type='assignment',
                description=f'Lead assigned to {assigned_to.username}. Reason: {reason}'
            )

            messages.success(request, f'Lead assigned to {assigned_to.username}')
            log_activity(
                user=request.user,
                action='update',
                target_model='Lead',
                target_id=lead.id,
                target_name=lead.client_name,
                details=f'Assigned lead to {assigned_to.username}',
                request=request
            )

            # Notify the assigned staff member
            notify(
                recipient=assigned_to,
                notification_type='lead_assigned',
                title='Lead Assigned to You',
                message=f'{request.user.username} assigned lead "{lead.client_name}" to you.',
                url=f'/leads/edit/{lead.id}/',
                sender=request.user,
            )

            return redirect('edit_lead', lead_id=lead.id)
        else:
            messages.error(request, 'Please fix the errors in the assignment form.')
    else:
        form = LeadAssignmentForm(user=request.user)

    return render(request, 'core/lead_assignment.html', {
        'form': form,
        'lead': lead
    })


@login_required
@require_permission('can_view_analytics')
def lead_analytics(request):
    """Comprehensive analytics: leads + team performance"""
    from django.db.models.functions import TruncMonth

    user = request.user
    profile = user.profile
    print_mode = request.GET.get('print') == '1'
    analytics_monthly_tf = _get_query_choice(request, 'monthly_tf', {'6m', '12m', '24m', 'all'}, '12m')
    analytics_team_tf = _get_query_choice(request, 'team_tf', {'all', 'today', 'week', '7d', '15d', '30d', '90d'}, '7d')
    status_sort_keys = {status_key for status_key, _ in Lead.STATUS_CHOICES}
    analytics_team_sort = _get_query_choice(request, 'team_sort', {'total', 'name', *status_sort_keys}, 'total')
    today = timezone.now().date()
    last_30 = today - timedelta(days=30)
    last_7 = today - timedelta(days=7)

    if profile.role == 'super_admin':
        leads = Lead.objects.filter(deleted_by__isnull=True)
    elif profile.role == 'owner' and profile.is_approved:
        staff_ids = list(TeamMember.objects.filter(boss=user).values_list('staff_id', flat=True))
        all_user_ids = [user.id] + staff_ids
        leads = Lead.objects.filter(owner__in=all_user_ids, deleted_by__isnull=True)
    else:
        leads = Lead.objects.filter(created_by=user, deleted_by__isnull=True)

    stats = leads.aggregate(
        total=Count('id'),
        new=Count('id', filter=Q(status='new')),
        contacted=Count('id', filter=Q(status='contacted')),
        qualified=Count('id', filter=Q(status='qualified')),
        won=Count('id', filter=Q(status='won')),
        lost=Count('id', filter=Q(status='lost')),
        converted=Count('id', filter=Q(converted_to_customer=True)),
        avg_score=Avg('lead_score'),
        overdue_followups=Count('id', filter=Q(follow_up_date__lt=today, follow_up_date__isnull=False)),
        today_followups=Count('id', filter=Q(follow_up_date=today)),
        upcoming_followups=Count('id', filter=Q(follow_up_date__gt=today)),
    )

    total_leads = stats['total']
    won_leads = stats['won']
    lost_leads = stats['lost'] or 0
    conversion_rate = round(won_leads / total_leads * 100, 1) if total_leads > 0 else 0
    loss_rate = round(lost_leads / total_leads * 100, 1) if total_leads > 0 else 0

    top_sources = leads.values('source__name').annotate(count=Count('id')).order_by('-count')[:5]
    top_categories = leads.values('category__name').annotate(count=Count('id')).order_by('-count')[:5]
    status_distribution = leads.values('status').annotate(count=Count('id')).order_by('-count')

    # Monthly trends (last 12 months) with real data
    twelve_months_ago = timezone.now() - timedelta(days=365)
    monthly_raw = (
        leads.filter(created_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(
            total=Count('id'),
            won=Count('id', filter=Q(status='won')),
        )
        .order_by('month')
    )
    monthly_labels = [m['month'].strftime('%b %Y') for m in monthly_raw]
    monthly_totals = [m['total'] for m in monthly_raw]
    monthly_won = [m['won'] for m in monthly_raw]

    # ========== TEAM ANALYTICS (owners & super admins) ==========
    employee_data = []
    show_team = profile.role in ('owner', 'super_admin')

    if show_team:
        if profile.role == 'super_admin':
            team_members = TeamMember.objects.filter(is_active=True).select_related('staff', 'staff__profile', 'role', 'boss')
        else:
            team_members = TeamMember.objects.filter(boss=user, is_active=True).select_related('staff', 'staff__profile', 'role')

        people = []
        if profile.role == 'owner':
            people.append({'user_obj': user, 'label': user.username + ' (You)', 'role': 'Owner'})
        for tm in team_members:
            people.append({'user_obj': tm.staff, 'label': tm.staff.username, 'role': tm.role.name if tm.role else 'Staff'})

        for p in people:
            u = p['user_obj']
            u_leads = leads.filter(created_by=u)
            s = u_leads.aggregate(
                total=Count('id'),
                won=Count('id', filter=Q(status='won')),
                lost=Count('id', filter=Q(status='lost')),
                contacted=Count('id', filter=Q(status='contacted')),
                new=Count('id', filter=Q(status='new')),
                last_30=Count('id', filter=Q(created_at__date__gte=last_30)),
                last_7=Count('id', filter=Q(created_at__date__gte=last_7)),
                overdue=Count('id', filter=Q(follow_up_date__lt=today, follow_up_date__isnull=False)),
            )
            t = s['total'] or 0
            w = s['won'] or 0
            cr = round(w / t * 100, 1) if t > 0 else 0
            employee_data.append({
                'username': p['label'],
                'role_name': p['role'],
                'total': t, 'won': w, 'lost': s['lost'] or 0,
                'contacted': s['contacted'] or 0, 'new': s['new'] or 0,
                'conversion_rate': cr,
                'last_30': s['last_30'] or 0, 'last_7': s['last_7'] or 0,
                'overdue': s['overdue'] or 0,
            })

        employee_data.sort(key=lambda x: x['total'], reverse=True)

    context = {
        'total_leads': total_leads,
        'won_leads': won_leads,
        'lost_leads': lost_leads,
        'new_leads': stats['new'],
        'contacted_leads': stats['contacted'],
        'qualified_leads': stats['qualified'],
        'conversion_rate': conversion_rate,
        'loss_rate': loss_rate,
        'top_sources': top_sources,
        'top_categories': top_categories,
        'status_distribution': status_distribution,
        'overdue_followups': stats['overdue_followups'],
        'today_followups': stats['today_followups'],
        'upcoming_followups': stats['upcoming_followups'],
        # Monthly charts
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_totals_json': json.dumps(monthly_totals),
        'monthly_won_json': json.dumps(monthly_won),
        # Status chart
        'status_labels_json': json.dumps([s['status'].title() for s in status_distribution]),
        'status_counts_json': json.dumps([s['count'] for s in status_distribution]),
        # Source chart
        'source_labels_json': json.dumps([s['source__name'] or 'Unknown' for s in top_sources]),
        'source_counts_json': json.dumps([s['count'] for s in top_sources]),
        # Category chart
        'cat_labels_json': json.dumps([c['category__name'] or 'Unknown' for c in top_categories]),
        'cat_counts_json': json.dumps([c['count'] for c in top_categories]),
        # Team
        'show_team': show_team,
        'employee_data': employee_data,
        'emp_names_json': json.dumps([e['username'] for e in employee_data]),
        'emp_totals_json': json.dumps([e['total'] for e in employee_data]),
        'emp_won_json': json.dumps([e['won'] for e in employee_data]),
        'emp_lost_json': json.dumps([e['lost'] for e in employee_data]),
        'emp_conv_json': json.dumps([e['conversion_rate'] for e in employee_data]),
        'print_mode': print_mode,
        'analytics_monthly_tf': analytics_monthly_tf,
        'analytics_team_tf': analytics_team_tf,
        'analytics_team_sort': analytics_team_sort,
    }

    return render(request, 'core/lead_analytics.html', context)


@login_required
@require_permission('can_view_analytics')
def analytics_monthly_chart_data(request):
    """AJAX endpoint for analytics monthly trend chart with timeframe filters."""
    from django.db.models.functions import TruncMonth

    user = request.user
    profile = user.profile
    timeframe = request.GET.get('timeframe', '12m')
    today = timezone.now().date()

    if profile.role == 'super_admin':
        leads = Lead.objects.filter(deleted_by__isnull=True)
    elif profile.role == 'owner' and profile.is_approved:
        staff_ids = list(TeamMember.objects.filter(boss=user).values_list('staff_id', flat=True))
        all_user_ids = [user.id] + staff_ids
        leads = Lead.objects.filter(owner__in=all_user_ids, deleted_by__isnull=True)
    else:
        leads = Lead.objects.filter(created_by=user, deleted_by__isnull=True)

    if timeframe == 'all':
        start_dt = leads.order_by('created_at').values_list('created_at', flat=True).first()
        start = start_dt.date() if start_dt else today
    else:
        months_map = {'6m': 6, '12m': 12, '24m': 24}
        months = months_map.get(timeframe, 12)
        start = today - timedelta(days=months * 30)

    monthly_raw = (
        leads.filter(created_at__date__gte=start)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(
            total=Count('id'),
            won=Count('id', filter=Q(status='won')),
            new=Count('id', filter=Q(status='new')),
            contacted=Count('id', filter=Q(status='contacted')),
        )
        .order_by('month')
    )

    labels = [m['month'].strftime('%b %Y') for m in monthly_raw]
    totals = [m['total'] for m in monthly_raw]
    won = [m['won'] for m in monthly_raw]
    new = [m['new'] for m in monthly_raw]
    contacted = [m['contacted'] for m in monthly_raw]

    label_map = {
        '6m': 'Last 6 Months',
        '12m': 'Last 12 Months',
        '24m': 'Last 24 Months',
        'all': 'All Time',
    }

    return JsonResponse({
        'labels': labels,
        'totals': totals,
        'won': won,
        'new': new,
        'contacted': contacted,
        'label': label_map.get(timeframe, 'Last 12 Months'),
        'timeframe': timeframe,
    })


@login_required
@require_permission('can_view_analytics')
def analytics_monthly_chart_export(request):
    """Export analytics monthly trend data with selected timeframe."""
    from django.db.models.functions import TruncMonth

    user = request.user
    profile = user.profile
    timeframe = request.GET.get('timeframe', '12m')
    today = timezone.now().date()

    if profile.role == 'super_admin':
        leads = Lead.objects.filter(deleted_by__isnull=True)
    elif profile.role == 'owner' and profile.is_approved:
        staff_ids = list(TeamMember.objects.filter(boss=user).values_list('staff_id', flat=True))
        all_user_ids = [user.id] + staff_ids
        leads = Lead.objects.filter(owner__in=all_user_ids, deleted_by__isnull=True)
    else:
        leads = Lead.objects.filter(created_by=user, deleted_by__isnull=True)

    if timeframe == 'all':
        start = None
    else:
        months_map = {'6m': 6, '12m': 12, '24m': 24}
        months = months_map.get(timeframe, 12)
        start = today - timedelta(days=months * 30)

    if start is not None:
        leads = leads.filter(created_at__date__gte=start)

    monthly_raw = (
        leads.annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(
            total=Count('id'),
            won=Count('id', filter=Q(status='won')),
            new=Count('id', filter=Q(status='new')),
            contacted=Count('id', filter=Q(status='contacted')),
        )
        .order_by('month')
    )

    tf_label = {
        '6m': '6Months',
        '12m': '12Months',
        '24m': '24Months',
        'all': 'AllTime',
    }.get(timeframe, '12Months')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Analytics_Monthly_Trends_{tf_label}_{today}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Month', 'Total Leads', 'Won', 'New', 'Contacted'])

    for row in monthly_raw:
        writer.writerow([
            row['month'].strftime('%b %Y'),
            row['total'],
            row['won'],
            row['new'],
            row['contacted'],
        ])

    return response


@login_required
def employee_analytics(request):
    """Employee-based analytics report — only for business owners and super admins"""
    from django.db.models.functions import TruncDate, TruncMonth
    from datetime import timedelta

    user = request.user
    profile = user.profile

    # Only owners and super admins can see this
    if profile.role not in ('owner', 'super_admin'):
        messages.error(request, 'You do not have permission to view employee analytics.')
        return redirect('dashboard')

    today = timezone.now().date()
    last_30 = today - timedelta(days=30)
    last_7 = today - timedelta(days=7)

    # Get staff members
    if profile.role == 'super_admin':
        # Super admin sees all owners' staff
        team_members = TeamMember.objects.filter(is_active=True).select_related('staff', 'staff__profile', 'role', 'boss')
        all_leads = Lead.objects.filter(deleted_by__isnull=True)
    else:
        # Owner sees their own staff
        team_members = TeamMember.objects.filter(boss=user, is_active=True).select_related('staff', 'staff__profile', 'role')
        staff_ids = list(team_members.values_list('staff_id', flat=True))
        all_user_ids = [user.id] + staff_ids
        all_leads = Lead.objects.filter(owner__in=all_user_ids, deleted_by__isnull=True)

    # Build per-employee stats
    employee_data = []

    # Include owner themselves first (for owner role)
    if profile.role == 'owner':
        owner_leads = all_leads.filter(created_by=user)
        owner_stats = owner_leads.aggregate(
            total=Count('id'),
            new=Count('id', filter=Q(status='new')),
            contacted=Count('id', filter=Q(status='contacted')),
            qualified=Count('id', filter=Q(status='qualified')),
            proposal=Count('id', filter=Q(status='proposal')),
            negotiation=Count('id', filter=Q(status='negotiation')),
            won=Count('id', filter=Q(status='won')),
            lost=Count('id', filter=Q(status='lost')),
            converted=Count('id', filter=Q(converted_to_customer=True)),
            last_30_leads=Count('id', filter=Q(created_at__date__gte=last_30)),
            last_7_leads=Count('id', filter=Q(created_at__date__gte=last_7)),
            overdue_followups=Count('id', filter=Q(follow_up_date__lt=today, follow_up_date__isnull=False)),
            today_followups=Count('id', filter=Q(follow_up_date=today)),
        )
        total = owner_stats['total'] or 0
        won = owner_stats['won'] or 0
        conversion_rate = round((won / total * 100), 1) if total > 0 else 0

        # Recent activity count
        recent_activities = ActivityLog.objects.filter(user=user, timestamp__date__gte=last_7).count()

        employee_data.append({
            'user': user,
            'username': user.username + ' (You)',
            'email': user.email,
            'role_name': 'Owner',
            'joined_date': None,
            'total_leads': total,
            'new': owner_stats['new'] or 0,
            'contacted': owner_stats['contacted'] or 0,
            'qualified': owner_stats['qualified'] or 0,
            'proposal': owner_stats['proposal'] or 0,
            'negotiation': owner_stats['negotiation'] or 0,
            'won': won,
            'lost': owner_stats['lost'] or 0,
            'converted': owner_stats['converted'] or 0,
            'conversion_rate': conversion_rate,
            'last_30_leads': owner_stats['last_30_leads'] or 0,
            'last_7_leads': owner_stats['last_7_leads'] or 0,
            'overdue_followups': owner_stats['overdue_followups'] or 0,
            'today_followups': owner_stats['today_followups'] or 0,
            'recent_activities': recent_activities,
        })

    # Staff members
    for tm in team_members:
        staff_user = tm.staff
        staff_leads = all_leads.filter(created_by=staff_user)

        stats = staff_leads.aggregate(
            total=Count('id'),
            new=Count('id', filter=Q(status='new')),
            contacted=Count('id', filter=Q(status='contacted')),
            qualified=Count('id', filter=Q(status='qualified')),
            proposal=Count('id', filter=Q(status='proposal')),
            negotiation=Count('id', filter=Q(status='negotiation')),
            won=Count('id', filter=Q(status='won')),
            lost=Count('id', filter=Q(status='lost')),
            converted=Count('id', filter=Q(converted_to_customer=True)),
            last_30_leads=Count('id', filter=Q(created_at__date__gte=last_30)),
            last_7_leads=Count('id', filter=Q(created_at__date__gte=last_7)),
            overdue_followups=Count('id', filter=Q(follow_up_date__lt=today, follow_up_date__isnull=False)),
            today_followups=Count('id', filter=Q(follow_up_date=today)),
        )
        total = stats['total'] or 0
        won = stats['won'] or 0
        conversion_rate = round((won / total * 100), 1) if total > 0 else 0

        recent_activities = ActivityLog.objects.filter(user=staff_user, timestamp__date__gte=last_7).count()

        employee_data.append({
            'user': staff_user,
            'username': staff_user.username,
            'email': staff_user.email,
            'role_name': tm.role.name if tm.role else 'No Role',
            'joined_date': tm.joined_date,
            'total_leads': total,
            'new': stats['new'] or 0,
            'contacted': stats['contacted'] or 0,
            'qualified': stats['qualified'] or 0,
            'proposal': stats['proposal'] or 0,
            'negotiation': stats['negotiation'] or 0,
            'won': won,
            'lost': stats['lost'] or 0,
            'converted': stats['converted'] or 0,
            'conversion_rate': conversion_rate,
            'last_30_leads': stats['last_30_leads'] or 0,
            'last_7_leads': stats['last_7_leads'] or 0,
            'overdue_followups': stats['overdue_followups'] or 0,
            'today_followups': stats['today_followups'] or 0,
            'recent_activities': recent_activities,
        })

    # Sort by total leads descending
    employee_data.sort(key=lambda x: x['total_leads'], reverse=True)

    # Summary totals
    total_employees = len(employee_data)
    grand_total_leads = sum(e['total_leads'] for e in employee_data)
    grand_won = sum(e['won'] for e in employee_data)
    grand_lost = sum(e['lost'] for e in employee_data)
    grand_converted = sum(e['converted'] for e in employee_data)
    grand_conversion_rate = round((grand_won / grand_total_leads * 100), 1) if grand_total_leads > 0 else 0
    grand_last_30 = sum(e['last_30_leads'] for e in employee_data)
    grand_overdue = sum(e['overdue_followups'] for e in employee_data)

    # Chart data: employee names, total leads, won leads, conversion rates
    chart_names = json.dumps([e['username'] for e in employee_data])
    chart_total = json.dumps([e['total_leads'] for e in employee_data])
    chart_won = json.dumps([e['won'] for e in employee_data])
    chart_lost = json.dumps([e['lost'] for e in employee_data])
    chart_new = json.dumps([e['new'] for e in employee_data])
    chart_contacted = json.dumps([e['contacted'] for e in employee_data])
    chart_conversion = json.dumps([e['conversion_rate'] for e in employee_data])
    chart_last30 = json.dumps([e['last_30_leads'] for e in employee_data])

    # Top performer
    top_performer = employee_data[0] if employee_data else None

    # Best conversion rate
    best_converter = max(employee_data, key=lambda x: x['conversion_rate']) if employee_data else None

    context = {
        'employee_data': employee_data,
        'total_employees': total_employees,
        'grand_total_leads': grand_total_leads,
        'grand_won': grand_won,
        'grand_lost': grand_lost,
        'grand_converted': grand_converted,
        'grand_conversion_rate': grand_conversion_rate,
        'grand_last_30': grand_last_30,
        'grand_overdue': grand_overdue,
        'top_performer': top_performer,
        'best_converter': best_converter,
        # Chart JSON
        'chart_names': chart_names,
        'chart_total': chart_total,
        'chart_won': chart_won,
        'chart_lost': chart_lost,
        'chart_new': chart_new,
        'chart_contacted': chart_contacted,
        'chart_conversion': chart_conversion,
        'chart_last30': chart_last30,
    }

    return render(request, 'core/employee_analytics.html', context)


@login_required
@require_permission('can_manage_custom_fields')
def custom_fields(request):
    """View to manage custom fields"""
    if request.method == 'POST':
        form = CustomFieldForm(request.POST)
        if form.is_valid():
            custom_field = form.save(commit=False)
            custom_field.owner = request.user
            custom_field.save()
            messages.success(request, 'Custom field created successfully!')
            return redirect('custom_fields')
        else:
            messages.error(request, 'Please fix the errors in the custom field form.')
    else:
        form = CustomFieldForm()

    # Show custom fields based on role (staff sees own + boss's, owner sees own, super_admin sees all)
    # Note: listing shows ALL fields including inactive ones (for management)
    if request.user.is_superuser:
        custom_fields = CustomField.objects.all().select_related('owner')
    elif request.user.profile.role == 'staff':
        try:
            team_member = TeamMember.objects.get(staff=request.user)
            custom_fields = CustomField.objects.filter(
                Q(owner=team_member.boss) | Q(owner=request.user)
            ).select_related('owner')
        except TeamMember.DoesNotExist:
            custom_fields = CustomField.objects.filter(owner=request.user)
    else:
        custom_fields = CustomField.objects.filter(owner=request.user)

    return render(request, 'core/custom_fields.html', {
        'form': form,
        'custom_fields': custom_fields,
        'is_super_admin': request.user.is_superuser
    })


@login_required
@require_permission('can_manage_custom_fields')
def edit_custom_field(request, field_id):
    """View to edit a custom field - only name, required, is_active can be changed"""
    if request.user.is_superuser:
        custom_field = get_object_or_404(CustomField, id=field_id)
    else:
        custom_field = get_object_or_404(CustomField, id=field_id, owner=request.user)

    if request.method == 'POST':
        old_name = custom_field.name
        new_name = request.POST.get('name', '').strip()
        new_required = request.POST.get('required') == 'on'
        new_is_active = request.POST.get('is_active') == 'on'

        if not new_name:
            messages.error(request, 'Field name is required.')
            return redirect('custom_fields')

        # Check if new name already exists for this owner (excluding current field)
        if new_name != old_name and CustomField.objects.filter(name=new_name, owner=custom_field.owner).exclude(id=field_id).exists():
            messages.error(request, f'A custom field with name "{new_name}" already exists.')
            return redirect('custom_fields')

        # If name changed, update the key in all leads' custom_fields JSON
        if new_name != old_name:
            leads_with_data = Lead.objects.filter(
                owner=custom_field.owner,
                custom_fields__has_key=old_name
            )
            for lead in leads_with_data:
                if old_name in lead.custom_fields:
                    lead.custom_fields[new_name] = lead.custom_fields.pop(old_name)
                    lead.save(update_fields=['custom_fields'])

        # Update only allowed fields
        custom_field.name = new_name
        custom_field.required = new_required
        custom_field.is_active = new_is_active
        custom_field.save()

        messages.success(request, f'Custom field "{new_name}" updated successfully!')
        return redirect('custom_fields')

    return redirect('custom_fields')


@login_required
@require_permission('can_manage_custom_fields')
def delete_custom_field(request, field_id):
    """View to delete a custom field - blocked if leads have data for this field"""
    # Super admin can delete any custom field, others can only delete their own
    if request.user.is_superuser:
        custom_field = get_object_or_404(CustomField, id=field_id)
    else:
        custom_field = get_object_or_404(CustomField, id=field_id, owner=request.user)

    # Check if any leads have data for this field
    data_count = custom_field.lead_data_count()
    if data_count > 0:
        messages.error(
            request,
            f'Cannot delete "{custom_field.name}" — {data_count} lead(s) have data for this field. '
            f'You can deactivate it instead by turning off "Active" in the Edit option.'
        )
        return redirect('custom_fields')

    if request.method == 'POST':
        custom_field.delete()
        messages.success(request, 'Custom field deleted successfully!')
        return redirect('custom_fields')

    return render(request, 'core/delete_custom_field.html', {
        'custom_field': custom_field
    })


# Category/source management for super admin (global) and owner (private)


@login_required
def manage_categories(request):
    role = request.user.profile.role
    if role not in ('super_admin', 'owner'):
        return HttpResponseForbidden('Not allowed')

    private_limit = 5

    if request.method == 'POST':
        name = request.POST.get('name', '')
        if name:
            name = name.strip()
            if role == 'super_admin':
                if Category.objects.filter(name__iexact=name).exists():
                    messages.error(request, f'Category "{name}" already exists! Please choose a different name.')
                else:
                    Category.objects.create(name=name)
                    messages.success(request, f'Category "{name}" added successfully!')
                    log_activity(
                        user=request.user,
                        action='create',
                        target_model='Category',
                        target_name=name,
                        details=f'Created category: {name}',
                        request=request
                    )
            else:
                if OwnerCategory.objects.filter(owner=request.user, name__iexact=name).exists():
                    messages.error(request, f'Private category "{name}" already exists!')
                elif OwnerCategory.objects.filter(owner=request.user).count() >= private_limit:
                    messages.error(request, f'You can add up to {private_limit} private categories only.')
                else:
                    OwnerCategory.objects.create(owner=request.user, name=name)
                    messages.success(request, f'Private category "{name}" added successfully!')
                    log_activity(
                        user=request.user,
                        action='create',
                        target_model='OwnerCategory',
                        target_name=name,
                        details=f'Created private category: {name}',
                        request=request
                    )

    if role == 'super_admin':
        categories = list(Category.objects.all())
        for c in categories:
            c.usage_count = c.lead_set.count()

        other_categories = Lead.objects.exclude(category_other__isnull=True).exclude(category_other='').values_list(
            'category_other', flat=True).distinct()
        is_private_scope = False
    else:
        categories = list(OwnerCategory.objects.filter(owner=request.user))
        for c in categories:
            c.usage_count = Lead.objects.filter(
                owner=request.user,
                category__isnull=True,
                category_other__iexact=c.name,
            ).count()

        global_names = set(Category.objects.values_list('name', flat=True))
        owner_names = set(OwnerCategory.objects.filter(owner=request.user).values_list('name', flat=True))
        other_categories = Lead.objects.filter(owner=request.user).exclude(category_other__isnull=True).exclude(
            category_other=''
        ).values_list('category_other', flat=True).distinct()
        other_categories = [c for c in other_categories if c not in global_names and c not in owner_names]
        is_private_scope = True

    context = {
        'categories': categories,
        'other_categories': other_categories,
        'is_private_scope': is_private_scope,
        'private_limit': private_limit,
        'private_count': OwnerCategory.objects.filter(owner=request.user).count() if role == 'owner' else 0,
    }

    return render(request, 'core/manage_categories.html', context)


@login_required
def edit_category(request, category_id):
    """View to edit a category"""
    role = request.user.profile.role
    if role not in ('super_admin', 'owner'):
        return HttpResponseForbidden('Not allowed')

    if role == 'super_admin':
        category = get_object_or_404(Category, id=category_id)
    else:
        category = get_object_or_404(OwnerCategory, id=category_id, owner=request.user)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Category name cannot be empty!')
            return redirect('manage_categories')

        if role == 'super_admin':
            if Category.objects.filter(name__iexact=name).exclude(id=category_id).exists():
                messages.error(request, f'Category "{name}" already exists! Please choose a different name.')
                return redirect('manage_categories')
        else:
            if OwnerCategory.objects.filter(owner=request.user, name__iexact=name).exclude(id=category_id).exists():
                messages.error(request, f'Private category "{name}" already exists!')
                return redirect('manage_categories')

        old_name = category.name
        category.name = name
        category.save()
        messages.success(request, f'Category updated from "{old_name}" to "{name}"!')
        log_activity(
            user=request.user,
            action='update',
            target_model='Category' if role == 'super_admin' else 'OwnerCategory',
            target_id=category.id,
            target_name=category.name,
            details=f'Updated category from "{old_name}" to "{category.name}"',
            request=request
        )
        return redirect('manage_categories')

    return redirect('manage_categories')


@login_required
def delete_category(request, category_id):
    """View to delete a category"""
    role = request.user.profile.role
    if role not in ('super_admin', 'owner'):
        return HttpResponseForbidden('Not allowed')

    if role == 'super_admin':
        category = get_object_or_404(Category, id=category_id)
    else:
        category = get_object_or_404(OwnerCategory, id=category_id, owner=request.user)

    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted successfully!')
        log_activity(
            user=request.user,
            action='delete',
            target_model='Category' if role == 'super_admin' else 'OwnerCategory',
            target_id=category_id,
            target_name=category_name,
            details=f'Deleted category: {category_name}',
            request=request
        )
        return redirect('manage_categories')

    return redirect('manage_categories')


@login_required
@require_permission('can_view_leads')
def search_leads(request):
    """API endpoint to search for leads to update"""
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'leads': []})

    # Get leads based on user permissions
    leads = get_user_leads(request.user)

    # Filter leads by search query
    leads = leads.filter(
        Q(client_name__icontains=query) |
        Q(contact_number__icontains=query) |
        Q(email__icontains=query) |
        Q(requirement__icontains=query)
    ).select_related('created_by', 'owner', 'category', 'source')[:10]  # Limit to 10 results

    # Format leads for JSON response
    leads_data = []
    for lead in leads:
        leads_data.append({
            'id': lead.id,
            'client_name': lead.client_name,
            'contact_number': lead.contact_number,
            'email': lead.email or '',
            'requirement': lead.requirement,
            'status': lead.get_status_display(),
            'created_at': lead.created_at.strftime('%Y-%m-%d'),
            'category': lead.get_category_display_name(),
            'source': lead.get_source_display_name(),
        })

    return JsonResponse({'leads': leads_data})


@login_required
def manage_sources(request):
    role = request.user.profile.role
    if role not in ('super_admin', 'owner'):
        return HttpResponseForbidden('Not allowed')

    private_limit = 5

    # Handle add new source
    if request.method == 'POST' and 'name' in request.POST:
        name = request.POST.get('name', '')
        if name:
            name = name.strip()
            if role == 'super_admin':
                if Source.objects.filter(name__iexact=name).exists():
                    messages.error(request, f'Source "{name}" already exists! Please choose a different name.')
                else:
                    source = Source.objects.create(name=name)
                    messages.success(request, f'Source "{name}" added successfully!')
                    log_activity(
                        user=request.user,
                        action='create',
                        target_model='Source',
                        target_id=source.id,
                        target_name=source.name,
                        details=f'Created source: {source.name}',
                        request=request
                    )
            else:
                if OwnerSource.objects.filter(owner=request.user, name__iexact=name).exists():
                    messages.error(request, f'Private source "{name}" already exists!')
                elif OwnerSource.objects.filter(owner=request.user).count() >= private_limit:
                    messages.error(request, f'You can add up to {private_limit} private sources only.')
                else:
                    source = OwnerSource.objects.create(owner=request.user, name=name)
                    messages.success(request, f'Private source "{name}" added successfully!')
                    log_activity(
                        user=request.user,
                        action='create',
                        target_model='OwnerSource',
                        target_id=source.id,
                        target_name=source.name,
                        details=f'Created private source: {source.name}',
                        request=request
                    )

    # Get sources by role scope
    sources_qs = Source.objects.all() if role == 'super_admin' else OwnerSource.objects.filter(owner=request.user)
    
    # Apply search filter
    search_query = request.GET.get('search', '').strip()
    if search_query:
        sources_qs = sources_qs.filter(name__icontains=search_query)

    # Get total count
    total_sources = Source.objects.count() if role == 'super_admin' else OwnerSource.objects.filter(owner=request.user).count()
    filtered_count = sources_qs.count()

    sources = list(sources_qs)
    for s in sources:
        if role == 'super_admin':
            s.usage_count = s.lead_set.count()
        else:
            s.usage_count = Lead.objects.filter(
                owner=request.user,
                source__isnull=True,
                source_other__iexact=s.name,
            ).count()

    if role == 'super_admin':
        other_sources = Lead.objects.exclude(source_other__isnull=True).exclude(source_other='').values_list(
            'source_other',
            flat=True,
        ).distinct()
    else:
        global_names = set(Source.objects.values_list('name', flat=True))
        owner_names = set(OwnerSource.objects.filter(owner=request.user).values_list('name', flat=True))
        other_sources = Lead.objects.filter(owner=request.user).exclude(source_other__isnull=True).exclude(
            source_other=''
        ).values_list('source_other', flat=True).distinct()
        other_sources = [s for s in other_sources if s not in global_names and s not in owner_names]
    
    # Apply search to other_sources if needed
    if search_query:
        other_sources = [s for s in other_sources if search_query.lower() in s.lower()]

    context = {
        'sources': sources,
        'other_sources': other_sources,
        'total_sources': total_sources,
        'filtered_count': filtered_count,
        'search_query': search_query,
        'is_private_scope': role == 'owner',
        'private_limit': private_limit,
        'private_count': OwnerSource.objects.filter(owner=request.user).count() if role == 'owner' else 0,
    }

    return render(request, 'core/manage_sources.html', context)


@login_required
def edit_source(request, source_id):
    """View to edit a source"""
    role = request.user.profile.role
    if role not in ('super_admin', 'owner'):
        return HttpResponseForbidden('Not allowed')

    source = get_object_or_404(Source, id=source_id) if role == 'super_admin' else get_object_or_404(
        OwnerSource,
        id=source_id,
        owner=request.user,
    )
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Source name cannot be empty!')
            return redirect('manage_sources')

        if role == 'super_admin':
            duplicate_exists = Source.objects.filter(name__iexact=name).exclude(id=source.id).exists()
        else:
            duplicate_exists = OwnerSource.objects.filter(owner=request.user, name__iexact=name).exclude(id=source.id).exists()

        if duplicate_exists:
            messages.error(request, f'Source "{name}" already exists! Please choose a different name.')
            return redirect('manage_sources')

        old_name = source.name
        source.name = name
        source.save()
        messages.success(request, f'Source updated from "{old_name}" to "{source.name}"!')
        log_activity(
            user=request.user,
            action='update',
            target_model='Source' if role == 'super_admin' else 'OwnerSource',
            target_id=source.id,
            target_name=source.name,
            details=f'Updated source from "{old_name}" to "{source.name}"',
            request=request
        )
        return redirect('manage_sources')

    if role != 'super_admin':
        return redirect('manage_sources')

    else:
        from .forms import SourceForm
        form = SourceForm(instance=source)
    
    return render(request, 'core/edit_source.html', {
        'form': form,
        'source': source
    })


@login_required
def delete_source(request, source_id):
    """View to delete a source"""
    role = request.user.profile.role
    if role not in ('super_admin', 'owner'):
        return HttpResponseForbidden('Not allowed')

    source = get_object_or_404(Source, id=source_id) if role == 'super_admin' else get_object_or_404(
        OwnerSource,
        id=source_id,
        owner=request.user,
    )
    
    if request.method == 'POST':
        source_name = source.name
        source.delete()
        messages.success(request, f'Source "{source_name}" deleted successfully!')
        log_activity(
            user=request.user,
            action='delete',
            target_model='Source' if role == 'super_admin' else 'OwnerSource',
            target_id=source_id,
            target_name=source_name,
            details=f'Deleted source: {source_name}',
            request=request
        )
        return redirect('manage_sources')
    
    if role != 'super_admin':
        return redirect('manage_sources')

    return render(request, 'core/delete_source.html', {
        'source': source
    })


# =====================================================
# NOTIFICATION VIEWS
# =====================================================

@login_required
def all_notifications(request):
    """View to display all notifications for the current user"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('sender').order_by('-created_at')

    # Paginate
    from django.core.paginator import Paginator
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    return render(request, 'core/all_notifications.html', {
        'page_obj': page_obj,
        'unread_count': unread_count,
    })


@login_required
def mark_notification_read(request, notification_id):
    """Mark a single notification as read and redirect to its URL"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()

    if notification.url:
        return redirect(notification.url)
    return redirect('all_notifications')


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('all_notifications')


@login_required
def clear_all_notifications(request):
    """Delete all notifications for the current user"""
    if request.method == 'POST':
        Notification.objects.filter(recipient=request.user).delete()
        messages.success(request, 'All notifications cleared.')
    return redirect('all_notifications')


@login_required
def api_notifications(request):
    """
    Lightweight JSON API for navbar notifications — called via AJAX.
    This avoids a context processor hitting the DB on every single request.
    """
    from django.http import JsonResponse

    unread_qs = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).select_related('sender').order_by('-created_at')[:10]

    unread_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    notifications_data = []
    for n in unread_qs:
        notifications_data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message[:80],  # truncate for dropdown
            'icon_class': n.icon_class,
            'time_ago': n.time_ago,
            'url': f'/leads/notifications/read/{n.id}/',
            'is_read': n.is_read,
        })

    return JsonResponse({
        'unread_count': unread_count,
        'notifications': notifications_data,
    })


@login_required
def api_chat_unread_count(request):
    """Return unread direct-message count for live sidebar badge updates."""
    unread_chat_count = DirectMessage.objects.filter(
        recipient=request.user,
        read_at__isnull=True,
    ).count()

    return JsonResponse({
        'unread_chat_count': unread_chat_count,
    })
