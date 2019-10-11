from django import template
from datetime import timedelta
from ..models import Config, Distance

register = template.Library()

@register.filter(name='get_pace')
def get_pace(guntime, distance): 
    """
    Calculate a pace from guntime and distance.
    If calculation doesn't work out just return ''
    """
    try:
        paceseconds = guntime.total_seconds() / float(distance)
    except:
        pace = ''
    else:
        rawpace = timedelta(seconds = round(paceseconds,0))
        pace = str(rawpace).lstrip('0:')
    return pace

@register.filter(name='get_place')
def get_place(raw_place):
    """ Substitute strings when place should be DQ, DNF, DNS """
    if raw_place < 990000:
        place = raw_place
    elif raw_place >= 990000 and raw_place < 991000:
        place = 'DQ'
    elif raw_place >= 991000 and raw_place < 992000:
        place = 'DNF'
    else:
        place = 'DNS'
    return place

@register.filter(name='get_time')
def get_time(orig_time):
    """ Truncate time and handle other weirdness """
    try:
        clean_time = orig_time - timedelta(microseconds=orig_time.microseconds)
    except:
        clean_time = ''
    else:
        if clean_time.total_seconds() >= 356400:
            clean_time = ''
    return clean_time

@register.filter(name='show_decimal')
def show_decimal(orig_time):
    """ Show one decimal place for time """
    if orig_time.microseconds == 0:
        decimal_time = str(orig_time) + ".0"
    else:
        decimal_time = str(orig_time).rstrip("0")
    return decimal_time

@register.filter(name='get_prekey')
def get_prekey(string):
    """ Get preupdate key """
    prekey = Config.objects.get(name='prekey').value
    return prekey

@register.filter(name='get_default_record_distance_slug')
def get_default_record_distance_slug(string):
    """ Get default record distance slug """
    default_record_distance_slug = "5-km"
    config_value = Config.objects.filter(name="default_record_distance_slug").first()
    if config_value is not None:
        db_distance = Distance.objects.filter(slug=config_value.value).first()
        if db_distance is not None:
            default_record_distance_slug = db_distance.slug
    return default_record_distance_slug
