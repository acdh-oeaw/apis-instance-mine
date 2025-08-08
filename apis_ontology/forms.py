from apis_core.generic.forms import GenericModelForm
from apis_ontology.models import AkademieInstitution, Institution


class AkademieInstitutionForm(GenericModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["typ"].choices = AkademieInstitution.TYP_AKAD_CHOICES
        self.fields["label"].label = "Name"


class InstitutionForm(GenericModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["typ"].choices = Institution.TYP_CHOICES
        self.fields["label"].label = "Name"


class MitgliedForm(GenericModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Translate inherited fields
        self.fields["surname"].label = "Nachname"
        self.fields["forename"].label = "Vorname"
        self.fields["date_of_birth"].label = "Geburtsdatum"
        self.fields["date_of_death"].label = "Sterbedatum"
        self.fields["gender"].label = "Geschlecht"
        # Your additional field
        self.fields["beruf"].label = "Beruf"
