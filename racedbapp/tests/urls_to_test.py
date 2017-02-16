test_urls = (
 # /bow
  '/bow/bow-i/',
  '/bow/bow-ii/?phase=after-event-1',
  '/bow/bow-iii/?filter=Female',
  '/bow/bow-iv/?filter=Masters',
  '/bow/bow-i/?filter=M-Masters',
  '/bow/bow-ii/?filter=M20-29',
  '/bow/bow-iii/?filter=Male&phase=after-event-2',
 # /bowrecap
  '/bowrecap/bow-i/after/1',
  '/bowrecap/bow-ii/after/2',
  '/bowrecap/bow-iii/after/3',
  '/bowrecap/bow-iv/after/4',
 # distance 
  '/distance/5-km/',     # with teams
  '/distance/10-km/?filter=F-Masters',     # with teams
 # /endurrace
  '/endurrace/latest/',
  '/endurrace/2015/',
  '/endurrace/2014/?filter=Male'
  '/endurrace/2013/?filter=Masters',
  '/endurrace/2012/?filter=F-Masters',
  '/endurrace/2011/?filter=SF-12',
 # /endurrun (home)
  '/endurrun',
 # /endurrun
  '/endurrun/ultimate/',
  '/endurrun/ultimate/?filter=Male',
  '/endurrun/ultimate/?filter=Masters',
  '/endurrun/ultimate/?filter=F-Masters',
  '/endurrun/ultimate/?phase=after-stage-1',
  '/endurrun/ultimate/?year=2017',
  '/endurrun/ultimate/?year=2016&filter=Female&phase=after-stage-2',
  '/endurrun/sport/',
  '/endurrun/sport/?filter=Female',
  '/endurrun/sport/?filter=Masters',
  '/endurrun/sport/?filter=M-Masters',
  '/endurrun/sport/?phase=after-stage-5',
  '/endurrun/sport/?year=2015',
  '/endurrun/sport/?year=2014&filter=Masters&phase=after-stage-6',
  '/endurrun/relay/',
  '/endurrun/relay/?filter=Female',
  '/endurrun/relay/?filter=Male',
  '/endurrun/relay/?filter=Mixed',
  '/endurrun/relay/?filter=Masters',
  '/endurrun/relay/?phase=after-stage-3',
  '/endurrun/relay/?year=2013',
  '/endurrun/relay/?year=2012&filter=Mixed&phase=after-stage-4',
 # /event
  '/event/2012/re-fridgee-eighter/8-km/',                           # regular event
  '/event/2013/endurrace/5-km/?filter=Female',                      # gender filter
  '/event/2014/waterloo-classic/5-km/?filter=Masters',              # masters filter
  '/event/2015/runway/2-mi/?filter=M-Masters',                      # gender masters filter
  '/event/2016/harvest/half-marathon/?filter=HF25-29',              # age category filter
  '/event/2016/endurrun/30-km/',                                    # endurrun (with splits and DNF)
  '/event/2015/endurrun/25_6-km/?division=Ultimate',                # endurrun with division filter (Ultimate)
  '/event/2014/endurrun/marathon/?division=Guest',                  # endurrun with division filter (Guest)
  '/event/2016/baden-road-races/7-mi/',                             # baden 7-miler (has hills)
  '/event/2015/baden-road-races/7-mi/?hill=true',                   # hills
  '/event/2015/baden-road-races/7-mi/?hill=true&filter=LF35-39',    # hills filtered
  '/event/2008/oktoberfest-run/10-km/?wheelchair=true',             # wheelchair
 # /event (team)
  '/event/2016/dirty-dash/6-km/team/parent-child/',     # actual team member times
  '/event/1984/waterloo-classic/10-km/team/open-15/',   # estimated team member times
 # /events
  '/events/',                                               # straight up
  '/events/?year=2016',                                     # year filter
  '/events/?race=waterloo-classic',                         # race filter
  '/events/?distance=5-km',                                 # distance filter
  '/events/?year=2015&race=laurier-loop&distance=10-km',    # all filters combined
 # /race
  '/race/fall-classic/5-km/',                       # regular
  '/race/dirty-dash/6-km/?filter=Female',           # gender filter 
  '/race/baden-road-races/7-mi/',                   # has hills
  '/race/endurrace/combined/',                      # endurrace combined
  '/race/harvest/half-marathon/?filter=Masters',    # masters filter
  '/race/pancake/mile/?filter=M-Masters',           # genders masters filter
  '/race/endurrun/half-marathon/',                  # endurrun ultimate
  '/race/endurrun/marathon/?division=All',          # endurrun all
 # /member
  '/member/sam-lalonde/',
 # /members
  '/members',
 # /multiwins
  '/multiwins/',
  '/multiwins/?gender=f',
 # /name
  '/name/?q=jordan+schmidt',
 # /notify
  '/notify',
 # recap
  '/recap/2016/harvest/half-marathon/',     # with teams
  '/recap/2015/runway/2-mi/',               # without teams
  '/recap/2014/baden-road-races/7-mi/',     # with hills
  '/recap/2013/endurrace/combined/',         # endurrace combined
  '/recap/2015/baden-road-races/7-mi/?format=json',     # json
  '/recap/2014/waterloo-classic/10-km/?format=json&callback=blah',     # jsonp
 # records
  '/records/harvest/half-marathon/',     # with teams
  '/records/runway/2-mi/',               # without teams
  '/records/baden-road-races/7-mi/',     # with hills
  '/records/endurrace/combined/',         # endurrace combined
  '/records/re-fridgee-eighter/8-km/?format=json',  # json
  '/records/laurier-loop/5-km/?format=json&callback=blah',  # jsonp
 # stats
  '/stats/',     # with teams
            )
