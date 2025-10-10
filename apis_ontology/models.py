import csv
import os
import re
from copy import deepcopy
from functools import cache
from typing import Any
from urllib.parse import urlencode

from apis_core.apis_entities.abc import E21_Person, E53_Place, E74_Group
from apis_core.apis_entities.models import AbstractEntity
from apis_core.generic.abc import GenericModel
from apis_core.history.models import VersionMixin
from apis_core.relations.models import Relation
from apis_core.uris.models import Uri
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.utils import IntegrityError
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_interval.fields import FuzzyDateParserField
from django_json_editor_field.fields import JSONEditorField

from apis_import.utils import BASE_URL, api_request


def map_dicts(map: list, data: dict) -> dict:
    res = {}
    for d in map:
        if d[0] in data.keys() and d[1] != d[0]:
            if data[d[0]] and d[1] is not None:
                data[d[1]] = deepcopy(data[d[0]])
                del data[d[0]]
            elif data[d[0]] and d[1] is None:
                del data[d[0]]
        elif "__" in d[0]:
            spl = d[0].split("__")
            if spl[1] in data[spl[0]].keys():
                data[d[1]] = data[spl[0]][spl[1]]
    for k in data.keys():
        if k in [x[1] for x in map]:
            res[k] = data[k]
    return res


def clean_fields(cls, data):
    """replace None values with empty strings for CharFields and TextFields"""
    fields = [
        field.name
        for field in cls._meta.concrete_fields
        if isinstance(field, models.CharField) or isinstance(field, models.TextField)
    ]
    for k, v in data.items():
        if v is None and k in fields:
            data[k] = ""
    return data


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

    def add_alternative_label(self, row):
        alternative_namen = self.alternative_namen or []
        alternative_namen.append(
            {
                "name": row["label"],
                "art": row["name"],
                "sprache": row["isoCode_639_3"],
                "beginn": row["start_date_written"],
                "ende": row["end_date_written"],
            }
        )
        self.alternative_namen = alternative_namen
        self.save()  # Don't forget to save!


class LegacyFieldsMixin(models.Model):
    notes = models.TextField(blank=True)
    references = models.TextField(blank=True)
    old_id = models.IntegerField(blank=True, null=True, unique=True, editable=False)

    class Meta:
        abstract = True


class BaseLegacyImport(models.Model):
    MAP_FIELDS_OLD = [
        ("id", "old_id"),
        ("notes", "notes"),
        ("references", "references"),
    ]

    class Meta:
        abstract = True

    @classmethod
    def create_from_legacy_data(cls, data: dict[str, Any], logger):
        data_mapped = map_dicts(cls.MAP_FIELDS_OLD, data)
        data_mapped = clean_fields(cls, data_mapped)
        res = cls(**data_mapped)
        res.save()
        if "sameAs" in data:
            for u in data["sameAs"]:
                try:
                    Uri.objects.create(uri=u, content_object=res)
                except IntegrityError:
                    logger.warning(f"URI {u} already exists, cant create for {res}")
        res.save()
        return res

    @classmethod
    def get_or_create_from_legacy_id(cls, legacy_id, logger, use_filter=False):
        obj = cls.objects.filter(old_id=legacy_id)
        if obj.exists():
            return obj.first()
        else:
            params_str = ""
            if use_filter:
                params = {"id": legacy_id}
                params_str = "?" + urlencode(params)
                legacy_id = ""

            if isinstance(cls.LEGACY_DATA_ROUTE, str):
                dr = [cls.LEGACY_DATA_ROUTE]
            elif isinstance(cls.LEGACY_DATA_ROUTE, list):
                dr = cls.LEGACY_DATA_ROUTE
            else:
                raise ValueError("LEGACY_DATA_ROUTE must be a string or a list")
            for route in dr:
                try:
                    data = api_request(
                        f"{BASE_URL}/apis/api/{route}/{legacy_id}" + params_str,
                        logger,
                    )
                except Exception as e:
                    logger.error(f"Error fetching data from {route}: {e}")
                    continue
                if "results" in data and len(data["results"]) > 0:
                    return cls.create_from_legacy_data(data["results"][0], logger)
                return cls.create_from_legacy_data(data, logger)


