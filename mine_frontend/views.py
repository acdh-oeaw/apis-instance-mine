import datetime
import re

from apis_core.apis_metainfo.models import Uri
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.expressions import ArraySubquery
from django.db.models import Case, OuterRef, Value, When
from django.db.models.functions import Concat
from django.views import generic
from django.views.generic.base import TemplateView
from django_tables2.views import SingleTableView

from apis_ontology.models import (
    AusbildungAn,
    Bild,
    GeborenIn,
    GestorbenIn,
    Gewinnt,
    Institution,
    InstitutionHierarchie,
    Mitglied,
    NichtGewaehlt,
    OeawMitgliedschaft,
    Person,
    PositionAn,
)
from mine_frontend.forms import MineMainform
from mine_frontend.mixins import FacetedSearchMixin
from mine_frontend.tables import SearchResultTable


def get_web_object_uri(uri_obj):
    def get_identifier(uri_obj):
        if "geschichtewiki" in uri_obj.uri:
            return uri_obj.uri.split("=")[-1]
        elif "parlament" in uri_obj.uri:
            return re.search(r"PAD_(\d+)", uri_obj.uri).group(1)
        elif "deutsche-biographie" in uri_obj.uri:
            return re.search(r"/([0-9A-Z]+)\.html", uri_obj.uri).group(1)
        else:
            return uri_obj.uri.split("/")[-1]

    return {
        "uri": uri_obj.uri,
        "kind": uri_obj.short_label,
        "identifier": get_identifier(uri_obj),
    }


class OEAWMemberDetailView(LoginRequiredMixin, generic.DetailView):
    model = Person
    queryset = Person.objects.filter(mitglied=True)
    context_object_name = "oeaw_member"
    template_name = "mine_frontend/oeaw_member_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        membership_list = list(
            OeawMitgliedschaft.objects.filter(subj_object_id=self.object.id)
        ) + list(NichtGewaehlt.objects.filter(subj_object_id=self.object.id))
        context["membership"] = sorted(
            membership_list,
            key=lambda obj: getattr(obj, "beginn_date_sort", None)
            or getattr(obj, "datum_date_sort", None)
            or datetime.date.today(),
        )
        context["membership_short"] = OeawMitgliedschaft.objects.filter(
            subj_object_id=self.object.id
        ).order_by("beginn_date_sort")
        context["place_of_birth"] = GeborenIn.objects.filter(
            subj_object_id=self.object.id
        )
        context["place_of_death"] = GestorbenIn.objects.filter(
            subj_object_id=self.object.id
        )
        context["education"] = AusbildungAn.objects.filter(
            subj_object_id=self.object.id
        ).order_by(
            Case(When(typ="Schule", then=Value(0)), default=Value(1)),
            "beginn_date_sort",
        )
        inst_akad = Institution.objects.filter(pk=OuterRef("obj_object_id"))
        career = (
            PositionAn.objects.filter(subj_object_id=self.object.id)
            .annotate(_inst_akad=inst_akad.values("akademie_institution"))
            .order_by("beginn_date_sort")
        )
        context["career"] = career.exclude(_inst_akad=True)
        context["career_akad"] = {}

        pres = career.exclude(_inst_akad=False).filter(position="Präsident(in)")
        sek = career.exclude(_inst_akad=False).filter(position="Sekretär(in)")
        obm = career.exclude(_inst_akad=False).filter(
            position="Obmann/Obfrau (Kommission)"
        )
        kom_mitgl = career.exclude(_inst_akad=False).filter(
            position="Kommissionsmitglied"
        )
        proposed_success = OeawMitgliedschaft.objects.filter(
            vorgeschlagen_von=self.object.id
        ).order_by("beginn_date_sort")
        proposed_unsuccess = NichtGewaehlt.objects.filter(
            vorgeschlagen_von=self.object.id
        ).order_by("datum_date_sort")

        if any(
            qs.exists()
            for qs in [pres, sek, obm, kom_mitgl, proposed_success, proposed_unsuccess]
        ):
            context["career_akad"] = {
                "pres": pres,
                "sek": sek,
                "obm": obm,
                "kom_mitgl": kom_mitgl,
                "proposed_success": proposed_success,
                "proposed_unsuccess": proposed_unsuccess,
            }
        else:
            context["career_akad"] = False
        context["image"] = (
            Bild.objects.filter(object_id=self.object.id).order_by("art").first()
        )
        context["reference_resources"] = [
            get_web_object_uri(x) for x in Uri.objects.filter(object_id=self.object.id)
        ]
        context["prizes"] = Gewinnt.objects.filter(
            subj_object_id=self.object.id
        ).order_by("datum")
        inst_member = Institution.objects.filter(pk=OuterRef("obj_object_id"))
        member = (
            Mitglied.objects.filter(subj_object_id=self.object.id)
            .annotate(
                _inst_kind=inst_member.values("typ"),
                _inst_label=inst_member.values("label"),
            )
            .order_by("beginn_date_sort")
        )
        context["memb_akad"] = member.filter(_inst_kind="Akademie (Ausland)")
        context["nazi"] = member.filter(_inst_label__icontains="nationalsozialistisch")
        context["entity_type"] = "person"

        return context


