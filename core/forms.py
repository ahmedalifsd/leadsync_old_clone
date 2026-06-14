from django import forms
from django.contrib.auth.models import User
from .models import Lead, Category, Source, OwnerCategory, OwnerSource, ProfileLink, CustomField, LeadSharing, LeadActivity, LeadAssignmentHistory
from .utils import get_custom_fields_for_user

from django import forms
from django.contrib.auth.models import User
from .models import Lead, Category, Source, OwnerCategory, OwnerSource
from .utils import get_custom_fields_for_user


def _get_owner_for_user(user):
    if not user or not hasattr(user, 'profile'):
        return None

    if user.profile.role == 'owner':
        return user

    if user.profile.role == 'staff':
        from team.models import TeamMember
        tm = TeamMember.objects.filter(staff=user, is_active=True).select_related('boss').first()
        return tm.boss if tm else None

    return None


def _build_category_choices_for_user(user, empty_label='Select Category'):
    global_categories = list(Category.objects.all().values_list('id', 'name'))
    choices = [('', empty_label)]
    choices.extend((str(cat_id), cat_name) for cat_id, cat_name in global_categories)

    owner_user = _get_owner_for_user(user)
    if owner_user:
        owner_categories = OwnerCategory.objects.filter(owner=owner_user).values_list('id', 'name')
        choices.extend((f'owner_{cat_id}', f'{cat_name} (Private)') for cat_id, cat_name in owner_categories)

    choices.append(('other', 'Other'))
    return choices


def _build_source_choices_for_user(user, empty_label='Select Source'):
    global_sources = list(Source.objects.all().values_list('id', 'name'))
    choices = [('', empty_label)]
    choices.extend((str(src_id), src_name) for src_id, src_name in global_sources)

    owner_user = _get_owner_for_user(user)
    if owner_user:
        owner_sources = OwnerSource.objects.filter(owner=owner_user).values_list('id', 'name')
        choices.extend((f'owner_{src_id}', f'{src_name} (Private)') for src_id, src_name in owner_sources)

    choices.append(('other', 'Other'))
    return choices


