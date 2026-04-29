from django.db.models import Case, Exists, OuterRef, Q, Value, When

from apis_ontology.models import PositionAn


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


def beruf_institution(queryset, config_dict, selected_values, request):
    """filter that combines position and institution"""
    position = request.GET.getlist("beruf_position", False)
    institution = request.GET.getlist("beruf_institution", False)
    q = Q(subj_object_id=OuterRef("id"))
    if position:
        qp = Q()
        for v in position:
            qp_1 = Q(position=v)
            qp |= qp_1
        q &= qp
    if institution:
        qp = Q()
        for v in institution:
            qp_1 = Q(obj_object_id=v)
            qp |= qp_1
        q &= qp
    rel = PositionAn.objects.filter(q).values_list("id", flat=True)
    return queryset.annotate(
        position_an=Case(When(Exists(rel), then=Value(True)), default=Value(None))
    ).filter(position_an__isnull=False)
