"""
URL configuration for mine project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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

from apis_acdhch_default_settings.urls import urlpatterns
from django.urls import include, path

urlpatterns += [path("", include("mine_frontend.urls"))]
urlpatterns += [path("", include("apis_acdhch_django_invite.urls"))]
urlpatterns += [path("", include("django_interval.urls"))]
urlpatterns += [
    path("", include("apis_acdhch_django_auditlog.urls")),
]
