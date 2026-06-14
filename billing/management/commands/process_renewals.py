from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from billing.models import Payment, Subscription, enforce_plan_limits, format_price
from core.utils import notify, send_email


class Command(BaseCommand):
    help = 'Process auto-renew workflow for manual-payment subscriptions.'

    def handle(self, *args, **options):
        today = date.today()
        site_base_url = str(getattr(settings, 'SITE_BASE_URL', '') or '').rstrip('/')
        my_plan_url = f'{site_base_url}/billing/my-plan/' if site_base_url else '/billing/my-plan/'
        notice_days = max(int(getattr(settings, 'RENEWAL_NOTICE_DAYS', 7)), 1)
        grace_days = max(int(getattr(settings, 'RENEWAL_GRACE_DAYS', 3)), 0)

        reminder_days_raw = str(getattr(settings, 'RENEWAL_REMINDER_DAYS', '7,3,1,0'))
        reminder_days = []
        for chunk in reminder_days_raw.split(','):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                reminder_days.append(int(chunk))
            except ValueError:
                continue

        if not reminder_days:
            reminder_days = [7, 3, 1, 0]

        rollover_candidates = Subscription.objects.exclude(queued_renewal_start_date__isnull=True)
        rollovers_applied = 0
        for sub in rollover_candidates:
            if sub.apply_queued_renewal_if_due(today=today):
                rollovers_applied += 1

        active_subscriptions = (
            Subscription.objects
            .filter(is_active=True, auto_renew=True)
            .exclude(end_date__isnull=True)
            .select_related('owner', 'plan')
        )

        super_admins = list(User.objects.filter(profile__role='super_admin', is_active=True))

        created_requests = 0
        sent_reminders = 0
        auto_deactivated = 0

        for subscription in active_subscriptions:
            owner = subscription.owner
            days_to_expiry = (subscription.end_date - today).days
            created_in_this_run = False

            pending_renewal = (
                Payment.objects
                .filter(
                    subscription=subscription,
                    is_renewal=True,
                    is_paid=False,
                    is_rejected=False,
                )
                .order_by('-created_at')
                .first()
            )

            if 0 <= days_to_expiry <= notice_days and not pending_renewal and not subscription.queued_renewal_start_date:
                amount = subscription.get_current_price() or Decimal('0.00')
                pending_renewal = Payment.objects.create(
                    user=owner,
                    subscription=subscription,
                    amount=amount,
                    original_amount=amount,
                    discount_amount=Decimal('0.00'),
                    discount_source='none',
                    due_date=subscription.end_date,
                    payment_method='bank_transfer',
                    payer_name=owner.get_full_name() or owner.username,
                    payer_email=owner.email or '',
                    is_renewal=True,
                    is_paid=False,
                    notes='Auto-generated renewal request (manual payment required).',
                )
                created_requests += 1
                created_in_this_run = True

                notify(
                    recipient=owner,
                    notification_type='system',
                    title='Renewal Request Created',
                    message=(
                        f'Auto-renew is enabled. Your renewal request for {subscription.plan.name} '
                        f'({subscription.get_billing_cycle_display()}) has been created. Please submit manual payment proof.'
                    ),
                    url='/billing/my-plan/',
                )

                for admin_user in super_admins:
                    notify(
                        recipient=admin_user,
                        notification_type='payment_received',
                        title='Auto Renewal Request',
                        message=(
                            f'{owner.username} renewal request was auto-created for '
                            f'{subscription.plan.name} ({subscription.get_billing_cycle_display()}).'
                        ),
                        url='/billing/manage-plans/',
                        sender=owner,
                    )

                send_email(
                    to_email=owner.email,
                    subject='LeadSync - Renewal Request Created',
                    template_name='emails/renewal_reminder.html',
                    context={
                        'username': owner.username,
                        'plan_name': subscription.plan.name if not subscription.is_custom_plan else 'Custom Plan',
                        'billing_cycle': subscription.get_billing_cycle_display(),
                        'amount': format_price(amount),
                        'due_date': subscription.end_date,
                        'days_to_expiry': days_to_expiry,
                        'expired_days': 0,
                        'dashboard_url': my_plan_url,
                        'grace_days': grace_days,
                        'is_first_notice': True,
                    },
                )

            renewal_details_submitted = bool(
                pending_renewal and (
                    (pending_renewal.transaction_id and str(pending_renewal.transaction_id).strip())
                    or pending_renewal.payment_proof
                )
            )

            # If transaction details/proof are already provided, do not send more reminders.
            if pending_renewal and (not created_in_this_run) and (not renewal_details_submitted) and days_to_expiry in reminder_days:
                reminder_token = f'[REMINDER_DAY_{days_to_expiry}]'
                notes_text = pending_renewal.notes or ''
                if reminder_token not in notes_text:
                    notify(
                        recipient=owner,
                        notification_type='system',
                        title='Renewal Payment Reminder',
                        message=(
                            f'Your plan renewal payment for {subscription.plan.name} is pending. '
                            f'Please submit manual payment proof before service interruption.'
                        ),
                        url='/billing/my-plan/',
                    )

                    send_email(
                        to_email=owner.email,
                        subject='LeadSync - Renewal Payment Reminder',
                        template_name='emails/renewal_reminder.html',
                        context={
                            'username': owner.username,
                            'plan_name': subscription.plan.name if not subscription.is_custom_plan else 'Custom Plan',
                            'billing_cycle': subscription.get_billing_cycle_display(),
                            'amount': format_price(pending_renewal.amount),
                            'due_date': subscription.end_date,
                            'days_to_expiry': days_to_expiry,
                            'expired_days': abs(days_to_expiry) if days_to_expiry < 0 else 0,
                            'dashboard_url': my_plan_url,
                            'grace_days': grace_days,
                            'is_first_notice': False,
                        },
                    )

                    pending_renewal.notes = (notes_text + '\n' + reminder_token).strip()
                    pending_renewal.save(update_fields=['notes'])
                    sent_reminders += 1

            if days_to_expiry < 0 and pending_renewal:
                days_past_expiry = abs(days_to_expiry)
                if days_past_expiry > grace_days and subscription.is_active:
                    if '[AUTO_DEACTIVATED_UNPAID_RENEWAL]' not in (pending_renewal.notes or ''):
                        pending_renewal.notes = ((pending_renewal.notes or '') + '\n[AUTO_DEACTIVATED_UNPAID_RENEWAL]').strip()
                        pending_renewal.save(update_fields=['notes'])

                    subscription.is_active = False
                    subscription.save(update_fields=['is_active'])
                    enforce_plan_limits(owner)
                    auto_deactivated += 1

                    notify(
                        recipient=owner,
                        notification_type='system',
                        title='Subscription Deactivated',
                        message=(
                            f'Your {subscription.plan.name} subscription was deactivated because renewal payment '
                            f'was not verified within the {grace_days}-day grace period.'
                        ),
                        url='/billing/my-plan/',
                    )

                    for admin_user in super_admins:
                        notify(
                            recipient=admin_user,
                            notification_type='system',
                            title='Auto Deactivated Subscription',
                            message=(
                                f'{owner.username} was auto-deactivated after {grace_days} grace days '
                                f'due to unpaid renewal request #{pending_renewal.id}.'
                            ),
                            url='/billing/manage-plans/',
                            sender=owner,
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Renewal processing completed. Rollovers={rollovers_applied}, Created={created_requests}, Reminders={sent_reminders}, Deactivated={auto_deactivated}'
            )
        )
