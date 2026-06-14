from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile
# l1-`E~8y6W6+ = employee and business owner passwords

class Command(BaseCommand):
    help = 'Create a super admin user'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Super admin username')
        parser.add_argument('--email', type=str, help='Super admin email')
        parser.add_argument('--password', type=str, help='Super admin password')

    def handle(self, *args, **kwargs):
        username = kwargs['username'] or 'admin'
        email = kwargs['email'] or 'admin@leadsync.com'
        password = kwargs['password'] or 'admin1122'

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User {username} already exists'))
            user = User.objects.get(username=username)
        else:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'Created superuser {username}'))

        # Update profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.role = 'super_admin'
        profile.is_approved = True
        profile.save()

        self.stdout.write(self.style.SUCCESS(f'Super admin setup complete'))