class LegacyImportDates(BaseLegacyImport):
    MAP_FIELDS_OLD = BaseLegacyImport.MAP_FIELDS_OLD + [
        ("start_date_written", "beginn"),
        ("end_date_written", "ende"),
    ]

    class Meta:
        abstract = True


class LegacyImportSingleDate(BaseLegacyImport):
    MAP_FIELDS_OLD = BaseLegacyImport.MAP_FIELDS_OLD + [
        ("start_date_written", "datum"),
    ]

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


class Beruf(GenericModel, BaseLegacyImport, models.Model):
    LEGACY_DATA_ROUTE = "vocabularies/professiontype"
    MAP_FIELDS_OLD = [
        ("old_id", "old_id"),
        ("name", "name"),
    ]
    old_id = models.IntegerField(blank=True, null=True, editable=False)
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

    @classmethod
    def create_from_legacy_data(cls, obj, data, data_full):
        data_fin = {
            "pfad": data["label"].replace("http://", "https://"),
            "content_object": obj,
            "art": "Wikimedia",
        }
        if data["name"] == "filename OEAW Archiv":
            data_fin["art"] = "OEAW Archiv"
            for d2 in data_full:
                if (
                    d2["temp_entity_id"] == data["temp_entity_id"]
                    and d2["name"] == "photocredit OEAW Archiv"
                ):
                    data_fin["credit"] = d2["label"]
        cls(**data_fin).save()


class Fach(AbstractEntity, VersionMixin, BaseLegacyImport):
    """akademische Fachrichtung"""

    MAP_FIELDS_OLD = BaseLegacyImport.MAP_FIELDS_OLD + [
        ("name", "name"),
    ]
    LEGACY_DATA_ROUTE = "vocabularies/personinstitutionrelation"

    old_id = models.IntegerField(blank=True, null=True, editable=False)
    name = models.CharField(max_length=400)
    oestat = models.CharField(max_length=400, blank=True, choices=get_oestat_choices)

    class Meta:
        verbose_name = _("Fachrichtung")
        verbose_name_plural = _("Fachrichtungen")

    def __str__(self):
        return str(self.name)

    @classmethod
    def create_from_legacy_data(cls, data, logger):
        res = cls.objects.filter(name=data["name"])
        if res.exists():
            logger.info(f"Found existing Fachrichtung with name {data['name']}")
            return res.first()
        return super().create_from_legacy_data(data, logger)


class Ereignis(
    VersionMixin,
    AbstractEntity,
    NameMixin,
    LegacyFieldsMixin,
    LegacyImportSingleDate,
    AlternativeNameMixin,
):
    """haupsächlich Sitzungen und Wahlen"""

    MAP_FIELDS_OLD = LegacyImportSingleDate.MAP_FIELDS_OLD + [
        ("name", "name"),
        ("kind__label", "typ"),
    ]
    LEGACY_DATA_ROUTE = "entities/event"

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

    @classmethod
    def create_election_from_year(cls, year, logger):
        data = api_request(
            f"{BASE_URL}/apis/api/entities/event/?name=f'Wahlsitzung der Gesamtakademie {year}'",
            logger=logger,
        )
        if not data["results"]:
            logger.warning(f"No event found for year {year}")
            return None
        return cls.create_from_legacy_data(data["results"][0], logger)

    @classmethod
    def get_or_create_election_from_year(cls, year, logger):
        try:
            return cls.objects.get(name=f"Wahlsitzung der Gesamtakademie {year}")
        except cls.DoesNotExist:
            return cls.create_election_from_year(year, logger)


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
    LegacyImportDates,
    AlternativeNameMixin,
):
    """Auschreibung eines Preises oder Preisaufgabe"""

    LEGACY_DATA_ROUTE = ["entities/event", "entities/institution"]
    MAP_FIELDS_OLD = LegacyImportDates.MAP_FIELDS_OLD + [
        ("name", "name"),
    ]
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


