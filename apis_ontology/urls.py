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

from apis_acdhch_default_settings.views import Imprint
from django.apps import apps
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views.generic import TemplateView

from apis_core.apis_entities.api_views import GetEntityGeneric

urlpatterns = [
    path("apis/", include("apis_core.urls", namespace="apis")),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("entity/<int:pk>/", GetEntityGeneric.as_view(), name="GetEntityGenericRoot"),
    path("admin/", admin.site.urls),
]
urlpatterns += staticfiles_urlpatterns()

if apps.is_installed("apis_bibsonomy"):
    urlpatterns.append(
        path("bibsonomy/", include("apis_bibsonomy.urls", namespace="bibsonomy"))
    )

urlpatterns.append(path("edit/", TemplateView.as_view(template_name="base.html")))
urlpatterns.append(path("imprint", Imprint.as_view(), name="imprint"))
urlpatterns += [
    path("", include("apis_acdhch_django_auditlog.urls")),
]


urlpatterns += [path("", include("mine_frontend.urls"))]
urlpatterns += [path("", include("apis_acdhch_django_invite.urls"))]
urlpatterns += [path("", include("django_interval.urls"))]
