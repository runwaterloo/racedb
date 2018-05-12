from django.conf.urls import url
from django.views.generic.base import RedirectView
from . import view_adminphotos, view_index, view_bow, view_bowrecap, view_distance, view_endurrace, view_endurrun, view_endurrunhome, view_event, view_events, view_event_team, view_notify, view_multiwins, view_member, view_members, view_recap, view_race, view_name, view_photoupdate, view_records, view_race, view_stats, view_boost, view_relay, view_durelay

urlpatterns = [
    url(r'^$', RedirectView.as_view(url='/events', permanent=False), name='index'),
    url(r'^adminphotos', view_adminphotos.index, name='adminphotos'),
    url(r'^bowrecap/(?P<bow_slug>.*)/after/(?P<phase>.*)$', view_bowrecap.index, name='bowrecap'),
    url(r'^bow/(?P<bow_slug>.*)/$', view_bow.index, name='bow'),
    url(r'^distance/(?P<distance_slug>.*)/$', view_distance.index, name='distance'),
    url(r'^distance', RedirectView.as_view(url='/distance/5-km/', permanent=False), name='distance_redirect'),
    url(r'^durelay/(?P<year>[0-9]{4})/$', view_durelay.index, name='durelay'),
    url(r'^endurrace/(?P<year>.*)/$', view_endurrace.index, name='endurrace'),
    url(r'^endurrun/(?P<division>.*)/$', view_endurrun.index, name='endurrun'),
    url(r'^endurrun', view_endurrunhome.index, name='endurrunhome'),
    url(r'^event/(?P<year>[0-9]{4})/(?P<race_slug>.*)/(?P<distance_slug>.*)/team/(?P<team_category_slug>.*)/$', view_event_team.index, name='event_team'),
    url(r'^event/(?P<year>[0-9]{4})/(?P<race_slug>.*)/(?P<distance_slug>.*)/$', view_event.index, name='event'),
    url(r'^events', view_events.index, name='events'),
    url(r'^index/', view_index.index, name='index'),
    url(r'^race/(?P<race_slug>.*)/(?P<distance_slug>.*)/$', view_race.index, name='race'),
    url(r'^members', view_members.index, name='members'),
    url(r'^member/(?P<member_slug>.*)/$', view_member.index, name='member'),
    url(r'^multiwins', view_multiwins.index, name='multiwins'),
    url(r'^name', view_name.index, name='name'),
    url(r'^boost/(?P<year>.*)/$', view_boost.index, name='boost'),
    url(r'^boost/$', RedirectView.as_view(url='/boost/2018/', permanent=False), name='index'),
    url(r'^notify', view_notify.index, name='notify'),
    url(r'^photoupdate', view_photoupdate.index, name='photoupdate'),
    url(r'^relay/(?P<year>[0-9]{4})/(?P<race_slug>.*)/(?P<distance_slug>.*)/$', view_relay.index, name='relay'),
    url(r'^recap/(?P<year>[0-9]{4})/(?P<race_slug>.*)/(?P<distance_slug>.*)/$', view_recap.index, name='recap'),
    url(r'^records/(?P<race_slug>.*)/(?P<distance_slug>.*)/$', view_records.index, name='records'),
    url(r'^stats', view_stats.index, name='stats'),
              ]
    #url(r'^$', view_index.index, name='index'),
    #url(r'^check/(?P<year>[0-9]{4})/(?P<race_slug>.*)/(?P<distance_slug>.*)/$', view_check.index, name='check'),
    #url(r'^search', view_search.index, name='search'),
    #url(r'^stats/(?P<race_slug>.*)/(?P<distance_slug>.*)/$', view_stats.index, name='stats')
