from apis_core.relations.forms import RelationForm
from django import forms
from django.db.models import QuerySet

from apis_ontology.models import AusbildungAn, PositionAn


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
