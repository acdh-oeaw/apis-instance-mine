import csv
import os
from functools import cache

from apis_core.apis_entities.abc import E21_Person, E53_Place, E74_Group
from apis_core.apis_entities.models import AbstractEntity
from apis_core.generic.abc import GenericModel
from apis_core.history.models import VersionMixin
from apis_core.relations.models import Relation
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_interval.fields import FuzzyDateParserField
from django_json_editor_field.fields import JSONEditorField

from mine_frontend.settings import POSITIONEN


class NameMixin(models.Model):
    name = models.CharField(max_length=255)
    alternative_namen = ArrayField(
        models.CharField(max_length=255, blank=True),
        blank=True,
        null=True,
        help_text="Alternative Namen",
    )

    class Meta:
        abstract = True


class AlternativeNameMixin(models.Model):
    schema = {
        "title": "Alternative Namen",
        "type": "array",
        "format": "table",
        "items": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "pattern": "^.+$",
                    "options": {
                        "inputAttributes": {
                            "required": True,
                        },
                    },
                },
                "sprache": {
                    "type": "string",
                    "enum": ["", "deu", "eng"],
                },
                "art": {
                    "type": "string",
                    "enum": [
                        "",
                        "alternative name (short)",
                        "collective term",
                        "alternative name",
                        "Legacy name (merge)",
                        "Legacy URI (merge)",
                        "Wikicommons Image",
                        "filename OEAW Archiv",
                        "photocredit OEAW Archiv",
                        "legacy name",
                        "Publikations URI",
                    ],
                },
                "beginn": {
                    "type": "string",
                    "pattern": "^$|^\d\d\d\d$",
                    "options": {
                        "inputAttributes": {
                            "placeholder": "YYYY",
                        },
                        "containerAttributes": {
                            "class": "yearinput",
                        },
                    },
                },
                "ende": {
                    "type": "string",
                    "pattern": "^$|^\d\d\d\d$",
                    "options": {
                        "inputAttributes": {
                            "placeholder": "YYYY",
                        },
                        "containerAttributes": {
                            "class": "yearinput",
                        },
                    },
                },
            },
        },
    }
    options = {
        "theme": "bootstrap4",
        "disable_collapse": True,
        "disable_edit_json": True,
        "disable_properties": True,
        "disable_array_reorder": True,
        "disable_array_delete_last_row": True,
        "disable_array_delete_all_rows": True,
        "prompt_before_delete": False,
    }

    alternative_namen = JSONEditorField(schema=schema, options=options, null=True)

    class Meta:
        abstract = True


class LegacyFieldsMixin(models.Model):
    notes = models.TextField(blank=True)
    references = models.TextField(blank=True)
    old_id = models.IntegerField(blank=True, null=True, unique=True, editable=False)

    class Meta:
        abstract = True


def add_to_dict(path, data, row):
    for i, p in enumerate(path):
        if i + 1 == len(path):
            data[p] = {f"{row[2]}:{row[3]}": row[3]}
            return data
    raise ValidationError("Parsing of the OESTAT data for generating choices failed.")


def get_oestat_choices():
    res = dict()
    with open(
        f"{os.path.dirname(__file__)}/../resources/OEFOS2012_DE_CTI.txt",
        newline="",
        encoding="latin1",
    ) as inp:
        oestat = csv.reader(inp, delimiter=";", quotechar='"')
        next(oestat)
        current_path = []
        old_level = 0
        for row in oestat:
            level = int(row[0])
            text = row[3]
            if level > old_level:
                current_path.append(text)
            elif level < old_level:
                rm_levels = level - old_level
                current_path = current_path[:rm_levels]
            res = add_to_dict(current_path, res, row)
    return res


class Beruf(GenericModel, models.Model):
    old_id = models.IntegerField(blank=True, null=True, unique=True, editable=False)
    name = models.CharField(max_length=1024)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = _("Beruf")
        verbose_name_plural = _("Berufe")


