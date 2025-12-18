import datetime
import re

from apis_core.uris.models import Uri
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.expressions import ArraySubquery
from django.db.models import Case, F, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Concat, Lower
from django.views import generic
from django.views.generic.base import TemplateView
from django_tables2.views import SingleTableView

from apis_ontology.models import (
    AusbildungAn,
    AutorVon,
    Bild,
    EhrentitelVonInstitution,
    ErwaehntIn,
    GeborenIn,
    GestorbenIn,
    Gewinnt,
    HaeltRedeBei,
    Institution,
    InstitutionHierarchie,
    Mitglied,
    NichtGewaehlt,
    OeawMitgliedschaft,
    Person,
    PositionAn,
    Preis,
    Werk,
    WirdVergebenVon,
)
from mine_frontend.forms import InstitutionMainForm, MineMainform
from mine_frontend.mixins import FacetedSearchMixin
from mine_frontend.settings import POSITIONEN_PRES
from mine_frontend.tables import SearchResultInstitutionTable, SearchResultTable


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
        context["membership_short"] = (
            OeawMitgliedschaft.objects.filter(subj_object_id=self.object.id)
            .exclude(beginn_typ="gewählt, nicht bestätigt")
            .order_by("beginn_date_sort")
        )
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
        context["honour_titles"] = EhrentitelVonInstitution.objects.filter(
            subj_object_id=self.object.id
        )
        inst_akad = Institution.objects.filter(pk=OuterRef("obj_object_id"))
        career = (
            PositionAn.objects.filter(subj_object_id=self.object.id)
            .annotate(
                _inst_akad=inst_akad.values("akademie_institution"),
                _inst_typ=inst_akad.values("typ"),
                _inst_name=Lower(inst_akad.values("label")),
                _sort_date=Case(
                    When(beginn_date_sort__isnull=False, then="beginn_date_sort"),
                    default="ende_date_sort",
                ),
            )
            .order_by("_sort_date")
        )
        context["career"] = career.exclude(_inst_akad=True)
        context["career_akad"] = {}

        pres = career.exclude(_inst_akad=False).filter(
            position="Präsident(in)",
            _inst_name__in=[
                "gesamtakademie",
                "junge akademie",
                "junge kurie",
                "mathematisch-naturwissenschaftliche klasse",
                "philosophisch-historische klasse",
            ],
        )
        viz_pres = career.exclude(_inst_akad=False).filter(
            position="Vizepräsident(in)",
            _inst_name__in=[
                "gesamtakademie",
                "junge akademie",
                "junge kurie",
                "mathematisch-naturwissenschaftliche klasse",
                "philosophisch-historische klasse",
            ],
        )
        sek = career.exclude(_inst_akad=False).filter(
            position="Sekretär(in)",
            _inst_name__in=[
                "gesamtakademie",
                "junge akademie",
                "junge kurie",
                "mathematisch-naturwissenschaftliche klasse",
                "philosophisch-historische klasse",
            ],
        )
        gen_sek = career.exclude(_inst_akad=False).filter(
            position="Generalsekretär(in)",
            _inst_name__in=[
                "gesamtakademie",
                "junge akademie",
                "junge kurie",
                "mathematisch-naturwissenschaftliche klasse",
                "philosophisch-historische klasse",
            ],
        )
        obm = career.exclude(_inst_akad=False).filter(
            position="Obmann/Obfrau (Kommission)"
        )
        kom_mitgl = career.exclude(_inst_akad=False).filter(
            position="Kommissionsmitglied"
        )
        pos_other_inst = (
            career.exclude(_inst_akad=False)
            .exclude(position="Sekretär(in)")
            .exclude(position="Präsident(in)")
            .exclude(position="Vizepräsident(in)")
            .exclude(position="Kommissionsmitglied")
            .exclude(position="Obmann/Obfrau (Kommission)")
            .exclude(position="Delegierte(r)")
            .exclude(position="Generalsekretär(in)")
        )
        proposed_success = OeawMitgliedschaft.objects.filter(
            vorgeschlagen_von=self.object.id
        ).order_by("beginn_date_sort")
        proposed_unsuccess = NichtGewaehlt.objects.filter(
            vorgeschlagen_von=self.object.id
        ).order_by("datum_date_sort")
        delegations = career.filter(_inst_typ="Delegation")

        if any(
            qs.exists()
            for qs in [
                pres,
                viz_pres,
                sek,
                gen_sek,
                obm,
                kom_mitgl,
                proposed_success,
                proposed_unsuccess,
                delegations,
                pos_other_inst,
            ]
        ):
            context["career_akad"] = {
                "pres": pres,
                "viz_pres": viz_pres,
                "sek": sek,
                "gen_sek": gen_sek,
                "obm": obm,
                "kom_mitgl": kom_mitgl,
                "pos_other_inst": pos_other_inst,
                "proposed_success": proposed_success,
                "proposed_unsuccess": proposed_unsuccess,
                "delegations": delegations,
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
        ).order_by("datum_date_sort")
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
        nekrolog = Werk.objects.filter(pk=OuterRef("obj_object_id"))
        aut_nekro_pre = (
            AutorVon.objects.filter(subj_object_id=self.object.id)
            .annotate(_title=nekrolog.values("titel"))
            .values("obj_object_id")
            .filter(_title__icontains="nekrolog")
        )
        context["nekrologe_verfasst"] = ErwaehntIn.objects.filter(
            obj_object_id__in=aut_nekro_pre
        )
        own_nekro_pre = AutorVon.objects.filter(
            obj_object_id__in=ErwaehntIn.objects.filter(subj_object_id=self.object.id)
            .annotate(_title=nekrolog.values("titel"))
            .filter(_title__icontains="nekrolog")
            .values("obj_object_id")
        )
        if own_nekro_pre.exists():
            context["own_nekro"] = own_nekro_pre.first()
        context["speaches"] = HaeltRedeBei.objects.filter(subj_object_id=self.object.id)
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
        list_struc = [
            "hat Untereinheit",
            "eingegliedert in",
            "ist Teil von",
            "gliedert ein",
        ]
        context["structure"] = (
            InstitutionHierarchie.objects.filter(
                Q(
                    subj_object_id=self.object.id,
                )
                | Q(obj_object_id=self.object.id),
                relation__in=list_struc,
            )
            .annotate(
                rel=Case(
                    When(subj_object_id=self.object.id, then=F("relation")),
                    default=F("relation_reverse"),
                ),
                obj_id=Case(
                    When(subj_object_id=self.object.id, then=F("obj_object_id")),
                    default=F("subj_object_id"),
                ),
                obj_label=Case(
                    When(
                        subj_object_id=self.object.id,
                        then=Subquery(
                            Institution.objects.filter(
                                pk=OuterRef("obj_object_id")
                            ).values("label")[:1]
                        ),
                    ),
                    default=Subquery(
                        Institution.objects.filter(
                            pk=OuterRef("subj_object_id")
                        ).values("label")[:1]
                    ),
                ),
            )
            .exclude(subj_object_id__in=ids_akad)
            .exclude(obj_object_id__in=ids_akad)
            .order_by("beginn_date_sort")
        )
        suc_pre_lst = [
            "umbenannt von",
            "zusammengelegt mit",
            "ist Vorgänger von",
        ]
        suc_pre_qs = (
            InstitutionHierarchie.objects.filter(
                Q(subj_object_id=self.object.id) | Q(obj_object_id=self.object.id),
                relation__in=suc_pre_lst,
            )
            .annotate(
                rel=Case(
                    When(subj_object_id=self.object.id, then=F("relation")),
                    default=F("relation_reverse"),
                ),
                rel_kind=Case(
                    When(subj_object_id=self.object.id, then=Value("predecessor")),
                    default=Value("successor"),
                ),
            )
            .exclude(obj_object_id__in=ids_akad)
        )

        context["predecessors"] = suc_pre_qs.filter(rel_kind="predecessor").order_by(
            "beginn_date_sort"
        )
        context["successors"] = suc_pre_qs.filter(rel_kind="successor").order_by(
            "beginn_date_sort"
        )
        context["presidents"] = PositionAn.objects.filter(
            obj_object_id=self.object.id, position="Obmann/Obfrau (Kommission)"
        ).order_by("beginn_date_sort")
        context["members"] = PositionAn.objects.filter(
            obj_object_id=self.object.id,
            position__in=["Kommissionsmitglied", "Delegierte(r)"],
        ).order_by("beginn_date_sort")
        return context


