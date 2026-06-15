from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .storage import get_payment_proof_storage


CURRENCY_CHOICES = (
    ('pkr', 'PKR - Pakistani Rupee (Rs.)'),
    ('usd', 'USD - US Dollar ($)'),
    ('eur', 'EUR - Euro (€)'),
    ('gbp', 'GBP - British Pound (£)'),
    ('inr', 'INR - Indian Rupee (₹)'),
    ('aed', 'AED - UAE Dirham (د.إ)'),
    ('sar', 'SAR - Saudi Riyal (﷼)'),
    ('cad', 'CAD - Canadian Dollar (C$)'),
    ('aud', 'AUD - Australian Dollar (A$)'),
    ('try', 'TRY - Turkish Lira (₺)'),
)

CURRENCY_SYMBOLS = {
    'pkr': 'Rs.',
    'usd': '$',
    'eur': '€',
    'gbp': '£',
    'inr': '₹',
    'aed': 'د.إ',
    'sar': '﷼',
    'cad': 'C$',
    'aud': 'A$',
    'try': '₺',
}


class SiteSettings(models.Model):
    """Singleton model for global site configuration."""
    currency_code = models.CharField(
        max_length=5, choices=CURRENCY_CHOICES, default='pkr',
        help_text="Currency used across the platform (plans, payments, Stripe)"
    )
    site_name = models.CharField(max_length=100, default='LeadSync')

    # Payment Details
    jazzcash_no = models.CharField(max_length=20, blank=True, verbose_name="JazzCash Number")
    easypaisa_no = models.CharField(max_length=20, blank=True, verbose_name="EasyPaisa Number")
    bank_name = models.CharField(max_length=100, blank=True, verbose_name="Bank Name")
    account_holder_name = models.CharField(max_length=150, blank=True, verbose_name="Account Holder Name")
    account_no = models.CharField(max_length=50, blank=True, verbose_name="Account Number")
    iban = models.CharField(max_length=50, blank=True, verbose_name="IBAN")

    def save(self, *args, **kwargs):
        if not self.pk and SiteSettings.objects.exists():
            existing = SiteSettings.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)

    @property
    def currency_symbol(self):
        return CURRENCY_SYMBOLS.get(self.currency_code, self.currency_code.upper())

    def __str__(self):
        return f"Site Settings - {self.currency_code.upper()} ({self.currency_symbol})"

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    @staticmethod
    def get_settings():
        """Get or create the singleton settings instance."""
        settings, _ = SiteSettings.objects.get_or_create(pk=1)
        return settings


def get_currency_symbol():
    """Helper function to get currency symbol from anywhere."""
    try:
        s = SiteSettings.objects.first()
        return s.currency_symbol if s else 'Rs.'
    except Exception:
        return 'Rs.'


def get_currency_code():
    """Helper function to get currency code for Stripe."""
    try:
        s = SiteSettings.objects.first()
        return s.currency_code if s else 'pkr'
    except Exception:
        return 'pkr'


def format_price(value):
    """Remove trailing zeros: 1000.00 → 1000, 1000.50 → 1000.5"""
    try:
        d = Decimal(str(value)).normalize()
        if d == d.to_integral_value():
            return str(int(d))
        return str(d)
    except Exception:
        return str(value)


