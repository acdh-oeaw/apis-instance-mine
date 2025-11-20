from apis_core.generic.views import Update
from apis_core.relations.views import CreateRelationForm
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse

from apis_ontology.models import AusbildungAn, PositionAn
from mine_edit.forms import CareerForm, EducationForm
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


class EducationEditView(EditView):
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


class CareerEditView(EditView):
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
