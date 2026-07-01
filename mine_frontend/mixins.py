from django.db.models import F, Func
from django.db.models.aggregates import Count
from django.db.models.query_utils import Q


def _facet_source_fields(config):
    """Return the list of model fields a facet should count values from.

    A facet may declare its source fields in any of these ways (checked
    in order):

    * ``field`` as a list of field names -> use it directly;
    * ``lookups`` as ``[(lookup, field), ...]`` -> collect the field of
      each tuple (this is the same list used for filtering);
    * ``field`` as a single string -> ``[field]``.

    The returned list always has at least one element (or is empty when
    the facet declares no field at all).
    """
    field = config.get("field")
    if isinstance(field, (list, tuple)):
        return list(field)
    lookups = config.get("lookups")
    if lookups:
        return [fld for (_lookup, fld) in lookups]
    if field:
        return [field]
    return []


class FacetedSearchMixin:
    """Mixin that provides faceted search and filtering for Django list views.

    Configuration attributes (set on the view class):

        facet_fields = {
            'param_name': {
                'label': 'Display Name',
                'field': 'model_field_name',   # string OR list of field names;
                                               # when a list is given the facet
                                               # options are the union of values
                                               # across all listed fields
                'lookup': 'exact',           # optional, default 'exact'
                'type': 'choice' | 'array',  # 'choice' = regular field,
                                             # 'array'  = ArraySubquery / ArrayField
            },
        }

        # Multi-field facets can also be declared via 'lookups' (the same
        # list used for filtering); the counting side then derives its
        # source fields from there:
        #
        #   'faecher': {
        #       'label': 'Fach',
        #       'lookups': [('exact', 'faecher_position'),
        #                   ('exact', 'faecher_ausbildung')],
        #       'type': 'array',
        #   }

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
    def _apply_single_filter(cls, queryset, config, values, combine="and"):
        """Apply one declarative filter config to *queryset*.

        Uses the ``lookups`` list to combine multiple (lookup, field)
        pairs into a single query.  ``combine`` controls how those pairs
        are joined:

        * ``"and"`` (default) - a row must match *every* pair.  Used for
          ``filter_fields`` where several fields describe the same
          constraint that all must hold.
        * ``"or"`` - a row must match *any* pair.  Used for facets whose
          options are the union of values across several source fields
          (see ``_facet_source_fields``): filtering has to mirror the
          counting and keep any object that carries the value in any of
          those fields.

        Falls back to the legacy single ``field`` + ``lookup`` keys when
        ``lookups`` is absent.  A per-config ``combine`` key overrides the
        caller-supplied default.
        """
        field_type = config.get("type", "choice")

        lookups = config.get("lookups")

        if not lookups and "field" in config:
            lookup = config.get("lookup", "exact")
            lookups = [(lookup, config["field"])]

        if not lookups:
            return queryset

        combine = config.get("combine", combine)
        join = (lambda a, b: a | b) if combine == "or" else (lambda a, b: a & b)

        query = Q()
        first = True
        for lookup_val, field_to_filter in lookups:
            effective = "array" if field_type == "array" else lookup_val
            part = cls._build_q(field_to_filter, effective, values)
            query = part if first else join(query, part)
            first = False
        return queryset.filter(query)

    def _get_selected(self, param):
        """Return non-empty selected values for a query parameter."""
        return [v for v in self.request.GET.getlist(param) if v]

    def _apply_filter_set(self, queryset, config_dict, *, exclude=None, combine="and"):
        """Apply every filter in *config_dict* to *queryset*.

        If *exclude* is given the corresponding key is skipped (used when
        calculating per-facet counts).  *combine* is the default join mode
        passed to ``_apply_single_filter`` (facets pass ``"or"``).
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

            queryset = self._apply_single_filter(
                queryset, config, values, combine=combine
            )
        return queryset

    def apply_non_facet_filters(self, queryset):
        """Apply all non-facet (sidebar / text) filters."""
        return self._apply_filter_set(queryset, self.get_filter_fields())

    def apply_facet_filters_except(self, queryset, exclude_facet=None):
        """Apply all facet filters except *exclude_facet*.

        Facet source fields are combined with OR (union semantics) so that
        filtering mirrors the counting: an object is kept if it carries the
        selected value in *any* of the facet's source fields.
        """  # FIXME: dont know anymore why exclude_facet is an option
        return self._apply_filter_set(
            queryset, self.get_facet_fields(), exclude=exclude_facet, combine="or"
        )

    def apply_filters_except(self, queryset, exclude_facet=None):
        queryset = self.apply_non_facet_filters(queryset)
        return self.apply_facet_filters_except(queryset, exclude_facet)

    # alias used for the "value" column in every facet result row; the
    # template fetches it via ``get_facet_value(item, field_name)`` where
    # ``field_name`` is set to this constant, so the templates do not need
    # to know which model field(s) a facet was built from.
    _FACET_VALUE_ALIAS = "value"

    @staticmethod
    def _facet_value_rows(queryset, field, ftype):
        """Return ``(value, oid)`` rows for one source *field*.

        ``choice`` - one row per object holding ``field``'s value.
        ``array``  - one row per array element (via ``unnest``).
        NULL values are dropped.  Used as the per-field input for the
        UNION-based multi-field counting.
        """
        if ftype == "array":
            return (
                queryset.annotate(
                    value=Func(F(field), function="unnest"),
                    oid=F("pk"),
                )
                .order_by()
                .values("value", "oid")
                .distinct()
            )
        return (
            queryset.filter(**{f"{field}__isnull": False})
            .annotate(value=F(field), oid=F("pk"))
            .order_by()
            .values("value", "oid")
            .distinct()
        )

    def _facet_value_counts(self, queryset, fields, ftype):
        """Build ``value -> distinct-object count`` across one or more fields.

        Single field: aggregated server-side (same SQL shape as before).

        Multiple fields: each field contributes ``(value, pk)`` rows; we
        ``UNION ALL`` them and aggregate in Python so that an object
        carrying the same value in several of *fields* is counted exactly
        once for that value.  (Django forbids ``annotate()`` after
        ``union()``, so the final grouping is done here.)
        """
        alias = self._FACET_VALUE_ALIAS

        if len(fields) == 1:
            field = fields[0]
            if ftype == "array":
                return (
                    queryset.annotate(**{alias: Func(F(field), function="unnest")})
                    .values(alias)
                    .annotate(count=Count("id"))
                    .values(alias, "count")
                    .order_by("-count", alias)
                )
            return (
                queryset.filter(**{f"{field}__isnull": False})
                .values(**{alias: F(field)})
                .annotate(count=Count("id", distinct=True))
                .values(alias, "count")
                .order_by("-count", alias)
            )

        parts = [self._facet_value_rows(queryset, fld, ftype) for fld in fields]
        unioned = parts[0].union(*parts[1:])
        counts = {}
        for value, oid in unioned.values_list("value", "oid"):
            if value is None:
                continue
            counts.setdefault(value, set()).add(oid)
        rows = [{alias: value, "count": len(oids)} for value, oids in counts.items()]
        rows.sort(key=lambda r: (-r["count"], r[alias]))
        return rows

    def get_facet_counts(self, base_queryset=None):
        """Calculate facet counts for all defined facets."""
        if base_queryset is None:
            base_queryset = self.get_base_queryset()

        filtered_qs = self.apply_non_facet_filters(base_queryset)
        facets = {}
        alias = self._FACET_VALUE_ALIAS

        for key, config in self.get_facet_fields().items():
            selected = self._get_selected(key)
            temp_qs = self.apply_facet_filters_except(filtered_qs)
            fields = _facet_source_fields(config)
            if not fields:
                continue
            ftype = config.get("type", "choice")
            if ftype not in ("choice", "array"):
                continue

            if selected:
                facets[key] = {
                    "label": config["label"],
                    "field_name": alias,
                    "values": [{alias: selected[0], "count": temp_qs.count()}],
                    "selected": selected,
                }
                continue

            value_counts = self._facet_value_counts(temp_qs, fields, ftype)
            facets[key] = {
                "label": config["label"],
                "field_name": alias,
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