class OEAWPrizeDetailView(LoginRequiredMixin, generic.DetailView):
    model = Preis
    queryset = Preis.objects.filter(academy_prize=True)
    context_object_name = "oeaw_prize"
    template_name = "mine_frontend/oeaw_prize_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entity_type"] = "institution"
        context["laureates"] = Gewinnt.objects.filter(
            obj_object_id=self.object.id,
        ).order_by("datum_date_sort")
        context["awarded_by"] = WirdVergebenVon.objects.filter(
            subj_object_id=self.object.id
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


class InstitutionIndexView(LoginRequiredMixin, TemplateView):
    model = Institution
    template_name = "mine_frontend/index_institution.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = InstitutionMainForm()
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
        "acad_func": {
            "label": "Funktionen im Präsidium",
            "field": "acad_func",
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
        klasse_ids = Institution.objects.filter(typ="Klasse").values_list(
            "id", flat=True
        )
        func = (
            PositionAn.objects.filter(
                subj_object_id=OuterRef("id"),
                obj_object_id__in=klasse_ids,
                position__in=POSITIONEN_PRES,
            )
            .values_list("position")
            .distinct()
        )

        return Person.objects.filter(mitglied=True).annotate(
            memberships=ArraySubquery(memb),
            acad_func=ArraySubquery(func),
            search_labels=Concat("forename", Value(" "), "surname"),
        )

    def get_queryset(self):
        """Get the final filtered queryset for the table"""
        qs = self.get_base_queryset()

        qs = self.apply_non_facet_filters(qs)

        qs = self.apply_facet_filters_except(qs)
        return qs


class InstitutionResultsView(FacetedSearchMixin, LoginRequiredMixin, SingleTableView):
    table_class = SearchResultInstitutionTable
    template_name = "mine_frontend/search_result.html"

    facet_fields = {
        "klasse": {
            "label": "Klasse",
            "field": "klasse_label",
            "lookup": "exact",
            "type": "choice",
        },
        "typ": {
            "label": "Art",
            "field": "typ",
            "lookup": "exact",
            "type": "choice",
        },
    }

    filter_fields = {
        "suche": {
            "label": "Suche",
            "field": "label",
            "param": "q",
            "lookup": "unaccent__icontains",
            "type": "text",
        },
    }

    def get_base_queryset(self):
        """Get base queryset before any filtering"""
        klasse_ids = Institution.objects.filter(typ="Klasse").values_list(
            "id", flat=True
        )

        klasse_relation = (
            InstitutionHierarchie.objects.filter(
                Q(subj_object_id__in=klasse_ids, obj_object_id=OuterRef("pk"))
                | Q(obj_object_id__in=klasse_ids, subj_object_id=OuterRef("pk"))
            )
            .annotate(
                klasse_id=Case(
                    When(subj_object_id__in=klasse_ids, then=F("subj_object_id")),
                    default=F("obj_object_id"),
                )
            )
            .values("klasse_id")[:1]
        )

        return Institution.objects.filter(akademie_institution=True).annotate(
            klasse_id=Subquery(klasse_relation),
            klasse_label=Subquery(
                Institution.objects.filter(pk=OuterRef("klasse_id")).values("label")[:1]
            ),
        )

    def get_queryset(self):
        """Get the final filtered queryset for the table"""
        qs = self.get_base_queryset()

        qs = self.apply_non_facet_filters(qs)

        qs = self.apply_facet_filters_except(qs)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["css_postfix"] = "-institutions"
        return context
