from django.urls import path
from . import views

urlpatterns = [
    path('my-plan/', views.my_plan, name='my_plan'),
    path('request-manual-payment/', views.request_manual_payment, name='request_manual_payment'),
    path('toggle-auto-renew/', views.toggle_auto_renew, name='toggle_auto_renew'),
    path('add-staff/', views.add_staff_member, name='add_staff_member'),
    path('upgrade/<int:plan_id>/', views.upgrade_plan, name='upgrade_plan'),
    path('create-stripe-session/<int:plan_id>/', views.create_stripe_checkout_session, name='create_stripe_session'),
    path('custom-pricing/', views.get_custom_pricing, name='get_custom_pricing'),
    path('create-custom-stripe-session/', views.create_custom_stripe_session, name='create_custom_stripe_session'),
    path('validate-coupon/', views.validate_coupon, name='validate_coupon'),
    path('coupon-plan-previews/', views.coupon_plan_previews, name='coupon_plan_previews'),
    path('stripe-success/', views.stripe_success, name='stripe_success'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('manage-plans/', views.manage_plans, name='manage_plans'),
    path('site-settings/', views.site_settings, name='site_settings'),
    path('set-default-plan/<int:plan_id>/', views.set_default_plan, name='set_default_plan'),
    path('toggle-plan/<int:plan_id>/', views.toggle_plan, name='toggle_plan'),
    path('delete-plan/<int:plan_id>/', views.delete_plan, name='delete_plan'),
    path('toggle-campaign/<int:campaign_id>/', views.toggle_campaign, name='toggle_campaign'),
    path('delete-campaign/<int:campaign_id>/', views.delete_campaign, name='delete_campaign'),
    path('toggle-coupon/<int:coupon_id>/', views.toggle_coupon, name='toggle_coupon'),
    path('delete-coupon/<int:coupon_id>/', views.delete_coupon, name='delete_coupon'),
    path('update-payment/<int:payment_id>/', views.update_payment_status, name='update_payment_status'),
]