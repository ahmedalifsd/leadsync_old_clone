# Migration: rename max_leads to monthly_max_leads, add yearly_max_leads

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_plan_monthly_yearly_subscription_billing_cycle'),
    ]

    operations = [
        # Rename max_leads to monthly_max_leads
        migrations.RenameField(
            model_name='plan',
            old_name='max_leads',
            new_name='monthly_max_leads',
        ),
        # Add yearly_max_leads to Plan
        migrations.AddField(
            model_name='plan',
            name='yearly_max_leads',
            field=models.IntegerField(blank=True, null=True, help_text='Max leads for yearly plan (null = unlimited)'),
        ),
    ]