class OEAWInstitutionDetailView(LoginRequiredMixin, generic.DetailView):
    model = Institution
    queryset = Institution.objects.filter(akademie_institution=True)
    context_object_name = "oeaw_institution"
    template_name = "mine_frontend/oeaw_institution_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ids_akad = Institution.objects.filter(
            akademie_institution=True,
            label__in=[
                "GESAMTAKADEMIE",
                "GEMEINSAME KOMMISSIONEN",
                "MATHEMATISCH-NATURWISSENSCHAFTLICHE KLASSE",
                "PHILOSOPHISCH-HISTORISCHE KLASSE",
            ],
        ).values_list("id", flat=True)
        context["entity_type"] = "institution"
        context["branches"] = InstitutionHierarchie.objects.filter(
            obj_object_id=self.object.id,
            relation="hat Untereinheit",
            subj_object_id__in=ids_akad,
        )
        context["structure"] = sorted(
            [
                {
                    "obj": r.obj,
                    "relation": r.relation,
                    "beginn": r.beginn_date_sort,
                    "ende": r.ende_date_sort,
                }
                for r in InstitutionHierarchie.objects.filter(
                    subj_object_id=self.object.id,
                    relation__in=["hat Untereinheit", "eingegliedert in"],
                ).exclude(obj_object_id__in=ids_akad)
            ]
            + [
                {
                    "obj": r.subj,
                    "relation": r.relation_reverse,
                    "beginn": r.beginn_date_sort,
                    "ende": r.ende_date_sort,
                }
                for r in InstitutionHierarchie.objects.filter(
                    obj_object_id=self.object.id,
                    relation__in=["eingegliedert in"],
                ).exclude(subj_object_id__in=ids_akad)
            ],
            key=lambda x: x["beginn"],
        )
        context["predecessors"] = sorted(
            [
                {
                    "obj": r.obj,
                    "relation": r.relation,
                    "beginn": r.beginn_date_sort,
                    "ende": r.ende_date_sort,
                }
                for r in InstitutionHierarchie.objects.filter(
                    subj_object_id=self.object.id,
                    relation__in=["umbenannt von"],
                ).exclude(obj_object_id__in=ids_akad)
            ]
            + [
                {
                    "obj": r.subj,
                    "relation": r.relation_reverse,
                    "beginn": r.beginn_date_sort,
                    "ende": r.ende_date_sort,
                }
                for r in InstitutionHierarchie.objects.filter(
                    obj_object_id=self.object.id,
                    relation__in=["umbenannt von"],
                ).exclude(subj_object_id__in=ids_akad)
            ],
            key=lambda x: x["beginn"],
        )
        context["successors"] = sorted(
            [
                {
                    "obj": r.obj,
                    "relation": r.relation,
                    "beginn": r.beginn_date_sort,
                    "ende": r.ende_date_sort,
                }
                for r in InstitutionHierarchie.objects.filter(
                    subj_object_id=self.object.id,
                    relation__in=["umbenannt in"],
                ).exclude(obj_object_id__in=ids_akad)
            ]
            + [
                {
                    "obj": r.subj,
                    "relation": r.relation_reverse,
                    "beginn": r.beginn_date_sort,
                    "ende": r.ende_date_sort,
                }
                for r in InstitutionHierarchie.objects.filter(
                    obj_object_id=self.object.id,
                    relation__in=["umbenannt in"],
                ).exclude(subj_object_id__in=ids_akad)
            ],
            key=lambda x: x["beginn"],
        )
        context["presidents"] = PositionAn.objects.filter(
            obj_object_id=self.object.id, position="Obmann/Obfrau (Kommission)"
        ).order_by("beginn_date_sort")
        context["members"] = PositionAn.objects.filter(
            obj_object_id=self.object.id, position="Kommissionsmitglied"
        ).order_by("beginn_date_sort")
        return context


class IndexView(LoginRequiredMixin, TemplateView):
    model = Person
    template_name = "mine_frontend/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = MineMainform()
        context["form_membership_end_date"] = datetime.date.today().year
        context["form_membership_start_date"] = datetime.date.today().year - 10
        return context


class PersonResultsView(FacetedSearchMixin, LoginRequiredMixin, SingleTableView):
    table_class = SearchResultTable
    template_name = "mine_frontend/search_result.html"

    facet_fields = {
        "klasse": {
            "label": "Klasse",
            "field": "klasse",
            "lookup": "exact",
            "type": "choice",
        },
        "membership": {
            "label": "Mitgliedschaft",
            "field": "memberships",
            "lookup": "exact",
            "type": "array",
        },
        "gender": {
            "label": "Geschlecht",
            "field": "gender",
            "lookup": "exact",
            "type": "choice",
        },
        "profession": {
            "label": "Beruf",
            "field": "beruf__name",
            "lookup": "exact",
            "type": "choice",
        },
    }

    filter_fields = {
        "suche": {
            "label": "Suche",
            "field": "search_labels",
            "param": "q",
            "lookup": "unaccent__icontains",
            "type": "text",
        },
    }

    def get_base_queryset(self):
        """Get base queryset before any filtering"""
        memb = (
            OeawMitgliedschaft.objects.filter(subj_object_id=OuterRef("id"))
            .values_list("mitgliedschaft")
            .distinct()
        )

        return Person.objects.filter(mitglied=True).annotate(
            memberships=ArraySubquery(memb),
            search_labels=Concat("forename", Value(" "), "surname"),
        )

    def get_queryset(self):
        """Get the final filtered queryset for the table"""
        qs = self.get_base_queryset()

        qs = self.apply_non_facet_filters(qs)

        qs = self.apply_facet_filters_except(qs)

        return qs
