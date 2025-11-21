from apis_core.generic.views import Update
from apis_core.relations.views import CreateRelationForm
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse

from apis_ontology.models import (
    AusbildungAn,
    Bild,
    GeborenIn,
    GestorbenIn,
    Person,
    PositionAn,
)
from mine_edit.forms import CareerForm, EducationForm, PersonEditForm
from mine_edit.utils import user_edit_permissions


class EditView(Update):
    template_name = "mine_edit/create_relations_form.html"

    def get(self, *args, **kwargs):
        resp = super().get(*args, **kwargs)
        content_type = ContentType.objects.get_for_model(self.model)
        resp["HX-Trigger-After-Settle"] = (
            '{"reinit_select2": "relation_' + content_type.model + '_form"}'
        )
        return resp

    def get_form_class(self):
        return self.form_class

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["params"] = {"hx_post_route": self.request.path}
        return kwargs

    def get_success_url(self) -> str:
        return reverse(
            "mine_frontend:person-detail", kwargs={"pk": self.object.subj_object_id}
        )


class EditDeleteView(EditView):
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not user_edit_permissions(request.user, self.object.subj):
            return HttpResponseForbidden()
        self.object.delete()

        if self.request.headers.get("HX-Request"):
            response = HttpResponse(status=200)
            return response

        return redirect(
            reverse(
                "mine_frontend:person-detail", kwargs={"pk": self.object.subj_object_id}
            )
        )


class CreateView(CreateRelationForm):
    template_name = "mine_edit/create_relations_form.html"

    def get_form_class(self):
        return self.form_class

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["params"] = {"hx_post_route": self.request.path}
        return kwargs

    def get_success_url(self) -> str:
        return reverse(
            "mine_frontend:person-detail", kwargs={"pk": self.object.subj_object_id}
        )


class EducationEditView(EditDeleteView):
    model = AusbildungAn
    form_class = EducationForm

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            html_temp = render(
                self.request,
                "mine_frontend/partials/education_li.html",
                {
                    "edu": self.object,
                    "has_edit_permissions": user_edit_permissions(
                        self.request.user, self.object.subj
                    ),
                },
            )
            html_temp["HX-Trigger"] = "closeRelationDialog"
            return html_temp
        return response


class EducationCreateView(CreateView):
    model = AusbildungAn
    form_class = EducationForm

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            html_temp = render(
                self.request,
                "mine_frontend/partials/education_li.html",
                {"edu": self.object, "has_edit_permissions": True},
            )
            html_temp["HX-Trigger"] = "closeRelationDialog"
            return html_temp
        return response


class CareerEditView(EditDeleteView):
    model = PositionAn
    form_class = CareerForm

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            html_temp = render(
                self.request,
                "mine_frontend/partials/career_li.html",
                {
                    "position": self.object,
                    "has_edit_permissions": user_edit_permissions(
                        self.request.user, self.object.subj
                    ),
                },
            )
            html_temp["HX-Trigger"] = "closeRelationDialog"
            return html_temp
        return response


class CareerCreateView(CreateView):
    model = PositionAn
    form_class = CareerForm

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            html_temp = render(
                self.request,
                "mine_frontend/partials/career_li.html",
                {"position": self.object, "has_edit_permissions": True},
            )
            html_temp["HX-Trigger"] = "closeRelationDialog"
            return html_temp
        return response


class PersonEditView(EditView):
    model = Person
    form_class = PersonEditForm

    def get_initial(self):
        initial = super().get_initial()
        if self.object and self.object.id:
            birth_relation = GeborenIn.objects.filter(
                subj_object_id=self.object.id
            ).first()
            if birth_relation:
                initial["place_of_birth"] = birth_relation.obj
            death_relation = GestorbenIn.objects.filter(
                subj_object_id=self.object.id
            ).first()
            if death_relation:
                initial["place_of_death"] = death_relation.obj
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request"):
            place_of_birth = GeborenIn.objects.filter(subj_object_id=self.object.id)
            place_of_death = GestorbenIn.objects.filter(subj_object_id=self.object.id)
            html_temp = render(
                self.request,
                "mine_frontend/partials/memb_left_panel_editable.html",
                {
                    "oeaw_member": self.object,
                    "place_of_birth": place_of_birth,
                    "place_of_death": place_of_death,
                    "image": (
                        Bild.objects.filter(object_id=self.object.id)
                        .order_by("art")
                        .first()
                    ),
                    "has_edit_permissions": user_edit_permissions(
                        self.request.user, self.object
                    ),
                },
            )
            html_temp["HX-Trigger"] = "closeRelationDialog"
            return html_temp
        return response

    def get_success_url(self) -> str:
        return reverse("mine_frontend:person-detail", kwargs={"pk": self.object.id})