class LeadForm(forms.ModelForm):

    category_choice = forms.ChoiceField(
        choices=[],
        required=False,
        label="Category"
    )

    category_other = forms.CharField(
        required=False,
        label="Specify Category",
        widget=forms.TextInput(attrs={'placeholder': 'Enter custom category'})
    )

    source_choice = forms.ChoiceField(
        choices=[],
        required=False,
        label="Source"
    )

    source_other = forms.CharField(
        required=False,
        label="Specify Source",
        widget=forms.TextInput(attrs={'placeholder': 'Enter custom source'})
    )

    class Meta:
        model = Lead
        fields = [
            'client_name', 'contact_number', 'email', 'requirement',
            'status', 'follow_up_date', 'notes', 'category', 'category_other',
            'source', 'source_other', 'budget', 'timeline', 'decision_maker',
            'converted_to_customer', 'assigned_to'
        ]

        widgets = {
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'timeline': forms.DateInput(attrs={'type': 'date'}),
            'requirement': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):

        user = kwargs.pop('user', None)
        instance = kwargs.get('instance')

        super().__init__(*args, **kwargs)

        self.user_instance = user

        # Optional fields
        self.fields['contact_number'].required = False
        self.fields['requirement'].required = False

        # Team assignment
        if user and hasattr(user, 'profile') and user.profile.role == 'owner':
            from team.models import TeamMember

            staff_ids = TeamMember.objects.filter(
                boss=user
            ).values_list('staff_id', flat=True)

            self.fields['assigned_to'].queryset = User.objects.filter(id__in=staff_ids)

        else:
            self.fields['assigned_to'].widget = forms.HiddenInput()

        self.fields['category_choice'].choices = _build_category_choices_for_user(user, empty_label='Select Category')
        self.fields['source_choice'].choices = _build_source_choices_for_user(user, empty_label='Select Source')

        # Staff status restriction
        if user and hasattr(user, 'profile') and user.profile.role == 'staff':
            self.fields['status'].choices = list(Lead.STATUS_CHOICES)

        # Dynamic custom fields
        if user:
            custom_fields = get_custom_fields_for_user(user)

            for custom_field in custom_fields:

                field_name = f"custom_{custom_field.id}"

                initial_value = None

                if instance and instance.custom_fields:
                    initial_value = instance.custom_fields.get(custom_field.name)

                if custom_field.field_type == 'text':

                    self.fields[field_name] = forms.CharField(
                        label=custom_field.name,
                        required=custom_field.required,
                        initial=initial_value
                    )

                elif custom_field.field_type == 'number':

                    self.fields[field_name] = forms.FloatField(
                        label=custom_field.name,
                        required=custom_field.required,
                        initial=initial_value
                    )

                elif custom_field.field_type == 'date':

                    self.fields[field_name] = forms.DateField(
                        label=custom_field.name,
                        required=custom_field.required,
                        widget=forms.DateInput(attrs={'type': 'date'}),
                        initial=initial_value
                    )

                elif custom_field.field_type == 'boolean':

                    self.fields[field_name] = forms.BooleanField(
                        label=custom_field.name,
                        required=False,
                        initial=initial_value
                    )

                elif custom_field.field_type == 'choice':

                    choices = [
                        (c.strip(), c.strip())
                        for c in custom_field.choices.split(',')
                    ]

                    self.fields[field_name] = forms.ChoiceField(
                        label=custom_field.name,
                        required=custom_field.required,
                        choices=[('', 'Select')] + choices,
                        initial=initial_value
                    )

                elif custom_field.field_type == 'textarea':

                    self.fields[field_name] = forms.CharField(
                        label=custom_field.name,
                        required=custom_field.required,
                        widget=forms.Textarea(attrs={'rows': 3}),
                        initial=initial_value
                    )

        # ===============================
        # ADD BOOTSTRAP CLASSES
        # ===============================

        for field_name, field in self.fields.items():

            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'

            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'

            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = 'form-control'

            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs['class'] = 'form-control'

            else:
                field.widget.attrs['class'] = 'form-control'

