import datetime
import re

from apis_core.apis_metainfo.models import Uri
from django.db.models import OuterRef
from django.views import generic

from apis_ontology.models import (
    AusbildungAn,
    Bild,
    GeborenIn,
    GestorbenIn,
    Gewinnt,
    Institution,
    Mitglied,
    NichtGewaehlt,
    OeawMitgliedschaft,
    Person,
    PositionAn,
)


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


class OEAWMemberDetailView(generic.DetailView):
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
        ).order_by("beginn_date_sort")
        inst_akad = Institution.objects.filter(pk=OuterRef("obj_object_id"))
        career = (
            PositionAn.objects.filter(subj_object_id=self.object.id)
            .annotate(_inst_akad=inst_akad.values("akademie_institution"))
            .order_by("beginn_date_sort")
        )
        context["career"] = career.exclude(_inst_akad=True)
        context["career_akad"] = {}
        context["career_akad"]["pres"] = career.exclude(_inst_akad=False).filter(
            position="Präsident(in)"
        )
        context["career_akad"]["sek"] = career.exclude(_inst_akad=False).filter(
            position="Sekretär(in)"
        )
        context["career_akad"]["obm"] = career.exclude(_inst_akad=False).filter(
            position="Obmann/Obfrau (Kommission)"
        )
        context["career_akad"]["kom_mitgl"] = career.exclude(_inst_akad=False).filter(
            position="Kommissionsmitglied"
        )
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

        return context
