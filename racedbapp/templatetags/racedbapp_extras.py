from datetime import timedelta

from django import template
from django.templatetags.static import static

from ..models import Config, Distance

register = template.Library()


@register.filter(name="get_pace")
def get_pace(guntime, distance):
    """
    Calculate a pace from guntime and distance.
    If calculation doesn't work out just return ''
    """
    try:
        paceseconds = guntime.total_seconds() / float(distance)
    except Exception:
        pace = ""
    else:
        rawpace = timedelta(seconds=round(paceseconds, 0))
        pace = str(rawpace).lstrip("0:")
    return pace


@register.filter(name="get_place")
def get_place(raw_place):
    """Substitute strings when place should be DQ, DNF, DNS"""
    if raw_place < 990000:
        place = raw_place
    elif raw_place >= 990000 and raw_place < 991000:
        place = "DQ"
    elif raw_place >= 991000 and raw_place < 992000:
        place = "DNF"
    else:
        place = "DNS"
    return place


@register.filter(name="get_time")
def get_time(orig_time):
    """Truncate time and handle other weirdness"""
    try:
        clean_time = orig_time - timedelta(microseconds=orig_time.microseconds)
    except Exception:
        clean_time = ""
    else:
        if clean_time.total_seconds() >= 356400:
            clean_time = ""
    return clean_time


@register.filter(name="show_decimal")
def show_decimal(orig_time):
    """Show one decimal place for time"""
    if orig_time.microseconds == 0:
        decimal_time = str(orig_time) + ".0"
    else:
        decimal_time = str(orig_time).rstrip("0")
    return decimal_time


@register.filter(name="show_str_decimal")
def show_str_decimal(orig_time):
    """Show one decimal place for time"""
    if "." in orig_time:
        decimal_time = str(orig_time).rstrip("0")
    else:
        decimal_time = str(orig_time) + ".0"
    return decimal_time


@register.filter(name="round_up")
def round_up(orig_time):
    """Round times up to the second"""
    if not orig_time:
        return orig_time
    if orig_time.microseconds == 0:
        rounded_up_time = orig_time
    else:
        round_up_amount = 1000000 - orig_time.microseconds
        rounded_up_time = orig_time + timedelta(microseconds=round_up_amount)
    return rounded_up_time


@register.filter(name="neg_to_pos")
def neg_to_pos(orig_value):
    """Turn a negative number to positive"""
    pos_value = orig_value * -1
    return pos_value


@register.filter(name="get_prekey")
def get_prekey(string):
    """Get preupdate key"""
    prekey_object = Config.objects.filter(name="prekey").first()
    return prekey_object.value if prekey_object else ""


@register.filter(name="get_default_record_distance_slug")
def get_default_record_distance_slug(string):
    """Get default record distance slug"""
    default_record_distance_slug = "5-km"
    config_value = Config.objects.filter(name="default_record_distance_slug").first()
    if config_value is not None:
        db_distance = Distance.objects.filter(slug=config_value.value).first()
        if db_distance is not None:
            default_record_distance_slug = db_distance.slug
    return default_record_distance_slug


@register.simple_tag
def event_logo(event):
    if getattr(event, "custom_logo_url", None):
        return event.custom_logo_url
    return static(f"race_logos/{event.race.slug}.png")
