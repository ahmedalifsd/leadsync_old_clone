import random
import string
from datetime import date, timedelta, datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

FIRST_NAMES = [
    'Ahmed', 'Ali', 'Hassan', 'Usman', 'Bilal', 'Zain', 'Hamza', 'Omar',
    'Sara', 'Ayesha', 'Fatima', 'Hira', 'Maryam', 'Sana', 'Nadia', 'Rabia',
    'Farhan', 'Kamran', 'Tariq', 'Imran', 'Asad', 'Junaid', 'Waqas', 'Danish',
    'Amina', 'Khadija', 'Zara', 'Mahnoor', 'Iqra', 'Bushra', 'Rida', 'Sidra',
]

LAST_NAMES = [
    'Khan', 'Ahmed', 'Ali', 'Hussain', 'Malik', 'Sheikh', 'Butt', 'Rana',
    'Qureshi', 'Siddiqui', 'Shah', 'Mirza', 'Javed', 'Akhtar', 'Raza', 'Nawaz',
    'Chaudhry', 'Aslam', 'Rehman', 'Iqbal', 'Saeed', 'Baig', 'Noor', 'Zahid',
]

COMPANY_NAMES = [
    'TechVista Solutions', 'PixelPeak Digital', 'CloudNine Systems', 'DataDriven Labs',
    'NexGen Software', 'BrightPath Consulting', 'EagleEye Analytics', 'SwiftCode Technologies',
    'GreenLeaf Enterprises', 'BlueStar Marketing', 'SilverLine Media', 'GoldCrest Ventures',
    'OceanWave IT', 'SkyHigh Solutions', 'RedStone Innovations', 'CrystalClear Tech',
    'IronBridge Consulting', 'SunRise Digital', 'MoonLight Studios', 'StarGaze Media',
]

CLIENT_NAMES = [
    'Muhammad Rizwan', 'Aisha Patel', 'Carlos Rodriguez', 'Priya Sharma',
    'John Smith', 'Emily Johnson', 'David Williams', 'Sarah Brown',
    'Michael Lee', 'Jessica Davis', 'Robert Wilson', 'Jennifer Taylor',
    'Ahmed Al-Farsi', 'Fatima Al-Rashid', 'Chen Wei', 'Yuki Tanaka',
    'Sofia Martinez', 'Lucas Santos', 'Emma Thompson', 'Oliver Green',
    'Rashid Mehmood', 'Anwar Sheikh', 'Tahir Abbas', 'Noman Akram',
    'Kashif Raza', 'Samina Baig', 'Uzma Tariq', 'Khalid Mahmood',
    'Faisal Iqbal', 'Naveed Aslam', 'Shoaib Malik', 'Yasir Hameed',
    'Amir Hassan', 'Zainab Noor', 'Huma Qureshi', 'Mehwish Hayat',
    'Fawad Khan', 'Mahira Shah', 'Saba Qamar', 'Hamza Abbasi',
    'Rehan Siddiqui', 'Adeel Ahmed', 'Raza Ali', 'Saad Rehman',
    'Mohsin Akhtar', 'Naeem Javed', 'Shahid Afridi', 'Wasim Akram',
]

REQUIREMENTS = [
    'Looking for a complete CRM solution for 50+ team members',
    'Need custom reporting dashboard with real-time analytics',
    'Interested in lead management with automated follow-ups',
    'Want to integrate email marketing with lead tracking',
    'Require mobile app for field sales team',
    'Need API integration with existing ERP system',
    'Looking for bulk SMS integration with lead management',
    'Want automated lead scoring based on engagement',
    'Need multi-branch support with centralized reporting',
    'Interested in WhatsApp Business API integration',
    'Looking for inventory management + CRM combo',
    'Need HR module along with CRM functionality',
    'Require e-commerce integration for order tracking',
    'Want social media lead capture automation',
    'Need custom invoice generation from leads',
    'Looking for project management integration',
    'Require document management with lead profiles',
    'Need automated contract generation',
    'Want chatbot integration for lead qualification',
    'Need appointment scheduling system',
    'Interested in predictive analytics for sales',
    'Looking for territory management features',
    'Need commission tracking for sales team',
    'Want call recording integration',
    'Require lead deduplication automation',
    'Need pipeline visualization with drag-drop',
    'Want email tracking with open rates',
    'Looking for proposal builder integration',
    'Need customer onboarding workflow automation',
    'Require support ticket integration with CRM',
]

