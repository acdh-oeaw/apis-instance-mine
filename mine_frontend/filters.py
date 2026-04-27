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


def life_starting(queryset, config_dict, selected_values, request):
    """filters lifespan beginning"""
    excl = request.GET.get("start_date_life_form_exclusive", False)
    val = selected_values[0]
    q = Q(date_of_death_date_to__gte=val) | Q(date_of_death_date_to__isnull=True)
    if excl:
        q &= Q(date_of_birth_date_from__gte=val)
    return queryset.filter(q)


def life_ending(queryset, config_dict, selected_values, request):
    """filters lifespan ending"""
    excl = request.GET.get("end_date_life_form_exclusive", False)
    val = selected_values[0]
    q = Q(date_of_birth_date_from__lte=val)
    if excl:
        q &= Q(date_of_death_date_to__lte=val)
    return queryset.filter(q)