class ProfileLinkForm(forms.ModelForm):
    class Meta:
        model = ProfileLink
        fields = ['platform', 'custom_platform', 'url']
        widgets = {
            'url': forms.URLInput(attrs={'placeholder': 'https://example.com'}),
            'custom_platform': forms.TextInput(attrs={'placeholder': 'Platform name'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make custom_platform required only when platform is 'other'
        if self.instance and self.instance.platform != 'other':
            self.fields['custom_platform'].required = False


class ProfileLinkFormSet(forms.formset_factory(ProfileLinkForm, extra=1, can_delete=True)):
    pass


class BulkLeadForm(forms.Form):
    # Shared fields for all leads
    category_choice = forms.ChoiceField(
        choices=[],
        required=False,
        label="Category for all leads",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_category_choice'})
    )
    category_other = forms.CharField(
        required=False,
        label="Specify Category",
        widget=forms.TextInput(attrs={'placeholder': 'Enter custom category', 'class': 'form-control', 'id': 'id_category_other'})
    )
    source_choice = forms.ChoiceField(
        choices=[],
        required=False,
        label="Source for all leads",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_source_choice'})
    )
    source_other = forms.CharField(
        required=False,
        label="Specify Source",
        widget=forms.TextInput(attrs={'placeholder': 'Enter custom source', 'class': 'form-control', 'id': 'id_source_other'})
    )
    status = forms.ChoiceField(
        choices=Lead.STATUS_CHOICES,
        initial='new',
        label="Status for all leads",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    follow_up_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_follow_up_date'}),
        label="Follow-up Date for all leads"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Common notes for all leads', 'class': 'form-control'}),
        label="Common Notes for all leads"
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Assign to team member (default)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Store user instance for later use in clean and save methods
        self.user_instance = user

        self.fields['category_choice'].choices = _build_category_choices_for_user(
            user,
            empty_label='Select Category for all leads'
        )

        self.fields['source_choice'].choices = _build_source_choices_for_user(
            user,
            empty_label='Select Source for all leads'
        )

        if user:
            # Set up assigned_to queryset (approved team members)
            from team.models import TeamMember
            owner_user = _get_owner_for_user(user)
            if owner_user:
                team_user_ids = TeamMember.objects.filter(
                    boss=owner_user,
                    is_active=True
                ).values_list('staff_id', flat=True)
                
                # Use UserProfile to find approved users
                from accounts.models import UserProfile
                approved_user_ids = UserProfile.objects.filter(
                    user_id__in=team_user_ids,
                    is_approved=True
                ).values_list('user_id', flat=True)
                
                self.fields['assigned_to'].queryset = User.objects.filter(id__in=approved_user_ids).order_by('username')
            else:
                self.fields.pop('assigned_to')

        if user and hasattr(user, 'profile') and user.profile.role == 'staff':
            self.fields['status'].choices = [
                ('new', 'New'),
                ('contacted', 'Contacted'),
            ]

        # Add custom fields dynamically (both 'all' and 'each' scopes for BulkLeadForm, only active)
        if user:
            custom_fields = get_custom_fields_for_user(user)
            for custom_field in custom_fields:
                field_name = f"custom_{custom_field.id}"
                if custom_field.field_type == 'text':
                    self.fields[field_name] = forms.CharField(
                        label=custom_field.name,
                        required=custom_field.required,
                        widget=forms.TextInput(attrs={'class': 'form-control'})
                    )
                elif custom_field.field_type == 'number':
                    self.fields[field_name] = forms.FloatField(
                        label=custom_field.name,
                        required=custom_field.required,
                        widget=forms.NumberInput(attrs={'class': 'form-control'})
                    )
                elif custom_field.field_type == 'date':
                    self.fields[field_name] = forms.DateField(
                        label=custom_field.name,
                        required=custom_field.required,
                        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
                    )
                elif custom_field.field_type == 'boolean':
                    self.fields[field_name] = forms.BooleanField(
                        label=custom_field.name,
                        required=custom_field.required,
                        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                    )
                elif custom_field.field_type == 'choice':
                    choices = [(choice.strip(), choice.strip()) for choice in custom_field.choices.split(',')]
                    self.fields[field_name] = forms.ChoiceField(
                        label=custom_field.name,
                        required=custom_field.required,
                        choices=[('', 'Select...')] + choices,
                        widget=forms.Select(attrs={'class': 'form-select'})
                    )
                elif custom_field.field_type == 'textarea':
                    self.fields[field_name] = forms.CharField(
                        label=custom_field.name,
                        required=custom_field.required,
                        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
                    )

        # Add assigned_to field for owners to assign leads during bulk creation
        if user and hasattr(user, 'profile') and user.profile.role == 'owner':
            from team.models import TeamMember
            # Only include active and approved team members
            staff_ids = TeamMember.objects.filter(boss=user, is_active=True).values_list('staff_id', flat=True)
            # Also ensure the staff member's profile is approved
            from accounts.models import UserProfile
            approved_staff_ids = UserProfile.objects.filter(
                user_id__in=staff_ids,
                is_approved=True
            ).values_list('user_id', flat=True)
            self.fields['assigned_to'] = forms.ModelChoiceField(
                queryset=User.objects.filter(id__in=approved_staff_ids),
                required=False,
                empty_label="Assign to team member (optional)",
                label="Assign to team member for all leads",
                widget=forms.Select(attrs={'class': 'form-control'})

            )


class LeadEntryForm(forms.Form):
    """Individual lead entry form"""
    client_name = forms.CharField(
        max_length=200,
        label="Client Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'required': 'required'})
    )
    contact_number = forms.CharField(
        max_length=20,
        required=False,
        label="Contact Number",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=False,
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    requirement = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        label="Requirement"
    )
    status = forms.ChoiceField(
        choices=[('', 'Use shared status')] + list(Lead.STATUS_CHOICES),
        required=False,
        label="Status (optional override)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    follow_up_date = forms.DateField(
        required=False,
        label="Follow-up Date (optional override)",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and hasattr(user, 'profile') and user.profile.role == 'staff':
            self.fields['status'].choices = [('', 'Use shared status')] + list(Lead.STATUS_CHOICES)

        if user and hasattr(user, 'profile') and user.profile.role == 'owner':
            from team.models import TeamMember
            from accounts.models import UserProfile

            staff_ids = TeamMember.objects.filter(
                boss=user,
                is_active=True,
            ).values_list('staff_id', flat=True)
            approved_staff_ids = UserProfile.objects.filter(
                user_id__in=staff_ids,
                is_approved=True,
            ).values_list('user_id', flat=True)

            self.fields['assigned_to'] = forms.ModelChoiceField(
                queryset=User.objects.filter(id__in=approved_staff_ids),
                required=False,
                empty_label='Use shared assignment',
                label='Assign Team Member (optional override)',
                widget=forms.Select(attrs={'class': 'form-select'})
            )


class LeadEntryCustomFieldsForm(forms.Form):
    """Form for custom fields for individual leads in bulk add"""
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        lead_index = kwargs.pop('lead_index', 0)  # Index of the lead in the formset
        super().__init__(*args, **kwargs)

        if user:
            # Only add active custom fields with 'each' scope
            custom_fields = get_custom_fields_for_user(user, scope='each')
            for custom_field in custom_fields:
                # Use a simple field name that will be prefixed by the formset
                field_name = f"custom_{custom_field.id}"
                if custom_field.field_type == 'text':
                    self.fields[field_name] = forms.CharField(
                        label=custom_field.name,
                        required=custom_field.required,
                        widget=forms.TextInput(attrs={'class': 'form-control'})
                    )
                elif custom_field.field_type == 'number':
                    self.fields[field_name] = forms.FloatField(
                        label=custom_field.name,
                        required=custom_field.required,
                        widget=forms.NumberInput(attrs={'class': 'form-control'})
                    )
                elif custom_field.field_type == 'date':
                    self.fields[field_name] = forms.DateField(
                        label=custom_field.name,
                        required=custom_field.required,
                        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
                    )
                elif custom_field.field_type == 'boolean':
                    self.fields[field_name] = forms.BooleanField(
                        label=custom_field.name,
                        required=custom_field.required,
                        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                    )
                elif custom_field.field_type == 'choice':
                    choices = [(choice.strip(), choice.strip()) for choice in custom_field.choices.split(',')]
                    self.fields[field_name] = forms.ChoiceField(
                        label=custom_field.name,
                        required=custom_field.required,
                        choices=[('', 'Select...')] + choices,
                        widget=forms.Select(attrs={'class': 'form-select'})
                    )
                elif custom_field.field_type == 'textarea':
                    self.fields[field_name] = forms.CharField(
                        label=custom_field.name,
                        required=custom_field.required,
                        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
                    )


class BaseLeadEntryFormSet(forms.BaseFormSet):
    """Base FormSet for lead rows with user-aware field options."""
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['user'] = self.user
        return kwargs


LeadEntryFormSet = forms.formset_factory(
    LeadEntryForm,
    formset=BaseLeadEntryFormSet,
    extra=1,
    max_num=20,
)


class BaseLeadEntryCustomFieldsFormSet(forms.BaseFormSet):
    """Base FormSet for custom fields per lead"""
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['user'] = self.user
        kwargs['lead_index'] = index
        return kwargs


# Create the formset class with the custom formset
LeadEntryCustomFieldsFormSet = forms.formset_factory(
    LeadEntryCustomFieldsForm,
    formset=BaseLeadEntryCustomFieldsFormSet,
    extra=0,
    max_num=20,
    can_delete=False
)


class MultipleLeadForm(forms.Form):
    """Form for multiple leads with shared properties"""
    category_choice = forms.ChoiceField(
        choices=[],
        required=False,
        label="Category for all leads"
    )
    category_other = forms.CharField(
        required=False,
        label="Specify Category",
        widget=forms.TextInput(attrs={'placeholder': 'Enter custom category'})
    )
    source_choice = forms.ChoiceField(
        choices=[],
        required=False,
        label="Source for all leads"
    )
    source_other = forms.CharField(
        required=False,
        label="Specify Source",
        widget=forms.TextInput(attrs={'placeholder': 'Enter custom source'})
    )
    status = forms.ChoiceField(
        choices=Lead.STATUS_CHOICES,
        initial='new',
        label="Status for all leads"
    )
    follow_up_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Follow-up Date for all leads"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Common notes for all leads'}),
        label="Common Notes for all leads"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['category_choice'].choices = _build_category_choices_for_user(
            user,
            empty_label='Select Category for all leads'
        )

        self.fields['source_choice'].choices = _build_source_choices_for_user(
            user,
            empty_label='Select Source for all leads'
        )

        if user and hasattr(user, 'profile') and user.profile.role == 'staff':
            self.fields['status'].choices = list(Lead.STATUS_CHOICES)


from django.core.validators import FileExtensionValidator
import csv
import io


# Import the model inside the form to avoid circular import
from .models import LeadTemplate


class LeadFilterForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        empty_label=" Categories",
        widget = forms.Select(attrs={'class': 'form-select form-control-sm '})  # Bootstrap select
    )
    source = forms.ModelChoiceField(
        queryset=Source.objects.none(),
        required=False,
        empty_label="All Sources",
    widget = forms.Select(attrs={'class': 'form-select form-control-sm '})  # Bootstrap select

    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Lead.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select select2 form-control-sm '})  # Bootstrap select

    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-select '}),

    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-select '})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set querysets for filtering
        self.fields['category'].queryset = Category.objects.all()
        self.fields['source'].queryset = Source.objects.all()


class LeadTemplateForm(forms.ModelForm):
    """Form for creating/updating lead templates"""
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="Select Category (optional)",
    widget = forms.Select(attrs={'class': 'form-select'})  # Bootstrap select

    )
    source = forms.ModelChoiceField(
        queryset=Source.objects.all(),
        required=False,
        empty_label="Select Source (optional)",
    widget = forms.Select(attrs={'class': 'form-select'})  # Bootstrap select

    )

    class Meta:
        model = LeadTemplate
        fields = ['name', 'category', 'source', 'status', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Ensure querysets are set even without user
        self.fields['category'].queryset = Category.objects.all()
        self.fields['source'].queryset = Source.objects.all()


class CSVUploadForm(forms.Form):
    """Form for uploading CSV files for lead import"""
    csv_file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        help_text="Upload a CSV file with leads data. Download the template below to see all supported columns including profile links and custom fields."
    )
    template = forms.ModelChoiceField(
        queryset=LeadTemplate.objects.none(),
        required=False,
        empty_label="Choose a template (optional)",
        help_text="Apply template settings to all imported leads",
    widget=forms.Select(attrs={'class': 'form-control'})

    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['template'].queryset = LeadTemplate.objects.filter(owner=user)

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if csv_file:
            # Validate file size (max 5MB)
            if csv_file.size > 5 * 1024 * 1024:  # 5MB
                raise forms.ValidationError('File size exceeds 5MB limit.')

            try:
                # Read and validate CSV content
                content = csv_file.read().decode('utf-8')
                csv_file.seek(0)  # Reset file pointer

                # Parse CSV to check if it has required headers
                reader = csv.DictReader(io.StringIO(content))

                # Validate column names to prevent injection attacks
                for fieldname in reader.fieldnames:
                    if not fieldname.replace('_', '').replace('-', '').replace(' ', '').isalnum():
                        raise forms.ValidationError('Invalid characters in column names.')

                required_columns = ['client_name', 'contact_number', 'requirement']

                # Check if required columns exist
                missing_columns = []
                for col in required_columns:
                    if col not in reader.fieldnames:
                        missing_columns.append(col)

                if missing_columns:
                    raise forms.ValidationError(f'Missing required columns: {", ".join(missing_columns)}')

                # Check if there are any rows to import
                rows = list(reader)
                if not rows or len(rows) == 0:
                    raise forms.ValidationError('CSV file is empty or has no data rows')

                # Limit number of rows to prevent abuse
                if len(rows) > 1000:  # Max 1000 leads per import
                    raise forms.ValidationError('CSV file has too many rows (max 1000)')

                # Validate each row for potential security issues
                for i, row in enumerate(rows, start=1):
                    for col, value in row.items():
                        if value:
                            # Check for potential script tags or malicious content
                            if '<script' in value.lower() or 'javascript:' in value.lower():
                                raise forms.ValidationError(f'Potential security issue detected in row {i}, column "{col}".')

                            # Sanitize input
                            row[col] = value.strip()

            except UnicodeDecodeError:
                raise forms.ValidationError('Invalid CSV file format. Please upload a valid CSV file.')
            except Exception as e:
                raise forms.ValidationError(f'Error reading CSV file: {str(e)}')

        return csv_file


class LeadAssignmentForm(forms.Form):
    """Form for assigning leads to team members"""
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=True,
        empty_label="Select Team Member"
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Reason for assignment'}),
        required=False,
        help_text="Optional reason for assigning this lead"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # Only show team members for owners
            from team.models import TeamMember
            staff_ids = TeamMember.objects.filter(boss=user).values_list('staff_id', flat=True)
            self.fields['assigned_to'].queryset = User.objects.filter(id__in=staff_ids)


class LeadScoringForm(forms.Form):
    """Form for lead scoring"""
    budget = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        help_text="Estimated budget of the lead"
    )
    timeline = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Expected timeline for decision"
    )
    decision_maker = forms.BooleanField(
        required=False,
        help_text="Is the contact the decision maker?"
    )


class CustomFieldForm(forms.ModelForm):
    """Form for creating custom fields"""
    class Meta:
        model = CustomField
        fields = ['name', 'field_type', 'scope', 'choices', 'required']
        widgets = {
            'choices': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Option 1, Option 2, Option 3...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'



class LeadActivityForm(forms.ModelForm):
    """Form for adding activities to leads"""
    class Meta:
        model = LeadActivity
        fields = ['activity_type', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe the activity...'}),
        }


class LeadSharingForm(forms.ModelForm):
    """Form for sharing leads with team members"""
    class Meta:
        model = LeadSharing
        fields = ['shared_with', 'permissions', 'expires_at']
        widgets = {
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        lead = kwargs.pop('lead', None)
        super().__init__(*args, **kwargs)

        if user:
            # Only show team members for sharing
            from team.models import TeamMember
            staff_ids = TeamMember.objects.filter(boss=user).values_list('staff_id', flat=True)
            self.fields['shared_with'].queryset = User.objects.filter(id__in=staff_ids).exclude(id=user.id)

        if lead:
            # Exclude already shared users
            shared_users = LeadSharing.objects.filter(lead=lead).values_list('shared_with', flat=True)
            self.fields['shared_with'].queryset = self.fields['shared_with'].queryset.exclude(id__in=shared_users)


class SourceForm(forms.ModelForm):
    """Form for creating/editing sources"""
    class Meta:
        model = Source
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter source name'}),
        }