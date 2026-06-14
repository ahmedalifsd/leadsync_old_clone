import stripe
import os
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from decimal import Decimal
from django.db import transaction
from .models import Plan, Subscription, Payment, PricingConfig, SiteSettings, PlanDiscount, Coupon, CouponRedemption, format_price, get_currency_symbol, get_currency_code, CURRENCY_CHOICES, enforce_plan_limits, can_create_leads
from accounts.views import is_owner, is_super_admin
from accounts.models import UserProfile
from datetime import date, timedelta, datetime
from core.utils import notify, send_email


def _get_active_campaign_for_plan(plan, check_date=None, custom_plan=False):
    check_date = check_date or date.today()
    campaigns = PlanDiscount.objects.filter(
        is_active=True,
        start_date__lte=check_date,
        end_date__gte=check_date,
    )

    if custom_plan:
        campaigns = campaigns.filter(applies_to_all_plans=True)
    else:
        campaigns = campaigns.filter(applies_to_all_plans=True) | campaigns.filter(plans=plan)

    campaigns = campaigns.distinct()
    best_campaign = None
    best_discount = Decimal('0.00')
    amount_probe = plan.monthly_price if not custom_plan else Decimal('100.00')

    for campaign in campaigns:
        discount_amount = campaign.get_discount_amount(amount_probe)
        if discount_amount > best_discount:
            best_discount = discount_amount
            best_campaign = campaign

    return best_campaign


def _calculate_discounted_amount(base_amount, plan, billing_cycle, user=None, coupon_code='', custom_plan=False):
    base_amount = Decimal(str(base_amount)).quantize(Decimal('0.01'))
    campaign = _get_active_campaign_for_plan(plan=plan, custom_plan=custom_plan)
    campaign_discount = Decimal('0.00')
    coupon_discount = Decimal('0.00')
    coupon_obj = None
    discount_notes = []

    if campaign:
        campaign_discount = campaign.get_discount_amount(base_amount)
        if campaign_discount > 0:
            discount_notes.append(campaign.name)

    subtotal = (base_amount - campaign_discount).quantize(Decimal('0.01'))

    coupon_code = (coupon_code or '').strip().upper()
    coupon_error = ''
    if coupon_code:
        coupon_obj = Coupon.objects.filter(code=coupon_code).first()
        if not coupon_obj:
            coupon_error = 'Coupon code not found.'
        elif not user:
            coupon_error = 'User is required to apply coupon.'
        else:
            valid, message = coupon_obj.can_use(user=user, plan=plan, check_date=date.today())
            if not valid:
                coupon_error = message
            else:
                coupon_discount = coupon_obj.get_discount_amount(subtotal)
                if coupon_discount > 0:
                    discount_notes.append(f'Coupon {coupon_obj.code}')

    total_discount = (campaign_discount + coupon_discount).quantize(Decimal('0.01'))
    final_amount = max(Decimal('0.00'), base_amount - total_discount).quantize(Decimal('0.01'))

    if coupon_discount > 0 and campaign_discount > 0:
        discount_source = 'campaign_coupon'
    elif coupon_discount > 0:
        discount_source = 'coupon'
    elif campaign_discount > 0:
        discount_source = 'campaign'
    else:
        discount_source = 'none'

    return {
        'base_amount': base_amount,
        'final_amount': final_amount,
        'total_discount': total_discount,
        'campaign_discount': campaign_discount,
        'coupon_discount': coupon_discount,
        'campaign': campaign,
        'coupon': coupon_obj if coupon_discount > 0 else None,
        'coupon_error': coupon_error,
        'discount_source': discount_source,
        'discount_label': ' + '.join(discount_notes),
    }


def _finalize_coupon_redemption(payment):
    if not payment or not payment.is_paid or not payment.pending_coupon:
        return

    if CouponRedemption.objects.filter(payment=payment).exists():
        return

    CouponRedemption.objects.create(
        coupon=payment.pending_coupon,
        user=payment.user,
        payment=payment,
        subscription=payment.subscription,
        original_amount=payment.original_amount,
        discount_amount=payment.discount_amount,
        final_amount=payment.amount,
    )

    payment.applied_coupon = payment.pending_coupon
    payment.pending_coupon = None
    payment.save(update_fields=['applied_coupon', 'pending_coupon'])


def _billing_period_dates(billing_cycle, start_from=None):
    start_date = start_from or date.today()
    duration_days = 365 if billing_cycle == 'yearly' else 30
    return start_date, start_date + timedelta(days=duration_days)


def _activate_subscription_from_payment(subscription, payment, reviewed_by=None):
    if not subscription:
        return

    queued_for_future = False
    activation_start = date.today()
    if payment.is_renewal and subscription.end_date:
        grace_days = max(int(getattr(settings, 'RENEWAL_GRACE_DAYS', 3)), 0)
        renewal_start = subscription.end_date + timedelta(days=1)

        # If current cycle has not finished yet, queue the next cycle to prevent early period reset.
        if date.today() < renewal_start:
            period_start, period_end = _billing_period_dates(subscription.billing_cycle, renewal_start)
            subscription.is_active = True
            subscription.queued_renewal_start_date = period_start
            subscription.queued_renewal_end_date = period_end
            subscription.queued_renewal_payment = payment
            subscription.save(update_fields=['is_active', 'queued_renewal_start_date', 'queued_renewal_end_date', 'queued_renewal_payment'])
            queued_for_future = True
        # Keep continuity when renewal is approved within grace window after expiry.
        elif date.today() <= (subscription.end_date + timedelta(days=grace_days)):
            activation_start = renewal_start
        else:
            activation_start = date.today()

    if not queued_for_future:
        period_start, period_end = _billing_period_dates(subscription.billing_cycle, activation_start)

        subscription.is_active = True
        subscription.start_date = period_start
        subscription.end_date = period_end
        subscription.queued_renewal_start_date = None
        subscription.queued_renewal_end_date = None
        subscription.queued_renewal_payment = None
        subscription.save(update_fields=['is_active', 'start_date', 'end_date', 'queued_renewal_start_date', 'queued_renewal_end_date', 'queued_renewal_payment'])

    payment.is_paid = True
    payment.paid_date = date.today()
    payment.reviewed_at = timezone.now()
    payment.reviewed_by = reviewed_by
    payment.save(update_fields=['is_paid', 'paid_date', 'reviewed_at', 'reviewed_by'])


