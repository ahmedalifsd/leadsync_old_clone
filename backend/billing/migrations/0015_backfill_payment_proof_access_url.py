from django.conf import settings
from django.db import migrations


def backfill_payment_proof_access_url(apps, schema_editor):
    Payment = apps.get_model('billing', 'Payment')

    base_url = str(getattr(settings, 'PAYMENT_PROOF_BASE_URL', '/payment-proofs/'))
    if not base_url.startswith('/'):
        base_url = f'/{base_url}'
    if not base_url.endswith('/'):
        base_url = f'{base_url}/'

    rows = Payment.objects.exclude(payment_proof='').iterator()
    for payment in rows:
        proof_name = str(payment.payment_proof or '').strip()
        if not proof_name:
            continue
        payment.payment_proof_access_url = f'{base_url}{proof_name}'
        payment.save(update_fields=['payment_proof_access_url'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0014_payment_payment_proof_access_url'),
    ]

    operations = [
        migrations.RunPython(backfill_payment_proof_access_url, noop_reverse),
    ]
