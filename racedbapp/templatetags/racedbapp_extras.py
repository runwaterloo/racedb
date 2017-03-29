from django import template
from datetime import timedelta
from ..models import Config

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

@register.filter(name='get_prekey')
def get_prekey(string):
    """ Get preupdate key """
    prekey = Config.objects.get(name='prekey').value
    return prekey
