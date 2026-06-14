from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0003_teammember_is_removed_teammember_removed_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='teammember',
            name='previous_active_state',
            field=models.BooleanField(default=False),
        ),
    ]