class Bild(GenericModel, models.Model):
    BILD_KIND_CHOICES = (("OEAW Archiv", "OEAW Archiv"), ("Wikimedia", "Wikimedia"))
    art = models.CharField(max_length=100, choices=BILD_KIND_CHOICES)
    pfad = models.CharField(max_length=1024)
    credit = models.TextField(max_length=1024, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    def __str__(self):
        return str(self.art) + ": " + str(self.pfad)

    class Meta:
        verbose_name = _("Bild")
        verbose_name_plural = _("Bilder")


class Fach(AbstractEntity, VersionMixin):
    """akademische Fachrichtung"""

    old_id = models.IntegerField(blank=True, null=True, unique=True, editable=False)
    name = models.CharField(max_length=400)
    oestat = models.CharField(max_length=400, blank=True, choices=get_oestat_choices)

    class Meta:
        verbose_name = _("Fachrichtung")
        verbose_name_plural = _("Fachrichtungen")

    def __str__(self):
        return str(self.name)


class Ereignis(
    VersionMixin,
    AbstractEntity,
    NameMixin,
    LegacyFieldsMixin,
    AlternativeNameMixin,
):
    """haupsächlich Sitzungen und Wahlen"""

    TYP_CHOICES = [
        ("Wahlsitzung", "Wahlsitzung"),
        ("Feierliche Sitzung", "Feierliche Sitzung"),
        ("Gesetz", "Gesetz"),
    ]
    typ = models.CharField(
        max_length=100,
        choices=TYP_CHOICES,
        default="unbekannt",
        blank=True,
        help_text="Art des Events",
    )
    datum = FuzzyDateParserField(blank=True)

    def __str__(self):
        return f"{self.name}"

    class Meta(
        VersionMixin.Meta, AbstractEntity.Meta, NameMixin.Meta, LegacyFieldsMixin.Meta
    ):
        verbose_name = "Ereignis"
        verbose_name_plural = "Ereignisse"


class PreisManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                academy_prize=models.Exists(
                    WirdVergebenVon.objects.filter(
                        subj_object_id=models.OuterRef("pk"),
                        obj_object_id__in=Institution.objects.filter(
                            akademie_institution=True
                        ).values_list("id", flat=True),
                    )
                )
            )
        )


class Preis(
    VersionMixin,
    AbstractEntity,
    NameMixin,
    LegacyFieldsMixin,
    AlternativeNameMixin,
):
    """Auschreibung eines Preises oder Preisaufgabe"""

    objects = PreisManager()

    @cached_property
    def academy_prize(self):
        return WirdVergebenVon.objects.filter(
            subj_object_id=self.pk,
            obj_object_id__in=Institution.objects.filter(
                akademie_institution=True
            ).values_list("id", flat=True),
        ).exists()

    text = models.TextField(blank=True)
    datum_ausschreibung = FuzzyDateParserField(
        blank=True, help_text="Datum der Ausschreibung bei Preisaufgaben"
    )
    beginn = FuzzyDateParserField(blank=True, help_text="Gründungsdatum des Preises")
    ende = FuzzyDateParserField(blank=True, help_text="Auflösungsdatum des Preises")

    class Meta(VersionMixin.Meta, AbstractEntity.Meta, NameMixin.Meta):
        verbose_name = "Preis/Preisausschreiben"
        verbose_name_plural = "Preise/Preisausschreiben"

    def __str__(self):
        return self.name


class Religion(VersionMixin, AbstractEntity, NameMixin, LegacyFieldsMixin):
    """Religionsgemeinschaft"""

    class Meta(VersionMixin.Meta, AbstractEntity.Meta, NameMixin.Meta):
        verbose_name = _("Religionsgemeinschaft")
        verbose_name_plural = _("Religionsgemeinschaften")


class Werk(
    VersionMixin,
    AbstractEntity,
    LegacyFieldsMixin,
    AlternativeNameMixin,
):
    TYP_CHOICES = [
        ("Buch", "Buch"),
        ("Zeitschrift", "Zeitschrift"),
        ("Zeitschriftenartikel", "Zeitschriftenartikel"),
        ("Monographie", "Monographie"),
        ("Konferenzband", "Konferenzband"),
        ("Konferenzbeitrag", "Konferenzbeitrag"),
        ("Dissertation", "Dissertation"),
        ("Habilitation", "Habilitation"),
        ("Patent", "Patent"),
        ("Nekrolog", "Nekrolog"),
        ("Sonstiges", "Sonstiges"),
    ]
    titel = models.CharField(max_length=400)
    bibtex = models.TextField(blank=True)
    typ = models.CharField(
        max_length=100,
        choices=TYP_CHOICES,
        default="Sonstiges",
        blank=True,
        help_text="Art des Werks",
    )

    class Meta(VersionMixin.Meta, AbstractEntity.Meta):
        verbose_name = _("Werk")
        verbose_name_plural = _("Werke")

    def __str__(self):
        return self.titel


