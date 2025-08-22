from django.db.models import F, Func
from django.db.models.aggregates import Count
from django.db.models.query_utils import Q


class FacetedSearchMixin:
    facet_fields = {}  # Define this in your view

    def get_facet_fields(self):
        """
        Returns dict: {
            'field_name': {
                'label': 'Display Name',
                'field': 'model_field_name',
                'lookup': 'icontains',  # or 'exact', 'in', etc.
                'type': 'choice',  # or 'text', 'range'
            }
        }
        """
        return getattr(self, "facet_fields", {})

    def get_filter_fields(self):
        """
        Returns dict: {
            'field_name': {
                'label': 'Display Name',
                'param': 'query param to use',
                'field': 'model_field_name',
                'lookup': 'icontains',  # or 'exact', 'in', the function to call etc.
                'type': 'choice',  # or 'text', 'range', 'callable'
            }
        }
        """
        return getattr(self, "filter_fields", {})

    def get_base_queryset(self):
        """Override this to provide the base queryset before faceting"""
        return self.get_queryset()

    def get_facet_counts(self, base_queryset=None):
        """Calculate facet counts for all defined facets"""
        if base_queryset is None:
            base_queryset = self.get_base_queryset()

        facets = {}
        facet_config = self.get_facet_fields()

        filtered_queryset = self.apply_non_facet_filters(base_queryset)

        for facet_key, config in facet_config.items():
            if config.get("type") == "choice":
                field_name = config["field"]

                temp_qs = self.apply_facet_filters_except(filtered_queryset, facet_key)

                # Get value counts
                value_counts = (
                    temp_qs.values(field_name)
                    .annotate(count=Count("id", distinct=True))
                    .filter(**{f"{field_name}__isnull": False})
                    .order_by("-count", field_name)
                )

                facets[facet_key] = {
                    "label": config["label"],
                    "field_name": field_name,
                    "values": value_counts,
                    "selected": self.request.GET.getlist(facet_key),
                }
            elif config.get("type") == "array":
                # For ArraySubquery annotated fields, unnest the annotation and count unique values
                field_name = config["field"]

                temp_qs = self.apply_facet_filters_except(filtered_queryset, facet_key)
                ann_dict = {
                    f"{field_name}_unnested": Func(F(field_name), function="unnest")
                }
                value_counts = (
                    temp_qs.annotate(**ann_dict)
                    .values(f"{field_name}_unnested")
                    .annotate(count=Count("id"))
                    .values(f"{field_name}_unnested", "count")
                    .order_by("-count", f"{field_name}_unnested")
                )

                facets[facet_key] = {
                    "label": config["label"],
                    "field_name": field_name,
                    "values": value_counts,
                    "selected": self.request.GET.getlist(facet_key),
                }

        return facets

    def get_filters(self):
        """
        Get the filters for the current request.
        """
        res = []
        filter_config = self.get_filter_fields()
        for field_name, config in filter_config.items():
            filter = {}
            label = config["label"]
            get_param = config.get("param", field_name)
            selected_values = [
                value for value in self.request.GET.getlist(get_param) if value
            ]
            if selected_values:
                filter["label"] = label
                filter["field_name"] = field_name
                filter["param"] = get_param
                filter["values"] = selected_values
                res.append(filter)
        return res

    def apply_non_facet_filters(self, queryset):
        """Apply all non-facet filters (text search, etc.)"""
        filter_config = self.get_filter_fields()

        for field_name, config in filter_config.items():
            field_name = config["field"]
            field_type = config.get("type", "choice")
            lookup = config.get("lookup", "exact")
            get_param = config.get("param", field_name)
            selected_values = self.request.GET.getlist(get_param)
            if not selected_values:
                continue
            if field_type == "array":
                query = Q()
                for value in selected_values:
                    # Use array contains lookup - this works with ArraySubquery annotations
                    query |= Q(**{f"{field_name}__contains": [value]})
                queryset = queryset.filter(query)
            elif lookup == "in":
                queryset = queryset.filter(**{f"{field_name}__in": selected_values})
            elif lookup == "icontains":
                query = Q()
                for value in selected_values:
                    query |= Q(**{f"{field_name}__icontains": value})
                queryset = queryset.filter(query)
            elif field_type == "callable":
                queryset = lookup(queryset)
            else:
                # Handle other lookup types
                query = Q()
                for value in selected_values:
                    query |= Q(**{f"{field_name}__{lookup}": value})
                queryset = queryset.filter(query)
        return queryset

    def apply_facet_filters_except(self, queryset, exclude_facet=None):
        """Apply all facet filters except the specified one"""
        facet_config = self.get_facet_fields()

        for facet_key, config in facet_config.items():
            if facet_key == exclude_facet:
                continue

            selected_values = self.request.GET.getlist(facet_key)
            if selected_values:
                field_name = config["field"]
                field_type = config.get("type", "choice")
                lookup = config.get("lookup", "exact")

                if field_type == "array":
                    query = Q()
                    for value in selected_values:
                        # Use array contains lookup - this works with ArraySubquery annotations
                        query |= Q(**{f"{field_name}__contains": [value]})
                    queryset = queryset.filter(query)
                elif lookup == "in":
                    queryset = queryset.filter(**{f"{field_name}__in": selected_values})
                elif lookup == "icontains":
                    query = Q()
                    for value in selected_values:
                        query |= Q(**{f"{field_name}__icontains": value})
                    queryset = queryset.filter(query)
                else:
                    # Handle other lookup types
                    query = Q()
                    for value in selected_values:
                        query |= Q(**{f"{field_name}__{lookup}": value})
                    queryset = queryset.filter(query)

        return queryset

    def apply_filters_except(self, queryset, exclude_facet=None):
        """Apply all filters except the specified facet (deprecated - use specific methods)"""
        # Apply non-facet filters
        queryset = self.apply_non_facet_filters(queryset)
        # Apply facet filters except the excluded one
        return self.apply_facet_filters_except(queryset, exclude_facet)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get base queryset before applying table filters
        base_qs = self.get_base_queryset()
        context["filters"] = self.get_filters()
        # Calculate facets
        context["facets"] = self.get_facet_counts(base_qs)
        context["has_active_filters"] = any(
            self.request.GET.getlist(facet) for facet in self.get_facet_fields().keys()
        ) or bool(context["filters"])

        return context
