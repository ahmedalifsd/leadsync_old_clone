# Generated manually to restore status column

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_chatgroupmessagereceipt_chatpresence'),
    ]

    operations = [
        # Drop the status_old column if it exists
        migrations.RunSQL(
            sql="ALTER TABLE core_lead DROP COLUMN IF EXISTS status_old;",
            reverse_sql="SELECT 1;",
        ),
        # Drop the status_v2_id column if it exists
        migrations.RunSQL(
            sql="ALTER TABLE core_lead DROP COLUMN IF EXISTS status_v2_id;",
            reverse_sql="SELECT 1;",
        ),
        # Keep this migration safe on databases where status already exists.
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE core_lead ADD COLUMN IF NOT EXISTS status varchar(20) NOT NULL DEFAULT 'new';",
                    reverse_sql="ALTER TABLE core_lead DROP COLUMN IF EXISTS status;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='lead',
                    name='status',
                    field=models.CharField(
                        choices=[
                            ('new', 'New'),
                            ('contacted', 'Contacted'),
                            ('qualified', 'Qualified'),
                            ('proposal', 'Proposal Sent'),
                            ('negotiation', 'Negotiation'),
                            ('won', 'Won'),
                            ('lost', 'Lost'),
                        ],
                        default='new',
                        max_length=20,
                    ),
                ),
            ],
        ),
    ]
