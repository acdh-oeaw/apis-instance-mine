import django_tables2 as tables

from apis_ontology.models import Person


class SearchResultTable(tables.Table):
    name = tables.TemplateColumn(
        template_code='<a class="text-oeaw-blau semi-bold" href="/person/{{record.pk}}">{{record}}</a>',
        verbose_name="Name",
        attrs={"a": {"class": ".text-oeaw-blau semi-bold"}},
    )

    profession = tables.Column(accessor="beruf", verbose_name="Beruf")

    # birth_date = tables.DateColumn(
    #     accessor="date_of_birth",
    #     format="Y",
    #     verbose_name="geboren",
    #     attrs={"td": {"class": "no-wrap"}},
    # )

    # death_date = tables.DateColumn(
    #     accessor="date_of_death",
    #     format="Y",
    #     verbose_name="gestorben",
    #     attrs={"td": {"class": "no-wrap"}},
    # )
    birth_date = tables.Column(
        accessor="date_of_birth",
        verbose_name="geboren",
        attrs={"td": {"class": "no-wrap"}},
    )

    death_date = tables.Column(
        accessor="date_of_death",
        verbose_name="gestorben",
        attrs={"td": {"class": "no-wrap"}},
    )

    mitgliedschaft = tables.Column(
        accessor="memberships",
        verbose_name="Mitgliedschaft",
        attrs={"td": {"class": "no-wrap"}},
    )

    # birth_place = tables.Column(accessor="place_of_birth", verbose_name="geboren in")

    # death_place = tables.Column(accessor="place_of_death", verbose_name="gestorben in")

    def render_profession(self, value):
        separator = ", "
        return separator.join([str(item) for item in value.all()])

    def render_mitgliedschaft(self, value):
        separator = ", "
        return separator.join(value)

    class Meta:
        model = Person
        fields = (
            "name",
            "birth_date",
            "death_date",
            # "birth_place",
            "mitgliedschaft",
            "profession",
        )
        attrs = {"class": "table table-hover custom-table bg-mine", "thead": {}}
        # template_name = "theme/custom_table.html"
        # row_attrs = {"data-member": lambda record: record.academy_member}
        empty_text = "Keine Ergebnisse"
