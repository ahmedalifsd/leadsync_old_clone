from django.contrib import admin
from .models import Plan, Subscription, Payment, PlanDiscount, Coupon, CouponRedemption, SiteSettings

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'currency_code', 'jazzcash_no', 'easypaisa_no', 'bank_name')
    fieldsets = (
        ('General Settings', {
            'fields': ('site_name', 'currency_code')
        }),
        ('Payment Details', {
            'fields': ('jazzcash_no', 'easypaisa_no', 'bank_name', 'account_holder_name', 'account_no', 'iban'),
            'description': 'These details will be shown to users when they request a manual payment.'
        }),
    )

    def has_add_permission(self, request):
        # Only allow one instance
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'monthly_price', 'yearly_discount', 'max_employees', 'monthly_max_leads', 'yearly_max_leads', 'is_active', 'is_default_signup_plan', 'created_at')
    list_filter = ('is_active', 'is_default_signup_plan', 'created_at')
    search_fields = ('name', 'features')
    readonly_fields = ('created_at',)
    ordering = ('monthly_price',)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('owner', 'plan', 'billing_cycle', 'start_date', 'end_date', 'is_active', 'auto_renew')
    list_filter = ('plan', 'billing_cycle', 'is_active', 'auto_renew', 'start_date', 'created_at')
    search_fields = ('owner__username', 'owner__email', 'plan__name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    date_hierarchy = 'start_date'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription', 'amount', 'original_amount', 'discount_amount', 'discount_source', 'due_date', 'paid_date', 'payment_method', 'is_paid', 'is_renewal', 'payment_proof_access_url')
    list_filter = ('payment_method', 'is_paid', 'due_date', 'paid_date', 'created_at')
    search_fields = ('user__username', 'user__email', 'transaction_id', 'payer_name', 'payer_phone', 'notes')
    readonly_fields = ('created_at', 'payment_proof_access_url')
    ordering = ('-due_date',)
    date_hierarchy = 'due_date'


@admin.register(PlanDiscount)
class PlanDiscountAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_type', 'discount_value', 'applies_to_all_plans', 'start_date', 'end_date', 'is_active')
    list_filter = ('discount_type', 'applies_to_all_plans', 'is_active', 'start_date', 'end_date')
    search_fields = ('name',)
    filter_horizontal = ('plans',)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'max_uses', 'applies_to_all_plans', 'start_date', 'end_date', 'is_active')
    list_filter = ('discount_type', 'applies_to_all_plans', 'is_active', 'start_date', 'end_date')
    search_fields = ('code', 'description')
    filter_horizontal = ('plans',)


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ('coupon', 'user', 'original_amount', 'discount_amount', 'final_amount', 'redeemed_at')
    list_filter = ('coupon', 'redeemed_at')
    search_fields = ('coupon__code', 'user__username', 'user__email')