NOTES = [
    'High priority client - CEO directly involved in decision making',
    'Follow up next week - currently evaluating 3 other vendors',
    'Budget approved for Q2 - ready to proceed after board meeting',
    'Technical team needs demo before final decision',
    'Referred by existing client - warm lead',
    'Met at tech conference - very interested in enterprise plan',
    'Called twice, waiting for callback from IT head',
    'Sent proposal, awaiting feedback from procurement',
    'Decision expected by end of month',
    'Price sensitive - may need custom quote',
    'Fast mover - wants to start implementation ASAP',
    'Needs POC before committing to annual plan',
    'Currently using competitor product, looking to switch',
    'Startup with rapid growth, needs scalable solution',
    'Government sector - longer procurement cycle expected',
    'Multiple stakeholders involved - arrange group demo',
    'Seasonal business - plan activation in March',
    'Requires data migration from existing system',
    'International client - consider timezone for follow-ups',
    'Urgent requirement - lost data in previous system',
]

CATEGORY_NAMES = [
    'Technology', 'Healthcare', 'Education', 'Real Estate', 'Finance',
    'E-Commerce', 'Manufacturing', 'Retail', 'Hospitality', 'Logistics',
    'Automotive', 'Media & Entertainment', 'Telecommunications', 'Agriculture',
    'Construction', 'Energy', 'Legal Services', 'Food & Beverage',
]

SOURCE_NAMES = [
    'Website', 'Google Ads', 'Facebook', 'Instagram', 'LinkedIn',
    'Referral', 'Cold Call', 'Email Campaign', 'Trade Show', 'YouTube',
    'WhatsApp', 'Twitter/X', 'SEO Organic', 'Partner', 'Walk-in',
    'Webinar', 'Blog', 'TikTok',
]

LEAD_STATUSES = ['new', 'contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost']
STATUS_WEIGHTS = [25, 20, 18, 12, 10, 10, 5]

PLAN_DATA = [
    {'name': 'Free Starter', 'monthly_price': 0, 'yearly_discount': 0, 'max_employees': 1, 'monthly_max_leads': 50, 'yearly_max_leads': 50, 'is_default_signup_plan': True,
     'features': 'Basic lead management\n1 team member\n50 leads/month\nEmail support'},
    {'name': 'Basic', 'monthly_price': 9.99, 'yearly_discount': 15, 'max_employees': 3, 'monthly_max_leads': 500, 'yearly_max_leads': 700,
     'features': 'Everything in Free\n3 team members\n500 leads/month\nLead scoring\nCSV import/export'},
    {'name': 'Professional', 'monthly_price': 29.99, 'yearly_discount': 20, 'max_employees': 10, 'monthly_max_leads': 5000, 'yearly_max_leads': 7000,
     'features': 'Everything in Basic\n10 team members\n5,000 leads/month\nAdvanced analytics\nCustom fields\nRole management'},
    {'name': 'Business', 'monthly_price': 79.99, 'yearly_discount': 25, 'max_employees': 50, 'monthly_max_leads': 25000, 'yearly_max_leads': 35000,
     'features': 'Everything in Professional\n50 team members\n25,000 leads/month\nAPI access\nPriority support\nCustom integrations'},
    {'name': 'Enterprise', 'monthly_price': 199.99, 'yearly_discount': 30, 'max_employees': 200, 'monthly_max_leads': None, 'yearly_max_leads': None,
     'features': 'Everything in Business\n200 team members\nUnlimited leads\nDedicated account manager\nCustom development\nSLA guarantee'},
]