class Religion(
    VersionMixin, AbstractEntity, NameMixin, LegacyFieldsMixin, BaseLegacyImport
):
    """Religionsgemeinschaft"""

    LEGACY_DATA_ROUTE = "entities/institution"

    class Meta(VersionMixin.Meta, AbstractEntity.Meta, NameMixin.Meta):
        verbose_name = _("Religionsgemeinschaft")
        verbose_name_plural = _("Religionsgemeinschaften")


class Werk(
    VersionMixin,
    AbstractEntity,
    LegacyFieldsMixin,
    BaseLegacyImport,
    AlternativeNameMixin,
):
    LEGACY_DATA_ROUTE = "entities/work"
    MAP_FIELDS_OLD = BaseLegacyImport.MAP_FIELDS_OLD + [
        ("name", "titel"),
    ]
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

    @classmethod
    def create_from_legacy_data(cls, data, logger):
        obj = super().create_from_legacy_data(data, logger)
        if "nekrolog" in str(obj.titel).lower():
            obj.typ = "Nekrolog"
            obj.save()
        return obj


class Person(
    VersionMixin,
    E21_Person,
    AbstractEntity,
    LegacyFieldsMixin,
    BaseLegacyImport,
    AlternativeNameMixin,
):
    LEGACY_DATA_ROUTE = "entities/person"
    MAP_FIELDS_OLD = BaseLegacyImport.MAP_FIELDS_OLD + [
        ("start_date_written", "date_of_birth"),
        ("end_date_written", "date_of_death"),
        ("name", "surname"),
        ("first_name", "forename"),
        ("gender", "gender"),
    ]
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

    @classmethod
    def create_from_legacy_data(cls, data, logger):
        data_mapped = map_dicts(cls.MAP_FIELDS_OLD, data)
        data_mapped = clean_fields(cls, data_mapped)
        if data_mapped["gender"] == "male":
            data_mapped["gender"] = "männlich"
        elif data_mapped["gender"] == "female":
            data_mapped["gender"] = "weiblich"
        profs = []
        for prof in data["profession"]:
            p = Beruf.get_or_create_from_legacy_id(prof["id"], logger)
            profs.append(p)

        for rel in data["relations"]:
            if (
                ("(gewählt und" in rel["label"])
                or ("(Gewählt)" in rel["label"] or "(ernannt)" in rel["label"].lower())
                and (("KLASSE" in rel["label"]) or ("GESAMTAKADEMIE" in rel["label"]))
            ):
                logger.info("Person is member of the academy")
                data_mapped["mitglied"] = True
            if "PHILOSOPHISCH-HISTORISCHE KLASSE" in rel["label"]:
                logger.info("Person is member of the philosophical-historical class")
                if "klasse" in data_mapped:
                    if data_mapped["klasse"] != "GESAMTAKADEMIE":
                        logger.warning(
                            "Person is already member of another class, skipping"
                        )
                        continue
                data_mapped["klasse"] = "Philosophisch-Historische Klasse"
            if "MATHEMATISCH-NATURWISSENSCHAFTLICHE KLASSE" in rel["label"]:
                logger.info(
                    "Person is member of the mathematical-natural-sciences class"
                )
                if "klasse" in data_mapped:
                    if data_mapped["klasse"] != "GESAMTAKADEMIE":
                        logger.warning(
                            "Person is already member of another class, skipping"
                        )
                        continue
                data_mapped["klasse"] = "Mathematisch-Naturwissenschaftliche Klasse"
            if "GESAMTAKADEMIE" in rel["label"] and "klasse" not in data_mapped:
                logger.info("Person has role in GESAMTAKADEMIE")
                data_mapped["klasse"] = "GESAMTAKADEMIE"
        pers = cls(**data_mapped)
        pers.save()
        pers.beruf.add(*profs)
        if "sameAs" in data:
            for u in data["sameAs"]:
                try:
                    Uri.objects.create(uri=u, content_object=pers)
                except IntegrityError:
                    logger.warning(f"URI {u} already exists, cant create for {pers}")
        pers.save()
        return pers