@login_required
@user_passes_test(is_owner)
def my_plan(request):
    subscription = Subscription.objects.filter(owner=request.user, is_active=True).first()
    payments = Payment.objects.filter(user=request.user).order_by('-due_date')[:10]
    
    # Logic to hide Free plan if user has ever paid/activated a non-free plan
    has_had_paid_plan = Payment.objects.filter(
        user=request.user, 
        original_amount__gt=0, 
        is_paid=True
    ).exists()
    
    if has_had_paid_plan:
        plans = list(Plan.objects.filter(is_active=True, monthly_price__gt=0))
    else:
        plans = list(Plan.objects.filter(is_active=True))
        
    support_email = (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
    if not support_email:
        support_email = (getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip()
    support_phone = (getattr(settings, 'SUPPORT_PHONE', '') or '').strip()
    support_whatsapp = (getattr(settings, 'SUPPORT_WHATSAPP', '') or '').strip()
    renewal_days_left = subscription.get_remaining_days() if subscription and subscription.is_active else None
    renewal_notice_days = max(int(getattr(settings, 'RENEWAL_NOTICE_DAYS', 7)), 1)
    renewal_grace_days = max(int(getattr(settings, 'RENEWAL_GRACE_DAYS', 3)), 0)
    today = date.today()

    pending_renewal_payment = None
    queued_renewal_start_date = None
    queued_renewal_end_date = None
    days_past_expiry = 0
    is_in_grace_period = False
    if subscription:
        pending_renewal_payment = Payment.objects.filter(
            subscription=subscription,
            is_renewal=True,
            is_paid=False,
            is_rejected=False,
        ).order_by('-created_at').first()
        queued_renewal_start_date = subscription.queued_renewal_start_date
        queued_renewal_end_date = subscription.queued_renewal_end_date

        if subscription.end_date and subscription.end_date < today:
            days_past_expiry = (today - subscription.end_date).days
            is_in_grace_period = subscription.is_active and days_past_expiry <= renewal_grace_days

    # Get current staff count (only active team members)
    from team.models import TeamMember
    current_staff_count = TeamMember.objects.filter(boss=request.user, is_active=True).count()

    # Get custom pricing config
    pricing_config = PricingConfig.objects.first()

    # Attach campaign-adjusted display prices for plan cards.
    for plan in plans:
        monthly_calc = _calculate_discounted_amount(
            base_amount=plan.monthly_price,
            plan=plan,
            billing_cycle='monthly',
            user=request.user,
        )
        yearly_calc = _calculate_discounted_amount(
            base_amount=plan.yearly_price,
            plan=plan,
            billing_cycle='yearly',
            user=request.user,
        )

        plan.yearly_base_price = (plan.monthly_price * Decimal('12')).quantize(Decimal('0.01'))
        plan.display_monthly_price = monthly_calc['final_amount']
        plan.display_yearly_price = yearly_calc['final_amount']
        plan.monthly_campaign_discount = monthly_calc['campaign_discount']
        plan.yearly_campaign_discount = yearly_calc['campaign_discount']
        plan.active_campaign_name = monthly_calc['campaign'].name if monthly_calc['campaign'] else ''

    active_coupons = Coupon.objects.filter(
        is_active=True,
        start_date__lte=date.today(),
        end_date__gte=date.today(),
    ).order_by('-created_at')[:5]

    context = {
        'subscription': subscription,
        'payments': payments,
        'plans': plans,
        'current_staff_count': current_staff_count,
        'pricing_config': pricing_config,
        'active_coupons': active_coupons,
        'support_email': support_email,
        'support_phone': support_phone,
        'support_whatsapp': support_whatsapp,
        'renewal_days_left': renewal_days_left,
        'renewal_notice_days': renewal_notice_days,
        'renewal_grace_days': renewal_grace_days,
        'pending_renewal_payment': pending_renewal_payment,
        'queued_renewal_start_date': queued_renewal_start_date,
        'queued_renewal_end_date': queued_renewal_end_date,
        'days_past_expiry': days_past_expiry,
        'is_in_grace_period': is_in_grace_period,
        'show_renewal_alert': renewal_days_left is not None and renewal_days_left <= renewal_notice_days and not queued_renewal_start_date,
    }

    return render(request, 'billing/my_plan.html', context)


@login_required
@user_passes_test(is_owner)
def add_staff_member(request):
    """Owner can register a new staff member directly from the my-plan page."""
    if request.method != 'POST':
        return redirect('my_plan')

    # Check subscription & staff limit
    subscription = Subscription.objects.filter(owner=request.user, is_active=True).first()
    if not subscription:
        messages.error(request, 'You need an active subscription to add staff members.')
        return redirect('my_plan')

    from team.models import TeamMember
    # Get form data
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password1 = request.POST.get('password1', '')
    password2 = request.POST.get('password2', '')
    phone_number = request.POST.get('phone_number', '').strip()
    company_name = request.POST.get('company_name', '').strip()

    # Validation
    if not username or not email or not password1:
        messages.error(request, 'Username, email, and password are required.')
        return redirect('my_plan')

    if password1 != password2:
        messages.error(request, 'Passwords do not match.')
        return redirect('my_plan')

    if len(password1) < 8:
        messages.error(request, 'Password must be at least 8 characters.')
        return redirect('my_plan')

    if User.objects.filter(username=username).exists():
        messages.error(request, f'Username "{username}" is already taken.')
        return redirect('my_plan')

    if User.objects.filter(email=email).exists():
        messages.error(request, f'Email "{email}" is already registered.')
        return redirect('my_plan')

    # Create the staff user
    user = User.objects.create_user(username=username, email=email, password=password1)
    profile = user.profile
    profile.role = 'staff'
    profile.pending_boss_username = ''
    profile.phone_number = phone_number
    profile.company_name = company_name or request.user.profile.company_name
    profile.is_approved = True  # Auto-approved since owner is creating
    profile.save()

    # Add to team as inactive so owner can explicitly activate from team management
    TeamMember.objects.create(boss=request.user, staff=user, is_active=False)

    messages.success(request, f'Staff member "{username}" created as inactive. Activate from Team Management when ready.')

    # Notify the new staff member
    notify(
        recipient=user,
        notification_type='staff_approved',
        title='Welcome to the Team!',
        message=f'Your account has been created by {request.user.username}. Your manager will activate it before first login.',
        url='/dashboard/',
        sender=request.user,
    )

    # Send welcome email with credentials to the new staff member
    send_email(
        to_email=email,
        subject='LeadSync - Your Account Has Been Created!',
        template_name='emails/staff_created.html',
        context={
            'staff_username': username,
            'staff_password': password1,
            'staff_email': email,
            'boss_username': request.user.username,
            'company_name': profile.company_name,
            'login_url': request.build_absolute_uri('/login/'),
            'is_auto_inactive': True,
        },
    )

    return redirect('my_plan')


@login_required
@user_passes_test(is_owner)
def toggle_auto_renew(request):
    """Toggle auto-renew for the owner's active subscription."""
    subscription = Subscription.objects.filter(owner=request.user, is_active=True).first()
    if subscription:
        subscription.auto_renew = not subscription.auto_renew
        subscription.save()
        status = "enabled" if subscription.auto_renew else "disabled"
        messages.success(request, f'Auto-renew has been {status} for your {subscription.plan.name} plan.')
    else:
        messages.error(request, 'No active subscription found.')
    return redirect('my_plan')


@login_required
@user_passes_test(is_owner)
def upgrade_plan(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id, is_active=True)
    billing_cycle = request.GET.get('cycle', 'monthly')
    coupon_code = request.GET.get('coupon', '')

    # Check if user already has this plan
    subscription = Subscription.objects.filter(owner=request.user).first()
    if subscription and subscription.plan == plan and subscription.is_active:
        messages.info(request, f'You are already on the {plan.name} plan!')
        return redirect('my_plan')

    # Calculate charge amount with optional campaign/coupon discounts.
    base_amount = plan.yearly_price if billing_cycle == 'yearly' else plan.monthly_price
    pricing = _calculate_discounted_amount(
        base_amount=base_amount,
        plan=plan,
        billing_cycle=billing_cycle,
        user=request.user,
        coupon_code=coupon_code,
    )

    if pricing['coupon_error']:
        messages.error(request, pricing['coupon_error'])
        return redirect('my_plan')

    charge_amount = pricing['final_amount']

    # FREE PLAN: Activate immediately without payment
    if charge_amount == 0:
        if subscription:
            subscription.plan = plan
            subscription.billing_cycle = billing_cycle
            subscription.is_active = True
            subscription.start_date = date.today()
            subscription.end_date = None
            subscription.save()
        else:
            subscription = Subscription.objects.create(
                owner=request.user,
                plan=plan,
                billing_cycle=billing_cycle,
                is_active=True,
                auto_renew=True,
            )

        # Record zero-value purchase when discount made this plan free.
        if pricing['total_discount'] > 0:
            payment = Payment.objects.create(
                user=request.user,
                subscription=subscription,
                amount=Decimal('0.00'),
                original_amount=pricing['base_amount'],
                discount_amount=pricing['total_discount'],
                discount_source=pricing['discount_source'],
                discount_label=pricing['discount_label'],
                pending_coupon=pricing['coupon'],
                applied_campaign=pricing['campaign'],
                due_date=date.today(),
                paid_date=date.today(),
                payment_method='manual',
                is_paid=True,
                notes='Auto-activated with discount',
            )
            _finalize_coupon_redemption(payment)

        enforce_plan_limits(request.user)
        messages.success(request, f'You are now on the {plan.name} plan!')
        notify(
            recipient=request.user,
            notification_type='plan_upgraded',
            title='Plan Activated',
            message=f'Your {plan.name} plan is now active.',
            url='/billing/my-plan/',
        )

        # Send plan activation email
        send_email(
            to_email=request.user.email,
            subject=f'LeadSync - Your {plan.name} Plan is Now Active!',
            template_name='emails/plan_activated.html',
            context={
                'username': request.user.username,
                'plan_name': plan.name,
                'billing_cycle': billing_cycle.capitalize(),
                'amount': format_price(charge_amount) if charge_amount else 'Free',
                'max_employees': plan.max_employees,
                'dashboard_url': request.build_absolute_uri('/dashboard/'),
            },
        )

        return redirect('my_plan')

    # PAID PLAN: Create subscription (inactive) and payment record
    if subscription:
        subscription.plan = plan
        subscription.billing_cycle = billing_cycle
        subscription.is_active = False  # Will be activated after payment
        subscription.auto_renew = True
        subscription.end_date = None
        subscription.save()
    else:
        subscription = Subscription.objects.create(
            owner=request.user,
            plan=plan,
            billing_cycle=billing_cycle,
            is_active=False,
            auto_renew=True,
        )

    # Create payment record
    Payment.objects.create(
        user=request.user,
        subscription=subscription,
        amount=charge_amount,
        original_amount=pricing['base_amount'],
        discount_amount=pricing['total_discount'],
        discount_source=pricing['discount_source'],
        discount_label=pricing['discount_label'],
        pending_coupon=pricing['coupon'],
        applied_campaign=pricing['campaign'],
        due_date=date.today(),
        payment_method='manual',
        is_paid=False
    )

    messages.success(request, f'Plan selected! Please make payment to activate your {plan.name} plan.')

    notify(
        recipient=request.user,
        notification_type='plan_upgraded',
        title='Plan Selected',
        message=f'You selected the {plan.name} plan ({billing_cycle}). Please complete payment to activate.',
        url='/billing/my-plan/',
    )

    return redirect('my_plan')


@login_required
@user_passes_test(is_owner)
@require_POST
def request_manual_payment(request):
    billing_cycle = request.POST.get('billing_cycle', 'monthly')
    if billing_cycle not in ('monthly', 'yearly'):
        messages.error(request, 'Invalid billing cycle selected.')
        return redirect('my_plan')

    coupon_code = request.POST.get('coupon', '')
    payer_name = (request.POST.get('payer_name') or request.user.get_full_name() or request.user.username).strip()
    payer_phone = (request.POST.get('payer_phone') or '').strip()
    payer_email = (request.POST.get('payer_email') or request.user.email or '').strip()
    contact_note = (request.POST.get('contact_note') or '').strip()
    is_custom = request.POST.get('is_custom') == '1'
    is_renewal = request.POST.get('is_renewal') == '1'

    subscription = Subscription.objects.filter(owner=request.user).first()

    if is_custom:
        employees_raw = request.POST.get('employees')
        leads_raw = request.POST.get('leads')
        try:
            employees = int(employees_raw)
            leads = int(leads_raw)
        except (TypeError, ValueError):
            messages.error(request, 'Invalid custom plan configuration.')
            return redirect('my_plan')

        config = PricingConfig.objects.first()
        if not config or not config.is_active:
            messages.error(request, 'Custom plan builder is not available right now.')
            return redirect('my_plan')

        if employees != -1 and (employees < config.min_employees or employees > config.max_employees):
            messages.error(request, f'Employees must be between {config.min_employees} and {config.max_employees}.')
            return redirect('my_plan')
        if leads != -1 and (leads < config.min_leads or leads > config.max_leads):
            messages.error(request, f'Leads must be between {config.min_leads} and {config.max_leads}.')
            return redirect('my_plan')

        monthly_price = config.calculate_monthly_price(employees, leads)
        base_charge_amount = config.calculate_yearly_price(employees, leads) if billing_cycle == 'yearly' else monthly_price

        base_plan = Plan.objects.filter(is_active=True).order_by('monthly_price').first()
        if not base_plan:
            messages.error(request, 'No plan is available for activation. Please contact support.')
            return redirect('my_plan')

        pricing = _calculate_discounted_amount(
            base_amount=base_charge_amount,
            plan=base_plan,
            billing_cycle=billing_cycle,
            user=request.user,
            coupon_code=coupon_code,
            custom_plan=True,
        )
        if pricing['coupon_error']:
            messages.error(request, pricing['coupon_error'])
            return redirect('my_plan')

        if not subscription:
            subscription = Subscription.objects.create(
                owner=request.user,
                plan=base_plan,
                billing_cycle=billing_cycle,
                is_active=False,
                auto_renew=True,
                is_custom_plan=True,
                custom_max_employees=employees,
                custom_max_leads=leads,
                custom_monthly_price=monthly_price,
            )
        else:
            subscription.plan = base_plan
            subscription.billing_cycle = billing_cycle
            subscription.is_custom_plan = True
            subscription.custom_max_employees = employees
            subscription.custom_max_leads = leads
            subscription.custom_monthly_price = monthly_price
            if not is_renewal:
                subscription.is_active = False
                subscription.end_date = None
            subscription.save()

    else:
        plan_id = request.POST.get('plan_id')
        if not plan_id:
            messages.error(request, 'Please select a plan first.')
            return redirect('my_plan')

        plan = get_object_or_404(Plan, id=plan_id, is_active=True)
        base_amount = plan.yearly_price if billing_cycle == 'yearly' else plan.monthly_price
        pricing = _calculate_discounted_amount(
            base_amount=base_amount,
            plan=plan,
            billing_cycle=billing_cycle,
            user=request.user,
            coupon_code=coupon_code,
        )
        if pricing['coupon_error']:
            messages.error(request, pricing['coupon_error'])
            return redirect('my_plan')

        if not subscription:
            subscription = Subscription.objects.create(
                owner=request.user,
                plan=plan,
                billing_cycle=billing_cycle,
                is_active=False,
                auto_renew=True,
            )
        else:
            subscription.plan = plan
            subscription.billing_cycle = billing_cycle
            subscription.is_custom_plan = False
            subscription.custom_max_employees = None
            subscription.custom_max_leads = None
            subscription.custom_monthly_price = None
            if not is_renewal:
                subscription.is_active = False
                subscription.end_date = None
            subscription.save()

    charge_amount = pricing['final_amount']
    due_on = subscription.end_date if (is_renewal and subscription.end_date and subscription.end_date >= date.today()) else date.today()

    # Mark any previous pending requests for this subscription as superseded
    previous_pending = Payment.objects.filter(
        subscription=subscription,
        is_paid=False,
        is_rejected=False,
    )
    if previous_pending.exists():
        previous_pending.update(
            is_rejected=True,
            rejected_at=timezone.now(),
            rejection_reason='Superseded by newer payment request',
        )

    transaction_id = request.POST.get('transaction_id', '').strip()
    payment_proof = request.FILES.get('payment_proof')

    payment = Payment.objects.create(
        user=request.user,
        subscription=subscription,
        amount=charge_amount,
        original_amount=pricing['base_amount'],
        discount_amount=pricing['total_discount'],
        discount_source=pricing['discount_source'],
        discount_label=pricing['discount_label'],
        pending_coupon=pricing['coupon'],
        applied_campaign=pricing['campaign'],
        due_date=due_on,
        payment_method='manual',
        payer_name=payer_name,
        payer_phone=payer_phone,
        payer_email=payer_email,
        contact_note=contact_note,
        transaction_id=transaction_id,
        payment_proof=payment_proof,
        is_renewal=is_renewal,
        is_paid=False,
        notes='Manual payment request submitted by customer.',
    )

    if charge_amount == 0:
        _activate_subscription_from_payment(subscription, payment)
        _finalize_coupon_redemption(payment)
        enforce_plan_limits(request.user)
        messages.success(request, 'Your request was auto-approved because the final amount is zero.')
        return redirect('my_plan')

    super_admins = User.objects.filter(profile__role='super_admin', is_active=True)
    for admin_user in super_admins:
        notify(
            recipient=admin_user,
            notification_type='payment_received',
            title='Manual Payment Request',
            message=f'{request.user.username} requested {subscription.get_billing_cycle_display()} activation for {subscription.plan.name}.',
            url='/billing/manage-plans/',
            sender=request.user,
        )

    messages.success(request, 'Payment request submitted. Please contact support and share your transaction screenshot for verification.')
    return redirect('my_plan')


@login_required
@user_passes_test(is_super_admin)
def manage_plans(request):
    if request.method == 'POST':
        if 'add_plan' in request.POST:
            name = request.POST.get('name', '').strip()
            monthly_price = request.POST.get('monthly_price')
            yearly_discount = request.POST.get('yearly_discount', 0)
            max_employees = request.POST.get('max_employees')
            features = request.POST.get('features')

            # Monthly leads
            monthly_unlimited = request.POST.get('monthly_unlimited_leads')
            monthly_leads_val = request.POST.get('monthly_max_leads')
            monthly_max_leads = None if (monthly_unlimited or not monthly_leads_val) else int(monthly_leads_val)

            # Yearly leads
            yearly_unlimited = request.POST.get('yearly_unlimited_leads')
            yearly_leads_val = request.POST.get('yearly_max_leads')
            yearly_max_leads = None if (yearly_unlimited or not yearly_leads_val) else int(yearly_leads_val)

            if not name or not monthly_price:
                messages.error(request, 'Plan name and monthly price are required!')
            elif Plan.objects.filter(name__iexact=name).exists():
                messages.error(request, f'Plan "{name}" already exists! Please choose a different name.')
            else:
                Plan.objects.create(
                    name=name,
                    monthly_price=monthly_price,
                    yearly_discount=yearly_discount or 0,
                    max_employees=max_employees or 1,
                    monthly_max_leads=monthly_max_leads,
                    yearly_max_leads=yearly_max_leads,
                    features=features
                )
                messages.success(request, f'Plan "{name}" added successfully!')

        elif 'update_pricing_config' in request.POST:
            config, _ = PricingConfig.objects.get_or_create(pk=1)
            config.price_per_employee = request.POST.get('price_per_employee', 2)
            config.price_per_lead_block = request.POST.get('price_per_lead_block', 1)
            config.lead_block_size = request.POST.get('lead_block_size', 1000)
            config.min_employees = request.POST.get('min_employees', 1)
            config.max_employees = request.POST.get('config_max_employees', 500)
            config.min_leads = request.POST.get('min_leads', 1000)
            config.max_leads = request.POST.get('max_leads', 1000000)
            config.lead_step = request.POST.get('lead_step', 1000)
            config.employee_step = request.POST.get('employee_step', 1)
            config.base_price = request.POST.get('base_price', 0)
            config.yearly_discount = request.POST.get('config_yearly_discount', 20)
            config.unlimited_employees_price = request.POST.get('unlimited_employees_price', 50)
            config.unlimited_leads_price = request.POST.get('unlimited_leads_price', 30)
            config.is_active = 'pricing_is_active' in request.POST
            config.save()
            messages.success(request, 'Custom pricing configuration updated!')

        elif 'update_plan' in request.POST:
            plan_id = request.POST.get('plan_id')
            plan = get_object_or_404(Plan, id=plan_id)
            name = request.POST.get('name', '').strip()
            monthly_price = request.POST.get('monthly_price')
            yearly_discount = request.POST.get('yearly_discount', 0)

            # Monthly leads
            monthly_unlimited = request.POST.get('monthly_unlimited_leads')
            monthly_leads_val = request.POST.get('monthly_max_leads')
            monthly_max_leads = None if (monthly_unlimited or not monthly_leads_val) else int(monthly_leads_val)

            # Yearly leads
            yearly_unlimited = request.POST.get('yearly_unlimited_leads')
            yearly_leads_val = request.POST.get('yearly_max_leads')
            yearly_max_leads = None if (yearly_unlimited or not yearly_leads_val) else int(yearly_leads_val)

            if not name or not monthly_price:
                messages.error(request, 'Plan name and monthly price are required!')
            elif Plan.objects.filter(name__iexact=name).exclude(id=plan.id).exists():
                messages.error(request, f'Plan "{name}" already exists! Please choose a different name.')
            else:
                plan.name = name
                plan.monthly_price = monthly_price
                plan.yearly_discount = yearly_discount or 0
                plan.max_employees = request.POST.get('max_employees')
                plan.monthly_max_leads = monthly_max_leads
                plan.yearly_max_leads = yearly_max_leads
                plan.features = request.POST.get('features')
                plan.save()
                messages.success(request, f'Plan "{plan.name}" updated successfully!')

        elif 'add_discount_campaign' in request.POST:
            name = request.POST.get('campaign_name', '').strip()
            discount_type = request.POST.get('campaign_discount_type', 'percent')
            discount_value = request.POST.get('campaign_discount_value', '0').strip()
            start_date = request.POST.get('campaign_start_date')
            end_date = request.POST.get('campaign_end_date')
            applies_all = 'campaign_applies_all' in request.POST
            plan_ids = request.POST.getlist('campaign_plan_ids')

            if not name or not start_date or not end_date:
                messages.error(request, 'Campaign name and date range are required.')
            else:
                campaign = PlanDiscount.objects.create(
                    name=name,
                    discount_type=discount_type,
                    discount_value=discount_value or 0,
                    start_date=start_date,
                    end_date=end_date,
                    applies_to_all_plans=applies_all,
                    is_active=True,
                )
                if not applies_all and plan_ids:
                    campaign.plans.set(Plan.objects.filter(id__in=plan_ids))
                messages.success(request, f'Campaign "{campaign.name}" created successfully.')

        elif 'add_coupon' in request.POST:
            code = (request.POST.get('coupon_code') or '').strip().upper()
            description = (request.POST.get('coupon_description') or '').strip()
            discount_type = request.POST.get('coupon_discount_type', 'percent')
            discount_value = request.POST.get('coupon_discount_value', '0').strip()
            max_uses = request.POST.get('coupon_max_uses', '1').strip() or '1'
            start_date = request.POST.get('coupon_start_date')
            end_date = request.POST.get('coupon_end_date')
            applies_all = 'coupon_applies_all' in request.POST
            plan_ids = request.POST.getlist('coupon_plan_ids')

            if not code or not start_date or not end_date:
                messages.error(request, 'Coupon code and date range are required.')
            elif Coupon.objects.filter(code=code).exists():
                messages.error(request, f'Coupon "{code}" already exists.')
            else:
                coupon = Coupon.objects.create(
                    code=code,
                    description=description,
                    discount_type=discount_type,
                    discount_value=discount_value or 0,
                    max_uses=max(int(max_uses), 1),
                    start_date=start_date,
                    end_date=end_date,
                    applies_to_all_plans=applies_all,
                    is_active=True,
                )
                if not applies_all and plan_ids:
                    coupon.plans.set(Plan.objects.filter(id__in=plan_ids))
                messages.success(request, f'Coupon "{coupon.code}" created successfully.')

        elif 'approve_manual_payment' in request.POST:
            payment_id = request.POST.get('payment_id')
            payment = get_object_or_404(Payment, id=payment_id)
            subscription = payment.subscription

            if payment.is_paid:
                messages.info(request, f'Payment request #{payment.id} is already approved.')
                return redirect('manage_plans')

            plan_id = request.POST.get('activation_plan_id')
            billing_cycle = request.POST.get('activation_billing_cycle', subscription.billing_cycle)
            auto_renew_enabled = request.POST.get('activation_auto_renew') == '1'
            transaction_id = (request.POST.get('transaction_id') or '').strip()
            payment_method = request.POST.get('payment_method') or payment.payment_method or 'bank_transfer'
            admin_note = (request.POST.get('admin_note') or '').strip()
            proof_file = request.FILES.get('payment_proof')

            if billing_cycle not in ('monthly', 'yearly'):
                messages.error(request, 'Invalid billing cycle selected.')
                return redirect('manage_plans')

            if not proof_file and not payment.payment_proof:
                messages.error(request, f'Upload transaction proof before approving payment request #{payment.id}.')
                return redirect('manage_plans')

            if plan_id:
                selected_plan = get_object_or_404(Plan, id=plan_id, is_active=True)
                subscription.plan = selected_plan
                payment.subscription = subscription

            subscription.billing_cycle = billing_cycle
            subscription.auto_renew = auto_renew_enabled
            subscription.save(update_fields=['plan', 'billing_cycle', 'auto_renew'])

            payment.payment_method = payment_method
            payment.transaction_id = transaction_id
            if proof_file:
                # Rename uploaded file: {user_id}-{date}-{transaction_id}-{original_filename}
                original_filename = os.path.splitext(proof_file.name)[1]  # Get extension
                transaction_part = transaction_id if transaction_id else 'notx'
                new_filename = f"{payment.user.id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{transaction_part}{original_filename}"
                proof_file.name = new_filename
                payment.payment_proof = proof_file
            if admin_note:
                existing_notes = (payment.notes or '').strip()
                payment.notes = f"{existing_notes}\nAdmin note: {admin_note}".strip()
            try:
                payment.save(update_fields=['payment_method', 'transaction_id', 'payment_proof', 'notes'])
            except Exception as exc:
                messages.error(request, f'Could not upload payment proof: {exc}')
                return redirect('manage_plans')

            _activate_subscription_from_payment(subscription, payment, reviewed_by=request.user)
            _finalize_coupon_redemption(payment)
            enforce_plan_limits(subscription.owner)

            plan_display = 'Custom Plan' if subscription.is_custom_plan else subscription.plan.name
            is_queued_renewal = payment.is_renewal and bool(subscription.queued_renewal_start_date)
            customer_message = (
                f'Your payment has been verified. Next cycle for {plan_display} '
                f'({subscription.get_billing_cycle_display()}) is scheduled from {subscription.queued_renewal_start_date}.'
            ) if is_queued_renewal else (
                f'Your payment has been verified. {plan_display} ({subscription.get_billing_cycle_display()}) is now active.'
            )
            notify(
                recipient=payment.user,
                notification_type='payment_received',
                title='Payment Confirmed',
                message=customer_message,
                url='/billing/my-plan/',
                sender=request.user,
            )

            send_email(
                to_email=payment.user.email,
                subject=(
                    f'LeadSync - {plan_display} Renewal Scheduled'
                    if is_queued_renewal else f'LeadSync - {plan_display} Activated'
                ),
                template_name='emails/plan_activated.html',
                context={
                    'username': payment.user.username,
                    'plan_name': plan_display,
                    'billing_cycle': subscription.get_billing_cycle_display(),
                    'amount': format_price(payment.amount),
                    'max_employees': subscription.effective_max_employees,
                    'dashboard_url': request.build_absolute_uri('/dashboard/'),
                },
            )

            if payment.is_renewal and subscription.queued_renewal_start_date:
                messages.success(
                    request,
                    f'Payment request #{payment.id} approved. Renewal is scheduled from {subscription.queued_renewal_start_date}.'
                )
            else:
                messages.success(request, f'Payment request #{payment.id} approved and subscription activated.')

        elif 'reject_manual_payment' in request.POST:
            payment_id = request.POST.get('payment_id')
            payment = get_object_or_404(Payment, id=payment_id)
            rejection_reason = (request.POST.get('rejection_reason') or '').strip()

            if payment.is_paid or payment.is_rejected:
                messages.info(request, f'Payment request #{payment.id} has already been processed.')
                return redirect('manage_plans')

            if not rejection_reason:
                messages.error(request, 'Please provide a rejection reason.')
                return redirect('manage_plans')

            payment.is_rejected = True
            payment.rejected_at = timezone.now()
            payment.rejected_by = request.user
            payment.rejection_reason = rejection_reason
            payment.save(update_fields=['is_rejected', 'rejected_at', 'rejected_by', 'rejection_reason'])

            notify(
                recipient=payment.user,
                notification_type='payment_rejected',
                title='Payment Request Rejected',
                message=f'Your payment request for {payment.subscription.plan.name} ({payment.subscription.get_billing_cycle_display()}) has been rejected. Reason: {rejection_reason}',
                url='/billing/my-plan/',
                sender=request.user,
            )

            send_email(
                to_email=payment.user.email,
                subject=f'LeadSync - Payment Request Rejected',
                template_name='emails/payment_rejected.html',
                context={
                    'username': payment.user.username,
                    'plan_name': payment.subscription.plan.name if not payment.subscription.is_custom_plan else 'Custom Plan',
                    'billing_cycle': payment.subscription.get_billing_cycle_display(),
                    'amount': format_price(payment.amount),
                    'rejection_reason': rejection_reason,
                    'support_email': settings.SUPPORT_EMAIL if hasattr(settings, 'SUPPORT_EMAIL') else '',
                },
            )

            messages.success(request, f'Payment request #{payment.id} has been rejected and customer notified.')

        elif 'manual_activate_plan' in request.POST:
            owner_id = request.POST.get('owner_id')
            plan_id = request.POST.get('activation_plan_id')
            billing_cycle = request.POST.get('activation_billing_cycle', 'monthly')
            auto_renew_enabled = request.POST.get('activation_auto_renew') == '1'
            activation_mode = request.POST.get('activation_mode', 'fresh')
            transaction_id = (request.POST.get('transaction_id') or '').strip()
            payment_proof = request.FILES.get('payment_proof')
            admin_note = (request.POST.get('admin_note') or '').strip()

            if billing_cycle not in ('monthly', 'yearly'):
                messages.error(request, 'Invalid billing cycle selected for manual activation.')
                return redirect('manage_plans')

            if activation_mode not in ('fresh', 'renewal'):
                messages.error(request, 'Invalid activation mode selected.')
                return redirect('manage_plans')

            owner_profile = get_object_or_404(UserProfile.objects.select_related('user'), user_id=owner_id, role='owner')
            owner_user = owner_profile.user
            selected_plan = get_object_or_404(Plan, id=plan_id, is_active=True)

            subscription, _ = Subscription.objects.get_or_create(
                owner=owner_user,
                defaults={
                    'plan': selected_plan,
                    'billing_cycle': billing_cycle,
                    'is_active': False,
                    'auto_renew': auto_renew_enabled,
                }
            )

            subscription.plan = selected_plan
            subscription.billing_cycle = billing_cycle
            subscription.auto_renew = auto_renew_enabled
            subscription.is_custom_plan = False
            subscription.custom_max_employees = None
            subscription.custom_max_leads = None
            subscription.custom_monthly_price = None
            if activation_mode == 'fresh':
                subscription.end_date = None
            subscription.save(update_fields=[
                'plan', 'billing_cycle', 'auto_renew', 'is_custom_plan',
                'custom_max_employees', 'custom_max_leads', 'custom_monthly_price', 'end_date'
            ])

            amount = subscription.plan.yearly_price if billing_cycle == 'yearly' else subscription.plan.monthly_price
            payment = Payment.objects.create(
                user=owner_user,
                subscription=subscription,
                amount=amount,
                original_amount=amount,
                discount_amount=Decimal('0.00'),
                discount_source='none',
                due_date=date.today(),
                payment_method='manual',
                transaction_id=transaction_id,
                is_renewal=(activation_mode == 'renewal'),
                notes=(
                    f"Manually activated by super admin {request.user.username}."
                    + (f"\nAdmin note: {admin_note}" if admin_note else "")
                ),
            )

            if payment_proof:
                payment.payment_proof = payment_proof
                payment.save(update_fields=['payment_proof', 'payment_proof_access_url'])

            _activate_subscription_from_payment(subscription, payment, reviewed_by=request.user)
            enforce_plan_limits(owner_user)

            plan_display = subscription.plan.name
            notify(
                recipient=owner_user,
                notification_type='plan_upgraded',
                title='Plan Activated By Admin',
                message=f'Your {plan_display} ({subscription.get_billing_cycle_display()}) plan is now active.',
                url='/billing/my-plan/',
                sender=request.user,
            )

            send_email(
                to_email=owner_user.email,
                subject=f'LeadSync - {plan_display} Plan Activated',
                template_name='emails/plan_activated.html',
                context={
                    'username': owner_user.username,
                    'plan_name': plan_display,
                    'billing_cycle': subscription.get_billing_cycle_display(),
                    'amount': format_price(amount),
                    'max_employees': subscription.effective_max_employees,
                    'dashboard_url': request.build_absolute_uri('/dashboard/'),
                },
            )

            messages.success(request, f'{owner_user.username} plan activated successfully via manual action.')

        elif 'stop_active_plan' in request.POST:
            owner_id = request.POST.get('owner_id')
            owner_profile = get_object_or_404(UserProfile.objects.select_related('user'), user_id=owner_id, role='owner')
            owner_user = owner_profile.user
            subscription = Subscription.objects.filter(owner=owner_user, is_active=True).first()

            if not subscription:
                messages.info(request, f'{owner_user.username} has no active subscription to stop.')
                return redirect('manage_plans')

            # Stop current active plan
            subscription.is_active = False
            subscription.auto_renew = False
            subscription.end_date = date.today()
            subscription.save(update_fields=['is_active', 'auto_renew', 'end_date'])
            
            # Auto-activate free plan
            free_plan = Plan.objects.filter(monthly_price=0, is_active=True).first()
            if free_plan:
                free_subscription, _ = Subscription.objects.get_or_create(
                    owner=owner_user,
                    defaults={
                        'plan': free_plan,
                        'billing_cycle': 'monthly',
                        'is_active': True,
                        'auto_renew': False,
                    }
                )
                if not free_subscription.is_active or free_subscription.plan != free_plan:
                    free_subscription.plan = free_plan
                    free_subscription.is_active = True
                    free_subscription.auto_renew = False
                    free_subscription.start_date = date.today()
                    free_subscription.end_date = date.today() + timedelta(days=365)
                    free_subscription.save(update_fields=['plan', 'is_active', 'auto_renew', 'start_date', 'end_date'])
                
                enforce_plan_limits(owner_user)
                
                notify(
                    recipient=owner_user,
                    notification_type='system',
                    title='Plan Stopped - Free Plan Activated',
                    message=f'Your active subscription has been stopped and you have been switched to the Free plan.',
                    url='/billing/my-plan/',
                    sender=request.user,
                )
                
                messages.success(request, f'Active plan stopped for {owner_user.username} and free plan activated.')
            else:
                enforce_plan_limits(owner_user)
                
                notify(
                    recipient=owner_user,
                    notification_type='system',
                    title='Plan Stopped By Admin',
                    message='Your active subscription has been stopped by support. Please contact support for details.',
                    url='/billing/my-plan/',
                    sender=request.user,
                )

                messages.success(request, f'Active plan stopped for {owner_user.username}.')

    plans = Plan.objects.all()
    pricing_config, _ = PricingConfig.objects.get_or_create(pk=1)
    campaigns = PlanDiscount.objects.prefetch_related('plans').all()
    coupons = Coupon.objects.prefetch_related('plans').all()
    pending_payments = Payment.objects.filter(is_paid=False, is_rejected=False).select_related('user', 'subscription', 'subscription__plan').order_by('-created_at')[:50]
    owner_profiles = UserProfile.objects.filter(role='owner').select_related('user').order_by('user__username')
    context = {
        'plans': plans,
        'pricing_config': pricing_config,
        'campaigns': campaigns,
        'coupons': coupons,
        'pending_payments': pending_payments,
        'owner_profiles': owner_profiles,
        'auto_open_pending_requests_modal': pending_payments.exists(),
    }
    return render(request, 'billing/manage_plans.html', context)


@login_required
@user_passes_test(is_super_admin)
def site_settings(request):
    """Super admin page to configure site-wide settings like currency."""
    settings_obj = SiteSettings.get_settings()

    if request.method == 'POST':
        currency_code = request.POST.get('currency_code', 'pkr')
        settings_obj.currency_code = currency_code
        settings_obj.save()
        # Clear cached currency so it takes effect immediately
        from django.core.cache import cache
        cache.delete('site_currency')
        messages.success(request, f'Currency updated to {currency_code.upper()} ({settings_obj.currency_symbol})')
        return redirect('site_settings')

    context = {
        'site_settings': settings_obj,
        'currency_choices': CURRENCY_CHOICES,
    }
    return render(request, 'billing/site_settings.html', context)


@login_required
@user_passes_test(is_super_admin)
@require_POST
def set_default_plan(request, plan_id):
    """Set a plan as the default signup plan for new business owners."""
    plan = get_object_or_404(Plan, id=plan_id)
    # Toggle: if already default, unset it; otherwise set it
    if plan.is_default_signup_plan:
        plan.is_default_signup_plan = False
        plan.save()
        messages.success(request, f'"{plan.name}" is no longer the default signup plan.')
    else:
        plan.is_default_signup_plan = True
        plan.save()  # save() automatically unsets other defaults
        messages.success(request, f'"{plan.name}" is now the default signup plan for new owners!')
    return redirect('manage_plans')


@login_required
@user_passes_test(is_super_admin)
@require_POST
def toggle_plan(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    plan.is_active = not plan.is_active
    plan.save()

    status = "activated" if plan.is_active else "deactivated"
    messages.success(request, f'Plan {plan.name} {status}!')
    return redirect('manage_plans')


@login_required
@user_passes_test(is_super_admin)
@require_POST
def delete_plan(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)

    # Check if any active subscriptions are using this plan
    active_subs = Subscription.objects.filter(plan=plan, is_active=True).count()
    if active_subs > 0:
        messages.error(request, f'Cannot delete "{plan.name}" — {active_subs} active subscription(s) are using this plan. Deactivate them first or switch their plans.')
        return redirect('manage_plans')

    plan_name = plan.name
    plan.delete()
    messages.success(request, f'Plan "{plan_name}" deleted successfully!')
    return redirect('manage_plans')


@login_required
@user_passes_test(is_super_admin)
@require_POST
def toggle_campaign(request, campaign_id):
    campaign = get_object_or_404(PlanDiscount, id=campaign_id)
    campaign.is_active = not campaign.is_active
    campaign.save(update_fields=['is_active'])
    messages.success(request, f'Campaign "{campaign.name}" is now {"active" if campaign.is_active else "inactive"}.')
    return redirect('manage_plans')


@login_required
@user_passes_test(is_super_admin)
@require_POST
def delete_campaign(request, campaign_id):
    campaign = get_object_or_404(PlanDiscount, id=campaign_id)
    campaign_name = campaign.name
    campaign.delete()
    messages.success(request, f'Campaign "{campaign_name}" deleted successfully.')
    return redirect('manage_plans')


@login_required
@user_passes_test(is_super_admin)
@require_POST
def toggle_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.is_active = not coupon.is_active
    coupon.save(update_fields=['is_active'])
    messages.success(request, f'Coupon "{coupon.code}" is now {"active" if coupon.is_active else "inactive"}.')
    return redirect('manage_plans')


@login_required
@user_passes_test(is_super_admin)
@require_POST
def delete_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    code = coupon.code
    coupon.delete()
    messages.success(request, f'Coupon "{code}" deleted successfully.')
    return redirect('manage_plans')


@login_required
@user_passes_test(is_super_admin)
@require_POST
def update_payment_status(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    payment.is_paid = not payment.is_paid
    payment.paid_date = date.today() if payment.is_paid else None
    payment.save()

    status = "marked as paid" if payment.is_paid else "marked as unpaid"
    messages.success(request, f'Payment {status}!')

    # Notify owner about payment status update
    if payment.is_paid:
        subscription = payment.subscription
        _activate_subscription_from_payment(subscription, payment, reviewed_by=request.user)

        _finalize_coupon_redemption(payment)

        notify(
            recipient=payment.user,
            notification_type='payment_received',
            title='Payment Confirmed',
            message=f'Your payment of {get_currency_symbol()}{format_price(payment.amount)} has been confirmed. Your {subscription.plan.name} plan is now active!',
            url='/billing/my-plan/',
            sender=request.user,
        )

        # Send plan activation email
        send_email(
            to_email=payment.user.email,
            subject=f'LeadSync - Your {subscription.plan.name} Plan is Now Active!',
            template_name='emails/plan_activated.html',
            context={
                'username': payment.user.username,
                'plan_name': subscription.plan.name,
                'billing_cycle': subscription.get_billing_cycle_display(),
                'amount': format_price(payment.amount),
                'max_employees': subscription.effective_max_employees,
                'dashboard_url': request.build_absolute_uri('/dashboard/'),
            },
        )

    return redirect('admin_panel')


@login_required
@user_passes_test(is_owner)
def create_stripe_checkout_session(request, plan_id):
    """Create a Stripe checkout session for the selected plan"""
    plan = get_object_or_404(Plan, id=plan_id, is_active=True)

    # Check if user already has this plan
    existing_sub = Subscription.objects.filter(owner=request.user).first()
    if existing_sub and existing_sub.plan == plan and existing_sub.is_active:
        return JsonResponse({'free': True, 'redirect': '/billing/my-plan/'})

    # Determine billing cycle from request
    billing_cycle = request.GET.get('cycle', 'monthly')
    coupon_code = request.GET.get('coupon', '')

    base_amount = plan.yearly_price if billing_cycle == 'yearly' else plan.monthly_price
    pricing = _calculate_discounted_amount(
        base_amount=base_amount,
        plan=plan,
        billing_cycle=billing_cycle,
        user=request.user,
        coupon_code=coupon_code,
    )

    if pricing['coupon_error']:
        return JsonResponse({'error': pricing['coupon_error']}, status=400)

    charge_amount = pricing['final_amount']

    # FREE PLAN: No payment needed — activate immediately
    if charge_amount == 0:
        subscription, created = Subscription.objects.get_or_create(
            owner=request.user,
            defaults={
                'plan': plan,
                'billing_cycle': billing_cycle,
                'is_active': True,
                'auto_renew': True,
            }
        )
        if not created:
            subscription.plan = plan
            subscription.billing_cycle = billing_cycle
            subscription.is_active = True
            subscription.start_date = date.today()
            subscription.end_date = None
            subscription.save()

        if pricing['total_discount'] > 0:
            payment = Payment.objects.create(
                user=request.user,
                subscription=subscription,
                amount=Decimal('0.00'),
                original_amount=pricing['base_amount'],
                discount_amount=pricing['total_discount'],
                discount_source=pricing['discount_source'],
                discount_label=pricing['discount_label'],
                pending_coupon=pricing['coupon'],
                applied_campaign=pricing['campaign'],
                due_date=date.today(),
                paid_date=date.today(),
                payment_method='stripe',
                is_paid=True,
                notes='Stripe checkout skipped due to full discount',
            )
            _finalize_coupon_redemption(payment)

        notify(
            recipient=request.user,
            notification_type='plan_upgraded',
            title='Plan Activated',
            message=f'Your {plan.name} plan is now active.',
            url='/billing/my-plan/',
        )

        return JsonResponse({'free': True, 'redirect': '/billing/my-plan/'})

    # PAID PLAN: Try Stripe checkout first
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_SECRET_KEY.startswith('sk_'):
        return JsonResponse({'error': 'Stripe is not properly configured. Please contact administrator.'}, status=400)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        if billing_cycle == 'yearly':
            description = f'{plan.name} Plan - {get_currency_symbol()}{format_price(plan.yearly_price)}/year ({format_price(plan.yearly_discount)}% off)'
        else:
            description = f'{plan.name} Plan - {get_currency_symbol()}{format_price(plan.monthly_price)}/month'

        # Create a Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': get_currency_code(),
                    'product_data': {
                        'name': f'{plan.name} Plan ({billing_cycle.capitalize()})',
                        'description': description,
                    },
                    'unit_amount': int(charge_amount * 100),  # Convert to cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri('/billing/stripe-success/') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri('/billing/my-plan/'),
            metadata={
                'user_id': str(request.user.id),
                'plan_id': str(plan.id),
                'billing_cycle': billing_cycle,
            }
        )

        # Get or create the subscription for this user
        subscription, created = Subscription.objects.get_or_create(
            owner=request.user,
            defaults={
                'plan': plan,
                'billing_cycle': billing_cycle,
                'is_active': False,  # Will be activated after payment confirmation
                'auto_renew': True
            }
        )

        # If subscription already existed, update it
        if not created:
            subscription.plan = plan
            subscription.billing_cycle = billing_cycle
            subscription.is_active = False  # Will be activated after payment
            subscription.auto_renew = True
            subscription.end_date = None
            subscription.save()

        # Create payment record
        Payment.objects.create(
            user=request.user,
            subscription=subscription,
            amount=charge_amount,
            original_amount=pricing['base_amount'],
            discount_amount=pricing['total_discount'],
            discount_source=pricing['discount_source'],
            discount_label=pricing['discount_label'],
            pending_coupon=pricing['coupon'],
            applied_campaign=pricing['campaign'],
            due_date=date.today(),
            payment_method='stripe',
            stripe_payment_intent_id=checkout_session.id,
            is_paid=False
        )

        return JsonResponse({'sessionId': checkout_session.id})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@user_passes_test(is_owner)
def get_custom_pricing(request):
    """API endpoint to get custom plan pricing configuration."""
    config = PricingConfig.objects.first()
    if not config or not config.is_active:
        return JsonResponse({'error': 'Custom plan builder is not available.'}, status=404)

    return JsonResponse({
        'price_per_employee': float(config.price_per_employee),
        'price_per_lead_block': float(config.price_per_lead_block),
        'lead_block_size': config.lead_block_size,
        'min_employees': config.min_employees,
        'max_employees': config.max_employees,
        'min_leads': config.min_leads,
        'max_leads': config.max_leads,
        'lead_step': config.lead_step,
        'base_price': float(config.base_price),
        'yearly_discount': float(config.yearly_discount),
        'currency_symbol': get_currency_symbol(),
        'currency_code': get_currency_code(),
    })


@login_required
@user_passes_test(is_owner)
def create_custom_stripe_session(request):
    """Create a Stripe checkout session for a custom plan configuration."""
    employees = request.GET.get('employees')
    leads = request.GET.get('leads')
    billing_cycle = request.GET.get('cycle', 'monthly')
    coupon_code = request.GET.get('coupon', '')

    if not employees or not leads:
        return JsonResponse({'error': 'Please select employees and leads.'}, status=400)

    try:
        employees = int(employees)
        leads = int(leads)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid employee or lead count.'}, status=400)

    config = PricingConfig.objects.first()
    if not config or not config.is_active:
        return JsonResponse({'error': 'Custom plan builder is not available.'}, status=400)

    # Validate ranges (allow -1 for unlimited)
    if employees != -1:
        if employees < config.min_employees or employees > config.max_employees:
            return JsonResponse({'error': f'Employees must be between {config.min_employees} and {config.max_employees}.'}, status=400)
    if leads != -1:
        if leads < config.min_leads or leads > config.max_leads:
            return JsonResponse({'error': f'Leads must be between {config.min_leads} and {config.max_leads}.'}, status=400)

    # Calculate base custom plan price.
    monthly_price = config.calculate_monthly_price(employees, leads)
    if billing_cycle == 'yearly':
        base_charge_amount = config.calculate_yearly_price(employees, leads)
    else:
        base_charge_amount = monthly_price

    if base_charge_amount <= 0:
        return JsonResponse({'error': 'Invalid plan configuration.'}, status=400)

    # Need a base plan to attach to the subscription (use the cheapest active plan)
    base_plan = Plan.objects.filter(is_active=True).order_by('monthly_price').first()
    if not base_plan:
        return JsonResponse({'error': 'No base plan available. Please contact administrator.'}, status=400)

    pricing = _calculate_discounted_amount(
        base_amount=base_charge_amount,
        plan=base_plan,
        billing_cycle=billing_cycle,
        user=request.user,
        coupon_code=coupon_code,
        custom_plan=True,
    )

    if pricing['coupon_error']:
        return JsonResponse({'error': pricing['coupon_error']}, status=400)

    charge_amount = pricing['final_amount']

    # Full discount can activate immediately without Stripe checkout.
    if charge_amount == 0:
        subscription, created = Subscription.objects.get_or_create(
            owner=request.user,
            defaults={
                'plan': base_plan,
                'billing_cycle': billing_cycle,
                'is_active': True,
                'auto_renew': True,
                'is_custom_plan': True,
                'custom_max_employees': employees,
                'custom_max_leads': leads,
                'custom_monthly_price': monthly_price,
            }
        )

        if not created:
            subscription.plan = base_plan
            subscription.billing_cycle = billing_cycle
            subscription.is_active = True
            subscription.auto_renew = True
            subscription.is_custom_plan = True
            subscription.custom_max_employees = employees
            subscription.custom_max_leads = leads
            subscription.custom_monthly_price = monthly_price
            subscription.start_date = date.today()
            subscription.end_date = date.today() + timedelta(days=365 if billing_cycle == 'yearly' else 30)
            subscription.save()

        payment = Payment.objects.create(
            user=request.user,
            subscription=subscription,
            amount=Decimal('0.00'),
            original_amount=pricing['base_amount'],
            discount_amount=pricing['total_discount'],
            discount_source=pricing['discount_source'],
            discount_label=pricing['discount_label'],
            pending_coupon=pricing['coupon'],
            applied_campaign=pricing['campaign'],
            due_date=date.today(),
            paid_date=date.today(),
            payment_method='stripe',
            is_paid=True,
            notes='Custom plan activated with full discount',
        )
        _finalize_coupon_redemption(payment)
        enforce_plan_limits(request.user)
        return JsonResponse({'free': True, 'redirect': '/billing/my-plan/'})

    # Validate Stripe config
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_SECRET_KEY.startswith('sk_'):
        return JsonResponse({'error': 'Stripe is not properly configured. Please contact administrator.'}, status=400)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        if billing_cycle == 'yearly':
            description = f'Custom Plan - {employees} employees, {leads} leads - {get_currency_symbol()}{format_price(charge_amount)}/year ({format_price(config.yearly_discount)}% off)'
        else:
            description = f'Custom Plan - {employees} employees, {leads} leads - {get_currency_symbol()}{format_price(charge_amount)}/month'

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': get_currency_code(),
                    'product_data': {
                        'name': f'Custom Plan ({billing_cycle.capitalize()})',
                        'description': description,
                    },
                    'unit_amount': int(charge_amount * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri('/billing/stripe-success/') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri('/billing/my-plan/'),
            metadata={
                'user_id': str(request.user.id),
                'plan_id': str(base_plan.id),
                'billing_cycle': billing_cycle,
                'is_custom': 'true',
                'custom_employees': str(employees),
                'custom_leads': str(leads),
                'custom_monthly_price': str(monthly_price),
            }
        )

        # Get or create subscription
        subscription, created = Subscription.objects.get_or_create(
            owner=request.user,
            defaults={
                'plan': base_plan,
                'billing_cycle': billing_cycle,
                'is_active': False,
                'auto_renew': True,
                'is_custom_plan': True,
                'custom_max_employees': employees,
                'custom_max_leads': leads,
                'custom_monthly_price': monthly_price,
            }
        )

        if not created:
            subscription.plan = base_plan
            subscription.billing_cycle = billing_cycle
            subscription.is_active = False
            subscription.auto_renew = True
            subscription.is_custom_plan = True
            subscription.custom_max_employees = employees
            subscription.custom_max_leads = leads
            subscription.custom_monthly_price = monthly_price
            subscription.end_date = None
            subscription.save()

        # Create payment record
        Payment.objects.create(
            user=request.user,
            subscription=subscription,
            amount=charge_amount,
            original_amount=pricing['base_amount'],
            discount_amount=pricing['total_discount'],
            discount_source=pricing['discount_source'],
            discount_label=pricing['discount_label'],
            pending_coupon=pricing['coupon'],
            applied_campaign=pricing['campaign'],
            due_date=date.today(),
            payment_method='stripe',
            stripe_payment_intent_id=checkout_session.id,
            is_paid=False,
        )

        return JsonResponse({'sessionId': checkout_session.id})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@user_passes_test(is_owner)
def validate_coupon(request):
    coupon_code = request.GET.get('coupon', '').strip()
    billing_cycle = request.GET.get('cycle', 'monthly')
    plan_id = request.GET.get('plan_id')
    is_custom = request.GET.get('is_custom') == '1'

    if not coupon_code:
        return JsonResponse({'valid': False, 'message': 'Please enter a coupon code.'}, status=400)

    if is_custom:
        employees = request.GET.get('employees')
        leads = request.GET.get('leads')
        if not employees or not leads:
            return JsonResponse({'valid': False, 'message': 'Select employees and leads first.'}, status=400)

        try:
            employees = int(employees)
            leads = int(leads)
        except (TypeError, ValueError):
            return JsonResponse({'valid': False, 'message': 'Invalid custom plan values.'}, status=400)

        config = PricingConfig.objects.first()
        if not config or not config.is_active:
            return JsonResponse({'valid': False, 'message': 'Custom plan builder is unavailable.'}, status=400)

        base_plan = Plan.objects.filter(is_active=True).order_by('monthly_price').first()
        if not base_plan:
            return JsonResponse({'valid': False, 'message': 'No active plan available for validation.'}, status=400)

        base_amount = config.calculate_yearly_price(employees, leads) if billing_cycle == 'yearly' else config.calculate_monthly_price(employees, leads)
        pricing = _calculate_discounted_amount(
            base_amount=base_amount,
            plan=base_plan,
            billing_cycle=billing_cycle,
            user=request.user,
            coupon_code=coupon_code,
            custom_plan=True,
        )
    else:
        if not plan_id:
            return JsonResponse({'valid': False, 'message': 'Choose a plan first.'}, status=400)

        plan = get_object_or_404(Plan, id=plan_id, is_active=True)
        base_amount = plan.yearly_price if billing_cycle == 'yearly' else plan.monthly_price
        pricing = _calculate_discounted_amount(
            base_amount=base_amount,
            plan=plan,
            billing_cycle=billing_cycle,
            user=request.user,
            coupon_code=coupon_code,
        )

    if pricing['base_amount'] <= 0:
        return JsonResponse({'valid': False, 'message': 'Selected plan is already free. Coupon cannot reduce it further.'}, status=400)

    if pricing['coupon_error']:
        return JsonResponse({'valid': False, 'message': pricing['coupon_error']}, status=400)

    if not pricing['coupon']:
        return JsonResponse({'valid': False, 'message': 'Coupon did not apply any discount.'}, status=400)

    return JsonResponse({
        'valid': True,
        'message': 'Coupon applied successfully.',
        'base_amount': format_price(pricing['base_amount']),
        'final_amount': format_price(pricing['final_amount']),
        'discount_amount': format_price(pricing['total_discount']),
        'campaign_discount': format_price(pricing['campaign_discount']),
        'coupon_discount': format_price(pricing['coupon_discount']),
        'discount_label': pricing['discount_label'],
        'currency_symbol': get_currency_symbol(),
    })


@login_required
@user_passes_test(is_owner)
def coupon_plan_previews(request):
    coupon_code = request.GET.get('coupon', '').strip()
    billing_cycle = request.GET.get('cycle', 'monthly')

    if not coupon_code:
        return JsonResponse({'message': 'Please enter a coupon code.'}, status=400)

    previews = []
    for plan in Plan.objects.filter(is_active=True).order_by('monthly_price', 'id'):
        base_amount = plan.yearly_price if billing_cycle == 'yearly' else plan.monthly_price
        pricing = _calculate_discounted_amount(
            base_amount=base_amount,
            plan=plan,
            billing_cycle=billing_cycle,
            user=request.user,
            coupon_code=coupon_code,
        )

        previews.append({
            'plan_id': plan.id,
            'base_amount': format_price(pricing['base_amount']),
            'final_amount': format_price(pricing['final_amount']),
            'discount_amount': format_price(pricing['total_discount']),
            'campaign_discount': format_price(pricing['campaign_discount']),
            'coupon_discount': format_price(pricing['coupon_discount']),
            'discount_label': pricing['discount_label'],
            'coupon_applied': bool(pricing['coupon']),
            'base_is_free': pricing['base_amount'] <= 0,
        })

    return JsonResponse({
        'currency_symbol': get_currency_symbol(),
        'cycle': billing_cycle,
        'previews': previews,
    })


@login_required
@user_passes_test(is_owner)
def stripe_success(request):
    """Handle successful Stripe payment"""
    session_id = request.GET.get('session_id')

    if session_id:
        # Check if Stripe keys are configured
        if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_SECRET_KEY.startswith('sk_'):
            messages.error(request, 'Stripe is not properly configured. Please contact administrator.')
            return redirect('my_plan')

        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            session = stripe.checkout.Session.retrieve(session_id)

            # Find the payment associated with this session
            payment = Payment.objects.filter(stripe_payment_intent_id=session.id).first()

            if payment and not payment.is_paid:
                # Update payment status
                payment.is_paid = True
                payment.paid_date = date.today()
                payment.stripe_charge_id = session.payment_intent
                payment.transaction_id = session.payment_intent
                payment.save()

                subscription = payment.subscription
                subscription.is_active = True
                subscription.start_date = date.today()
                if subscription.billing_cycle == 'yearly':
                    subscription.end_date = date.today() + timedelta(days=365)
                else:
                    subscription.end_date = date.today() + timedelta(days=30)
                subscription.save()

                _finalize_coupon_redemption(payment)

                # Enforce plan limits after plan change (deactivate excess employees)
                enforce_plan_limits(request.user)

                plan_display = 'Custom Plan' if subscription.is_custom_plan else subscription.plan.name
                messages.success(request, f'Payment successful! Your {plan_display} ({subscription.get_billing_cycle_display()}) is now active.')

                # Notify owner about successful payment
                notify(
                    recipient=request.user,
                    notification_type='payment_received',
                    title='Payment Successful!',
                    message=f'Your payment of {get_currency_symbol()}{format_price(payment.amount)} for {plan_display} ({subscription.get_billing_cycle_display()}) was successful.',
                    url='/billing/my-plan/',
                )

                # Send plan activation email
                send_email(
                    to_email=request.user.email,
                    subject=f'LeadSync - Your {plan_display} is Now Active!',
                    template_name='emails/plan_activated.html',
                    context={
                        'username': request.user.username,
                        'plan_name': plan_display,
                        'billing_cycle': subscription.get_billing_cycle_display(),
                        'amount': format_price(payment.amount),
                        'max_employees': subscription.effective_max_employees,
                        'max_leads': subscription.effective_max_leads,
                        'dashboard_url': request.build_absolute_uri('/dashboard/'),
                    },
                )
            elif payment and payment.is_paid:
                messages.info(request, 'This payment has already been processed.')
            else:
                messages.error(request, 'Payment record not found.')

        except Exception as e:
            messages.error(request, f'Error retrieving payment details: {str(e)}')

    return redirect('my_plan')


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=400)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Handle checkout.session.completed (our main flow uses checkout sessions)
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        payment = Payment.objects.filter(stripe_payment_intent_id=session['id']).first()

        if payment and not payment.is_paid:
            payment.is_paid = True
            payment.paid_date = date.today()
            payment.stripe_charge_id = session.get('payment_intent', '')
            payment.transaction_id = session.get('payment_intent', '')
            payment.save()

            subscription = payment.subscription
            subscription.is_active = True
            subscription.start_date = date.today()
            if subscription.billing_cycle == 'yearly':
                subscription.end_date = date.today() + timedelta(days=365)
            else:
                subscription.end_date = date.today() + timedelta(days=30)
            subscription.save()

            _finalize_coupon_redemption(payment)

            enforce_plan_limits(payment.user)

            notify(
                recipient=payment.user,
                notification_type='payment_received',
                title='Payment Confirmed',
                message=f'Your payment of {get_currency_symbol()}{format_price(payment.amount)} has been confirmed. Your {subscription.plan.name} plan is now active!',
                url='/billing/my-plan/',
            )

            # Send plan activation email
            send_email(
                to_email=payment.user.email,
                subject=f'LeadSync - Your {subscription.plan.name} Plan is Now Active!',
                template_name='emails/plan_activated.html',
                context={
                    'username': payment.user.username,
                    'plan_name': subscription.plan.name,
                    'billing_cycle': subscription.get_billing_cycle_display(),
                    'amount': format_price(payment.amount),
                    'max_employees': subscription.effective_max_employees,
                    'dashboard_url': '/dashboard/',
                },
            )

    elif event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        # Fallback: if checkout.session.completed wasn't caught
        payment = Payment.objects.filter(stripe_payment_intent_id=payment_intent['id']).first()
        if payment and not payment.is_paid:
            payment.is_paid = True
            payment.paid_date = date.today()
            payment.stripe_charge_id = payment_intent.get('charges', {}).get('data', [{}])[0].get('id', '')
            payment.transaction_id = payment_intent['id']
            payment.save()

            subscription = payment.subscription
            subscription.is_active = True
            subscription.start_date = date.today()
            if subscription.billing_cycle == 'yearly':
                subscription.end_date = date.today() + timedelta(days=365)
            else:
                subscription.end_date = date.today() + timedelta(days=30)
            subscription.save()

            _finalize_coupon_redemption(payment)

            enforce_plan_limits(payment.user)

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        payment = Payment.objects.filter(stripe_payment_intent_id=payment_intent['id']).first()
        if payment:
            # Notify user about failed payment
            notify(
                recipient=payment.user,
                notification_type='system',
                title='Payment Failed',
                message='Your payment could not be processed. Please try again or use a different payment method.',
                url='/billing/my-plan/',
            )

    return HttpResponse(status=200)