# Custom migration: rename price to monthly_price, add yearly_discount, add billing_cycle

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_payment_stripe_charge_id_and_more'),
    ]

    operations = [
        # Rename price to monthly_price
        migrations.RenameField(
            model_name='plan',
            old_name='price',
            new_name='monthly_price',
        ),
        # Add yearly_discount to Plan
        migrations.AddField(
            model_name='plan',
            name='yearly_discount',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Yearly discount percentage (e.g., 20 for 20%)', max_digits=5),
        ),
        # Add billing_cycle to Subscription
        migrations.AddField(
            model_name='subscription',
            name='billing_cycle',
            field=models.CharField(choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')], default='monthly', max_length=10),
        ),
    ]
