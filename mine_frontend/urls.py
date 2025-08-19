from django.urls import path

from mine_frontend.views import OEAWInstitutionDetailView, OEAWMemberDetailView

urlpatterns = [
    path("person/<int:pk>/", OEAWMemberDetailView.as_view(), name="person-detail"),
    path(
        "institution/<int:pk>/",
        OEAWInstitutionDetailView.as_view(),
        name="institution-detail",
    ),
]
