# from collections import namedtuple
# from django.db.models import Min, Count, Q
import logging
from itertools import chain
from operator import attrgetter

from .models import *

logger = logging.getLogger(__name__)


def update_membership(member):
    """ Update rwmember field and isrwb in result table """
    logger.info("Updating membership for {} ({})".format(member, member.id))
    # Clear all existing member results
    Result.objects.filter(rwmember=member).update(rwmember=None, isrwpb=False)
    primaryresults = Result.objects.filter(athlete=member.name)
    altresults = Result.objects.filter(athlete=member.altname)
    includes = get_includes(member)
    results_list = list(chain(primaryresults, altresults)) + includes
    results_list = sorted(set(results_list), key=attrgetter("event.date"))
    excludes = get_excludes(member)
    rwpbs = {}
    pb_exclude_events = (1266, 1267, 1268, 1316, 1317, 1318)
    for r in results_list:
        if r in excludes:
            continue
        r.rwmember = member
        dist = r.event.distance
        if dist.slug != "roughly-five" and r.event.id not in pb_exclude_events:
            if dist in rwpbs:
                if r.guntime < rwpbs[dist]:
                    rwpbs[dist] = r.guntime
                    r.isrwpb = True
            else:
                rwpbs[dist] = r.guntime
                r.isrwpb = True
        r.save()
        logger.info("Updating {} with {}".format(r, member))


def get_includes(member):
    includes = []
    dbincludes = Rwmembercorrection.objects.filter(
        rwmember=member, correction_type="include"
    )
    for i in dbincludes:
        include_result = Result.objects.filter(event=i.event, place=i.place)
        if len(include_result) == 1:
            includes.append(include_result[0])
    return includes


def get_excludes(member):
    dbexcludes = Rwmembercorrection.objects.filter(
        rwmember=member, correction_type="exclude"
    )
    excludes = []
    for e in dbexcludes:
        exclude_result = Result.objects.filter(event=e.event, place=e.place)
        if len(exclude_result) == 1:
            excludes.append(exclude_result[0])
    return excludes
