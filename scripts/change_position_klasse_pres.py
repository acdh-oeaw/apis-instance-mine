import logging

import django

django.setup()
from apis_ontology.models import Institution, PositionAn  # noqa: E402

# Create new positions "Präsident(in) Klasse" and "Vizepräsident(in) Klasse"

logger = logging.getLogger(__name__)


def run_migration():
    insts = Institution.objects.filter(
        label__in=[
            "PHILOSOPHISCH-HISTORISCHE KLASSE",
            "MATHEMATISCH-NATURWISSENSCHAFTLICHE KLASSE",
        ]
    ).values_list("id")
    pos = PositionAn.objects.filter(
        position__in=["Präsident(in)", "Vizepräsident(in)", "Sekretär(in)"],
        obj_object_id__in=insts,
    )
    logger.info(f"found {pos.count()} positions, changing now")
    for rel in pos:
        logger.info(f"changing {pos}")
        rel.position += " Klasse"
        rel.save()


if __name__ == "__main__":
    run_migration()
