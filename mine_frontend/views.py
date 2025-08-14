import datetime

from django.views import generic

from apis_ontology.models import (
    AusbildungAn,
    GeborenIn,
    GestorbenIn,
    NichtGewaehlt,
    OeawMitgliedschaft,
    Person,
    PositionAn,
)


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
        context["career"] = PositionAn.objects.filter(
            subj_object_id=self.object.id
        ).order_by("beginn_date_sort")
        return context
