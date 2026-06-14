from datetime import date
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class PlanExpiryMiddleware(MiddlewareMixin):
    """Checks once per session if the owner's plan has expired and enforces limits."""

    def process_request(self, request):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None

        try:
            profile = request.user.profile
        except Exception:
            return None

        if profile.role != 'owner':
            return None

        # Only run the check once every 5 minutes per session to avoid DB hits on every request
        last_check = request.session.get('_plan_check_ts')
        import time
        now = int(time.time())
        if last_check and (now - last_check) < 300:
            return None
        request.session['_plan_check_ts'] = now

        from billing.models import Subscription, enforce_plan_limits

        subscription = Subscription.objects.filter(owner=request.user, is_active=True).first()
        if not subscription:
            enforce_plan_limits(request.user)
            return None

        if subscription.apply_queued_renewal_if_due(today=date.today()):
            subscription.refresh_from_db()

        if subscription.end_date and subscription.end_date < date.today():
            grace_days = max(int(getattr(settings, 'RENEWAL_GRACE_DAYS', 3)), 0)
            days_past_expiry = (date.today() - subscription.end_date).days

            # Auto-renew plans stay active only inside grace period; payment is still manual.
            should_deactivate = (not subscription.auto_renew) or (days_past_expiry > grace_days)
            if should_deactivate:
                subscription.is_active = False
                subscription.save(update_fields=['is_active'])

            # Whether expired or downgraded, enforce employee limits
            enforce_plan_limits(request.user)

        return None