class Ort(
    VersionMixin,
    E53_Place,
    AbstractEntity,
    LegacyFieldsMixin,
    BaseLegacyImport,
    AlternativeNameMixin,
):
    MAP_FIELDS_OLD = BaseLegacyImport.MAP_FIELDS_OLD + [
        ("name", "label"),
        ("lat", "latitude"),
        ("lng", "longitude"),
    ]
    LEGACY_DATA_ROUTE = "entities/place"

    class Meta(AbstractEntity.Meta, E53_Place.Meta, VersionMixin.Meta):
        verbose_name = "Ort"
        verbose_name_plural = "Orte"


class Institution(
    VersionMixin,
    E74_Group,
    AbstractEntity,
    LegacyFieldsMixin,
    LegacyImportDates,
    AlternativeNameMixin,
):
    LEGACY_DATA_ROUTE = "entities/institution"
    MAP_FIELDS_OLD = LegacyImportDates.MAP_FIELDS_OLD + [
        ("name", "label"),
    ]
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

    @classmethod
    def get_or_create_from_legacy_id(cls, legacy_id, logger, use_filter=True):
        return super().get_or_create_from_legacy_id(legacy_id, logger, use_filter)

    @classmethod
    def create_from_legacy_data(cls, data, logger):
        data_mapped = map_dicts(cls.MAP_FIELDS_OLD, data)
        data_mapped = clean_fields(cls, data_mapped)
        if "kind" in data and data["kind"] is not None:
            label_lst = data["kind"]["label"].split(" >> ")
            if label_lst[0] == "Akademie":
                data_mapped["akademie_institution"] = True
                data_mapped["typ"] = label_lst[-1]
            elif len(label_lst) == 1:
                data_mapped["typ"] = label_lst[0]
        res = cls(**data_mapped)
        res.save()
        if "sameAs" in data:
            for u in data["sameAs"]:
                try:
                    Uri.objects.create(uri=u, content_object=res)
                except IntegrityError:
                    logger.warning(f"URI {u} already exists, cant create for {res}")
        res.save()
        return res