class PricingConfig(models.Model):
    """Singleton model for custom plan pricing configuration."""
    price_per_employee = models.DecimalField(
        max_digits=10, decimal_places=2, default=2.00,
        help_text="Price per employee per month"
    )
    price_per_lead_block = models.DecimalField(
        max_digits=10, decimal_places=2, default=1.00,
        help_text="Price per lead block per month"
    )
    lead_block_size = models.IntegerField(
        default=1000,
        help_text="Number of leads per block (e.g., 1000 means every 1000 leads costs price_per_lead_block)"
    )
    min_employees = models.IntegerField(default=1, help_text="Minimum employees selectable")
    max_employees = models.IntegerField(default=500, help_text="Maximum employees selectable")
    min_leads = models.IntegerField(default=1000, help_text="Minimum leads selectable")
    max_leads = models.IntegerField(default=1000000, help_text="Maximum leads selectable (e.g., 1000000 = 10 lakh)")
    lead_step = models.IntegerField(default=1000, help_text="Leads selection step (e.g., 1000, 2000, 3000...)")
    employee_step = models.IntegerField(default=1, help_text="Employee selection step")
    base_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Base monthly price before adding per-employee/per-lead costs"
    )
    yearly_discount = models.DecimalField(
        max_digits=5, decimal_places=2, default=20.00,
        help_text="Yearly discount percentage for custom plans"
    )
    # Unlimited pricing
    unlimited_employees_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=50.00,
        help_text="Fixed monthly price for unlimited employees"
    )
    unlimited_leads_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=30.00,
        help_text="Fixed monthly price for unlimited leads"
    )
    is_active = models.BooleanField(default=True, help_text="Enable custom plan builder for business owners")

    def save(self, *args, **kwargs):
        # Ensure only one PricingConfig exists (singleton)
        if not self.pk and PricingConfig.objects.exists():
            existing = PricingConfig.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)

    def calculate_monthly_price(self, employees, leads):
        """Calculate monthly price based on selected employees and leads.
        employees=-1 means unlimited, leads=-1 means unlimited.
        """
        # Employee cost
        if employees == -1:
            emp_cost = self.unlimited_employees_price
        else:
            emp_cost = self.price_per_employee * employees

        # Lead cost
        if leads == -1:
            lead_cost = self.unlimited_leads_price
        else:
            lead_blocks = leads / self.lead_block_size if self.lead_block_size > 0 else 0
            lead_cost = self.price_per_lead_block * Decimal(str(lead_blocks))

        total = self.base_price + emp_cost + lead_cost
        return total.quantize(Decimal('0.01'))

    def calculate_yearly_price(self, employees, leads):
        """Calculate yearly price with discount."""
        monthly = self.calculate_monthly_price(employees, leads)
        yearly_total = monthly * 12
        discount = yearly_total * (self.yearly_discount / Decimal('100'))
        return (yearly_total - discount).quantize(Decimal('0.01'))

    def __str__(self):
        return f"Pricing Config: {get_currency_symbol()}{format_price(self.price_per_employee)}/emp, {get_currency_symbol()}{format_price(self.price_per_lead_block)}/{self.lead_block_size} leads"

    class Meta:
        verbose_name = "Pricing Configuration"
        verbose_name_plural = "Pricing Configuration"


class Plan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monthly price in the configured currency")
    yearly_discount = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Yearly discount percentage (e.g., 20 for 20%)")
    max_employees = models.IntegerField(default=1)
    monthly_max_leads = models.IntegerField(blank=True, null=True, help_text="Max leads for monthly plan (null = unlimited)")
    yearly_max_leads = models.IntegerField(blank=True, null=True, help_text="Max leads for yearly plan (null = unlimited)")
    features = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_default_signup_plan = models.BooleanField(default=False, help_text="Auto-assign this plan to new business owners on signup (only 1 allowed)")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Ensure only ONE plan can be the default signup plan
        if self.is_default_signup_plan:
            Plan.objects.filter(is_default_signup_plan=True).exclude(pk=self.pk).update(is_default_signup_plan=False)
        super().save(*args, **kwargs)

    @property
    def yearly_price(self):
        """Calculate yearly price after discount"""
        total = self.monthly_price * 12
        discount_amount = total * (self.yearly_discount / Decimal('100'))
        return (total - discount_amount).quantize(Decimal('0.01'))

    @property
    def yearly_price_per_month(self):
        """Calculate effective monthly price when billed yearly"""
        if self.yearly_price:
            return (self.yearly_price / 12).quantize(Decimal('0.01'))
        return self.monthly_price

    @property
    def yearly_savings(self):
        """Calculate how much you save per year"""
        return (self.monthly_price * 12 - self.yearly_price).quantize(Decimal('0.01'))

    def __str__(self):
        return f"{self.name} - {get_currency_symbol()}{format_price(self.monthly_price)}/month"

    class Meta:
        ordering = ['monthly_price']


class PlanDiscount(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )

    name = models.CharField(max_length=120)
    applies_to_all_plans = models.BooleanField(default=False)
    plans = models.ManyToManyField(Plan, blank=True, related_name='discount_campaigns')
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percent')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.discount_type == 'percent':
            return f"{self.name} ({format_price(self.discount_value)}%)"
        return f"{self.name} ({get_currency_symbol()}{format_price(self.discount_value)})"

    def is_live(self, check_date=None):
        check_date = check_date or timezone.now().date()
        return self.is_active and self.start_date <= check_date <= self.end_date

    def get_discount_amount(self, amount):
        if amount <= 0:
            return Decimal('0.00')

        if self.discount_type == 'percent':
            discount = amount * (self.discount_value / Decimal('100'))
        else:
            discount = self.discount_value
        return max(Decimal('0.00'), min(discount, amount)).quantize(Decimal('0.01'))


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )

    code = models.CharField(max_length=40, unique=True)
    description = models.CharField(max_length=255, blank=True)
    applies_to_all_plans = models.BooleanField(default=True)
    plans = models.ManyToManyField(Plan, blank=True, related_name='coupons')
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percent')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_uses = models.PositiveIntegerField(default=1, help_text='Total allowed uses for this coupon code')
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = (self.code or '').strip().upper()
        super().save(*args, **kwargs)

    @property
    def used_count(self):
        return self.redemptions.count()

    def is_live(self, check_date=None):
        check_date = check_date or timezone.now().date()
        return self.is_active and self.start_date <= check_date <= self.end_date

    def is_plan_eligible(self, plan):
        if self.applies_to_all_plans:
            return True
        return self.plans.filter(id=plan.id).exists()

    def can_use(self, user, plan, check_date=None):
        if not self.is_live(check_date=check_date):
            return False, 'Coupon is inactive or expired.'
        if self.used_count >= self.max_uses:
            return False, 'Coupon usage limit reached.'
        if CouponRedemption.objects.filter(coupon=self, user=user).exists():
            return False, 'You have already used this coupon.'
        if not self.is_plan_eligible(plan):
            return False, 'Coupon is not valid for this plan.'
        return True, ''

    def get_discount_amount(self, amount):
        if amount <= 0:
            return Decimal('0.00')

        if self.discount_type == 'percent':
            discount = amount * (self.discount_value / Decimal('100'))
        else:
            discount = self.discount_value
        return max(Decimal('0.00'), min(discount, amount)).quantize(Decimal('0.01'))


