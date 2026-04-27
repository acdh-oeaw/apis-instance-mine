from django.db.models import Q


def memb_starting(queryset, config_dict, selected_values, request):
    """filters according to the membership dates"""
    excl = request.GET.get("start_date_form_exclusive", False)
    val = selected_values[0]
    q = Q(max_date_memb__gte=val) | Q(max_date_memb__isnull=True)
    if excl:
        q &= Q(min_date_memb__gte=val)
    return queryset.filter(q)


def memb_ending(queryset, config_dict, selected_values, request):
    """filters according to the membership dates"""
    excl = request.GET.get("end_date_form_exclusive", False)
    val = selected_values[0]
    q = Q(min_date_memb__lte=val)
    if excl:
        q &= Q(max_date_memb__lte=val)
    return queryset.filter(q)
