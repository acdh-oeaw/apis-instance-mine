from apis_core.generic.forms.fields import ModelImportChoiceField
from apis_core.relations.forms import RelationForm
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet

from apis_ontology.models import (
    AusbildungAn,
    GeborenIn,
    GestorbenIn,
    Ort,
    Person,
    PositionAn,
)


class BaseEditForm(RelationForm):
    template_name = "mine_edit/create_relations_form.html"

    def clean(self):
        r = super().clean()
        return r

    def clean_collections(self):
        collections = self.cleaned_data.get("collections")
        if collections == "[]":
            collections = []
        elif isinstance(collections, QuerySet):
            collections = list(collections)
        return collections

    def __init__(self, *args, **kwargs):
        if data := kwargs.get("data", False):
            if data.get("collections") == "[]":
                kwargs["data"] = kwargs["data"].copy()
                kwargs["data"]["collections"] = []
        elif (
            "obj_object_id" in kwargs.get("initial", {})
            and kwargs["initial"]["obj_object_id"] is None
        ):
            kwargs["initial"]["collections"] = None
        super().__init__(*args, **kwargs)
        if "subj_object_id" in self.fields:
            self.fields["subj_object_id"].widget = forms.HiddenInput()
            self.fields["subj_content_type"].widget = forms.HiddenInput()
            self.fields["collections"].widget = forms.HiddenInput()


class EducationForm(BaseEditForm):
    relation_name = "Education"
    description = """
    Please use this form to enter any formal education that you have encountered.
    """

    class Meta:
        model = AusbildungAn
        fields = [
            "obj_object_id",
            "obj_content_type",
            "subj_object_id",
            "subj_content_type",
            "typ",
            "fach",
            "beginn",
            "ende",
            "references",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.subj:
            self.helper.attrs["hx-target"] = f"#relation-li-{self.instance.id}"
        else:
            self.helper.attrs["hx-target"] = "#add_education_button"
            self.helper.attrs["hx-swap"] = "beforebegin"


class CareerForm(BaseEditForm):
    relation_name = "Career"
    description = """
    Please use this form to enter any career steps.
    """

    class Meta:
        model = PositionAn
        fields = [
            "obj_object_id",
            "obj_content_type",
            "subj_object_id",
            "subj_content_type",
            "position",
            "fach",
            "beginn",
            "ende",
            "references",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.subj:
            self.helper.attrs["hx-target"] = f"#relation-li-{self.instance.id}"
        else:
            self.helper.attrs["hx-target"] = "#add_career_button"
            self.helper.attrs["hx-swap"] = "beforebegin"


class PersonEditForm(BaseEditForm):
    relation_name = "Person"
    description = """
    Please use this form to enter any person information.
    """
    place_of_birth = ModelImportChoiceField(
        queryset=Ort.objects.all(),
        required=False,
        label="Place of Birth",
    )
    place_of_death = ModelImportChoiceField(
        queryset=Ort.objects.all(),
        required=False,
        label="Place of Death",
    )
    image = forms.FileField(
        required=False,
        label="Image",
    )

    class Meta:
        model = Person
        fields = [
            "forename",
            "surname",
            "date_of_birth",
            "date_of_death",
            "beruf",
        ]

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if "place_of_birth" in self.changed_data:
            if place_of_birth := self.cleaned_data.get("place_of_birth"):
                pb, created = GeborenIn.objects.get_or_create(
                    subj_object_id=instance.id,
                    subj_content_type=ContentType.objects.get_for_model(instance),
                    defaults={
                        "obj_object_id": place_of_birth.id,
                        "obj_content_type": ContentType.objects.get_for_model(
                            place_of_birth
                        ),
                    },
                )
            else:
                GeborenIn.objects.get(subj_object_id=instance.id).delete()
        if "place_of_death" in self.changed_data:
            if place_of_death := self.cleaned_data.get("place_of_death"):
                pd, created = GestorbenIn.objects.get_or_create(
                    subj_object_id=instance.id,
                    subj_content_type=ContentType.objects.get_for_model(instance),
                    defaults={
                        "obj_object_id": place_of_death.id,
                        "obj_content_type": ContentType.objects.get_for_model(
                            place_of_death
                        ),
                    },
                )
            else:
                GestorbenIn.objects.get(subj_object_id=instance.id).delete()
        return instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.attrs["hx-target"] = "#person-meta-left-panel"
