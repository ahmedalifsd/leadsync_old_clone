from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_lead_contact_attempts'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='status_repeat_count',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
