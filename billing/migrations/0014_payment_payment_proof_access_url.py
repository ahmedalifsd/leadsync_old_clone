from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0013_subscription_queued_renewal_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='payment_proof_access_url',
            field=models.URLField(blank=True),
        ),
    ]
