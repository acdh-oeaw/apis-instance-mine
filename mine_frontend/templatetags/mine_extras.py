from apis_core.apis_metainfo.models import Uri
from django import template
from django.utils.html import mark_safe

register = template.Library()


@register.filter()
def mine_link(value):
    if hasattr(value, "mitglied"):
        if value.mitglied:
            return mark_safe(f'<a href="/person/{value.pk}">{value}</a>')
    if hasattr(value, "akademie_institution"):
        if value.akademie_institution:
            return mark_safe(f'<a href="/institution/{value.pk}">{value}</a>')
    gnd = Uri.objects.filter(uri__contains="d-nb.info", object_id=value.pk)
    if gnd.exists():
        return mark_safe(
            f'<a href="{gnd.first().uri}">{value}</a><i data-feather="external-link" style="width: 1.1em; height: 1.1em; padding-left: 0.2em; vertical-align: middle;"></i>'
        )
    return value


@register.filter
def zumals(value):
    match value:
        case "umgewidmet":
            return "zum"
    return "als"


@register.filter
def caseklasse(value):
    return value.replace("e K", "en K")


@register.filter
def class_name(instance):
    return instance._meta.verbose_name


@register.filter
def mine_date(value):
    if value.beginn_date_sort or value.ende_date_sort:
        if not value.ende_date_sort:
            if hasattr(value, "typ"):
                if value.typ == "Schule":
                    return f"(Abschluss {value.beginn_date_sort.strftime('%Y')})"
                elif value.typ in [
                    "Habilitation",
                    "Promotion",
                    "Titel nostrifiziert von",
                ]:
                    return f"({value.beginn_date_sort.strftime('%Y')})"
            return f"(ab {value.beginn_date_sort.strftime('%Y')})"
        elif not value.beginn_date_sort:
            return f"(bis {value.ende_date_sort.strftime('%Y')})"
        else:
            return f"({value.beginn_date_sort.strftime('%Y')} - {value.ende_date_sort.strftime('%Y')})"
    return ""


@register.filter
def fach(value):
    if hasattr(value, "fach"):
        if value.typ in ["Promotion", "Habilitation"] and value.fach:
            return f" in {value.fach}"
    return ""
