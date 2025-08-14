from django.urls import path

from mine_frontend.views import OEAWMemberDetailView

urlpatterns = [
    path("person/<int:pk>/", OEAWMemberDetailView.as_view(), name="person-detail"),
]
