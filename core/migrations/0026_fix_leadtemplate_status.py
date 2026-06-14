from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_alter_lead_status_alter_leadtemplate_status'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE core_leadtemplate ADD COLUMN IF NOT EXISTS status varchar(20) NOT NULL DEFAULT 'new';",
            reverse_sql="ALTER TABLE core_leadtemplate DROP COLUMN IF EXISTS status;",
        ),
        # Ensure Django knows about the field
        migrations.AlterField(
            model_name='leadtemplate',
            name='status',
            field=models.CharField(choices=[('new', 'New'), ('not_contacted', 'Not Contacted'), ('contacted', 'Contacted'), ('no_response', 'No Response'), ('interested', 'Interested'), ('not_interested', 'Not Interested'), ('qualified', 'Qualified'), ('proposal', 'Proposal Sent'), ('negotiation', 'Negotiation'), ('won', 'Won'), ('lost', 'Lost')], default='new', max_length=20),
        ),
    ]
