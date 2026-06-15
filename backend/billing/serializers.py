from rest_framework import serializers
from .models import Plan


class PlanSerializer(serializers.ModelSerializer):
    yearly_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        help_text="Calculated yearly price after discount"
    )
    yearly_price_per_month = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        help_text="Effective monthly price when billed yearly"
    )
    yearly_savings = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        help_text="Amount saved per year with yearly billing"
    )

    class Meta:
        model = Plan
        fields = [
            'id',
            'name',
            'monthly_price',
            'yearly_price',
            'yearly_price_per_month',
            'yearly_savings',
            'yearly_discount',
            'max_employees',
            'monthly_max_leads',
            'yearly_max_leads',
            'features',
            'is_active',
            'is_default_signup_plan',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'yearly_price',
            'yearly_price_per_month',
            'yearly_savings',
            'created_at',
        ]
