import django_tables2 as tables


class SearchResultTable(tables.Table):
    name = tables.TemplateColumn(
        template_code='<a class="text-oeaw-blau semi-bold" href="/person/{{record.pk}}">{{record.surname}}, {{record.forename}}</a>',
        verbose_name="Name",
        attrs={
            "a": {"class": ".text-oeaw-blau semi-bold"},
            "th": {"style": "min-width: 20%;"},
        },
        order_by=("surname", "forename"),
    )

    birth_date = tables.Column(
        accessor="date_of_birth",
        verbose_name="geboren",
        attrs={"td": {"class": "no-wrap"}},
        order_by="date_of_birth_date_sort",
    )

    death_date = tables.Column(
        accessor="date_of_death",
        verbose_name="gestorben",
        attrs={"td": {"class": "no-wrap"}},
        order_by="date_of_death_date_sort",
    )

    mitgliedschaft = tables.Column(
        accessor="memberships",
        verbose_name="Mitgliedschaft",
        attrs={"td": {"class": "no-wrap"}},
    )
    klasse = tables.Column(
        accessor="klasse",
        verbose_name="Klasse",
        attrs={"td": {"class": "no-wrap"}},
    )

    def render_profession(self, value):
        separator = ", "
        return separator.join([str(item) for item in value.all()])

    def render_mitgliedschaft(self, value):
        separator = ", "
        return separator.join(value)

    class Meta:
        fields = (
            "name",
            "birth_date",
            "death_date",
            "mitgliedschaft",
            "klasse",
        )
        attrs = {"class": "table table-hover custom-table bg-mine", "thead": {}}
        empty_text = "Keine Ergebnisse"


class SearchResultInstitutionTable(tables.Table):
    name = tables.TemplateColumn(
        template_code='<a class="text-oeaw-blau semi-bold" href="/institution/{{record.pk}}"><span title="{{record.label}}">{{record.label}}</span></a>',
        verbose_name="Name",
        order_by=("label"),
        attrs={"th": {"style": "width: 50%;"}},
    )

    art = tables.Column(
        accessor="typ",
        verbose_name="Art",
        attrs={"td": {"class": "no-wrap"}},
    )

    beginn = tables.Column(
        accessor="beginn",
        verbose_name="Gründung",
        attrs={"td": {"class": "no-wrap"}},
        order_by="beginn_date_sort",
    )

    ende = tables.Column(
        accessor="ende",
        verbose_name="Auflösung",
        attrs={"td": {"class": "no-wrap"}},
        order_by="ende_date_sort",
    )

    def render_profession(self, value):
        separator = ", "
        return separator.join([str(item) for item in value.all()])

    def render_mitgliedschaft(self, value):
        separator = ", "
        return separator.join(value)

    class Meta:
        fields = ("name", "art", "beginn", "ende")
        attrs = {"class": "table table-hover custom-table bg-mine"}
        # template_name = "mine_frontend/custom_results_table.html"
        # row_attrs = {"data-member": lambda record: record.academy_member}
        empty_text = "Keine Ergebnisse"