class Person(
    VersionMixin,
    E21_Person,
    AbstractEntity,
    LegacyFieldsMixin,
    AlternativeNameMixin,
):
    KLASSE_CHOICES = [
        (
            "Mathematisch-Naturwissenschaftliche Klasse",
            "Mathematisch-Naturwissenschaftliche Klasse",
        ),
        ("Philosophisch-Historische Klasse", "Philosophisch-Historische Klasse"),
        ("Gesamtakademie", "Gesamtakademie"),
    ]
    klasse = models.CharField(max_length=100, blank=True, choices=KLASSE_CHOICES)
    beruf = models.ManyToManyField(Beruf, blank=True)
    date_of_birth = FuzzyDateParserField(blank=True, verbose_name="Geburtsdatum")
    date_of_death = FuzzyDateParserField(blank=True, verbose_name="Sterbedatum")
    mitglied = models.BooleanField(default=False, blank=False, null=False)  # pyright: ignore [reportArgumentType]
    klasse = models.CharField(max_length=100, blank=True, choices=KLASSE_CHOICES)
    reg_pflichtig = models.BooleanField(
        default=False,
        help_text="registierungspflichtig aufgrund des Verbotsgesetzes",
    )
    sf_befreit_ab = FuzzyDateParserField(
        blank=True,
        help_text="von Sühnefolgen befreit aufgrund Nationalsozialistengesetz oder Amnestie für minderbelastete Personen ab",
    )
    schema = {
        "title": "Alternative Names",
        "type": "array",
        "format": "table",
        "items": {
            "type": "object",
            "properties": {
                "titel": {
                    "type": "string",
                    "pattern": "^.+$",
                    "options": {
                        "inputAttributes": {
                            "required": True,
                        },
                    },
                },
                "art": {
                    "type": "string",
                    "enum": [
                        "",
                        "Akademisch",
                        "Ehrentitel",
                        "Adelstitel",
                    ],
                },
                "beginn": {
                    "type": "string",
                    "pattern": "^$|^\d\d\d\d$",
                    "options": {
                        "inputAttributes": {
                            "placeholder": "YYYY",
                        },
                        "containerAttributes": {
                            "class": "yearinput",
                        },
                    },
                },
                "ende": {
                    "type": "string",
                    "pattern": "^$|^\d\d\d\d$",
                    "options": {
                        "inputAttributes": {
                            "placeholder": "YYYY",
                        },
                        "containerAttributes": {
                            "class": "yearinput",
                        },
                    },
                },
            },
        },
    }
    options = {
        "theme": "bootstrap4",
        "disable_collapse": True,
        "disable_edit_json": True,
        "disable_properties": True,
        "disable_array_reorder": True,
        "disable_array_delete_last_row": True,
        "disable_array_delete_all_rows": True,
        "prompt_before_delete": False,
    }

    titel = JSONEditorField(schema=schema, options=options, null=True)

    class Meta(AbstractEntity.Meta, E21_Person.Meta, VersionMixin.Meta):
        verbose_name = "Person"
        verbose_name_plural = "Personen"


class Ort(
    VersionMixin,
    E53_Place,
    AbstractEntity,
    LegacyFieldsMixin,
    AlternativeNameMixin,
):
    class Meta(AbstractEntity.Meta, E53_Place.Meta, VersionMixin.Meta):
        verbose_name = "Ort"
        verbose_name_plural = "Orte"


