from django.urls import path

from mine_frontend.views import (
    IndexView,
    OEAWInstitutionDetailView,
    OEAWMemberDetailView,
    PersonResultsView,
)

urlpatterns = [
    path("mine/", IndexView.as_view(), name="index"),
    path("person/<int:pk>/", OEAWMemberDetailView.as_view(), name="person-detail"),
    path(
        "institution/<int:pk>/",
        OEAWInstitutionDetailView.as_view(),
        name="institution-detail",
    ),
    path("search/", PersonResultsView.as_view(), name="search"),
]
