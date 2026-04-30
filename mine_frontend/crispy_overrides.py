from crispy_forms.bootstrap import AccordionGroup
from django.forms.widgets import CheckboxSelectMultiple


class AccordionGroupTooltip(AccordionGroup):
    def __init__(
        self,
        name,
        *fields,
        css_id=None,
        css_class=None,
        template="mine_frontend/crispy_layouts/accordion_group.html",
        active=None,
        tooltip=None,
        **kwargs,
    ):
        super().__init__(
            name,
            *fields,
            css_id=css_id,
            css_class=css_class,
            template=template,
            active=active,
            **kwargs,
        )
        self.tooltip = tooltip


class HtmlCheckboxSelectMultiple(CheckboxSelectMultiple):
    option_template_name = (
        "mine_frontend/crispy_layouts/forms_checkbox_option_html.html"
    )
