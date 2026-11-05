"""Precompute event results rows as HTML in Python.

The event view's results table was the dominant cost of template rendering
(~72% of render time on a large event: hundreds of rows x dozens of template
nodes each). This module builds each row's HTML in Python using format_html /
html.escape so every interpolated value stays escape-safe, and the template
receives one precomputed string per page.

Branching here must mirror the `{% for r in results %}` loop in
templates/racedbapp/event.html exactly. A byte-equivalence test
(tests/test_event_rows_equivalence.py) renders both ways and asserts the
output matches.
"""


from django.utils.html import format_html
from django.utils.safestring import mark_safe

from racedbapp.shared.tracing import tracer
from racedbapp.templatetags.racedbapp_extras import get_pace, get_place, round_up, show_str_decimal


def render_rows(
    results,
    event,
    phototags,
    show_category,
    show_age,
    hasdivision,
    show_chip,
    guntimes_have_microseconds,
    splits_have_microseconds,
    hill_dict,
):
    """Return the complete <tr>...</tr> HTML for all result rows."""
    with tracer.start_as_current_span("event: rows fastpath"):
        km = event.distance.km
        year = event.date.year
        show_youtube = event.youtube_id != "" and event.youtube_offset_seconds is not None
        parts = []
        for r in results:
            cells = []
            # place
            cells.append(format_html('<td class="text-center">{}</td>', get_place(r.place)))
            # bib
            cells.append(format_html('<td class="text-center">{}</td>', r.bib))
            # name (+ award icons)
            name = ""
            if r.member:
                name = format_html('<a href="/member/{}/">{}</a>', r.member.slug, r.name)
            else:
                name = format_html("{}", r.name)
            icon_parts = []
            if r.gender_place == 1:
                icon_parts.append(format_html(
                    '<i class="fas fa-trophy fa-icon-1st-oa" title="1st Overall ({})"></i>', r.gender
                ))
            elif r.gender_place == 2:
                icon_parts.append(format_html(
                    '<i class="fas fa-medal fa-icon-2nd-oa" title="2nd Overall ({})"></i>', r.gender
                ))
            elif r.gender_place == 3:
                icon_parts.append(format_html(
                    '<i class="fas fa-medal fa-icon-3rd-oa" title="3rd Overall ({})"></i>', r.gender
                ))
            if r.masters_place == 1:
                icon_parts.append(format_html(
                    '<i class="fas fa-medal fa-icon-1st-master" title="1st Master ({})"></i>', r.gender
                ))
            if r.isrwpb and r.member:
                icon_parts.append(format_html(
                    '<i class="fas fa-stopwatch fa-icon-pb" title="RW PB for the {}"></i>',
                    event.distance.name,
                ))
            if r.isrwfirst:
                icon_parts.append('<i class="fa-solid fa-hand-wave fa-icon-firstrace" title="Welcome new RW member!"></i>')
            if r.relay_team:
                icon_parts.append(format_html('<i class="fas fa-users" title="{}"></i>', r.relay_team))
            cells.append(format_html('<td class="text-left">{}{}</td>', name, mark_safe("".join(icon_parts))))
            # phototags column
            if phototags:
                if r.hasphotos:
                    cells.append(format_html(
                        '<td class="text-center"><a href="https://www.flickr.com/photos/runwaterloo/tags/{},{}" target="_blank"><i class="fas fa-camera"></i></a></td>',
                        event.flickrsearchstr,
                        r.bib,
                    ))
                else:
                    cells.append("<td></td>")
            # youtube column
            if show_youtube:
                if r.youtube_url:
                    cells.append(format_html(
                        '<td class="text-center"><a href="{}" target="_blank"><i class="fas fa-video"></i></a></td>',
                        r.youtube_url,
                    ))
                else:
                    cells.append("<td></td>")
            # guntime
            if guntimes_have_microseconds:
                cells.append(format_html('<td class="text-center">{}</td>', round_up(r.guntime)))
            else:
                cells.append(format_html('<td class="text-center">{}</td>', r.guntime))
            # hill prime column
            if hill_dict:
                cells.append(format_html('<td class="text-center">{}</td>', r.prime))
            # gender / gender_place
            cells.append(format_html('<td class="text-center">{}</td>', r.gender))
            cells.append(format_html('<td class="text-center">{}</td>', r.gender_place))
            # category + category_place
            if show_category:
                cells.append(format_html('<td class="text-center">{}</td>', r.category))
                cells.append(format_html('<td class="text-center">{}</td>', r.category_place))
            # age
            if show_age:
                cells.append(format_html('<td class="text-center">{}</td>', r.age))
            # endurrun division
            if hasdivision:
                if r.division != "Guest":
                    cells.append(format_html(
                        '<td class="text-left"><a href="/endurrun/{}/?year={}">{}</a></td>',
                        r.division.lower(),
                        year,
                        r.division,
                    ))
                else:
                    cells.append(format_html('<td class="text-left">{}</td>', r.division))
            # pace
            cells.append(format_html('<td class="text-center">{}</td>', get_pace(r.guntime, km)))
            # chiptime
            if show_chip:
                if guntimes_have_microseconds:
                    cells.append(format_html('<td class="text-center">{}</td>', round_up(r.chiptime)))
                else:
                    cells.append(format_html('<td class="text-center">{}</td>', r.chiptime))
            # city
            cells.append(format_html('<td class="text-left">{}</td>', r.city))
            # splits
            for s in r.splits:
                if str(s.split_time) != "None":
                    if splits_have_microseconds:
                        cells.append(format_html('<td class="text-center">{}</td>', show_str_decimal(s.split_time)))
                    else:
                        cells.append(format_html('<td class="text-center">{}</td>', s.split_time))
                else:
                    cells.append("<td></td>")
            parts.append("<tr>" + "".join(cells) + "</tr>")
        return "".join(parts)
