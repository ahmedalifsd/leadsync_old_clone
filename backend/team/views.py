from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from openpyxl import load_workbook, Workbook

from accounts.views import is_owner, is_super_admin
from billing.models import Subscription
from core.utils import notify, send_email, get_table_page_size
from .forms import AssignRoleForm, RoleForm, TeamEmployeeCreateForm
from .models import Role, TeamMember


def _invalidate_staff_perms_cache(staff_user_id):
    """Clear cached permissions for a staff user when their role changes."""
    cache.delete(f'user_perms_{staff_user_id}')


def _soft_remove_member_for_owner(team_member):
    """Archive a staff member for an owner without deleting the user record."""
    staff = team_member.staff
    team_member.is_active = False
    team_member.is_removed = True
    team_member.removed_at = timezone.now()
    team_member.save(update_fields=['is_active', 'is_removed', 'removed_at'])

    # Keep credentials reserved but block any future login.
    staff.is_active = False
    staff.save(update_fields=['is_active'])

    profile = staff.profile
    profile.is_approved = False
    profile.pending_boss_username = ''
    profile.save(update_fields=['is_approved', 'pending_boss_username'])

    _invalidate_staff_perms_cache(staff.id)


def _set_owner_team_active_state(owner_user, is_active):
    """Suspend or restore an owner's active team members."""
    team_members = TeamMember.objects.filter(boss=owner_user, is_removed=False).select_related('staff')

    with transaction.atomic():
        for team_member in team_members:
            staff_user = team_member.staff

            if is_active:
                should_restore = team_member.previous_active_state
                team_member.is_active = should_restore
                team_member.previous_active_state = False
                staff_user.is_active = should_restore
            else:
                team_member.previous_active_state = team_member.is_active
                team_member.is_active = False
                staff_user.is_active = False

            team_member.save(update_fields=['is_active', 'previous_active_state'])
            staff_user.save(update_fields=['is_active'])
            _invalidate_staff_perms_cache(staff_user.id)


@login_required
@user_passes_test(is_owner)
def manage_team(request):
    search_query = request.GET.get('search', '')

    # Show approved members only in the main table.
    team_members = TeamMember.objects.filter(
        boss=request.user,
        is_removed=False,
        staff__profile__is_approved=True,
    ).select_related('staff', 'staff__profile', 'role')

    if search_query:
        team_members = team_members.filter(
            Q(staff__username__icontains=search_query) |
            Q(staff__first_name__icontains=search_query) |
            Q(staff__last_name__icontains=search_query) |
            Q(staff__email__icontains=search_query) |
            Q(staff__profile__phone_number__icontains=search_query)
        ).distinct()

    per_page = get_table_page_size(request, 'manage_team', default=15)
    paginator = Paginator(team_members, per_page)
    page_number = request.GET.get('page')
    team_members_page = paginator.get_page(page_number)

    subscription = Subscription.objects.filter(owner=request.user, is_active=True).first()
    available_roles = Role.objects.filter(owner=request.user)

    from accounts.models import UserProfile
    pending_staff = UserProfile.objects.filter(
        role='staff',
        user__is_active=True,
        is_approved=False,
    ).filter(
        Q(pending_boss_username__iexact=request.user.username)
        | Q(user__team_boss__boss=request.user, user__team_boss__is_removed=False)
    ).select_related('user').distinct()

    active_count = TeamMember.objects.filter(
        boss=request.user,
        is_active=True,
        is_removed=False,
        staff__profile__is_approved=True,
    ).count()
    inactive_count = TeamMember.objects.filter(
        boss=request.user,
        is_active=False,
        is_removed=False,
        staff__profile__is_approved=True,
    ).count()
    deleted_staff = TeamMember.objects.filter(
        boss=request.user,
        is_removed=True,
    ).select_related('staff', 'staff__profile', 'role').order_by('-removed_at')

    remaining_slots = 0
    if subscription:
        max_emp = subscription.effective_max_employees
        if max_emp is not None:
            remaining_slots = max(0, max_emp - active_count)
        else:
            remaining_slots = None # Unlimited if max_emp is None in sub
    else:
        remaining_slots = 0

    employee_form = TeamEmployeeCreateForm(request.user)

    context = {
        'team_members': team_members_page,
        'subscription': subscription,
        'search_query': search_query,
        'available_roles': available_roles,
        'pending_staff': pending_staff,
        'active_count': active_count,
        'inactive_count': inactive_count,
        'deleted_staff': deleted_staff,
        'remaining_slots': remaining_slots,
        'employee_form': employee_form,
        'per_page': per_page,
    }

    return render(request, 'team/manage_team.html', context)


