from django.db.models import F, Func
from django.db.models.aggregates import Count
from django.db.models.query_utils import Q


class FacetedSearchMixin:
    """Mixin that provides faceted search and filtering for Django list views.

    Configuration attributes (set on the view class):

        facet_fields = {
            'param_name': {
                'label': 'Display Name',
                'field': 'model_field_name',
                'lookup': 'exact',           # optional, default 'exact'
                'type': 'choice' | 'array',  # 'choice' = regular field,
                                             # 'array'  = ArraySubquery / ArrayField
            },
        }

        filter_fields = {
            'key': {
                'label': 'Display Name',
                'param': 'query_param',       # optional, defaults to key
                'type': 'text' | 'choice' | 'array',

                # ---- lookups (AND-combined across fields) ----
                'lookups': [
                    ('icontains', 'field_a'),
                    ('icontains', 'field_b'),
                ],

                # ---- callable variant ----
                # Instead of (or in addition to) 'lookups',
                # supply a callable.  It receives:
                #   (queryset, config_dict, selected_values, request)
                # and must return a (possibly filtered) queryset.
                'filter_func': some_callable,

                # optional: used by template helpers to resolve IDs -> labels
                'model_resolve': 'person',
            },
        }
    """

    facet_fields = {}
    filter_fields = {}

    def get_facet_fields(self):
        return getattr(self, "facet_fields", {})

    def get_filter_fields(self):
        return getattr(self, "filter_fields", {})

    def get_base_queryset(self):
        """Override to provide the base queryset before any filtering."""
        return self.get_queryset()

    @staticmethod
    def _build_q(field, lookup, values):
        """Return a Q object for *field* / *lookup* / *values*.

        Handles the special cases ``array`` (``__contains``), ``in``,
        and the generic ``field__lookup`` pattern.  Multiple values are
        always OR-combined.
        """
        if lookup == "array":
            q = Q()
            for v in values:
                q |= Q(**{f"{field}__contains": [v]})
            return q
        if lookup == "in":
            return Q(**{f"{field}__in": values})
        if lookup == "bool":
            q = Q()
            for v in values:
                q |= Q(**{field: True if v == "on" else False})
            return q
        q = Q()
        for v in values:
            q |= Q(**{f"{field}__{lookup}": v})
        return q

    @classmethod
    def _apply_single_filter(cls, queryset, config, values):
        """Apply one declarative filter config to *queryset*.

        Uses the ``lookups`` list to AND-combine multiple (lookup, field)
        pairs into a single query.  Falls back to the legacy single
        ``field`` + ``lookup`` keys when ``lookups`` is absent.
        """
        field_type = config.get("type", "choice")

        lookups = config.get("lookups")

        if not lookups and "field" in config:
            lookup = config.get("lookup", "exact")
            lookups = [(lookup, config["field"])]

        if not lookups:
            return queryset

        query = Q()
        for lookup_val, field_to_filter in lookups:
            effective = "array" if field_type == "array" else lookup_val
            query &= cls._build_q(field_to_filter, effective, values)
        return queryset.filter(query)

    def _get_selected(self, param):
        """Return non-empty selected values for a query parameter."""
        return [v for v in self.request.GET.getlist(param) if v]

    def _apply_filter_set(self, queryset, config_dict, *, exclude=None):
        """Apply every filter in *config_dict* to *queryset*.

        If *exclude* is given the corresponding key is skipped (used when
        calculating per-facet counts).
        """
        for key, config in config_dict.items():
            if key == exclude:
                continue
            param = config.get("param", key)
            values = self._get_selected(param)
            if not values:
                continue

            if "filter_func" in config:
                queryset = config["filter_func"](queryset, config, values, self.request)
                continue

            queryset = self._apply_single_filter(queryset, config, values)
        return queryset

    def apply_non_facet_filters(self, queryset):
        """Apply all non-facet (sidebar / text) filters."""
        return self._apply_filter_set(queryset, self.get_filter_fields())

    def apply_facet_filters_except(self, queryset, exclude_facet=None):
        """Apply all facet filters except *exclude_facet*."""  # FIXME: dont know anymore why exclude_facet is an option
        return self._apply_filter_set(
            queryset, self.get_facet_fields(), exclude=exclude_facet
        )

    def apply_filters_except(self, queryset, exclude_facet=None):
        queryset = self.apply_non_facet_filters(queryset)
        return self.apply_facet_filters_except(queryset, exclude_facet)

    def get_facet_counts(self, base_queryset=None):
        """Calculate facet counts for all defined facets."""
        if base_queryset is None:
            base_queryset = self.get_base_queryset()

        filtered_qs = self.apply_non_facet_filters(base_queryset)
        facets = {}

        for key, config in self.get_facet_fields().items():
            selected = self._get_selected(key)
            field = config["field"]
            temp_qs = self.apply_facet_filters_except(filtered_qs)
            if selected:
                facets[key] = {
                    "label": config["label"],
                    "field_name": field,
                    "values": [
                        {field + "_unnested": selected[0], "count": temp_qs.count()},
                    ],
                    "selected": selected,
                }
                continue
            ftype = config.get("type", "choice")

            value_counts = None

            if ftype == "choice":
                value_counts = (
                    temp_qs.values(field)
                    .annotate(count=Count("id", distinct=True))
                    .filter(**{f"{field}__isnull": False})
                    .order_by("-count", field)
                )
            elif ftype == "array":
                field_to_unnest = field
                unnested_alias = f"{field_to_unnest}_unnested"

                if not field_to_unnest:
                    continue

                value_counts = (
                    temp_qs.annotate(
                        **{unnested_alias: Func(F(field_to_unnest), function="unnest")}
                    )
                    .values(unnested_alias)
                    .annotate(count=Count("id"))
                    .values(unnested_alias, "count")
                    .order_by("-count", unnested_alias)
                )
            else:
                continue

            if value_counts is not None:
                facets[key] = {
                    "label": config["label"],
                    "field_name": field,
                    "values": value_counts,
                    "selected": selected,
                }

        return facets

    def get_filters(self):
        """Return a list of dicts describing the currently active filters."""
        result = []
        for key, config in self.get_filter_fields().items():
            param = config.get("param", key)
            values = self._get_selected(param)
            if not values:
                continue
            entry = {
                "label": config["label"],
                "field_name": key,
                "param": param,
                "values": values,
            }
            if "model_resolve" in config:
                entry["model_resolve"] = config["model_resolve"]
            result.append(entry)
        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = self.get_base_queryset()
        context["filters"] = self.get_filters()
        context["facets"] = self.get_facet_counts(base_qs)
        context["has_active_filters"] = any(
            self._get_selected(facet) for facet in self.get_facet_fields()
        ) or bool(context["filters"])
        return context
