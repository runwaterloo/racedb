#from collections import namedtuple
#from django.db.models import Min, Count, Q
from .models import *      
from itertools import chain
import logging
logger = logging.getLogger(__name__)

def update_membership(member):
    """ Update rwmember field in result table """
    logger.info('Updating membership for {} ({})'.format(member, member.id))
    # Clear all existing member results
    Result.objects.filter(rwmember=member).update(rwmember=None)
    # Only tag results if member is active
    if member.active:
        primaryresults = Result.objects.filter(athlete=member.name) 
        altresults = Result.objects.filter(athlete=member.altname)  
        includes = get_includes(member)                                              
        results_list = list(chain(primaryresults, altresults)) + includes            
        excludes = get_excludes(member)            
        for r in results_list:
            if r in excludes:
                continue
            r.rwmember=member
            r.save()
            logger.info('Updating {} with {}'.format(r, member))

def get_includes(member):                                                        
    includes = []                                                                
    dbincludes = Rwmembercorrection.objects.filter(rwmember=member, correction_type='include')
    for i in dbincludes:                                                         
        include_result = Result.objects.filter(event=i.event, place=i.place)
        if len(include_result) == 1:                                             
            includes.append(include_result[0])                                   
    return includes                                                              
                                                                                 
def get_excludes(member):                                                        
    dbexcludes = Rwmembercorrection.objects.filter(rwmember=member, correction_type='exclude')
    excludes = []                                                                
    for e in dbexcludes:                                                         
        exclude_result = Result.objects.filter(event=e.event, place=e.place)     
        if len(exclude_result) == 1:                                             
            excludes.append(exclude_result[0])                                   
    return excludes                                                              
