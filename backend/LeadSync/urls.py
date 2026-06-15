"""
URL configuration for LeadSync project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from accounts import views as accounts_views
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Routes (v1)
    path('api/auth/', include('accounts.api_urls')),
    path('api/', include('core.api_urls')),
    
    # Legacy Django Template URLs (for backward compatibility)
    path('', core_views.home, name='home'),
    path('my-plans/', core_views.my_plans_page, name='my_plans_page'),
    path('privacy-policy/', core_views.privacy_policy, name='privacy_policy'),
    path('terms-and-conditions/', core_views.terms_and_conditions, name='terms_and_conditions'),
    path('support/', core_views.support, name='support'),
    path('signup/', accounts_views.signup, name='signup'),
    path('login/', accounts_views.custom_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', core_views.dashboard, name='dashboard'),

    # Password change URLs
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(template_name='accounts/password_change.html'), name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='accounts/password_change_done.html'), name='password_change_done'),

    # Accounts URLs
    path('accounts/', include('accounts.urls')),

    # Core URLs
    path('leads/', include('core.urls')),

    # Billing URLs
    path('billing/', include('billing.urls')),

    # Team URLs
    path('team/', include('team.urls')),
]

if settings.DEBUG:
    proof_backend = str(getattr(settings, 'PAYMENT_PROOF_STORAGE_BACKEND', 'filesystem')).lower()
    proof_url = getattr(settings, 'PAYMENT_PROOF_BASE_URL', '')
    proof_root = getattr(settings, 'PAYMENT_PROOF_ROOT', '')
    if proof_backend == 'filesystem' and proof_url and proof_root and str(proof_url).startswith('/'):
        urlpatterns += static(proof_url, document_root=str(proof_root))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
