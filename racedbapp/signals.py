from django.db.models.signals import pre_save, pre_delete, post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from racedbapp.models import *
from racedbapp import membership
from racedbapp import tasks
 
@receiver(post_save, sender=Rwmember)
@receiver(post_save, sender=Rwmembercorrection)
def model_post_save(sender, **kwargs):
    #print('Saved: {}'.format(kwargs['instance'].__dict__))
    if 'racedbapp.models.Rwmembercorrection' in str(sender):
        member = kwargs['instance'].rwmember
    elif 'racedbapp.models.Rwmember' in str(sender):
        member = kwargs['instance']
    membership.update_membership(member)

@receiver(post_delete, sender=Rwmembercorrection)
def model_post_delete(sender, **kwargs):
    member = kwargs['instance'].rwmember
    membership.update_membership(member)

@receiver(post_save, sender=Config)
def config_post_save(sender, **kwargs):
    tasks.clear_cache.delay()