ROLE_DATA = [
    {'name': 'Sales Agent', 'description': 'Basic sales team member with lead management access',
     'can_view_leads': True, 'can_add_leads': True, 'can_edit_leads': True, 'can_delete_leads': False,
     'can_bulk_add_leads': False, 'can_csv_upload': False, 'can_manage_templates': False,
     'can_manage_custom_fields': False, 'can_view_analytics': False, 'can_view_activity_log': False,
     'can_view_deleted_leads': False, 'can_assign_leads': False, 'can_share_leads': True},
    {'name': 'Senior Sales', 'description': 'Senior sales with full lead control and analytics',
     'can_view_leads': True, 'can_add_leads': True, 'can_edit_leads': True, 'can_delete_leads': True,
     'can_bulk_add_leads': True, 'can_csv_upload': True, 'can_manage_templates': False,
     'can_manage_custom_fields': False, 'can_view_analytics': True, 'can_view_activity_log': True,
     'can_view_deleted_leads': True, 'can_assign_leads': True, 'can_share_leads': True},
    {'name': 'Team Lead', 'description': 'Team lead with management capabilities',
     'can_view_leads': True, 'can_add_leads': True, 'can_edit_leads': True, 'can_delete_leads': True,
     'can_bulk_add_leads': True, 'can_csv_upload': True, 'can_manage_templates': True,
     'can_manage_custom_fields': True, 'can_view_analytics': True, 'can_view_activity_log': True,
     'can_view_deleted_leads': True, 'can_assign_leads': True, 'can_share_leads': True},
    {'name': 'Viewer', 'description': 'Read-only access to leads',
     'can_view_leads': True, 'can_add_leads': False, 'can_edit_leads': False, 'can_delete_leads': False,
     'can_bulk_add_leads': False, 'can_csv_upload': False, 'can_manage_templates': False,
     'can_manage_custom_fields': False, 'can_view_analytics': True, 'can_view_activity_log': False,
     'can_view_deleted_leads': False, 'can_assign_leads': False, 'can_share_leads': False},
]


def rand_phone():
    return f'+92 3{random.randint(0,4)}{random.randint(0,9)} {random.randint(1000000, 9999999)}'


def rand_email(first, last, domain=None):
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'company.pk', 'business.com']
    d = domain or random.choice(domains)
    sep = random.choice(['.', '_', ''])
    num = random.randint(1, 999)
    return f'{first.lower()}{sep}{last.lower()}{num}@{d}'


def rand_date_between(start, end):
    delta = (end - start).days
    if delta <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta))


