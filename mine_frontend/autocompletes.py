from dal import autocomplete
from django.db.models import Case, Exists, OuterRef, Q, Value, When

from apis_ontology.models import GeborenIn, GestorbenIn, Institution, Ort, Person


class VorschlagendeDal(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if self.q:
            return Person.objects.filter(
                Q(Q(forename__icontains=self.q) | Q(surname__icontains=self.q)),
                vorgeschlagen_von_set__isnull=False,
            ).distinct()
        else:
            return Person.objects.filter(vorgeschlagen_von_set__isnull=False).distinct()


class OEAWInstitutionsDal(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        inst = Institution.objects.filter(akademie_institution=True)
        if self.q:
            inst = inst.filter(label__icontains=self.q)
        return inst


class LebenOrte(autocomplete.Select2QuerySetView):
    class_for_relation = None

    def get_queryset(self):
        mitgld = Person.objects.filter(
            id=OuterRef("subj_object_id"), mitglied=True
        ).values_list("id", flat=True)
        geb_in = (
            self.class_for_relation.objects.annotate(
                geb_mitgld=Case(
                    When(Exists(mitgld), then=Value(True)), default=Value(None)
                )
            )
            .filter(obj_object_id=OuterRef("pk"), geb_mitgld__isnull=False)
            .values_list("id", flat=True)
        )
        place = Ort.objects.annotate(
            geb_mitgld=Case(When(Exists(geb_in), then=Value(True)), default=Value(None))
        ).filter(geb_mitgld__isnull=False)
        if self.q:
            place = place.filter(label__icontains=self.q)
        return place


class GeburtsorteDal(LebenOrte):
    class_for_relation = GeborenIn


class SterbeorteDal(LebenOrte):
    class_for_relation = GestorbenIn
