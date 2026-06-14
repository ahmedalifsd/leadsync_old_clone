from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from .forms import CustomUserCreationForm, UserProfileForm
from .models import UserProfile
from team.models import TeamMember
from billing.models import Subscription
from core.utils import notify, send_email


def custom_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, 'Please enter both username and password.')
            return render(request, 'accounts/login.html')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Check if user has a profile and is approved
            try:
                profile = user.profile
            except Exception:
                profile = None

            # Super admin can always login
            if profile and profile.role == 'super_admin':
                login(request, user)
                return redirect('dashboard')

            # Check if account is approved
            if profile and not profile.is_approved:
                if profile.role == 'owner':
                    messages.warning(
                        request,
                        'Your account is pending approval. You will receive an email once your account is approved by the admin.'
                    )
                elif profile.role == 'staff':
                    boss_name = profile.pending_boss_username or 'your manager'
                    messages.warning(
                        request,
                        f'Your account is pending approval from {boss_name}. You will receive an email once approved.'
                    )
                else:
                    messages.warning(request, 'Your account is not yet approved. Please wait for approval.')
                return render(request, 'accounts/login.html')

            # For staff: also check if their TeamMember is active (deactivated ≠ unapproved)
            if profile and profile.role == 'staff':
                from team.models import TeamMember
                tm = TeamMember.objects.select_related('boss').filter(staff=user).first()
                if tm and not tm.boss.is_active:
                    messages.warning(
                        request,
                        'Your manager account is currently inactive. Please contact the admin.'
                    )
                    return render(request, 'accounts/login.html')

                tm = TeamMember.objects.filter(staff=user, is_active=False).first()
                if tm:
                    messages.warning(
                        request,
                        'Your account has been deactivated by your manager. Please contact them to reactivate it.'
                    )
                    return render(request, 'accounts/login.html')

            login(request, user)
            remember = request.POST.get('remember')
            if not remember:
                request.session.set_expiry(0)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')

    return render(request, 'accounts/login.html')


@require_GET
def check_availability(request):
    """AJAX endpoint to check if username or email already exists."""
    field = request.GET.get('field', '')
    value = request.GET.get('value', '').strip()

    if not value:
        return JsonResponse({'available': True})

    if field == 'username':
        exists = User.objects.filter(username__iexact=value).exists()
        if exists:
            return JsonResponse({'available': False, 'message': 'This username is already taken.'})
        return JsonResponse({'available': True, 'message': 'Username is available!'})

    elif field == 'email':
        exists = User.objects.filter(email__iexact=value).exists()
        if exists:
            return JsonResponse({'available': False, 'message': 'An account with this email already exists.'})
        return JsonResponse({'available': True, 'message': 'Email is available!'})

    return JsonResponse({'available': True})


