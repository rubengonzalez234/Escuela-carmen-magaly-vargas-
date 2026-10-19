from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Permite acceder a un diccionario con clave dinámica en templates."""
    if dictionary is None:
        return None
    try:
        return dictionary.get(key)
    except AttributeError:
        return None