class Institution(
    VersionMixin,
    E74_Group,
    AbstractEntity,
    LegacyFieldsMixin,
    AlternativeNameMixin,
):
    TYP_CHOICES = [
        ("Kommission", "Kommission"),
        ("Institut", "Institut"),
        ("Forschungsstelle", "Forschungsstelle"),
        ("Klasse", "Klasse"),
        ("Institution der Gesamtakademie", "Institution der Gesamtakademie"),
        ("Forschungsorientierte Einheit", "Forschungsorientierte Einheit"),
        ("Einrichtung", "Einrichtung"),
        ("Komitee", "Komitee"),
        ("Kuratorium", "Kuratorium"),
        ("Beirat", "Beirat"),
        ("Delegation", "Delegation"),
        ("Internationales Forschungsprogramm", "Internationales Forschungsprogramm"),
        ("Preis", "Preis"),
        ("Ministerium", "Ministerium"),
        ("Orden (geistl.)", "Orden (geistl.)"),
        ("Schule", "Schule"),
        ("Kirche", "Kirche"),
        ("Gymnasium", "Gymnasium"),
        ("Akademie (Ausland)", "Akademie (Ausland)"),
        ("Universität", "Universität"),
        ("Ministerium", "Ministerium"),
    ]
    typ = models.CharField(
        max_length=100,
        choices=TYP_CHOICES,
        default="unbekannt",
        blank=True,
        help_text="Art der Institution",
    )
    akademie_institution = models.BooleanField(default=False, blank=False, null=False)  # pyright: ignore [reportArgumentType]
    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)

    def abbrv(self):
        match self.label.lower():
            case "philosophisch-historische klasse":
                return "phil.hist Klasse"
            case "mathematisch-naturwissenschaftliche klasse":
                return "math.nat Klasse"
            case "gesamtakademie":
                return "Gesamtakademie"
        return self.label

    class Meta(VersionMixin.Meta, E74_Group.Meta, AbstractEntity.Meta):
        verbose_name = "Institution"
        verbose_name_plural = "Institutionen"


class OeawMitgliedschaft(Relation, VersionMixin, LegacyFieldsMixin):
    """class for the membership in the OeAW"""

    BEGIN_TYP_CHOICES = [
        ("gewählt", "gewählt"),
        ("bestätigt", "bestätigt"),
        ("gewählt und bestätigt", "gewählt und bestätigt"),
        ("gewählt und ernannt", "gewählt und ernannt"),
        ("gewählt, nicht bestätigt", "gewählt, nicht bestätigt"),
        ("ernannt", "ernannt"),
        ("genehmigt", "genehmigt"),
        ("eingereiht", "eingereiht"),
        ("reaktiviert", "reaktiviert"),
        ("unbekannt", "unbekannt"),
    ]
    END_TYP_CHOICES = [
        ("ausgetreten", "ausgetreten"),
        ("ausgeschlossen", "ausgeschlossen"),
        ("erloschen", "erloschen"),
        ("ruhend gestellt", "ruhend gestellt"),
        ("andere Mitgliedschaft", "andere Mitgliedschaft"),  # neu hinzugefügt
        ("Tod", "Tod"),  # neu hinzugefügt
        ("unbekannt", "unbekannt"),
    ]
    MEMBERSHIP_CHOICES = [
        ("wM", "wM"),
        ("oM", "oM"),
        ("kM I", "kM I"),
        ("kM A", "kM A"),
        ("EM", "EM"),
        ("JA", "JA"),
    ]
    MEMBERSHIP_MAPPING = {
        "wM": "Wirkliches Mitglied",
        "oM": "Ordentliches Mitglied",
        "kM I": "korrespondierendes Mitglied im Inland",
        "kM A": "korrespondierendes Mitglied im Ausland",
        "EM": "Ehrenmitglied",
        "JA": "Junge Akademie/Junge Kurie",
    }

    subj_model = Person
    obj_model = Institution
    vorgeschlagen_von = models.ManyToManyField(
        Person, blank=True, related_name="vorgeschlagen_von_set", symmetrical=False
    )
    einspruch_von = models.ManyToManyField(
        Person,
        blank=True,
        related_name="einspruch_von_set",
        symmetrical=False,
        help_text="gegen seine Reaktivierung wurde Einspruch erhoben durch",
    )
    wahlsitzung = models.ForeignKey(
        Ereignis, on_delete=models.CASCADE, blank=True, null=True
    )
    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)
    beginn_typ = models.CharField(
        max_length=100,
        choices=BEGIN_TYP_CHOICES,
        default="unbekannt",
        blank=True,
        help_text="Art des Beginns der Mitgliedschaft",
    )
    ende_typ = models.CharField(
        max_length=100,
        choices=END_TYP_CHOICES,
        default="unbekannt",
        blank=True,
        help_text="Art des Endes der Mitgliedschaft",
    )
    mitgliedschaft = models.CharField(
        max_length=4,
        choices=MEMBERSHIP_CHOICES,
        blank=False,
        help_text="Art der Mitgliedschaft",
    )

    def get_long_membership(self) -> str:
        """return the long form of the membership"""

        return self.MEMBERSHIP_MAPPING[str(self.mitgliedschaft)]

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Mitgliedschaft")
        verbose_name_plural = _("Mitgliedschaften")


