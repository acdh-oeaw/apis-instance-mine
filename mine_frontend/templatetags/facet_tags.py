from django import template
from django.contrib.contenttypes.models import ContentType

register = template.Library()


@register.simple_tag
def facet_url(request, facet_key, value, action="add"):
    """
    Generate URL with facet parameter added or removed
    """
    params = request.GET.copy()

    if action == "add":
        # Add the facet value
        params.appendlist(facet_key, value)
    elif action == "remove":
        # Remove the specific facet value
        values = params.getlist(facet_key)
        if value in values:
            values.remove(value)
        params.setlist(facet_key, values)

    return f"?{params.urlencode()}"


@register.simple_tag
def get_facet_label(filter, value):
    if "model_resolve" in filter:
        cls = ContentType.objects.get(model=filter["model_resolve"]).model_class()
        return str(cls.objects.get(pk=value))
    else:
        return value


@register.filter
def lookup(dictionary, key):
    """Template filter to do dictionary lookup"""
    if hasattr(dictionary, "get"):
        return dictionary.get(key)
    return getattr(dictionary, key, None)


@register.filter
def get_facet_value(item_dict, field_name):
    """Get the facet value from the item dictionary"""
    if field_name in item_dict:
        return item_dict[field_name]
    elif f"{field_name}_unnested" in item_dict:
        return item_dict[f"{field_name}_unnested"]
    return ""


@register.filter
def in_list(value, list_values):
    """Check if value is in list"""
    return str(value) in [str(v) for v in list_values]
