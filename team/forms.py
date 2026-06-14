from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Role, TeamMember


class RoleForm(forms.ModelForm):
    """Form for creating/editing roles with permissions"""

    class Meta:
        model = Role
        fields = [
            'name', 'description',
            'can_view_leads', 'can_add_leads', 'can_edit_leads', 'can_delete_leads',
            'can_bulk_add_leads', 'can_csv_upload',
            'can_manage_templates', 'can_manage_custom_fields',
            'can_view_analytics', 'can_view_activity_log', 'can_view_deleted_leads',
            'can_assign_leads', 'can_share_leads',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Manager, HR, Senior'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Brief description of this role...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all checkbox fields
        for field_name, field in self.fields.items():
            if isinstance(field, forms.BooleanField):
                field.widget.attrs.update({'class': 'form-check-input'})


class AssignRoleForm(forms.Form):
    """Form for assigning a role to a team member"""
    role = forms.ModelChoiceField(
        queryset=Role.objects.none(),
        required=False,
        empty_label="-- No Role (No Permissions) --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, owner, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].queryset = Role.objects.filter(owner=owner)


class TeamEmployeeCreateForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=20, required=True)
    role = forms.ModelChoiceField(
        queryset=Role.objects.none(),
        required=False,
        empty_label='-- No Role --',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'phone_number', 'role', 'password1', 'password2')

    def __init__(self, owner, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.fields['role'].queryset = Role.objects.filter(owner=owner)

        field_classes = {
            'username': 'form-control',
            'email': 'form-control',
            'phone_number': 'form-control',
            'password1': 'form-control',
            'password2': 'form-control',
        }
        placeholders = {
            'username': 'Employee username',
            'email': 'Employee email',
            'phone_number': 'Phone number',
            'password1': 'Temporary password',
            'password2': 'Confirm password',
        }

        for field_name, css_class in field_classes.items():
            self.fields[field_name].widget.attrs.update({
                'class': css_class,
                'placeholder': placeholders[field_name],
            })

        self.fields['username'].help_text = None
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        selected_role = self.cleaned_data.get('role')
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
            profile = user.profile
            profile.role = 'staff'
            profile.pending_boss_username = ''
            profile.phone_number = self.cleaned_data['phone_number']
            profile.company_name = self.owner.profile.company_name
            profile.is_approved = True
            profile.save()

            team_member, created = TeamMember.objects.get_or_create(
                boss=self.owner,
                staff=user,
                defaults={'role': selected_role, 'is_active': False, 'is_removed': False, 'removed_at': None}
            )
            if not created:
                team_member.role = selected_role
                team_member.is_active = False
                team_member.is_removed = False
                team_member.removed_at = None
                team_member.save(update_fields=['role', 'is_active', 'is_removed', 'removed_at'])

        return user
