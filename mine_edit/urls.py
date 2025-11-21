from django.urls import path

from mine_edit.views import (
    CareerCreateView,
    CareerEditView,
    EducationCreateView,
    EducationEditView,
    PersonEditView,
)

app_name = "mine_edit"
urlpatterns = [
    path(
        "education/<int:pk>/edit/", EducationEditView.as_view(), name="education_edit"
    ),
    path(
        "education/<int:pk_subj>/create/",
        EducationCreateView.as_view(),
        name="education_create",
    ),
    path("career/<int:pk>/edit/", CareerEditView.as_view(), name="career_edit"),
    path(
        "career/<int:pk_subj>/create/",
        CareerCreateView.as_view(),
        name="career_create",
    ),
    path(
        "member/<int:pk>/edit/",
        PersonEditView.as_view(),
        name="member_edit",
    ),
]
