from crispy_forms.bootstrap import Accordion, AccordionGroup
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Fieldset, Layout, Submit
from dal import autocomplete
from django import forms

from apis_ontology.models import Institution, Ort, Person
from mine_frontend.settings import POSITIONEN_PRES


class MineMainFormHelper(FormHelper):
    form_class = "genericFilterForm"
    form_method = "GET"
    form_tag = False
    # self.template = "forms/template_person_form.html"
    layout = Layout(
        Fieldset("", "q", css_class="bg-mine", css_id="basic_search_fields"),
        Div(
            Div(
                Accordion(
                    Div(
                        Fieldset(
                            "",
                            "membership",
                            "klasse",
                            css_id="mitgliedschaft",
                            css_class="show card-body card filter-wrapper pb-1",
                        ),
                        HTML("<br/>"),
                        Fieldset(
                            "",
                            "start_date_form",
                            "end_date_form",
                            "start_date_form_exclusive",
                            "end_date_form_exclusive",
                            HTML(  # Mitgliedschaft slider
                                """
                                <div class="px-3 pb-3 pt-1">
                                    <label id="mitgliedschaft-slider-label" class="font-weight-bold pb-5">Wer war in diesem Zeitraum Mitglied?</label>
                                    <p><span id="mitgliedschaft-slider-help" class="pb-5">Doppelclick auf die Grenzen um Personen anzuzeigen deren Mitgliedschaft ausschließlich innerhalb der Zeitspanne aufrecht war.</span></p>
                                        <div class="slider-container pt-3">
                                            <div data-start-form="start_date_membership" data-end-form="end_date_membership" class="range-slider" data-range-start="{{form_membership_start_date}}" data-range-end="{{form_membership_end_date}}" data-start-exclusive="start_data_membership_exclusive" data-end-exclusive="end_data_membership_exclusive" data-subject-label="Mitgliedschaft">
                                        </div>
                                        <div class="mt-3 d-flex align-items-center">
                                    

                                    <div class="w-50"></div>
                </div>
                                    </div>
                                </div>"""
                            ),
                            css_class="show card-body card filter-wrapper pb-1",
                        ),
                        css_class="bg-white",
                    ),
                ),
                css_class="col-md-6 pt-30 pr-0 pr-md-custom pl-0 align-items-md-stretch d-flex",
            ),
            Div(
                Accordion(
                    AccordionGroup(
                        "Funktionen im Präsidium",
                        "acad_func",
                        css_id="praesidium",
                    ),
                    AccordionGroup(
                        "Geschlecht",
                        "gender",
                        css_id="geschlecht",
                    ),
                    AccordionGroup(
                        "Lebenslauf",
                        HTML(  # DEBUG: TURNED OFF RANGE SLIDER
                            """<div class="pb-3 pt-1">
                                    <label class="pb-5">Wer lebte in diesem Zeitraum?</label>
                                    <p><span id="life-slider-help" class="pb-5">Doppelclick auf die Grenzen um Personen anzuzeigen die nur innerhalb der Grenzen lebten.</span></p>
                                        <div class="slider-container pt-3">
                                            <div data-start-form="start_date_life_form" data-end-form="end_date_life_form" class="range-slider" data-range-start="{{form_life_start_date}}" data-range-end="{{form_life_end_date}}" data-start-exclusive="start_date_life_form_exclusive" data-end-exclusive="end_date_life_form_exclusive" data-subject-label="Leben">
                                        </div>
                                </div>"""
                        ),
                        "start_date_life_form",
                        "end_date_life_form",
                        "start_date_life_form_exclusive",
                        "end_date_life_form_exclusive",
                        "geburtsort",
                        "sterbeort",
                        # "place_of_birth",
                        # "place_of_death",
                        # "schule",
                        # "uni",
                        # "uni_habil",
                        # "fach_habilitation",
                        # "profession",
                        Fieldset(
                            "Berufliche Positionen",
                            # "beruf_position",
                            # "beruf_institution",
                            css_id="beruf_subform",
                        ),
                        "memb_nsdap",
                        css_id="akademischer_CV",
                    ),
                    AccordionGroup(
                        "Funktionen in Akademieinstitutionen",
                        "akademiefunktionen",
                        css_id="in_der_akademie",
                    ),
                    AccordionGroup(
                        "zur Wahl vorgeschlagen von",
                        "wahl_person",
                        # "wahl_vorschlag_erfolgreich",
                        # "wahl_person",
                        # "wahl_beruf",
                        # "wahl_gender",
                        css_id="wahlvorschlag",
                    ),
                    AccordionGroup(
                        "Wissenschaftler/innen/austausch",
                        # "wiss_austausch"
                    ),
                    AccordionGroup(
                        "Auszeichnungen",
                        # "preise"
                    ),
                ),
                css_class="col-md-6 pt-30 pr-0 pl-0 pl-md-custom",
            ),
            css_class="row ml-0 mr-0 mt-4",
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_input(
            Submit(
                "",
                "Kombinierte Auswertung starten",
                css_class="rounded-0 mt-3 text-uppercase w-100 text-left",
            )
        )


class MineMainform(forms.Form):
    q = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Mitgliedersuche",
                "class": "border-0 rounded-0 d-block mx-auto w-75",
            }
        ),
        required=False,
        label="",
    )
    start_date_form = forms.CharField(
        required=False, widget=forms.HiddenInput(attrs={"id": "start_date_membership"})
    )
    end_date_form = forms.CharField(
        required=False, widget=forms.HiddenInput(attrs={"id": "end_date_membership"})
    )
    start_date_form_exclusive = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "start_data_membership_exclusive"}),
    )
    end_date_form_exclusive = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "end_data_membership_exclusive"}),
    )
    start_date_life_form = forms.CharField(
        required=False, widget=forms.HiddenInput(attrs={"id": "start_date_life_form"})
    )
    end_date_life_form = forms.CharField(
        required=False, widget=forms.HiddenInput(attrs={"id": "end_date_life_form"})
    )
    start_date_life_form_exclusive = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "start_date_life_form_exclusive"}),
    )
    end_date_life_form_exclusive = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "end_date_life_form_exclusive"}),
    )
    death_date = forms.DateField(required=False)
    birth_date = forms.DateField(required=False)
    name = forms.CharField(required=False)
    akademiemitgliedschaft = forms.CharField(required=False)
    akademiefunktionen = forms.MultipleChoiceField(
        # widget=forms.SelectMultiple(attrs={"class": "select2-main"}),
        label="",
        required=False,
        choices=[
            ("funk_praesidentin", "Präsident/in"),
            ("funk_vizepraesidentin", "Vizepräsident/in"),
            ("funk_generalsekretaerin", "Generalsekretär"),
            ("funk_sekretaerin", "Sekretär "),
            ("funk_obfrau", "Obmann/Obfrau einer Kommission"),
            ("funk_mitgl_kommission", "Mitglied einer Kommission"),
            (
                "funk_obfrau_kurat",
                "Obmann/Obfrau eines Kuratoriums/Board eines Institut/einer Forschungsstelle",
            ),
            (
                "funk_direkt_forsch_inst",
                "Direktor/in eines Instituts/einer Forschungsstelle",
            ),
        ],
    )
    acad_func = forms.MultipleChoiceField(
        required=False,
        label="",
        widget=forms.CheckboxSelectMultiple(),
        choices=[(x, x) for x in POSITIONEN_PRES],
    )
    gender = forms.ChoiceField(
        # widget=forms.Select(attrs={"class": "select2-main no-search rounded-0"}),
        required=False,
        choices=(
            ("", "-"),
            ("männlich", "Männlich"),
            ("weiblich", "Weiblich"),
        ),
        label="",
    )
    membership = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label="Mitgliedschaft",
        choices=[
            ("kM I", "korrespondierendes Mitglied im Inland"),
            ("kM A", "korrespondierendes Mitglied im Ausland"),
            ("wM", "Wirkliches Mitglied"),
            ("EM", "Ehrenmitglied"),
            ("Junge Kurie/Junge Akademie", "Junge Kurie/Junge Akademie"),
        ],
    )
    klasse = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label="Klasse",
        choices=[
            (
                "Mathematisch-Naturwissenschaftliche Klasse",
                "Mathematisch-Naturwissenschaftliche Klasse",
            ),
            ("Philosophisch-Historische Klasse", "Philosophisch-Historische Klasse"),
        ],
    )
    wahl_person = forms.ModelMultipleChoiceField(
        queryset=Person.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url="dal-vorschlagende"),
        required=False,
        label="Vorschlagendes Mitglied",
    )
    akademiefunktionen = forms.ModelMultipleChoiceField(
        queryset=Institution.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url="dal-institute"),
        required=False,
        label="Funktion in einer der folgendenen Akademieinstitutionen",
    )

    geburtsort = forms.ModelMultipleChoiceField(
        queryset=Ort.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url="dal-geburtsort"),
        required=False,
        label="Geburtsort",
    )
    sterbeort = forms.ModelMultipleChoiceField(
        queryset=Ort.objects.all(),
        widget=autocomplete.ModelSelect2Multiple(url="dal-sterbeort"),
        required=False,
        label="Sterbeort",
    )
    memb_nsdap = forms.BooleanField(label="Mitglied in der NSDAP", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = MineMainFormHelper()


class MineInstitutionFormHelper(FormHelper):
    form_class = "genericFilterForm"
    form_method = "GET"
    form_tag = False
    # self.template = "forms/template_person_form.html"
    layout = Layout(
        Fieldset("", "q", css_class="bg-mine", css_id="basic_search_fields"),
        Div(
            Div(
                Accordion(
                    Div(
                        Fieldset(
                            "",
                            "typ",
                            "klasse",
                            css_id="mitgliedschaft",
                            css_class="show card-body card filter-wrapper pb-1",
                        ),
                        css_class="bg-white",
                    ),
                ),
                css_class="col-md-6 pt-30 pr-0 pr-md-custom pl-0 align-items-md-stretch d-flex",
            ),
            Div(
                # Accordion(),
                css_class="col-md-6 pt-30 pr-0 pl-0 pl-md-custom",
            ),
            css_class="row ml-0 mr-0 mt-4",
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_input(
            Submit(
                "",
                "Kombinierte Auswertung starten",
                css_class="rounded-0 mt-3 text-uppercase w-100 text-left",
            )
        )


class InstitutionMainForm(forms.Form):
    CHOICES_INST_TYPE = __import__("apis_ontology").models.Institution.TYP_CHOICES[:-8]
    q = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Institutionensuche",
                "class": "border-0 rounded-0 d-block mx-auto w-75",
            }
        ),
        required=False,
        label="",
    )
    klasse = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label="Klasse",
        choices=[
            (
                "Mathematisch-Naturwissenschaftliche Klasse",
                "Mathematisch-Naturwissenschaftliche Klasse",
            ),
            ("Philosophisch-Historische Klasse", "Philosophisch-Historische Klasse"),
            ("Gesamtakademie", "Gesamtakademie"),
        ],
    )
    typ = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label="Art",
        choices=CHOICES_INST_TYPE,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = MineInstitutionFormHelper()
