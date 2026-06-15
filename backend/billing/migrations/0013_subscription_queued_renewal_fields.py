from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0012_payment_is_rejected_payment_rejected_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='queued_renewal_end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='queued_renewal_payment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='queued_subscriptions', to='billing.payment'),
        ),
        migrations.AddField(
            model_name='subscription',
            name='queued_renewal_start_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
