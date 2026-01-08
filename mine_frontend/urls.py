from django.urls import path
from django.views.generic import TemplateView

from mine_frontend.autocompletes import VorschlagendeDal
from mine_frontend.views import (
    IndexView,
    InstitutionIndexView,
    InstitutionResultsView,
    OEAWInstitutionDetailView,
    OEAWMemberDetailView,
    OEAWPrizeDetailView,
    PersonResultsView,
)

urlpatterns = [
    path("mine/", IndexView.as_view(), name="index"),
    path("mine-institution/", InstitutionIndexView.as_view(), name="institution-index"),
    path(
        "about/",
        TemplateView.as_view(template_name="mine_frontend/about.html"),
        name="about",
    ),
    path("person/<int:pk>/", OEAWMemberDetailView.as_view(), name="person-detail"),
    path(
        "institution/<int:pk>/",
        OEAWInstitutionDetailView.as_view(),
        name="institution-detail",
    ),
    path(
        "preis/<int:pk>/",
        OEAWPrizeDetailView.as_view(),
        name="prize-detail",
    ),
    path("search/", PersonResultsView.as_view(), name="search"),
    path(
        "search_institution/",
        InstitutionResultsView.as_view(),
        name="institution-search",
    ),
    path("ac/vorgeschlagende", VorschlagendeDal.as_view(), name="dal-vorschlagende"),
]
