from django import template
from omero.gateway import MapAnnotationWrapper

register = template.Library()

@register.filter
def is_map_annotation(ann):
    return isinstance(ann, MapAnnotationWrapper)