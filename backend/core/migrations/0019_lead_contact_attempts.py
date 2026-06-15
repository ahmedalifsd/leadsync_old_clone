from django.db import migrations, models


def seed_contact_attempts(apps, schema_editor):
    Lead = apps.get_model('core', 'Lead')
    Lead.objects.filter(status='contacted', contact_attempts=0).update(contact_attempts=1)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_chatgroup_chatgroupmember_chatgroupmessage_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='contact_attempts',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(seed_contact_attempts, migrations.RunPython.noop),
    ]