class CouponRedemption(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, related_name='redemptions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coupon_redemptions')
    payment = models.OneToOneField('Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='coupon_redemption')
    subscription = models.ForeignKey('Subscription', on_delete=models.SET_NULL, null=True, blank=True, related_name='coupon_redemptions')
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-redeemed_at']
        unique_together = ('coupon', 'user')

    def __str__(self):
        return f"{self.coupon.code} by {self.user.username}"


class Subscription(models.Model):
    BILLING_CYCLE_CHOICES = (
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    )

    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE_CHOICES, default='monthly')
    is_custom_plan = models.BooleanField(default=False, help_text="True if this is a custom-configured plan")
    custom_max_employees = models.IntegerField(blank=True, null=True, help_text="Custom employee limit (for custom plans)")
    custom_max_leads = models.IntegerField(blank=True, null=True, help_text="Custom lead limit (for custom plans)")
    custom_monthly_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Custom monthly price")
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(blank=True, null=True)
    queued_renewal_start_date = models.DateField(blank=True, null=True)
    queued_renewal_end_date = models.DateField(blank=True, null=True)
    queued_renewal_payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='queued_subscriptions')
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.is_custom_plan:
            return f"{self.owner.username} - Custom Plan ({self.billing_cycle})"
        return f"{self.owner.username} - {self.plan.name} ({self.billing_cycle})"

    @property
    def effective_max_employees(self):
        """Get the effective max employees (custom or plan-based).
        Returns None for unlimited.
        """
        if self.is_custom_plan and self.custom_max_employees is not None:
            if self.custom_max_employees == -1:
                return None  # Unlimited
            return self.custom_max_employees
        return self.plan.max_employees

    @property
    def effective_max_leads(self):
        """Get the effective max leads (custom or plan-based).
        Returns None for unlimited.
        """
        if self.is_custom_plan and self.custom_max_leads is not None:
            if self.custom_max_leads == -1:
                return None  # Unlimited
            return self.custom_max_leads
        if self.billing_cycle == 'yearly':
            return self.plan.yearly_max_leads
        return self.plan.monthly_max_leads

    def get_current_price(self):
        """Get the current price based on billing cycle"""
        if self.is_custom_plan and self.custom_monthly_price is not None:
            if self.billing_cycle == 'yearly':
                config = PricingConfig.objects.first()
                discount = config.yearly_discount if config else Decimal('20')
                yearly_total = self.custom_monthly_price * 12
                discount_amount = yearly_total * (discount / Decimal('100'))
                return (yearly_total - discount_amount).quantize(Decimal('0.01'))
            return self.custom_monthly_price
        if self.billing_cycle == 'yearly':
            return self.plan.yearly_price
        return self.plan.monthly_price

    def get_remaining_days(self):
        from datetime import date
        if self.end_date:
            remaining = (self.end_date - date.today()).days
            return max(0, remaining)
        return None

    def check_and_expire(self):
        """Check if subscription has expired and deactivate it. Returns True if expired."""
        from datetime import date
        if self.is_active and self.end_date and self.end_date < date.today():
            if not self.auto_renew:
                self.is_active = False
                self.save(update_fields=['is_active'])
                return True
        return False

    def apply_queued_renewal_if_due(self, today=None):
        today = today or timezone.now().date()

        if not self.queued_renewal_start_date or not self.queued_renewal_end_date:
            return False

        if self.queued_renewal_start_date > today:
            return False

        self.start_date = self.queued_renewal_start_date
        self.end_date = self.queued_renewal_end_date
        self.is_active = True
        self.queued_renewal_start_date = None
        self.queued_renewal_end_date = None
        self.queued_renewal_payment = None
        self.save(update_fields=[
            'start_date', 'end_date', 'is_active',
            'queued_renewal_start_date', 'queued_renewal_end_date', 'queued_renewal_payment'
        ])
        return True


