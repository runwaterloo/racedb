from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from racedbapp import membership, tasks
from racedbapp.models import Config, Event, Rwmember, Rwmembercorrection


def _clear_cache(source):
    """Enqueue a cache clear unless disabled (local dev SETTINGS=min)."""
    if settings.CACHE_SIGNALS_ENABLED:
        tasks.safe_enqueue(tasks.clear_cache, source=source)


@receiver(post_save, sender=Rwmember)
@receiver(post_save, sender=Rwmembercorrection)
def model_post_save(sender, **kwargs):
    # print('Saved: {}'.format(kwargs['instance'].__dict__))
    if "racedbapp.models.Rwmembercorrection" in str(sender):
        member = kwargs["instance"].rwmember
    elif "racedbapp.models.Rwmember" in str(sender):
        member = kwargs["instance"]
    membership.update_membership(member)
    _clear_cache("member_save")


@receiver(post_delete, sender=Rwmembercorrection)
def model_post_delete(sender, **kwargs):
    member = kwargs["instance"].rwmember
    membership.update_membership(member)
    _clear_cache("member_delete")


@receiver(post_save, sender=Config)
def config_post_save(sender, **kwargs):
    if kwargs.get("raw"):
        return
    _clear_cache("config_save")


@receiver(post_save, sender=Event)
def event_post_save(sender, **kwargs):
    if kwargs.get("raw"):
        return
    _clear_cache("event_save")
