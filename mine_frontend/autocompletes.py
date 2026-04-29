from dal import autocomplete
from django.db.models import Case, Exists, OuterRef, Q, Value, When

from apis_ontology.models import (
    AusbildungAn,
    GeborenIn,
    GestorbenIn,
    Institution,
    Ort,
    Person,
    PositionAn,
)


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


class RelDalBase(autocomplete.Select2QuerySetView):
    class_for_relation = None
    class_fin = None
    query_param = "label__icontains"
    add_qp_rel = None
    add_qp = None

    def get_queryset(self):
        mitgld = Person.objects.filter(
            id=OuterRef("subj_object_id"), mitglied=True
        ).values_list("id", flat=True)
        rel = (
            self.class_for_relation.objects.annotate(
                mitgld=Case(When(Exists(mitgld), then=Value(True)), default=Value(None))
            )
            .filter(obj_object_id=OuterRef("pk"), mitgld__isnull=False)
            .values_list("id", flat=True)
        )
        if self.add_qp_rel:
            q = Q()
            for param, value in self.add_qp_rel:
                q &= Q(**{param: value})
            rel = rel.filter(q)
        res = self.class_fin.objects.annotate(
            rel=Case(When(Exists(rel), then=Value(True)), default=Value(None))
        ).filter(rel__isnull=False)
        if self.add_qp:
            q = Q()
            for param, value in self.add_qp:
                q &= Q(**{param: value})
            res = res.filter(q)
        if self.q:
            res = res.filter(**{self.query_param: self.q})
        return res


class GeburtsorteDal(RelDalBase):
    class_for_relation = GeborenIn
    class_fin = Ort


class SterbeorteDal(RelDalBase):
    class_for_relation = GestorbenIn
    class_fin = Ort


class AusbildungUniDal(RelDalBase):
    class_for_relation = AusbildungAn
    class_fin = Institution
    add_qp_rel = [("typ__in", ["Studium", "Promotion", "Habilitation"])]


class InstitutionBerufDal(RelDalBase):
    class_for_relation = PositionAn
    class_fin = Institution