class Command(BaseCommand):
    help = 'Seeds the database with comprehensive mock data for testing'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Delete existing seed data before creating new')
        parser.add_argument('--owners', type=int, default=3, help='Number of business owners (default: 3)')
        parser.add_argument('--staff-per-owner', type=int, default=6, help='Staff per owner (default: 6)')
        parser.add_argument('--leads-per-owner', type=int, default=500, help='Leads per owner (default: 500)')
        parser.add_argument('--months', type=int, default=8, help='Months of historical data (default: 8)')

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting seed data generation...'))

        flush = options['flush']
        num_owners = options['owners']
        staff_per_owner = options['staff_per_owner']
        leads_per_owner = options['leads_per_owner']
        months = options['months']

        if flush:
            self._flush()

        self._create_site_settings()
        self._create_pricing_config()
        categories = self._create_categories()
        sources = self._create_sources()
        plans = self._create_plans()
        superadmin = self._ensure_superadmin()

        today = date.today()
        start_date = today - timedelta(days=months * 30)

        owners_data = []
        for i in range(num_owners):
            owner_data = self._create_owner(i, plans, start_date, today)
            if owner_data:
                owners_data.append(owner_data)

        for owner_data in owners_data:
            owner = owner_data['user']
            sub = owner_data['subscription']

            roles = self._create_roles(owner)
            staff_list = self._create_staff(owner, roles, staff_per_owner, start_date, today)

            self._create_leads(
                owner, staff_list, categories, sources,
                leads_per_owner, start_date, today
            )
            self._create_payments(owner, sub, start_date, today)
            self._create_notifications(owner, staff_list, today)
            self._create_activity_logs(owner, staff_list, start_date, today)

        total_leads = leads_per_owner * num_owners
        total_staff = staff_per_owner * num_owners
        self.stdout.write(self.style.SUCCESS(
            f'\nSeed data created successfully!\n'
            f'  Owners: {num_owners}\n'
            f'  Staff: {total_staff}\n'
            f'  Leads: ~{total_leads}\n'
            f'  Months: {months}\n'
            f'  Plans: {len(plans)}\n'
            f'  Categories: {len(categories)}\n'
            f'  Sources: {len(sources)}\n'
        ))

        self.stdout.write(self.style.WARNING('\nTest Accounts:'))
        self.stdout.write(f'  Super Admin: admin / admin1122')
        for i, od in enumerate(owners_data):
            self.stdout.write(f'  Owner {i+1}: {od["user"].username} / test1234')
        self.stdout.write('')

    def _flush(self):
        from core.models import Lead, Category, Source, Notification, ActivityLog, CustomField, LeadActivity, ProfileLink, LeadTemplate, LeadSharing, LeadAssignmentHistory
        from billing.models import Payment, Subscription, Plan
        from team.models import TeamMember, Role
        from accounts.models import UserProfile

        self.stdout.write('  Flushing existing data...')
        LeadActivity.objects.all().delete()
        LeadAssignmentHistory.objects.all().delete()
        LeadSharing.objects.all().delete()
        ProfileLink.objects.all().delete()
        ActivityLog.objects.all().delete()
        Notification.objects.all().delete()
        Lead.objects.all().delete()
        LeadTemplate.objects.all().delete()
        CustomField.objects.all().delete()
        Payment.objects.all().delete()
        TeamMember.objects.all().delete()
        Role.objects.all().delete()
        Subscription.objects.all().delete()
        Plan.objects.all().delete()
        # Delete non-admin users
        User.objects.filter(is_superuser=False).delete()
        Category.objects.all().delete()
        Source.objects.all().delete()

    def _create_site_settings(self):
        from billing.models import SiteSettings
        obj, created = SiteSettings.objects.get_or_create(pk=1, defaults={'currency_code': 'usd', 'site_name': 'LeadSync'})
        if created:
            self.stdout.write('  Created SiteSettings (USD)')

    def _create_pricing_config(self):
        from billing.models import PricingConfig
        obj, created = PricingConfig.objects.get_or_create(pk=1, defaults={
            'price_per_employee': Decimal('2.00'),
            'price_per_lead_block': Decimal('1.50'),
            'lead_block_size': 1000,
            'min_employees': 1,
            'max_employees': 500,
            'min_leads': 1000,
            'max_leads': 1000000,
            'lead_step': 1000,
            'employee_step': 1,
            'base_price': Decimal('5.00'),
            'yearly_discount': Decimal('20.00'),
            'unlimited_employees_price': Decimal('50.00'),
            'unlimited_leads_price': Decimal('30.00'),
            'is_active': True,
        })
        if created:
            self.stdout.write('  Created PricingConfig')

    def _create_categories(self):
        from core.models import Category
        cats = []
        for name in CATEGORY_NAMES:
            obj, _ = Category.objects.get_or_create(name=name)
            cats.append(obj)
        self.stdout.write(f'  Categories: {len(cats)}')
        return cats

    def _create_sources(self):
        from core.models import Source
        srcs = []
        for name in SOURCE_NAMES:
            obj, _ = Source.objects.get_or_create(name=name)
            srcs.append(obj)
        self.stdout.write(f'  Sources: {len(srcs)}')
        return srcs

    def _create_plans(self):
        from billing.models import Plan
        plans = []
        for pd in PLAN_DATA:
            obj, _ = Plan.objects.get_or_create(name=pd['name'], defaults={
                'monthly_price': Decimal(str(pd['monthly_price'])),
                'yearly_discount': Decimal(str(pd['yearly_discount'])),
                'max_employees': pd['max_employees'],
                'monthly_max_leads': pd['monthly_max_leads'],
                'yearly_max_leads': pd['yearly_max_leads'],
                'features': pd['features'],
                'is_active': True,
                'is_default_signup_plan': pd.get('is_default_signup_plan', False),
            })
            plans.append(obj)
        self.stdout.write(f'  Plans: {len(plans)}')
        return plans

    def _ensure_superadmin(self):
        user, created = User.objects.get_or_create(username='admin', defaults={
            'email': 'admin@leadsync.com', 'is_superuser': True, 'is_staff': True,
        })
        if created:
            user.set_password('admin1122')
            user.save()
        profile = user.profile
        profile.role = 'super_admin'
        profile.is_approved = True
        profile.save()
        self.stdout.write(f'  Super Admin: admin')
        return user

    def _create_owner(self, index, plans, start_date, today):
        from billing.models import Subscription
        from accounts.models import UserProfile

        first = FIRST_NAMES[index % len(FIRST_NAMES)]
        last = LAST_NAMES[index % len(LAST_NAMES)]
        username = f'{first.lower()}{last.lower()}{index+1}'
        email = rand_email(first, last, 'business.com')
        company = COMPANY_NAMES[index % len(COMPANY_NAMES)]

        user, created = User.objects.get_or_create(username=username, defaults={
            'email': email,
            'first_name': first,
            'last_name': last,
        })
        if created:
            user.set_password('test1234')
            user.save()

        profile = user.profile
        profile.role = 'owner'
        profile.is_approved = True
        profile.phone_number = rand_phone()
        profile.company_name = company
        profile.save()

        # Assign a paid plan (different for each owner)
        paid_plans = [p for p in plans if p.monthly_price > 0]
        plan = paid_plans[index % len(paid_plans)] if paid_plans else plans[0]
        cycle = random.choice(['monthly', 'yearly'])

        sub, sub_created = Subscription.objects.get_or_create(owner=user, defaults={
            'plan': plan,
            'billing_cycle': cycle,
            'is_active': True,
            'auto_renew': True,
        })
        if sub_created:
            sub.start_date = today - timedelta(days=random.randint(5, 25))
            if cycle == 'yearly':
                sub.end_date = sub.start_date + timedelta(days=365)
            else:
                sub.end_date = sub.start_date + timedelta(days=30)
            sub.save()

        self.stdout.write(f'  Owner: {username} ({company}) -> {plan.name} ({cycle})')
        return {'user': user, 'subscription': sub, 'company': company}

    def _create_roles(self, owner):
        from team.models import Role
        roles = []
        for rd in ROLE_DATA:
            role, _ = Role.objects.get_or_create(name=rd['name'], owner=owner, defaults={
                'description': rd['description'],
                'can_view_leads': rd['can_view_leads'],
                'can_add_leads': rd['can_add_leads'],
                'can_edit_leads': rd['can_edit_leads'],
                'can_delete_leads': rd['can_delete_leads'],
                'can_bulk_add_leads': rd['can_bulk_add_leads'],
                'can_csv_upload': rd['can_csv_upload'],
                'can_manage_templates': rd['can_manage_templates'],
                'can_manage_custom_fields': rd['can_manage_custom_fields'],
                'can_view_analytics': rd['can_view_analytics'],
                'can_view_activity_log': rd['can_view_activity_log'],
                'can_view_deleted_leads': rd['can_view_deleted_leads'],
                'can_assign_leads': rd['can_assign_leads'],
                'can_share_leads': rd['can_share_leads'],
            })
            roles.append(role)
        return roles

    def _create_staff(self, owner, roles, count, start_date, today):
        from team.models import TeamMember
        staff_list = []
        used = set()

        for i in range(count):
            while True:
                first = random.choice(FIRST_NAMES)
                last = random.choice(LAST_NAMES)
                username = f'{first.lower()}.{last.lower()}{random.randint(1,99)}'
                if username not in used and not User.objects.filter(username=username).exists():
                    used.add(username)
                    break

            email = rand_email(first, last)
            user, created = User.objects.get_or_create(username=username, defaults={
                'email': email,
                'first_name': first,
                'last_name': last,
            })
            if created:
                user.set_password('test1234')
                user.save()

            profile = user.profile
            profile.role = 'staff'
            profile.is_approved = True
            profile.pending_boss_username = owner.username
            profile.phone_number = rand_phone()
            profile.company_name = owner.profile.company_name
            profile.save()

            join_date = rand_date_between(start_date, today - timedelta(days=10))
            is_active = random.random() > 0.15  # 85% active

            tm, _ = TeamMember.objects.get_or_create(boss=owner, staff=user, defaults={
                'role': random.choice(roles) if roles else None,
                'is_active': is_active,
            })
            # Override auto_now_add by using update
            TeamMember.objects.filter(pk=tm.pk).update(joined_date=join_date)

            staff_list.append(user)

        self.stdout.write(f'    Staff for {owner.username}: {count}')
        return staff_list

    def _create_leads(self, owner, staff_list, categories, sources, count, start_date, today):
        from core.models import Lead, LeadActivity, ProfileLink

        all_creators = [owner] + staff_list
        leads_bulk = []
        now = timezone.now()

        for i in range(count):
            created_date = rand_date_between(start_date, today)
            created_dt = timezone.make_aware(
                datetime.combine(created_date, datetime.min.time().replace(
                    hour=random.randint(8, 20), minute=random.randint(0, 59)
                ))
            )

            status = random.choices(LEAD_STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
            creator = random.choice(all_creators)
            client = random.choice(CLIENT_NAMES)
            budget = Decimal(str(random.randint(500, 500000))) if random.random() > 0.3 else None

            follow_up = None
            if status in ('new', 'contacted', 'qualified', 'proposal', 'negotiation'):
                follow_up = created_date + timedelta(days=random.randint(1, 30))

            score = 0
            if status == 'new':
                score = random.randint(0, 30)
            elif status == 'contacted':
                score = random.randint(20, 50)
            elif status == 'qualified':
                score = random.randint(40, 70)
            elif status in ('proposal', 'negotiation'):
                score = random.randint(60, 90)
            elif status == 'won':
                score = random.randint(80, 100)
            elif status == 'lost':
                score = random.randint(10, 40)

            converted = status == 'won' and random.random() > 0.3
            conversion_date = created_dt + timedelta(days=random.randint(5, 60)) if converted else None

            decision_maker = random.random() > 0.6

            assigned_to = None
            if staff_list and random.random() > 0.4:
                assigned_to = random.choice(staff_list)

            deleted_at = None
            deleted_by = None
            if random.random() < 0.03:
                deleted_at = created_dt + timedelta(days=random.randint(1, 15))
                deleted_by = owner

            lead = Lead(
                owner=owner,
                created_by=creator,
                category=random.choice(categories) if random.random() > 0.05 else None,
                source=random.choice(sources) if random.random() > 0.05 else None,
                client_name=f'{client} #{random.randint(100, 9999)}',
                contact_number=rand_phone(),
                email=rand_email(client.split()[0], client.split()[-1]) if len(client.split()) > 1 else rand_email(client, 'client'),
                requirement=random.choice(REQUIREMENTS) if random.random() > 0.1 else '',
                status=status,
                follow_up_date=follow_up,
                notes=random.choice(NOTES) if random.random() > 0.3 else '',
                lead_score=score,
                budget=budget,
                decision_maker=decision_maker,
                converted_to_customer=converted,
                conversion_date=conversion_date,
                assigned_to=assigned_to,
                assignment_date=created_dt if assigned_to else None,
                deleted_at=deleted_at,
                deleted_by=deleted_by,
                custom_fields={},
            )
            leads_bulk.append((lead, created_dt))

        # Bulk create in batches
        batch_size = 500
        created_leads = []
        for batch_start in range(0, len(leads_bulk), batch_size):
            batch = leads_bulk[batch_start:batch_start + batch_size]
            objs = Lead.objects.bulk_create([l[0] for l in batch], batch_size=batch_size)
            created_leads.extend(zip(objs, [l[1] for l in batch]))

        # Update created_at timestamps (bulk_create ignores auto_now_add for update)
        for lead_obj, created_dt in created_leads:
            Lead.objects.filter(pk=lead_obj.pk).update(created_at=created_dt, updated_at=created_dt)

        # Create some lead activities
        activities = []
        activity_types = ['note', 'call', 'meeting', 'email', 'status_update']
        activity_descriptions = [
            'Initial contact made via phone',
            'Sent introductory email with product catalog',
            'Scheduled demo meeting for next week',
            'Follow-up call - client requesting pricing details',
            'Meeting went well, client interested in Professional plan',
            'Sent revised proposal with custom pricing',
            'Client requested additional features demo',
            'Negotiation in progress, budget discussion',
            'Contract sent for review and signing',
            'Deal closed successfully!',
            'Client postponed decision to next quarter',
            'Left voicemail, awaiting callback',
            'Email bounced, need updated contact info',
            'Referred to technical team for integration queries',
            'Competitor comparison shared with the client',
        ]

        sample_leads = random.sample(created_leads, min(len(created_leads), count // 3))
        for lead_obj, created_dt in sample_leads:
            num_activities = random.randint(1, 4)
            for _ in range(num_activities):
                act_date = created_dt + timedelta(days=random.randint(0, 20))
                activities.append(LeadActivity(
                    lead=lead_obj,
                    user=random.choice(all_creators),
                    activity_type=random.choice(activity_types),
                    description=random.choice(activity_descriptions),
                ))

        if activities:
            LeadActivity.objects.bulk_create(activities, batch_size=500)

        # Create some profile links
        platforms = ['linkedin', 'facebook', 'instagram', 'twitter', 'website']
        links = []
        sample_for_links = random.sample(created_leads, min(len(created_leads), count // 5))
        for lead_obj, _ in sample_for_links:
            platform = random.choice(platforms)
            links.append(ProfileLink(
                lead=lead_obj,
                platform=platform,
                url=f'https://{platform}.com/{lead_obj.client_name.replace(" ", "").lower()[:20]}',
            ))

        if links:
            ProfileLink.objects.bulk_create(links, batch_size=500)

        self.stdout.write(f'    Leads for {owner.username}: {count} ({len(activities)} activities, {len(links)} links)')

    def _create_payments(self, owner, subscription, start_date, today):
        from billing.models import Payment
        if not subscription or subscription.plan.monthly_price <= 0:
            return

        payments = []
        price = subscription.get_current_price()
        current = start_date

        while current <= today:
            is_paid = current < today - timedelta(days=2)
            payments.append(Payment(
                user=owner,
                subscription=subscription,
                amount=price,
                due_date=current,
                paid_date=current + timedelta(days=random.randint(0, 3)) if is_paid else None,
                payment_method=random.choice(['stripe', 'stripe', 'stripe', 'bank_transfer']),
                transaction_id=f'pi_{"".join(random.choices(string.ascii_lowercase + string.digits, k=24))}' if is_paid else None,
                is_paid=is_paid,
                notes='' if is_paid else 'Pending payment',
            ))
            if subscription.billing_cycle == 'yearly':
                current += timedelta(days=365)
            else:
                current += timedelta(days=30)

        if payments:
            Payment.objects.bulk_create(payments, batch_size=100)
        self.stdout.write(f'    Payments for {owner.username}: {len(payments)}')

    def _create_notifications(self, owner, staff_list, today):
        from core.models import Notification

        notif_templates = [
            ('lead_added', 'New Lead Added', 'A new lead "{name}" has been added.', '/leads/'),
            ('lead_updated', 'Lead Updated', 'Lead "{name}" status changed to {status}.', '/leads/'),
            ('lead_assigned', 'Lead Assigned', 'Lead "{name}" has been assigned to you.', '/leads/'),
            ('lead_converted', 'Lead Converted!', 'Lead "{name}" has been converted to a customer!', '/leads/'),
            ('staff_approved', 'Staff Approved', '{staff} has been approved and added to your team.', '/team/manage/'),
            ('plan_upgraded', 'Plan Upgraded', 'Your plan has been upgraded to {plan}.', '/billing/my-plan/'),
            ('payment_received', 'Payment Received', 'Your payment of ${amount} has been confirmed.', '/billing/my-plan/'),
            ('followup_due', 'Follow-up Due', 'You have a follow-up due for lead "{name}".', '/leads/'),
            ('followup_overdue', 'Follow-up Overdue!', 'Follow-up for "{name}" is overdue!', '/leads/'),
            ('system', 'System Update', 'LeadSync has been updated with new features. Check it out!', '/dashboard/'),
        ]

        notifications = []
        all_users = [owner] + staff_list

        for user in all_users:
            num_notifs = random.randint(5, 20)
            for _ in range(num_notifs):
                template = random.choice(notif_templates)
                days_ago = random.randint(0, 60)
                msg = template[2].format(
                    name=random.choice(CLIENT_NAMES),
                    status=random.choice(LEAD_STATUSES),
                    staff=random.choice(FIRST_NAMES),
                    plan=random.choice(['Basic', 'Professional', 'Business']),
                    amount=random.choice(['9.99', '29.99', '79.99', '199.99']),
                )
                notifications.append(Notification(
                    recipient=user,
                    sender=random.choice(all_users) if random.random() > 0.3 else None,
                    notification_type=template[0],
                    title=template[1],
                    message=msg,
                    url=template[3],
                    is_read=random.random() > 0.4,
                ))

        if notifications:
            created = Notification.objects.bulk_create(notifications, batch_size=500)
            # Backdate created_at
            for notif in created:
                days_ago = random.randint(0, 60)
                Notification.objects.filter(pk=notif.pk).update(
                    created_at=timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
                )
        self.stdout.write(f'    Notifications for {owner.username}: {len(notifications)}')

    def _create_activity_logs(self, owner, staff_list, start_date, today):
        from core.models import ActivityLog

        actions = ['create', 'update', 'delete', 'view', 'import', 'export', 'login']
        models = ['Lead', 'Lead', 'Lead', 'Lead', 'TeamMember', 'Role', 'Subscription']
        all_users = [owner] + staff_list
        logs = []

        for user in all_users:
            num_logs = random.randint(20, 80)
            for _ in range(num_logs):
                log_date = rand_date_between(start_date, today)
                action = random.choice(actions)
                model = random.choice(models)
                logs.append(ActivityLog(
                    user=user,
                    action=action,
                    target_model=model,
                    target_id=random.randint(1, 1000),
                    target_name=f'{model} #{random.randint(1, 500)}',
                    details=f'{action.capitalize()}d {model.lower()} record',
                    ip_address=f'192.168.{random.randint(1,10)}.{random.randint(1,254)}',
                ))

        if logs:
            created = ActivityLog.objects.bulk_create(logs, batch_size=500)
            for log in created:
                log_date = rand_date_between(start_date, today)
                log_dt = timezone.make_aware(datetime.combine(
                    log_date, datetime.min.time().replace(hour=random.randint(8, 22), minute=random.randint(0, 59))
                ))
                ActivityLog.objects.filter(pk=log.pk).update(timestamp=log_dt)

        self.stdout.write(f'    Activity logs for {owner.username}: {len(logs)}')
