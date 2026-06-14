from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile


class CustomUserCreationForm(UserCreationForm):
    ROLE_CHOICES = (
        ('owner', 'Business Owner'),
        ('staff', 'Employee'),
    )

    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    pending_boss_username = forms.CharField(
        max_length=150,
        required=False,
        label="Boss Username",
        help_text="Enter your boss's username if registering as staff"
    )
    phone_number = forms.CharField(max_length=20, required=True)
    company_name = forms.CharField(max_length=200, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2',
                  'role', 'pending_boss_username', 'phone_number', 'company_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': 'Choose a username',
            'email': 'Enter your email',
            'password1': 'Create a password',
            'password2': 'Confirm your password',
            'phone_number': 'Enter phone number',
            'company_name': 'Enter company name',
        }
        for field_name, field in self.fields.items():
            if field_name == 'role':
                continue
            css = 'form-control'
            if field_name in ('pending_boss_username',):
                continue
            field.widget.attrs.update({
                'class': css,
                'placeholder': placeholders.get(field_name, ''),
            })
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None
        self.fields['username'].help_text = None

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        boss_username = cleaned_data.get('pending_boss_username', '').strip()

        if role == 'staff' and not boss_username:
            raise forms.ValidationError("Boss username is required for staff registration")

        if role == 'staff' and boss_username:
            try:
                # Case-insensitive lookup to avoid mismatch issues
                boss = User.objects.get(username__iexact=boss_username)
                if boss.profile.role != 'owner' or not boss.profile.is_approved:
                    raise forms.ValidationError("Boss must be an approved business owner")
                # Store the ACTUAL boss username (correct case) so it matches in queries
                cleaned_data['pending_boss_username'] = boss.username
            except User.DoesNotExist:
                raise forms.ValidationError("Boss username not found. Please check the spelling.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
            profile = user.profile
            profile.role = self.cleaned_data['role']
            profile.pending_boss_username = self.cleaned_data.get('pending_boss_username', '')
            profile.phone_number = self.cleaned_data['phone_number']
            profile.company_name = self.cleaned_data['company_name']
            profile.is_approved = False  # All new accounts need approval
            profile.save()

        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('phone_number', 'company_name')