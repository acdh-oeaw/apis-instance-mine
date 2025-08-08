import django_tables2 as tables
from apis_core.generic.tables import CustomTemplateColumn
from apis_core.relations.tables import RelationsListTable


class BibsonomyColumn(CustomTemplateColumn):
    template_name = "columns/bibsonomy.html"


class AbstractEntityRelationsTable(RelationsListTable):
    beginn = tables.Column(accessor="beginn", order_by="beginn_date_sort")
    ende = tables.Column(accessor="ende", order_by="ende_date_sort")
    notes = tables.Column()
    # bibsonomy = BibsonomyColumn()

    class Meta(RelationsListTable.Meta):
        sequence = (
            ["beginn", "ende"]
            + list(RelationsListTable.Meta.sequence)[:-3]
            + ["notes"]
            + list(RelationsListTable.Meta.sequence)[-3:]
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.columns["notes"].column.attrs = {
            "td": {
                "style": "max-width:30vw; word-wrap:break-word; overflow-wrap:break-word; white-space:normal;"
            }
        }


class E21_PersonInstitutionRelationsTable(AbstractEntityRelationsTable):
    mitgliedschaft = tables.Column()
    fach = tables.Column(accessor="fach__name")

    class Meta(AbstractEntityRelationsTable.Meta):
        sequence = (
            list(AbstractEntityRelationsTable.Meta.sequence)[:3]
            + ["mitgliedschaft", "fach"]
            + list(AbstractEntityRelationsTable.Meta.sequence)[3:]
        )
