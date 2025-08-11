import csv
import json
import logging
import os
from datetime import datetime

import django
from apis_core.apis_metainfo.models import RootObject
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apis_import.utils import BASE_URL, api_request, get_vocab

django.setup()

from apis_ontology.models import Bild, Person  # noqa: E402

# BASE_URL = os.getenv("APIS_BASE_URL", "https://mine.acdh-ch-dev.oeaw.ac.at")
logger = logging.getLogger("import_person")


def process_relations(
    pers_id: int, voc_file: dict, relations: list[dict]
) -> list[dict]:
    rel_objects = []
    for rel in relations:
        logger.info(f"Fetch ing {rel} relations for person ID {pers_id}")
        rel_data = api_request(rel["url"], logger)
        vocab = get_vocab(rel_data["relation_type"]["url"], logger)
        rel_data["relation_type_resolved"] = vocab
        rel_objects.append(rel_data)

    for idx, rel in enumerate(rel_objects):
        if str(rel["relation_type"]["id"]) in voc_file:
            new_class = voc_file[str(rel["relation_type"]["id"])]["new_class"]
            if not new_class:
                logger.error(
                    f"New class not defined for relation type {rel['relation_type']['id']}, former {voc_file[str(rel['relation_type']['id'])]['new_class']}"
                )
                continue
            try:
                rel_class = ContentType.objects.get(
                    model=new_class.lower(), app_label="apis_ontology"
                ).model_class()
            except ContentType.DoesNotExist:
                logger.error(f"Model {new_class} not found")
                continue
            try:
                rel_class.create_from_legacy_data(rel, logger)
            except Exception as e:
                logger.error(f"Error creating {rel_class} from legacy data: {e}")
        else:
            logger.error(f"Relation type {rel['relation_type']['id']} not found")
    return rel_objects


def import_person(id: int, voc_file: dict) -> Person:
    # Get person data
    logger.info(f"Fetching person data for ID {id}")
    pers_url = f"{BASE_URL}/apis/api/entities/person/{id}/"
    pers_data = api_request(pers_url, logger)
    person = Person.create_from_legacy_data(pers_data, logger)
    process_relations(pers_id=id, voc_file=voc_file, relations=pers_data["relations"])
    return person


class Command(BaseCommand):
    help = "Import a person from the APIS API by ID"

    def add_arguments(self, parser):
        parser.add_argument(
            "person_query",
            type=str,
            help='Query for persons to import. Can be a simple ID or a JSON string with query parameters (e.g., \'{"id": 123, "name": "John"}\')',
        )
        parser.add_argument(
            "--log-file",
            dest="log_file",
            default="import_person.log",
            help="Path to the log file. If not provided, logging to file will be disabled.",
        )
        parser.add_argument(
            "--voc-file",
            dest="voc_file",
            default="prel_csv_relations/combined_relations.csv",
            help="location of the vocabulary matching file",
        )
        parser.add_argument(
            "--labels-file",
            dest="labels_file",
            default="resources/labels_mine_export_20250807.csv",
            help="location of the labels matching file",
        )
        parser.add_argument(
            "--log-level",
            dest="log_level",
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Set the logging level (default: INFO)",
        )

    def setup_logging(self, log_file=None, log_level="INFO"):
        """Set up logging to file and console."""
        # Create logger
        logger = logging.getLogger("import_person")
        logger.setLevel(getattr(logging, log_level))
        logger.handlers = []  # Clear any existing handlers

        # Create formatter
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Create file handler if log_file is provided
        if log_file:
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def handle(self, *args, **options):
        person_query = options["person_query"]
        log_file = options.get("log_file")
        log_level = options.get("log_level", "INFO")
        voc_file = options.get("voc_file")
        labels_file = options.get("labels_file")

        # Parse person_query - could be a simple ID or JSON
        query_params = json.loads(person_query)
        with open(voc_file, newline="") as inp:
            voc_file = csv.DictReader(inp, delimiter=",", quotechar='"')
            voc_file = {x["id"]: x for x in voc_file}

        # Set up logging
        global logger
        logger = self.setup_logging(log_file, log_level)
        pers_list = api_request(
            f"{BASE_URL}/apis/api/entities/person", logger, params=query_params
        )
        logger.info(
            f"Starting import of persons with query {query_params}, found {pers_list['count']} persons"
        )
        while pers_list:
            for pers in pers_list["results"]:
                try:
                    person_id = pers["id"]
                    logger.info(f"Starting import of person with ID {person_id}")
                    start_time = datetime.now()

                    person = import_person(person_id, voc_file)

                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    success_message = f"Successfully imported person: {person} (took {duration:.2f} seconds)"

                    logger.info(success_message)
                    self.stdout.write(self.style.SUCCESS(success_message))

                except CommandError as e:
                    # CommandError is already formatted properly, just pass it through
                    logger.error(str(e), exc_info=True)
                    raise e

                except Exception as e:
                    error_message = f"Error importing person with ID {person_id}: {e}"
                    logger.error(error_message, exc_info=True)
                    raise CommandError(error_message)
            if pers_list["next"] is not None:
                logger.info(f"Fetching next page of persons: {pers_list['next']}")
                pers_list = api_request(pers_list["next"], logger)
            else:
                logger.info("No more pages to fetch")
                pers_list = None

        with open(labels_file, newline="") as inp:
            logger.info(f"Reading labels from file: {labels_file}")
            labels_res = csv.DictReader(inp, delimiter=",", quotechar='"')
            for row in labels_res:
                old_id = row["temp_entity_id"]
                obj = RootObject.objects_inheritance.filter(
                    Q(ereignis__old_id=old_id)
                    | Q(person__old_id=old_id)
                    | Q(institution__old_id=old_id)
                    | Q(ort__old_id=old_id)
                    | Q(preis__old_id=old_id)
                    | Q(werk__old_id=old_id)
                ).select_subclasses()
                if not obj.exists():
                    logger.warning(
                        f"Object with old_id {old_id} not found, skipping label"
                    )
                    continue
                obj = obj.first()
                if row["name"] in ["Wikicommons Image", "filename OEAW Archiv"]:
                    Bild.create_from_legacy_data(obj, row, labels_res)
                else:
                    obj.add_alternative_label(row)