class NichtGewaehlt(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Institution
    vorgeschlagen_von = models.ManyToManyField(Person, blank=True)
    wahlsitzung = models.ForeignKey(
        Ereignis, on_delete=models.CASCADE, blank=True, null=True
    )
    datum = FuzzyDateParserField(blank=True)
    mitgliedschaft = models.CharField(
        max_length=4,
        choices=OeawMitgliedschaft.MEMBERSHIP_CHOICES,
        blank=False,
        help_text="Art der Mitgliedschaft",
    )

    @classmethod
    def name(cls) -> str:
        return "nicht gewählt"

    @classmethod
    def reverse_name(cls) -> str:
        return "nicht gewählt"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Nicht gewählte Person")
        verbose_name_plural = _("Nicht gewählte Personen")


def get_position_choices() -> list[tuple[str, str]]:
    with open(
        f"{os.path.dirname(__file__)}/../resources/position_inst_relations.csv",
        newline="",
    ) as inp:
        reader = csv.DictReader(inp, delimiter=",", quotechar='"')
        res = [(i["name"], i["name"]) for i in reader]
    return res


class PositionAn(Relation, VersionMixin, LegacyFieldsMixin):
    """Anstellung/Position in Institution"""

    subj_model = Person
    obj_model = Institution
    position = models.CharField(blank=True, choices=[(x, x) for x in POSITIONEN])
    fach = models.ForeignKey(Fach, on_delete=models.CASCADE, blank=True, null=True)
    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "hat Position inne"

    @classmethod
    def reverse_name(cls) -> str:
        return "hat Mitarbeiter"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Position an")
        verbose_name_plural = _("Positionen an")


class AusbildungAn(Relation, VersionMixin, LegacyFieldsMixin):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_institution"
    TYP_CHOICES = [
        ("Schule", "Schule"),
        ("Studium", "Studium"),
        ("Promotion", "Promotion"),
        ("Habilitation", "Habilitation"),
    ]
    subj_model = Person
    obj_model = Institution
    abgeschlossen = models.BooleanField(null=True, blank=True)
    fach = models.ForeignKey(Fach, on_delete=models.CASCADE, blank=True, null=True)
    typ = models.CharField(choices=TYP_CHOICES, max_length=255, blank=True)
    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "absolviert Ausbildung an"

    @classmethod
    def reverse_name(cls) -> str:
        return "hat Auszubildenden"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Ausbildung an")
        verbose_name_plural = _("Ausbildungen an")


class SchreibtAus(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Institution
    obj_model = Preis
    datum = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "schreibt aus"

    @classmethod
    def reverse_name(cls) -> str:
        return "wird ausgeschrieben von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("schreibt aus")
        verbose_name_plural = _("schreibt aus")


@cache
def get_choices_inst_hierarchie_data():
    with open(
        f"{os.path.dirname(__file__)}/../resources/optionen_inst_hierarchie.csv",
        newline="",
    ) as inp:
        reader = csv.DictReader(inp, delimiter=",", quotechar='"')
        return list(reader)


@cache
def get_choices_inst_hierarchie():
    reader = get_choices_inst_hierarchie_data()
    res = [(f"{i['name']}", f"{i['name']} ({i['name_reverse']})") for i in reader]
    return res


class InstitutionHierarchie(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Institution
    obj_model = Institution
    relation = models.CharField(max_length=255, choices=get_choices_inst_hierarchie)
    relation_reverse = models.CharField(max_length=255, editable=False)
    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "Hierarchie"

    @classmethod
    def reverse_name(cls) -> str:
        return "Hierarchie"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Institutionen Hierarchie")
        verbose_name_plural = _("Institutionen Hierarchie")

    def save(self, *args, **kwargs):
        data = get_choices_inst_hierarchie_data()
        for d in data:
            if d["name"] == self.relation:
                self.relation_reverse = d["name_reverse"]
        super().save(*args, **kwargs)


class WirdVergebenVon(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Preis
    obj_model = Institution
    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "wird vergeben von"

    @classmethod
    def reverse_name(cls) -> str:
        return "vergiebt"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("wird vergeben von")
        verbose_name_plural = _("wird vergeben von")


class WirdGestiftetVon(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Preis
    obj_model = Institution
    datum = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "wird vergeben von"

    @classmethod
    def reverse_name(cls) -> str:
        return "vergiebt"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("wird vergeben von")
        verbose_name_plural = _("wird vergeben von")


class GelegenIn(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Institution
    obj_model = Ort

    @classmethod
    def name(cls) -> str:
        return "gelegn in"

    @classmethod
    def reverse_name(cls) -> str:
        return "schließt ein"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("gelegen in")
        verbose_name_plural = _("gelegen in")


class Gewinnt(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Preis
    datum = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "gewinnt"

    @classmethod
    def reverse_name(cls) -> str:
        return "gewonnen von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("gewinnt")
        verbose_name_plural = _("gewinnt")


class Stiftet(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Institution
    datum = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "stiftet"

    @classmethod
    def reverse_name(cls) -> str:
        return "gestiftet von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("stiftet")
        verbose_name_plural = _("stiftet")


@cache
def get_choices_memberships_non_oeaw():
    with open(
        f"{os.path.dirname(__file__)}/../resources/optionen_mitglied.csv", newline=""
    ) as inp:
        reader = csv.DictReader(inp, delimiter=",", quotechar='"')
        res = [(f"{i['label_new']}", f"{i['label_new']}") for i in reader]
    return res


class Mitglied(Relation, VersionMixin, LegacyFieldsMixin):
    """Mitgliedschaften in anderen Institution als der ÖAW"""

    subj_model = Person
    obj_model = Institution
    art = models.CharField(
        max_length=255, choices=get_choices_memberships_non_oeaw, blank=True
    )
    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "Mitglied in"

    @classmethod
    def reverse_name(cls) -> str:
        return "hat Mitlied"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Mitglied")
        verbose_name_plural = _("Mitglieder")


class AnhaengerVon(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Religion

    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "Anhänger von"

    @classmethod
    def reverse_name(cls) -> str:
        return "hat Anhänger"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Anhänger")
        verbose_name_plural = _("Anhänger")


class NimmtTeilAn(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Ereignis

    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "nimmt Teil an"

    @classmethod
    def reverse_name(cls) -> str:
        return "hat TeilnehmerIn"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Teilnahme an")
        verbose_name_plural = _("Teilnahme an")


class EhrentitelVonInstitution(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Institution

    titel = models.CharField(max_length=255)
    datum = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "erhält Ehrentitel von"

    @classmethod
    def reverse_name(cls) -> str:
        return "verleiht Ehrentitel an"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Ehrentitel von")
        verbose_name_plural = _("Ehrentitel von")


class LehntPreisAb(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Preis

    datum = FuzzyDateParserField(blank=True)
    grund = models.CharField(max_length=255, blank=True)

    @classmethod
    def name(cls) -> str:
        return "lehnt Preis ab"

    @classmethod
    def reverse_name(cls) -> str:
        return "wird abgelehnt von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("abgelehnt von")
        verbose_name_plural = _("abgelehnt von")


class StelltAntragAn(Relation, VersionMixin, LegacyFieldsMixin):
    """verwendet für Förderanträge an Institutionen"""

    CHOICES_STATUS = [
        ("abgelehnt", "abgelehnt"),
        ("bewilligt", "bewilligt"),
        ("anderwitig erledigt", "anderweitig erledigt"),
        ("Förderstatus unbekannt", "Förderstatus unbekannt"),
    ]
    subj_model = Person
    obj_model = Institution

    datum = FuzzyDateParserField(blank=True)
    status = models.CharField(choices=CHOICES_STATUS, default="Förderstatus unbekannt")

    @classmethod
    def name(cls) -> str:
        return "stellt Antrag an"

    @classmethod
    def reverse_name(cls) -> str:
        return "bekommt Antrag von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("stellt Antrag an")
        verbose_name_plural = _("stellt Antrag an")


class EhepartnerVon(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Person

    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "Ehepartner von"

    @classmethod
    def reverse_name(cls) -> str:
        return "Ehepartner von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Ehepartner von")
        verbose_name_plural = _("Ehepartner von")


class FamilienmitgliedVon(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Person

    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "Familienmitglied von"

    @classmethod
    def reverse_name(cls) -> str:
        return "Familienmitglied von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Familienmitglied von")
        verbose_name_plural = _("Familienmitglied von")


class KindVon(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Person

    @classmethod
    def name(cls) -> str:
        return "Kind von"

    @classmethod
    def reverse_name(cls) -> str:
        return "Elternteil von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Kind von")
        verbose_name_plural = _("Kind von")


class FreundVon(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Person

    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "Freund von"

    @classmethod
    def reverse_name(cls) -> str:
        return "Freund von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Freund von")
        verbose_name_plural = _("Freund von")


class LehrerVon(Relation, VersionMixin, LegacyFieldsMixin):
    CHOICES_LEHRER = [
        ("Doktorvater/mutter", "Doktorvater/mutter"),
        ("LehrerIn", "LehrerIn"),
    ]
    subj_model = Person
    obj_model = Person
    art = models.CharField(choices=CHOICES_LEHRER, blank=True)
    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "Lehrer von"

    @classmethod
    def reverse_name(cls) -> str:
        return "Schüler von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Lehrer von")
        verbose_name_plural = _("Lehrer von")


class GeborenIn(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Ort

    @classmethod
    def name(cls) -> str:
        return "geboren in"

    @classmethod
    def reverse_name(cls) -> str:
        return "Geburtsort von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("geboren in")
        verbose_name_plural = _("geboren in")


class GestorbenIn(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Ort

    @classmethod
    def name(cls) -> str:
        return "gestorben in"

    @classmethod
    def reverse_name(cls) -> str:
        return "Sterbeort von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("gestorben in")
        verbose_name_plural = _("gestorben in")


class EhrentitelVon(Relation, VersionMixin, LegacyFieldsMixin):
    CHOICES_EHRENTITEL = [("Ehrenbürger(in)", "Ehrenbürger(in)")]
    subj_model = Person
    obj_model = Ort

    titel = models.CharField(
        choices=CHOICES_EHRENTITEL, default="Ehrenbürger(in)", max_length=150
    )
    datum = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "Ehrentitel von"

    @classmethod
    def reverse_name(cls) -> str:
        return "verleit Ehrentitel an"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Ehrentitel von")
        verbose_name_plural = _("Ehrentitel von")


class WissenschaftsaustauschIn(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Ort

    beginn = FuzzyDateParserField(blank=True)
    ende = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "nimmt an Wissenschaftsaustausch teil in"

    @classmethod
    def reverse_name(cls) -> str:
        return "Ziel eines Wissenschaftsaustausches von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Wissenschaftsaustausch in")
        verbose_name_plural = _("Wissenschaftsaustausch in")


class AutorVon(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Werk

    @classmethod
    def name(cls) -> str:
        return "verfasst"

    @classmethod
    def reverse_name(cls) -> str:
        return "verfasst von"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("AutorIn von")
        verbose_name_plural = _("AutorIn von")


class ErwaehntIn(Relation, VersionMixin, LegacyFieldsMixin):
    TYP_CHOICES = (("erwähnt", "erwähnt"), ("behandelt", "behandelt"))
    subj_model = Person
    obj_model = Werk
    typ = models.CharField(
        max_length=100,
        choices=TYP_CHOICES,
        default="erwähnt",
        blank=True,
        help_text="Art der Erwähnung",
    )

    @classmethod
    def name(cls) -> str:
        return "erwähnt in"

    @classmethod
    def reverse_name(cls) -> str:
        return "erwähnt"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("erwähnt in")
        verbose_name_plural = _("erwähnt in")


class FindetStattIn(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Ereignis
    obj_model = Ort

    @classmethod
    def name(cls) -> str:
        return "findet statt in"

    @classmethod
    def reverse_name(cls) -> str:
        return "veranstaltet"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("findet statt in")
        verbose_name_plural = _("findet statt in")


class GelegenInOrt(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Ort
    obj_model = Ort

    @classmethod
    def name(cls) -> str:
        return "gelegen in"

    @classmethod
    def reverse_name(cls) -> str:
        return "schliesst ein"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("gelegen in Ort")
        verbose_name_plural = _("gelegen in Ort")


class HaeltRedeBei(Relation, VersionMixin, LegacyFieldsMixin):
    subj_model = Person
    obj_model = Ereignis

    titel = models.CharField(blank=True, max_length=400)
    datum = FuzzyDateParserField(blank=True)

    @classmethod
    def name(cls) -> str:
        return "hält Rede bei"

    @classmethod
    def reverse_name(cls) -> str:
        return "Redner"

    class Meta(LegacyFieldsMixin.Meta):
        verbose_name = _("Hält Rede bei")
        verbose_name_plural = _("Redner")
