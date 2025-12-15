from crispy_forms.bootstrap import Accordion, AccordionGroup
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Fieldset, Hidden, Layout, Submit
from django import forms


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
                    Hidden("start_date_form", ""),
                    Hidden("end_date_form", ""),
                    Hidden("start_date_form_exclusive", ""),
                    Hidden("end_date_form_exclusive", ""),
                    Hidden("start_date_life_form", ""),
                    Hidden("end_date_life_form", ""),
                    Div(
                        Fieldset(
                            "",
                            "membership",
                            "klasse",
                            css_id="mitgliedschaft",
                            css_class="show card-body card filter-wrapper pb-1",
                        ),
                        HTML(  # Mitgliedschaft slider
                            """ <div class="px-3 pb-3 pt-1">
                                    <label id="mitgleidschaft-slider-label" class="font-weight-bold pb-5">Mitgliedschaft im Zeitraum</label>
                                        <div class="slider-container pt-3">
                                            <div data-start-form="start_date_form" data-end-form="end_date_form" class="range-slider" data-range-start="{{form_membership_start_date}}" data-range-end="{{form_membership_end_date}}">
                                        </div>
                                        <div class="mt-3 d-flex align-items-center">
                                    <input class="form-control form-control-sm w-25 mr-2" type="text" id="start_date_input" value="{{form_membership_start_date}}"/><input type="checkbox" class="mt-1 ml-1" id="start_date_exclusive_checkbox"/><span class="ml-1">⟼</span>

                                    <div class="w-50"></div><span class="mr-1">⟻</span><input type="checkbox" class="mt-1 mr-2"  id="end_date_exclusive_checkbox" class="mr-2"/>
                                    <input class="form-control form-control-sm w-25" type="text" id="end_date_input" value="{{form_membership_end_date}}"/>
                </div>
                                    </div>
                                </div>"""
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
                        "pres_funktionen",
                        css_id="praesidium",
                    ),
                    AccordionGroup(
                        "Geschlecht",
                        # "gender",
                        css_id="geschlecht",
                    ),
                    AccordionGroup(
                        "Lebenslauf",
                        HTML(  # DEBUG: TURNED OFF RANGE SLIDER
                            """<div class="pb-3 pt-1">
                                    <label class="pb-5">Leben im Zeitraum</label>
                                    <div class="slider-container pt-3">
                                        <div data-start-form="start_date_life_form" data-end-form="end_date_life_form" class="range-sliderOFF">
                                        </div>
                                    </div>
                                </div>"""
                        ),
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
                        # "mgld_nsdap",
                        css_id="akademischer_CV",
                    ),
                    AccordionGroup(
                        "Funktionen in Akademieinstitutionen",
                        # "akademiefunktionen",
                        css_id="in_der_akademie",
                    ),
                    AccordionGroup(
                        "zur Wahl vorgeschlagen von",
                        # "wahl_person",
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
    start_date_form = forms.CharField(required=False)
    end_date_form = forms.CharField(required=False)
    start_date_form_exclusive = forms.BooleanField(
        required=False, label="Membership start not before"
    )
    end_date_form_exclusive = forms.BooleanField(required=False)
    start_date_life_form = forms.CharField(required=False)
    end_date_life_form = forms.CharField(required=False)
    start_date_life_form_exclusive = forms.CharField(required=False)
    end_date_life_form_exclusive = forms.CharField(required=False)
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
    pres_funktionen = forms.MultipleChoiceField(
        required=False,
        label="",
        widget=forms.CheckboxSelectMultiple(),
        choices=[
            ("funk_praesidentin", "Präsident/in"),
            ("funk_vizepraesidentin", "Vizepräsident/in"),
            ("funk_generalsekretaerin", "Generalsekretär/in"),
            ("funk_sekretaerin", "Sekretär/in"),
            ("funk_klassenpres_math_nat", "Klassenpräsident/in math.-nat. Klasse"),
            ("funk_klassenpres_phil_hist", "Klassenpräsident/in phil.-hist. Klasse"),
        ],
    )
    gender = forms.ChoiceField(
        # widget=forms.Select(attrs={"class": "select2-main no-search rounded-0"}),
        required=False,
        choices=(
            ("", "-"),
            ("männlich", "Männlich"),
            ("weiblich", "Weiblich"),
            ("unbekannt", "Unbekannt"),
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
