from dal import autocomplete
from django.db.models import Q

from apis_ontology.models import Person


class VorschlagendeDal(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if self.q:
            return Person.objects.filter(
                Q(Q(forename__icontains=self.q) | Q(surname__icontains=self.q)),
                vorgeschlagen_von_set__isnull=False,
            ).distinct()
        else:
            return Person.objects.filter(vorgeschlagen_von_set__isnull=False).distinct()