class OeawMitgliedschaft(Relation, VersionMixin, LegacyFieldsMixin, BaseLegacyImport):
    """class for the membership in the OeAW"""

    BEGIN_TYP_CHOICES = [
        ("gewählt", "gewählt"),
        ("bestätigt", "bestätigt"),
        ("gewählt und bestätigt", "gewählt und bestätigt"),
        ("gewählt und ernannt", "gewählt und ernannt"),
        ("gewählt, nicht bestätigt", "gewählt, nicht bestätigt"),
        ("ernannt", "ernannt"),
        ("umgewidmet", "umgewidmet"),
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

    @classmethod
    def _create_nominated_by(cls, data, logger):
        """fetch nominators from legacy API and create Persons if they don't exist"""
        ids_check = [
            3141
        ]  # TODO: check if this ID is enough, there is also 3061, which is for not elected
        res = []
        year = data["beginn"].split(".")[-1]
        person_id = data["related_person"]["id"]
        try:
            rel_data = api_request(
                f"{BASE_URL}/apis/api/relations/personperson/?related_personA={person_id}&start_date__year={year}",
                logger,
            )
        except Exception as e:
            logger.error(f"Error fetching nominators: {e}")
            return None
        for rel in rel_data["results"]:
            if rel["relation_type"]["parent_id"] in ids_check:
                nominator_id = rel["related_personB"]["id"]
                nominator = Person.get_or_create_from_legacy_id(nominator_id, logger)
                res.append(nominator)
        return res

    @classmethod
    def create_from_legacy_data(cls, data, logger):
        MAP_FIELDS_OLD = [
            ("id", "old_id"),
            ("start_date_written", "beginn"),
            ("end_date_written", "ende"),
            ("references", "references"),
            ("notes", "notes"),
        ]
        data_mapped = map_dicts(MAP_FIELDS_OLD, data)
        data_mapped = clean_fields(cls, data_mapped)

        memb = re.search(r"\((.*?)\)", data["relation_type_resolved"][1]["name"])
        if memb:
            data_mapped["mitgliedschaft"] = memb.group(1)
        else:
            data_mapped["mitgliedschaft"] = "unknown"
        data_mapped["beginn_typ"] = (
            data["relation_type_resolved"][-1]["name"].strip().lower()
        )
        pers = Person.get_or_create_from_legacy_id(data["related_person"]["id"], logger)
        data_mapped["subj"] = pers
        inst = Institution.get_or_create_from_legacy_id(
            data["related_institution"]["id"], logger
        )
        data_mapped["obj"] = inst
        rel = cls(**data_mapped)
        rel.save()
        if "gewählt" in data_mapped["beginn_typ"].lower():
            nominees = cls._create_nominated_by(data, logger)
            rel.vorgeschlagen_von.add(*nominees)
            election = Ereignis.get_or_create_election_from_year(
                rel.beginn_date_sort.year, logger
            )
            rel.wahlsitzung = election
        rel.save()
        return rel


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

    @classmethod
    def _create_nominated_by(cls, data, logger):
        """fetch nominators from legacy API and create Persons if they don't exist"""
        ids_check = [3061]  # parent ids of "vorgeschlagen von"
        res = []
        year = data["datum"].split(".")[-1]
        person_id = data["related_person"]["id"]
        try:
            rel_data = api_request(
                f"{BASE_URL}/apis/api/relations/personperson/?related_personA={person_id}&start_date__year={year}",
                logger,
            )
        except Exception as e:
            logger.error(f"Error fetching nominators: {e}")
            return None
        for rel in rel_data["results"]:
            if rel["relation_type"]["parent_id"] in ids_check:
                nominator_id = rel["related_personB"]["id"]
                nominator = Person.get_or_create_from_legacy_id(nominator_id, logger)
                res.append(nominator)
        return res

    @classmethod
    def _get_klasse(cls, data, logger):
        kls = api_request(
            f"{BASE_URL}/apis/api/relations/personinstitution/?related_person={data['related_person']['id']}&related_institution__in=2,3",
            logger,
        )
        ids = list(set([inst["related_institution"]["id"] for inst in kls["results"]]))
        if len(ids) > 1:
            logger.warning("found more than one class for not elected person")
        elif len(ids) == 0:
            logger.warning("no class found for not elected person")
            return None
        return ids

    @classmethod
    def _match_membership(cls, relation_type_resolved):
        full_str = (
            relation_type_resolved[-1]["name"]
            .split("(")[-1]
            .replace(".)", "")
            .replace(". ", "")
        )
        return full_str

    @classmethod
    def create_from_legacy_data(cls, data, logger):
        """Create a new instance from legacy data"""
        MAP_FIELDS_OLD = [
            ("id", "old_id"),
            ("start_date_written", "datum"),
            ("references", "references"),
            ("notes", "notes"),
        ]
        data_mapped = map_dicts(MAP_FIELDS_OLD, data)
        data_mapped = clean_fields(cls, data_mapped)
        klasse = cls._get_klasse(data, logger)
        if klasse:
            data_mapped["obj"] = Institution.get_or_create_from_legacy_id(
                klasse[0], logger
            )
        else:
            logger.error(
                f"cant find klasse for not elected person {data['id']}, skipping"
            )
            return None
        data_mapped["subj"] = Person.get_or_create_from_legacy_id(
            data["related_person"]["id"], logger
        )
        election = Ereignis.get_or_create_from_legacy_id(
            data["related_event"]["id"], logger
        )
        data_mapped["wahlsitzung"] = election
        data_mapped["mitgliedschaft"] = cls._match_membership(
            data["relation_type_resolved"]
        )
        rel = cls(**data_mapped)
        rel.save()
        nominees = cls._create_nominated_by(data, logger)
        rel.vorgeschlagen_von.add(*nominees)
        rel.save()
        return rel

    def __str__(self):
        return f"{self.wahlsitzung} ({self.datum})"


def get_position_choices() -> list[tuple[str, str]]:
    with open(
        f"{os.path.dirname(__file__)}/../resources/position_inst_relations.csv",
        newline="",
    ) as inp:
        reader = csv.DictReader(inp, delimiter=",", quotechar='"')
        res = [(i["name"], i["name"]) for i in reader]
    return res


class RelLegacyDataBaseMixin(models.Model):
    MAP_FIELDS_OLD = [
        ("id", "old_id"),
        ("references", "references"),
        ("notes", "notes"),
    ]

    class Meta:
        abstract = True

    @classmethod
    def get_or_create_subj_obj(cls, kind: str, old_id: int, logger):
        entity_class = getattr(cls, f"{kind}_model")
        entity = entity_class.get_or_create_from_legacy_id(old_id, logger)
        return entity

    @classmethod
    def determine_subj_obj(cls, kind, data):
        if isinstance(getattr(cls, kind), str):
            return getattr(cls, kind)
        for k in getattr(cls, kind):
            if k in data:
                return k

    @classmethod
    def create_from_legacy_data(cls, data: dict[str, Any], logger):
        data_mapped = map_dicts(cls.MAP_FIELDS_OLD, data)
        data_mapped = clean_fields(cls, data_mapped)

        subj = cls.get_or_create_subj_obj(
            "subj", data[cls.determine_subj_obj("SUBJ_ID_OLD", data)]["id"], logger
        )
        obj = cls.get_or_create_subj_obj(
            "obj", data[cls.determine_subj_obj("OBJ_ID_OLD", data)]["id"], logger
        )
        data_mapped["subj"] = subj
        data_mapped["obj"] = obj
        if cls.objects.filter(old_id=data_mapped["old_id"]).exists():
            logger.warning(
                f"Relation {cls.__name__} with old_id {data_mapped['old_id']} already exists"
            )
            return cls.objects.get(old_id=data_mapped["old_id"])
        res = cls(**data_mapped)
        res.save()
        return res


class RelLegacyDataDatesMixin(RelLegacyDataBaseMixin):
    MAP_FIELDS_OLD = RelLegacyDataBaseMixin.MAP_FIELDS_OLD + [
        ("start_date_written", "beginn"),
        ("end_date_written", "ende"),
    ]

    class Meta:
        abstract = True


class RelLegacyDataSingleDateMixin(RelLegacyDataBaseMixin):
    MAP_FIELDS_OLD = RelLegacyDataBaseMixin.MAP_FIELDS_OLD + [
        ("start_date_written", "datum"),
    ]

    class Meta:
        abstract = True


class PositionAn(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataDatesMixin):
    """Anstellung/Position in Institution"""

    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_institution"

    subj_model = Person
    obj_model = Institution
    position = models.CharField(blank=True, choices=get_position_choices)
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

    @classmethod
    def create_from_legacy_data(cls, data: dict[str, Any], logger) -> "PositionAn":
        rel = super().create_from_legacy_data(data, logger)
        voc = data["relation_type_resolved"]
        if len(voc) == 3:  # all the variations of professors with their "fach"
            check = False
            for term in ["doz.", "prof.", "ass.", "wissenschaftliche"]:
                if term in voc[1]["name"].lower():
                    check = True
                    break
            if check and len(voc) > 1:
                rel.position = voc[1]["name"]
                rel.fach = Fach.get_or_create_from_legacy_id(voc[2]["id"], logger)
            else:
                rel.position = voc[1]["name"]
        elif voc[0]["id"] in [102]:  # positions that need first element
            rel.position = voc[0]["name"]
        else:
            rel.position = voc[-1]["name"]
        rel.save()
        return rel


class AusbildungAn(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataDatesMixin):
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

    @classmethod
    def create_from_legacy_data(cls, data: dict[str, Any], logger) -> "AusbildungAn":
        rel = super().create_from_legacy_data(data, logger)
        voc = data["relation_type_resolved"]
        if voc[0]["id"] == 1385:
            rel.typ = "Habilitation"
            if len(voc) > 1:
                rel.fach = Fach.get_or_create_from_legacy_id(voc[-1]["id"], logger)
        elif voc[0]["id"] == 1386:
            rel.typ = "Promotion"
            if len(voc) > 1:
                rel.fach = Fach.get_or_create_from_legacy_id(voc[-1]["id"], logger)
        elif voc[0]["id"] == 176:
            rel.typ = "Schule"
        elif voc[0]["id"] == 1369:
            rel.typ = "Studium"
        elif voc[0]["id"] == 1371:
            rel.typ = "Studienaufenthalt"
        else:
            rel.typ = voc[-1]["name"]
            logger.warning(f"Unknown relation type {voc[0]['id']} for AusbildungAn")
        rel.save()
        return rel


class SchreibtAus(Relation, VersionMixin, LegacyFieldsMixin, LegacyImportSingleDate):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_institution"
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


class InstitutionHierarchie(
    Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataDatesMixin
):
    SUBJ_ID_OLD = "related_institutionA"
    OBJ_ID_OLD = "related_institutionB"
    MAP_FIELDS_OLD = RelLegacyDataDatesMixin.MAP_FIELDS_OLD + [
        ("relation_type__label", "relation")
    ]
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

    def __str__(self):
        return f"{self.subj} {self.relation} {self.obj}"

    @classmethod
    def create_from_legacy_data(cls, data: dict[str, Any], logger):
        rel = super().create_from_legacy_data(data, logger)
        choices = get_choices_inst_hierarchie_data()
        for d in choices:
            if d["name"] == rel.relation:
                rel.relation_reverse = d["name_reverse"]
            elif d["name_reverse"] == rel.relation:
                rel.relation = d["name"]
                rel.reverse_relation = d["name_reverse"]
                rel.subj, rel.obj = rel.obj, rel.subj
        rel.save()
        return rel


class WirdVergebenVon(
    Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataDatesMixin
):
    SUBJ_ID_OLD = "related_institutionA"
    OBJ_ID_OLD = "related_institutionB"
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


class WirdGestiftetVon(
    Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataSingleDateMixin
):
    SUBJ_ID_OLD = "related_institutionA"
    OBJ_ID_OLD = "related_institutionB"
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


class GelegenIn(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataBaseMixin):
    SUBJ_ID_OLD = "related_institution"
    OBJ_ID_OLD = "related_place"
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


class Gewinnt(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataSingleDateMixin):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = ["related_event", "related_institution"]
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


class Stiftet(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataSingleDateMixin):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_institution"
    subj_model = Person
    obj_model = Preis
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


class Mitglied(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataDatesMixin):
    """Mitgliedschaften in anderen Institution als der ÖAW"""

    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_institution"

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

    @classmethod
    def create_from_legacy_data(cls, data: dict[str, Any], logger) -> "Mitglied":
        rel = super().create_from_legacy_data(data, logger)
        voc = data["relation_type_resolved"]
        if len(voc) == 3:
            if "anwärter" in voc[1]["name"].lower():
                rel.art = f"{voc[1]['name']} {voc[2]['name']}".title()
            elif "förderndes mitglied" in voc[1]["name"].lower():
                rel.art = f"{voc[1]['name']} {voc[2]['name']}".title()
            elif "kommissionsmitgliedschaft" in voc[1]["name"].lower():
                rel.art = f"{voc[2]['name']} Kommission".title()
        else:
            rel.art = voc[-1]["name"].capitalize()
        rel.save()
        return rel


class AnhaengerVon(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataDatesMixin):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_institution"
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


class NimmtTeilAn(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataDatesMixin):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_event"
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


class EhrentitelVonInstitution(
    Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataSingleDateMixin
):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_institution"
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

    @classmethod
    def create_from_legacy_data(cls, data: dict[str, Any], logger):
        rel = super().create_from_legacy_data(data, logger)
        if "Ehrendoktorat" in data["relation_type"]["label"]:
            rel.titel = "Ehrendoktorat"
        rel.save()
        return rel


class LehntPreisAb(
    Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataSingleDateMixin
):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_institution"
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


class StelltAntragAn(
    Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataSingleDateMixin
):
    """verwendet für Förderanträge an Institutionen"""

    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_institution"

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

    @classmethod
    def create_from_legacy_data(cls, data: dict[str, Any], logger):
        voc = data["relation_type_resolved"]
        rel = super().create_from_legacy_data(data, logger)
        if len(voc) == 2:
            rel.status = voc[1]["name"]
        rel.save()
        return rel


class EhepartnerVon(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataDatesMixin):
    SUBJ_ID_OLD = "related_personA"
    OBJ_ID_OLD = "related_personB"
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


class FamilienmitgliedVon(
    Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataDatesMixin
):
    SUBJ_ID_OLD = "related_personA"
    OBJ_ID_OLD = "related_personB"
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


class KindVon(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataBaseMixin):
    SUBJ_ID_OLD = "related_personA"
    OBJ_ID_OLD = "related_personB"
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

    @classmethod
    def create_from_legacy_data(cls, data: dict[str, Any], logger):
        if data["relation_type"]["label"] == "ist Elternteil von":
            data["related_personA_"] = data.pop("related_personB")
            data["related_personB"] = data.pop("related_personA")
            data["related_personA"] = data.pop("related_personA_")
        return super().create_from_legacy_data(data, logger)


class FreundVon(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataBaseMixin):
    SUBJ_ID_OLD = "related_personA"
    OBJ_ID_OLD = "related_personB"
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


class LehrerVon(
    Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataDatesMixin
):  # TODO: Implement reverse_name method
    SUBJ_ID_OLD = "related_personA"
    OBJ_ID_OLD = "related_personB"
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


class GeborenIn(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataBaseMixin):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_place"
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


class GestorbenIn(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataBaseMixin):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_place"
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


class EhrentitelVon(
    Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataSingleDateMixin
):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_place"
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


class WissenschaftsaustauschIn(
    Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataDatesMixin
):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_place"
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


class AutorVon(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataBaseMixin):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_work"
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


class ErwaehntIn(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataBaseMixin):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_work"
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

    @classmethod
    def create_from_legacy_data(cls, data, logger):
        obj = super().create_from_legacy_data(data, logger)
        if "nekrolog" in str(obj.obj.titel).lower():
            obj.typ = "behandelt"
            obj.save()
        return obj


class FindetStattIn(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataBaseMixin):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_place"
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


class GelegenInOrt(Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataBaseMixin):
    SUBJ_ID_OLD = "related_placeA"
    OBJ_ID_OLD = "related_placeB"
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


class HaeltRedeBei(
    Relation, VersionMixin, LegacyFieldsMixin, RelLegacyDataSingleDateMixin
):
    SUBJ_ID_OLD = "related_person"
    OBJ_ID_OLD = "related_event"
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

    @classmethod
    def create_from_legacy_data(cls, data: dict[str, Any], logger):
        d_work = api_request(
            f"{BASE_URL}/apis/api/entities/work/{data['related_work']['id']}", logger
        )
        d_work["related_person"] = data["related_person"]
        for r in d_work["relations"]:
            if r["related_entity"]["type"] == "Event":
                d_work["related_event"] = r["related_entity"]
        return super().create_from_legacy_data(d_work, logger)
