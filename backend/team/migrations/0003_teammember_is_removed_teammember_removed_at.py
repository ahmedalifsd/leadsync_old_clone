from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0002_role_teammember_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='teammember',
            name='is_removed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='teammember',
            name='removed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
