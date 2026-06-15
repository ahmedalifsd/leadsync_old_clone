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

# API-only backend - All UI is handled by the separate React frontend
urlpatterns = [
    # Admin interface (development only)
    path('admin/', admin.site.urls),
    
    # REST API Routes (v1)
    path('api/auth/', include('accounts.api_urls')),
    path('api/', include('core.api_urls')),
    path('api/', include('billing.api_urls')),
]

# Media files (for user uploads, etc.)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