def enforce_plan_limits(owner):
    """Auto-deactivate excess employees when plan limit is lower than active count.
    Called after plan expiry, downgrade, or any subscription change."""
    from team.models import TeamMember

    subscription = Subscription.objects.filter(owner=owner, is_active=True).first()

    if not subscription:
        # No active plan: deactivate ALL employees
        excess = TeamMember.objects.filter(boss=owner, is_active=True).order_by('-joined_date')
        if excess.exists():
            excess.update(is_active=False)
        return

    max_emp = subscription.effective_max_employees
    if max_emp is None:
        return  # Unlimited — nothing to enforce

    active_members = TeamMember.objects.filter(boss=owner, is_active=True).order_by('joined_date')
    active_count = active_members.count()

    if active_count > max_emp:
        # Keep the oldest N (by joined_date), deactivate the rest
        ids_to_keep = list(active_members[:max_emp].values_list('id', flat=True))
        TeamMember.objects.filter(
            boss=owner, is_active=True
        ).exclude(id__in=ids_to_keep).update(is_active=False)


def get_lead_count_for_owner(owner):
    """Get the current lead count for this billing period."""
    from core.models import Lead
    subscription = Subscription.objects.filter(owner=owner, is_active=True).first()
    if not subscription:
        return 0
    start = subscription.start_date
    return Lead.objects.filter(owner=owner, created_at__date__gte=start, deleted_at__isnull=True).count()


def can_create_leads(owner, count=1):
    """Check if the owner can create `count` more leads within their plan limit.
    Returns (allowed: bool, message: str)."""
    subscription = Subscription.objects.filter(owner=owner, is_active=True).first()

    if not subscription:
        return False, 'You don\'t have an active plan. Please subscribe to a plan first.'

    max_leads = subscription.effective_max_leads
    if max_leads is None:
        return True, ''  # Unlimited

    current = get_lead_count_for_owner(owner)
    remaining = max_leads - current

    if remaining <= 0:
        return False, f'Lead limit reached ({max_leads} leads). Upgrade your plan to add more leads.'

    if count > remaining:
        return False, f'You can only add {remaining} more lead(s) this period. Your limit is {max_leads}.'

    return True, ''


class Payment(models.Model):
    DISCOUNT_SOURCE_CHOICES = (
        ('none', 'No Discount'),
        ('campaign', 'Campaign Discount'),
        ('coupon', 'Coupon Discount'),
        ('campaign_coupon', 'Campaign + Coupon'),
    )

    PAYMENT_METHODS = (
        ('bank_transfer', 'Bank Transfer'),
        ('jazzcash', 'JazzCash'),
        ('stripe', 'Stripe'),
        ('manual', 'Manual'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_source = models.CharField(max_length=20, choices=DISCOUNT_SOURCE_CHOICES, default='none')
    discount_label = models.CharField(max_length=200, blank=True)
    pending_coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='pending_payments')
    applied_coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    applied_campaign = models.ForeignKey(PlanDiscount, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    due_date = models.DateField()
    paid_date = models.DateField(blank=True, null=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='manual')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payer_name = models.CharField(max_length=150, blank=True)
    payer_phone = models.CharField(max_length=50, blank=True)
    payer_email = models.EmailField(blank=True)
    contact_note = models.TextField(blank=True)
    payment_proof = models.ImageField(storage=get_payment_proof_storage, upload_to='', blank=True, null=True)
    payment_proof_access_url = models.URLField(blank=True, max_length=500)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_payments')
    is_renewal = models.BooleanField(default=False)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)  # Store Stripe payment intent ID
    stripe_charge_id = models.CharField(max_length=255, blank=True, null=True)  # Store Stripe charge ID
    is_paid = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    rejected_at = models.DateTimeField(blank=True, null=True)
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_payments')
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {get_currency_symbol()}{format_price(self.amount)} - {self.user.username}"

    def save(self, *args, **kwargs):
        proof_url = ''
        if self.payment_proof:
            try:
                proof_url = self.payment_proof.url
            except Exception:
                proof_url = ''
        self.payment_proof_access_url = proof_url

        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_set = set(update_fields)
            if 'payment_proof' in update_set or 'payment_proof_access_url' in update_set:
                update_set.add('payment_proof_access_url')
                kwargs['update_fields'] = list(update_set)

        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-due_date']