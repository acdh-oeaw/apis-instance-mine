from django.template import loader
from django.utils.safestring import mark_safe


def create_choices_with_tooltip(
    choices: list[tuple[str, str, str | None]],
) -> list[tuple[str, str]]:
    """converts the third part of a choices tuple to the info tooltip"""
    template = loader.get_template("mine_frontend/partials/tooltip_info.html")
    res = []
    for opt, label, *rest in choices:
        tooltip = rest[0] if rest else None
        if tooltip:
            tooltip_html = template.render({"text": tooltip})
            label = mark_safe(label + tooltip_html)
        res.append((opt, label))
    return res