def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Automatically assign the default signup plan to new OWNER users
            profile = user.profile
            if profile.role == 'owner':
                from billing.models import Plan, Subscription
                default_plan = Plan.objects.filter(is_default_signup_plan=True, is_active=True).first()
                if default_plan:
                    Subscription.objects.create(
                        owner=user,
                        plan=default_plan,
                        is_active=False  # Will be activated when admin approves
                    )

            messages.success(request, 'Registration successful! Please wait for approval.')

            # Send registration email to the user
            plan_name = ''
            if profile.role == 'owner':
                from billing.models import Subscription as Sub
                sub = Sub.objects.filter(owner=user).first()
                if sub and sub.plan:
                    plan_name = sub.plan.name

            role_display = 'Business Owner' if profile.role == 'owner' else 'Staff/Employee'
            send_email(
                to_email=user.email,
                subject='LeadSync - Account Registration Submitted for Approval',
                template_name='emails/registration_pending.html',
                context={
                    'username': user.username,
                    'email': user.email,
                    'role': role_display,
                    'plan_name': plan_name,
                },
            )

            # Notify: if staff signed up, notify the boss
            profile = user.profile
            if profile.role == 'staff' and profile.pending_boss_username:
                try:
                    boss = User.objects.get(username__iexact=profile.pending_boss_username)
                    notify(
                        recipient=boss,
                        notification_type='system',
                        title='New Staff Request',
                        message=f'{user.username} has requested to join your team. Please review and approve.',
                        url='/accounts/manage-staff-requests/',
                        sender=user,
                    )
                except User.DoesNotExist:
                    pass
            # If owner signed up, notify all super admins
            elif profile.role == 'owner':
                from accounts.models import UserProfile as UP
                super_admins = UP.objects.filter(role='super_admin').select_related('user')
                for sa in super_admins:
                    notify(
                        recipient=sa.user,
                        notification_type='system',
                        title='New Owner Registration',
                        message=f'{user.username} registered as a Business Owner and needs approval.',
                        url='/accounts/admin-panel/',
                        sender=user,
                    )

            return redirect('login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user.profile)

    return render(request, 'accounts/profile.html', {'form': form})


# Super Admin Functions
def is_super_admin(user):
    return user.profile.role == 'super_admin'


@login_required
@user_passes_test(is_super_admin)
def admin_panel(request):
    # Get pending owners
    pending_owners = UserProfile.objects.filter(
        role='owner',
        is_approved=False
    ).select_related('user')

    # Get all users except super admin
    all_users = UserProfile.objects.exclude(role='super_admin').select_related('user')
    total_users = all_users.count()
    approved_users = all_users.filter(is_approved=True).count()
    staff_users = all_users.filter(role='staff').count()

    context = {
        'pending_owners': pending_owners,
        'all_users': all_users,
        'total_users': total_users,
        'approved_users': approved_users,
        'staff_users': staff_users,
    }

    return render(request, 'accounts/admin_panel.html', context)


@login_required
@user_passes_test(is_super_admin)
def approve_owner(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = user.profile

    if profile.role == 'owner' and not profile.is_approved:
        profile.is_approved = True
        profile.save()

        # Activate existing subscription (created during signup) or create one with default plan
        from billing.models import Plan, Subscription
        subscription = Subscription.objects.filter(owner=user).first()

        if subscription:
            # User already has a subscription from signup — just activate it
            subscription.is_active = True
            subscription.save()
        else:
            # No subscription exists — create one with the default signup plan
            default_plan = Plan.objects.filter(is_default_signup_plan=True, is_active=True).first()
            if default_plan:
                Subscription.objects.create(
                    owner=user,
                    plan=default_plan,
                    is_active=True
                )
            else:
                messages.warning(request, 'No default signup plan set! Please set a default plan in Manage Plans.')
                profile.is_approved = False
                profile.save()
                return redirect('admin_panel')

        messages.success(request, f'Owner {user.username} approved successfully!')

        # Notify the approved owner
        notify(
            recipient=user,
            notification_type='owner_approved',
            title='Account Approved!',
            message='Your business owner account has been approved. You can now start using LeadSync!',
            url='/dashboard/',
            sender=request.user,
        )

        # Send approval email to the owner
        sub = Subscription.objects.filter(owner=user, is_active=True).first()
        plan_name = sub.plan.name if sub and sub.plan else ''
        login_url = request.build_absolute_uri('/login/')
        send_email(
            to_email=user.email,
            subject='LeadSync - Your Account Has Been Approved!',
            template_name='emails/account_approved.html',
            context={
                'username': user.username,
                'plan_name': plan_name,
                'login_url': login_url,
            },
        )
    else:
        messages.warning(request, f'Owner {user.username} is already approved or not a valid owner.')

    return redirect('admin_panel')


@login_required
@user_passes_test(is_super_admin)
@require_POST
def toggle_owner_approval(request, user_id):
    """Toggle a business owner's approval state without deleting the account."""
    user = get_object_or_404(User, id=user_id)
    profile = user.profile

    if profile.role != 'owner':
        messages.warning(request, f'{user.username} is not a valid owner account.')
        return redirect('admin_panel')

    profile.is_approved = not profile.is_approved
    profile.save(update_fields=['is_approved'])

    from billing.models import Plan, Subscription
    subscription = Subscription.objects.filter(owner=user).first()

    if profile.is_approved:
        if subscription:
            subscription.is_active = True
            subscription.save(update_fields=['is_active'])
        else:
            default_plan = Plan.objects.filter(is_default_signup_plan=True, is_active=True).first()
            if default_plan:
                Subscription.objects.create(owner=user, plan=default_plan, is_active=True)
            else:
                messages.warning(request, 'No default signup plan set! Please set a default plan in Manage Plans.')
                profile.is_approved = False
                profile.save(update_fields=['is_approved'])
                return redirect('admin_panel')
        messages.success(request, f'Owner {user.username} approved successfully!')
        notify(
            recipient=user,
            notification_type='owner_approved',
            title='Account Approved!',
            message='Your business owner account has been approved. You can now start using LeadSync!',
            url='/dashboard/',
            sender=request.user,
        )
    else:
        if subscription:
            subscription.is_active = False
            subscription.save(update_fields=['is_active'])
        messages.success(request, f'Owner {user.username} has been disapproved.')
        notify(
            recipient=user,
            notification_type='owner_rejected',
            title='Account Disapproved',
            message='Your business owner account approval has been removed. Please contact support if this was a mistake.',
            url='/accounts/admin-panel/',
            sender=request.user,
        )

    return redirect('admin_panel')


@login_required
@user_passes_test(is_super_admin)
def reject_owner(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = user.profile

    # Check if this owner is pending approval
    if profile.role == 'owner' and not profile.is_approved:
        username = user.username
        # Delete the user account completely
        user.delete()
        messages.success(request, f'Owner request from {username} rejected and removed.')
    else:
        messages.warning(request, f'Cannot reject {user.username}. Owner is already approved or not a valid owner.')

    return redirect('admin_panel')


@login_required
@user_passes_test(lambda user: user.profile.role == 'owner' and user.profile.is_approved)
@require_POST
def toggle_staff_approval(request, user_id):
    """Toggle a staff account's approval state without deleting it."""
    user = get_object_or_404(User, id=user_id)
    profile = user.profile

    if profile.role != 'staff':
        messages.warning(request, f'{user.username} is not a valid staff account.')
        return redirect('manage_team')

    team_member = TeamMember.objects.filter(boss=request.user, staff=user).first()
    if not team_member:
        messages.warning(request, f'{user.username} is not part of your team.')
        return redirect('manage_team')

    profile.is_approved = not profile.is_approved
    profile.save(update_fields=['is_approved'])

    if profile.is_approved:
        if team_member.previous_active_state or team_member.is_active:
            team_member.is_active = True
            team_member.previous_active_state = False
            team_member.save(update_fields=['is_active', 'previous_active_state'])
        messages.success(request, f'Staff {user.username} approved successfully!')
        notify(
            recipient=user,
            notification_type='staff_approved',
            title='Account Approved!',
            message=f'Your employee account has been approved by {request.user.username}. Welcome to the team!',
            url='/dashboard/',
            sender=request.user,
        )
    else:
        team_member.previous_active_state = team_member.is_active
        team_member.is_active = False
        team_member.save(update_fields=['is_active', 'previous_active_state'])
        messages.success(request, f'Staff {user.username} has been disapproved.')
        notify(
            recipient=user,
            notification_type='staff_rejected',
            title='Account Disapproved',
            message=f'Your employee account approval has been removed by {request.user.username}.',
            url='/dashboard/',
            sender=request.user,
        )

    return redirect('manage_team')


# Owner Functions
def is_owner(user):
    return user.profile.role == 'owner' and user.profile.is_approved


@login_required
@user_passes_test(is_owner)
def manage_staff_requests(request):
    return redirect('manage_team')


@login_required
@user_passes_test(is_owner)
def approve_staff(request, user_id):
    if request.method != 'POST':
        return redirect('manage_team')

    user = get_object_or_404(User, id=user_id)
    profile = user.profile

    linked_team_member = TeamMember.objects.filter(
        boss=request.user,
        staff=user,
        is_removed=False,
    ).first()

    is_pending_for_owner = (
        profile.pending_boss_username
        and profile.pending_boss_username.lower() == request.user.username.lower()
    )

    # Allow approve from either pending requests or previously disapproved linked staff.
    if (
        profile.role == 'staff'
        and user.is_active
        and not profile.is_approved
        and (is_pending_for_owner or linked_team_member is not None)
    ):

        # Check subscription limits
        subscription = Subscription.objects.filter(owner=request.user, is_active=True).first()
        current_staff_count = TeamMember.objects.filter(boss=request.user, is_active=True).count()

        max_emp = subscription.effective_max_employees if subscription else None
        if subscription and max_emp is not None and current_staff_count >= max_emp:
            messages.error(request, 'Cannot approve staff: Maximum employee limit reached!')
            return redirect('manage_team')

        # Approve staff
        profile.is_approved = True
        profile.save()

        # Add to team (get_or_create to avoid duplicate entry error)
        team_member, created = TeamMember.objects.get_or_create(
            boss=request.user,
            staff=user,
            defaults={'is_active': True}
        )
        if not created:
            # Reactivate linked staff, respecting any saved state from disapproval.
            team_member.is_active = True if team_member.previous_active_state else True
            team_member.previous_active_state = False
            team_member.save(update_fields=['is_active', 'previous_active_state'])

        messages.success(request, f'Staff {user.username} approved successfully!')

        # Notify the approved staff
        notify(
            recipient=user,
            notification_type='staff_approved',
            title='Account Approved!',
            message=f'Your employee account has been approved by {request.user.username}. Welcome to the team!',
            url='/dashboard/',
            sender=request.user,
        )

        # Send approval email to the staff member
        login_url = request.build_absolute_uri('/login/')
        send_email(
            to_email=user.email,
            subject='LeadSync - Your Account Has Been Approved!',
            template_name='emails/account_approved.html',
            context={
                'username': user.username,
                'plan_name': '',
                'login_url': login_url,
            },
        )
    else:
        messages.warning(request, f'Cannot approve {user.username}. Staff request is not valid for your account.')

    return redirect('manage_team')


@login_required
@user_passes_test(is_owner)
def reject_staff(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = user.profile

    if (profile.pending_boss_username and
            profile.pending_boss_username.lower() == request.user.username.lower() and
            profile.role == 'staff' and
            not profile.is_approved):

        username = user.username
        user.delete()
        messages.success(request, f'Staff request from {username} rejected and removed.')
    else:
        messages.warning(request, f'Cannot reject {user.username}. Staff request is not valid for your account.')

    return redirect('manage_team')