@login_required
@user_passes_test(is_owner)
def download_employees_template(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Employees"

    headers = ['username', 'email', 'phone_number', 'role', 'password']
    ws.append(headers)

    # Sample row (leave password empty to auto-generate during import)
    ws.append(['employee1', 'employee1@example.com', '03001234567', '', ''])

    # Basic formatting
    ws.freeze_panes = "A2"
    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 18
    ws.column_dimensions['E'].width = 18

    from io import BytesIO
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    response = HttpResponse(
        bio.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="employees_import_template.xlsx"'
    return response


@login_required
@user_passes_test(is_owner)
def import_employees(request):
    if request.method != 'POST':
        return redirect('manage_team')

    upload = request.FILES.get('file')
    if not upload:
        messages.error(request, 'Please select an Excel file to import.')
        return redirect('manage_team')

    try:
        wb = load_workbook(filename=upload, read_only=True, data_only=True)
        sheet = wb.active
    except Exception:
        messages.error(request, 'Could not read the uploaded Excel file. Please upload a valid .xlsx file.')
        return redirect('manage_team')

    # Expected headers (case-insensitive)
    header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
    if not header_row:
        messages.error(request, 'The Excel file is empty.')
        return redirect('manage_team')

    header_map = {str(v).strip().lower(): idx for idx, v in enumerate(header_row) if v is not None}

    required_headers = ['username', 'email', 'phone_number']
    missing = [h for h in required_headers if h not in header_map]
    if missing:
        messages.error(
            request,
            f'Missing required column(s): {", ".join(missing)}. Required columns are: username, email, phone_number. '
            'Optional columns: role, password.'
        )
        return redirect('manage_team')

    created_count = 0
    skipped_count = 0
    error_rows = []

    # Subscription limit enforcement
    subscription = Subscription.objects.filter(owner=request.user, is_active=True).first()
    max_emp = subscription.effective_max_employees if subscription else None
    current_active = TeamMember.objects.filter(
        boss=request.user,
        is_active=True,
        is_removed=False,
        staff__profile__is_approved=True,
    ).count()

    from django.contrib.auth.hashers import make_password
    from django.utils.crypto import get_random_string

    for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if not any(row):
            continue

        def get_val(col_name):
            col_idx = header_map.get(col_name)
            if col_idx is None:
                return ''
            value = row[col_idx]
            return str(value).strip() if value is not None else ''

        username = get_val('username')
        email = get_val('email')
        phone_number = get_val('phone_number')
        role_name = get_val('role')
        password = get_val('password') or get_random_string(10)

        if not username or not email or not phone_number:
            skipped_count += 1
            error_rows.append(f'Row {idx}: Missing required data.')
            continue

        if User.objects.filter(username__iexact=username).exists():
            skipped_count += 1
            error_rows.append(f'Row {idx}: Username "{username}" already exists.')
            continue

        if User.objects.filter(email__iexact=email).exists():
            skipped_count += 1
            error_rows.append(f'Row {idx}: Email "{email}" already exists.')
            continue

        if max_emp is not None and current_active >= max_emp:
            error_rows.append(
                f'Row {idx}: Subscription limit reached. No more employees can be added.'
            )
            break

        role_obj = None
        if role_name:
            role_obj = Role.objects.filter(owner=request.user, name__iexact=role_name).first()

        form_data = {
            'username': username,
            'email': email,
            'phone_number': phone_number,
            'role': role_obj.id if role_obj else '',
            'password1': password,
            'password2': password,
        }

        form = TeamEmployeeCreateForm(request.user, form_data)
        if form.is_valid():
            user = form.save()
            # Set a non-guessable password explicitly to avoid any issues
            user.password = make_password(password)
            user.save(update_fields=['password'])
            created_count += 1
            # Imported employees are created as inactive in TeamEmployeeCreateForm.save()
        else:
            skipped_count += 1
            first_error = next(iter(form.errors.values()))
            error_msg = first_error[0] if first_error else 'Invalid data.'
            error_rows.append(f'Row {idx}: {error_msg}')
            continue

    if created_count:
        messages.success(request, f'{created_count} employee(s) imported successfully from Excel.')
    if skipped_count:
        messages.warning(
            request,
            f'{skipped_count} row(s) were skipped during import. '
            f'{"; ".join(error_rows[:5])}' + ('; ...' if len(error_rows) > 5 else '')
        )

    return redirect('manage_team')


@login_required
@user_passes_test(is_owner)
def create_employee(request):
    if request.method != 'POST':
        return redirect('manage_team')

    form = TeamEmployeeCreateForm(request.user, request.POST)
    if form.is_valid():
        raw_password = form.cleaned_data['password1']
        user = form.save()
        send_email(
            to_email=user.email,
            subject='LeadSync - Your Employee Account Has Been Created',
            template_name='emails/staff_created.html',
            context={
                'staff_username': user.username,
                'staff_password': raw_password,
                'staff_email': user.email,
                'boss_username': request.user.username,
                'company_name': user.profile.company_name,
                'login_url': request.build_absolute_uri('/login/'),
                'is_auto_inactive': True,
            },
        )
        messages.success(request, f'Employee {user.username} created as inactive and login details emailed.')
    else:
        first_error = next(iter(form.errors.values()))
        messages.error(request, first_error[0] if first_error else 'Could not add employee. Please check the form.')

    return redirect('manage_team')


@login_required
@user_passes_test(is_owner)
@require_POST
def toggle_staff_status(request, staff_id):
    """Toggle a team member between active and inactive without affecting approval status."""
    team_member = get_object_or_404(TeamMember, staff_id=staff_id, boss=request.user, is_removed=False)

    if team_member.is_active:
        team_member.is_active = False
        team_member.save()
        _invalidate_staff_perms_cache(staff_id)
        messages.success(request, f'{team_member.staff.username} has been deactivated.')
    else:
        subscription = Subscription.objects.filter(owner=request.user, is_active=True).first()
        current_active = TeamMember.objects.filter(boss=request.user, is_active=True).count()
        max_emp = subscription.effective_max_employees if subscription else None
        if subscription and max_emp is not None and current_active >= max_emp:
            messages.error(request, 'Cannot reactivate: Maximum employee limit reached! Upgrade your plan.')
            return redirect('manage_team')

        team_member.is_active = True
        team_member.save()
        _invalidate_staff_perms_cache(staff_id)
        messages.success(request, f'{team_member.staff.username} has been reactivated.')

    return redirect('manage_team')


@login_required
@user_passes_test(is_owner)
def remove_staff(request, staff_id):
    if request.method != 'POST':
        return redirect('manage_team')

    staff = get_object_or_404(User, id=staff_id)

    # Check if this staff belongs to current owner
    team_member = TeamMember.objects.filter(boss=request.user, staff=staff, is_removed=False).first()

    if team_member:
        _soft_remove_member_for_owner(team_member)
        messages.success(request, f'Staff {staff.username} moved to deleted employees list.')

        # Notify removed staff
        notify(
            recipient=staff,
            notification_type='staff_removed',
            title='Removed from Team',
            message=f'You have been removed from {request.user.username}\'s team.',
            sender=request.user,
        )
    else:
        messages.error(request, 'This staff member does not belong to your team.')

    return redirect('manage_team')


@login_required
@user_passes_test(is_owner)
def bulk_remove_staff(request):
    if request.method == 'POST':
        staff_ids = request.POST.getlist('staff_ids')

        if staff_ids:
            team_members = TeamMember.objects.filter(
                boss=request.user,
                staff_id__in=staff_ids,
                is_removed=False,
            ).select_related('staff', 'staff__profile')

            updated = 0
            for team_member in team_members:
                _soft_remove_member_for_owner(team_member)
                updated += 1

            messages.success(request, f'{updated} staff member(s) moved to deleted employees list!')
        else:
            messages.warning(request, 'No staff members selected.')

    return redirect('manage_team')


@login_required
@user_passes_test(is_owner)
def bulk_deactivate_staff(request):
    if request.method == 'POST':
        staff_ids = request.POST.getlist('staff_ids')

        if staff_ids:
            updated = TeamMember.objects.filter(
                boss=request.user,
                staff_id__in=staff_ids,
                is_active=True
            ).update(is_active=False)

            for sid in staff_ids:
                _invalidate_staff_perms_cache(int(sid))

            messages.success(request, f'{updated} staff member(s) deactivated!')
        else:
            messages.warning(request, 'No staff members selected.')

    return redirect('manage_team')


@login_required
@user_passes_test(is_super_admin)
def admin_manage_employees(request):
    """View for super admin to manage all employees"""
    from accounts.models import UserProfile

    # Get all employees (users with role 'staff')
    employees_qs = UserProfile.objects.filter(role='staff').select_related('user').order_by('-created_at')
    total_employees = employees_qs.count()
    approved_employees = employees_qs.filter(is_approved=True).count()
    pending_employees = employees_qs.filter(is_approved=False).count()
    active_team_members = TeamMember.objects.filter(
        staff__profile__role='staff',
        is_active=True,
        is_removed=False,
    ).count()

    per_page = get_table_page_size(request, 'admin_manage_employees', default=15)
    paginator = Paginator(employees_qs, per_page)
    page_number = request.GET.get('page')
    employees = paginator.get_page(page_number)

    context = {
        'employees': employees,
        'total_employees': total_employees,
        'approved_employees': approved_employees,
        'pending_employees': pending_employees,
        'active_team_members': active_team_members,
        'per_page': per_page,
    }

    return render(request, 'team/admin_manage_employees.html', context)


@login_required
@user_passes_test(is_super_admin)
def admin_manage_business_owners(request):
    """View for super admin to manage all business owners"""
    from accounts.models import UserProfile
    from billing.models import Subscription

    # Get all business owners (users with role 'owner')
    business_owners = UserProfile.objects.filter(role='owner').select_related('user', 'user__subscription').order_by('-created_at')
    approved_owner_profiles_qs = business_owners.filter(is_approved=True)
    pending_owner_profiles_qs = business_owners.filter(is_approved=False)

    total_business_owners = business_owners.count()
    approved_business_owners = approved_owner_profiles_qs.count()
    pending_business_owners = pending_owner_profiles_qs.count()
    active_plan_owners = Subscription.objects.filter(owner__profile__role='owner', is_active=True).count()

    per_page = get_table_page_size(request, 'admin_manage_business_owners', default=15)
    approved_paginator = Paginator(approved_owner_profiles_qs, per_page)
    pending_paginator = Paginator(pending_owner_profiles_qs, per_page)
    business_owners_page = approved_paginator.get_page(request.GET.get('owners_page'))
    pending_owner_profiles_page = pending_paginator.get_page(request.GET.get('pending_page'))

    context = {
        'business_owners': business_owners_page,
        'pending_owner_profiles': pending_owner_profiles_page,
        'total_business_owners': total_business_owners,
        'approved_business_owners': approved_business_owners,
        'pending_business_owners': pending_business_owners,
        'active_plan_owners': active_plan_owners,
        'per_page': per_page,
    }

    return render(request, 'team/admin_manage_business_owners.html', context)


@login_required
@user_passes_test(is_super_admin)
@require_POST
def toggle_business_owner_status(request, user_id):
    """Activate or deactivate a business owner and sync their active employees."""
    owner_profile = get_object_or_404(UserProfile, user_id=user_id, role='owner')
    owner_user = owner_profile.user

    owner_user.is_active = not owner_user.is_active
    owner_user.save(update_fields=['is_active'])

    _set_owner_team_active_state(owner_user, owner_user.is_active)

    if owner_user.is_active:
        messages.success(request, f'{owner_user.username} has been reactivated and eligible employees were restored.')
    else:
        messages.success(request, f'{owner_user.username} has been deactivated and their active employees were suspended.')

    return redirect('admin_manage_business_owners')


@login_required
@user_passes_test(is_super_admin)
def admin_view_business_owner(request, user_id):
    """Detailed view for a specific business owner showing their employees, leads, and plans"""
    from accounts.models import UserProfile
    from core.models import Lead
    from billing.models import Subscription

    # Get the business owner
    business_owner = get_object_or_404(UserProfile, user_id=user_id, role='owner')
    owner_user = business_owner.user

    # Get their employees
    from team.models import TeamMember
    employees = TeamMember.objects.filter(boss=owner_user, is_active=True).select_related('staff__profile')

    # Get their leads
    leads = Lead.objects.filter(owner=owner_user).select_related('created_by', 'category', 'source').order_by('-created_at')[:10]  # Last 10 leads

    # Get their subscription
    subscription = Subscription.objects.filter(owner=owner_user).first()

    context = {
        'business_owner': business_owner,
        'employees': employees,
        'leads': leads,
        'subscription': subscription,
    }

    return render(request, 'team/admin_view_business_owner.html', context)


# =====================================================
# ROLE MANAGEMENT VIEWS (Business Owner Only)
# =====================================================

@login_required
@user_passes_test(is_owner)
def manage_roles(request):
    """View all roles created by this owner"""
    roles = Role.objects.filter(owner=request.user).prefetch_related('members')
    total_permissions = len(Role.get_permission_fields())
    roles_in_use = roles.filter(members__isnull=False).distinct().count()
    assigned_members = TeamMember.objects.filter(
        boss=request.user,
        is_active=True,
        role__isnull=False,
    ).count()

    context = {
        'roles': roles,
        'total_roles': roles.count(),
        'total_permissions': total_permissions,
        'roles_in_use': roles_in_use,
        'assigned_members': assigned_members,
    }
    return render(request, 'team/manage_roles.html', context)


@login_required
@user_passes_test(is_owner)
def create_role(request):
    """Create a new role"""
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save(commit=False)
            role.owner = request.user
            # Check if role name already exists for this owner
            if Role.objects.filter(name=role.name, owner=request.user).exists():
                messages.warning(request, f'Role "{role.name}" already exists!')
            else:
                role.save()
                messages.success(request, f'Role "{role.name}" created successfully!')
            return redirect('manage_roles')
    else:
        form = RoleForm()

    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'team/role_form.html', context)


@login_required
@user_passes_test(is_owner)
def edit_role(request, role_id):
    """Edit an existing role"""
    role = get_object_or_404(Role, id=role_id, owner=request.user)

    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            # Check if renamed role name conflicts with existing
            new_name = form.cleaned_data['name']
            if Role.objects.filter(name=new_name, owner=request.user).exclude(id=role.id).exists():
                messages.warning(request, f'Role "{new_name}" already exists!')
            else:
                form.save()
                # Invalidate cache for all staff with this role
                for sid in TeamMember.objects.filter(role=role, is_active=True).values_list('staff_id', flat=True):
                    _invalidate_staff_perms_cache(sid)
                messages.success(request, f'Role "{role.name}" updated successfully!')
            return redirect('manage_roles')
    else:
        form = RoleForm(instance=role)

    context = {
        'form': form,
        'role': role,
        'action': 'Edit',
    }
    return render(request, 'team/role_form.html', context)


@login_required
@user_passes_test(is_owner)
def delete_role(request, role_id):
    """Delete a role"""
    role = get_object_or_404(Role, id=role_id, owner=request.user)

    if request.method == 'POST':
        role_name = role.name
        # Invalidate cache for all staff with this role before deletion
        for sid in TeamMember.objects.filter(role=role, is_active=True).values_list('staff_id', flat=True):
            _invalidate_staff_perms_cache(sid)
        # Members with this role will have role set to NULL (handled by SET_NULL)
        role.delete()
        messages.success(request, f'Role "{role_name}" deleted successfully! Members with this role now have no role assigned.')
        return redirect('manage_roles')

    return redirect('manage_roles')


@login_required
@user_passes_test(is_owner)
def assign_role(request, staff_id):
    """Assign a role to a team member"""
    team_member = get_object_or_404(
        TeamMember,
        staff_id=staff_id,
        boss=request.user,
        is_removed=False,
    )

    if request.method == 'POST':
        form = AssignRoleForm(request.user, request.POST)
        if form.is_valid():
            role = form.cleaned_data['role']
            team_member.role = role
            team_member.save()

            # Invalidate cached permissions for this staff member
            _invalidate_staff_perms_cache(team_member.staff_id)

            if role:
                messages.success(request, f'Role "{role.name}" assigned to {team_member.staff.username}!')

                # Notify staff about role assignment
                notify(
                    recipient=team_member.staff,
                    notification_type='role_assigned',
                    title='Role Assigned',
                    message=f'{request.user.username} assigned you the role "{role.name}".',
                    url='/dashboard/',
                    sender=request.user,
                )
            else:
                messages.success(request, f'Role removed from {team_member.staff.username}.')
            return redirect('manage_team')
        messages.error(request, 'Invalid role selection. Please try again.')

    return redirect('manage_team')


@login_required
@user_passes_test(is_owner)
def view_role_permissions(request, role_id):
    """View permissions of a specific role (AJAX/modal friendly)"""
    role = get_object_or_404(Role, id=role_id, owner=request.user)
    permissions = Role.get_permission_fields()

    context = {
        'role': role,
        'permissions': permissions,
    }
    return render(request, 'team/role_permissions_detail.html', context)