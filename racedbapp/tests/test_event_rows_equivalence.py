"""Byte-equivalence tests for the event rows fastpath.

The oracle is the original template row loop (verbatim from event.html before
the fastpath landed). render_rows() must produce identical HTML for every
combination of page flags and row shapes.
"""

import datetime
import re
from collections import namedtuple

import django.test
from django.template import Context, Template

from racedbapp.shared.event_rows import render_rows

named_result = namedtuple(
    "nr",
    [
        "place", "bib", "name", "relay_team", "gender", "gender_place",
        "category", "category_place", "age", "division", "guntime", "prime",
        "chiptime", "city", "ismasters", "splits", "member", "hasphotos",
        "youtube_url", "masters_place", "isrwpb", "isrwfirst",
    ],
)
named_split = namedtuple("ns", ["split_num", "split_time"])

ORACLE_LOOP = """
{% for r in results %}
            <tr>
              <td class="text-center">{{ r.place|get_place }}</td>
              <td class="text-center">{{ r.bib }}</td>
              <td class="text-left">
                {% if r.member %}
                  <a href="/member/{{ r.member.slug }}/">{{ r.name }}</a>
                {% else %}
                  {{ r.name }}
                {% endif %}
                {% if r.gender_place == 1 %}
                  <i class="fas fa-trophy fa-icon-1st-oa"
                     title="1st Overall ({{ r.gender }})"></i>
                {% elif r.gender_place == 2 %}
                  <i class="fas fa-medal fa-icon-2nd-oa"
                     title="2nd Overall ({{ r.gender }})"></i>
                {% elif r.gender_place == 3 %}
                  <i class="fas fa-medal fa-icon-3rd-oa"
                     title="3rd Overall ({{ r.gender }})"></i>
                {% endif %}
                {% if r.masters_place == 1 %}
                  <i class="fas fa-medal fa-icon-1st-master"
                     title="1st Master ({{ r.gender }})"></i>
                {% endif %}
                {% if r.isrwpb and r.member %}
                  <i class="fas fa-stopwatch fa-icon-pb"
                     title="RW PB for the {{ event.distance.name }}"></i>
                {% endif %}
                {% if r.isrwfirst %}
                  <i class="fa-solid fa-hand-wave fa-icon-firstrace"
                     title="Welcome new RW member!"></i>
                {% endif %}
                {% if r.relay_team %}<i class="fas fa-users" title="{{ r.relay_team }}"></i>{% endif %}
              </td>
              {% if phototags %}
                {% if r.hasphotos %}
                  <td class="text-center">
                    <a href="https://www.flickr.com/photos/runwaterloo/tags/{{ event.flickrsearchstr }},{{ r.bib }}"
                       target="_blank">
                      <i class="fas fa-camera"></i>
                    </a>
                  </td>
                {% else %}
                  <td></td>
                {% endif %}
              {% endif %}
              {% if event.youtube_id and event.youtube_offset_seconds is not None %}
                {% if r.youtube_url %}
                  <td class="text-center">
                    <a href="{{ r.youtube_url }}" target="_blank">
                      <i class="fas fa-video"></i>
                    </a>
                  </td>
                {% else %}
                  <td></td>
                {% endif %}
              {% endif %}
              {% if guntimes_have_microseconds %}
                <td class="text-center">{{ r.guntime|round_up }}</td>
              {% else %}
                <td class="text-center">{{ r.guntime }}</td>
              {% endif %}
              {% if hill_dict %}<td class="text-center">{{ r.prime }}</td>{% endif %}
              <td class="text-center">{{ r.gender }}</td>
              <td class="text-center">{{ r.gender_place }}</td>
              {% if show_category %}
                <td class="text-center">{{ r.category }}</td>
                <td class="text-center">{{ r.category_place }}</td>
              {% endif %}
              {% if show_age %}
                <td class="text-center">{{ r.age }}</td>
              {% endif %}
              {% if hasdivision %}
                {% if r.division != "Guest" %}
                  <td class="text-left">
                    <a href="/endurrun/{{ r.division|lower }}/?year={{ event.date.year }}">{{ r.division }}</a>
                  </td>
                {% else %}
                  <td class="text-left">{{ r.division }}</td>
                {% endif %}
              {% endif %}
              <td class="text-center">{{ r.guntime|get_pace:event.distance.km }}</td>
              {% if show_chip %}
                {% if guntimes_have_microseconds %}
                  <td class="text-center">{{ r.chiptime|round_up }}</td>
                {% else %}
                  <td class="text-center">{{ r.chiptime }}</td>
                {% endif %}
              {% endif %}
              <td class="text-left">{{ r.city }}</td>
              {% for s in r.splits %}
                {% if s.split_time != "None" %}
                  {% if splits_have_microseconds %}
                    <td class="text-center">{{ s.split_time|show_str_decimal }}</td>
                  {% else %}
                    <td class="text-center">{{ s.split_time }}</td>
                  {% endif %}
                {% else %}
                  <td></td>
                {% endif %}
              {% endfor %}
            </tr>
          {% endfor %}
"""
ORACLE_TEMPLATE = "{% load racedbapp_extras %}" + ORACLE_LOOP


class FakeMember:
    def __init__(self, slug):
        self.slug = slug


def make_row(**overrides):
    defaults = dict(
        place=1,
        bib=101,
        name="Jane <b>Smith</b> & Co",
        relay_team=False,
        gender="F",
        gender_place=1,
        category="30-39",
        category_place=1,
        age=41,
        division="Open",
        guntime=datetime.timedelta(seconds=1200, microseconds=500000),
        prime="",
        chiptime=datetime.timedelta(seconds=1199),
        city="Waterloo <script>",
        ismasters=True,
        splits=[named_split(1, "10:00.5"), named_split(2, ""), named_split(3, "None")],
        member=FakeMember("jane-smith"),
        hasphotos=True,
        youtube_url="https://youtu.be/x?t=1m2s",
        masters_place=1,
        isrwpb=True,
        isrwfirst=True,
    )
    defaults.update(overrides)
    return named_result(**defaults)


def event_stub(**overrides):
    class E:
        pass

    e = E()
    e.distance = type("D", (), {"km": 5, "name": "5 Km"})()
    e.distance.km = 5
    e.distance.name = "5 Km"
    e.date = datetime.date(2026, 10, 31)
    e.flickrsearchstr = "trickortrot"
    e.youtube_id = ""
    e.youtube_offset_seconds = None
    for k, v in overrides.items():
        setattr(e, k, v)
    return e


BASE_CTX = dict(
    phototags=False,
    show_category=False,
    show_age=False,
    hasdivision=False,
    show_chip=False,
    guntimes_have_microseconds=False,
    splits_have_microseconds=False,
    hill_dict=None,
    event=event_stub(),
)


def render_both(rows, ctx):
    context = dict(BASE_CTX)
    context.update(ctx)
    oracle = Template(ORACLE_TEMPLATE).render(Context({**context, "results": rows}))
    fast = render_rows(
        rows,
        context["event"],
        context["phototags"],
        context["show_category"],
        context["show_age"],
        context["hasdivision"],
        context["show_chip"],
        context["guntimes_have_microseconds"],
        context["splits_have_microseconds"],
        context["hill_dict"],
    )
    return oracle, fast


class EventRowsEquivalenceTests(django.test.SimpleTestCase):
    @staticmethod
    def norm(html_out):
        """Collapse inter-tag whitespace so template indentation is ignored."""
        html_out = re.sub(r">\s+", ">", html_out)
        html_out = re.sub(r"\s+<", "<", html_out)
        html_out = re.sub(r'"\s+(\w+=)', r'"\1', html_out)  # attr line-wraps in template source
        return html_out.strip()

    def assert_same_html(self, rows, ctx):
        oracle, fast = render_both(rows, ctx)
        self.assertEqual(self.norm(oracle), self.norm(fast))

    def test_award_icons_and_member_link(self):
        rows = [
            make_row(),
            make_row(place=2, gender_place=2, member=None, isrwpb=False, masters_place=False),
            make_row(place=3, gender_place=3, masters_place=False, isrwfirst=False),
            make_row(place=4, gender_place=4, masters_place=False, isrwpb=False, isrwfirst=False),
            make_row(relay_team="Team Fast"),
        ]
        self.assert_same_html(rows, {})

    def test_all_column_flags(self):
        rows = [make_row(), make_row(place=990001, guntime=datetime.timedelta(seconds=1500), chiptime=None)]
        for ctx in [
            {"phototags": True},
            {"show_category": True},
            {"show_age": True},
            {"hasdivision": True},
            {"show_chip": True},
            {"hill_dict": {1: "1:00"}},
        ]:
            with self.subTest(**ctx):
                self.assert_same_html(rows, ctx)

    def test_microsecond_variants(self):
        rows = [make_row(), make_row(place=2, gender_place=2)]
        self.assert_same_html(rows, {"guntimes_have_microseconds": True, "splits_have_microseconds": True})

    def test_youtube_column(self):
        rows = [make_row(), make_row(place=2, gender_place=2, youtube_url=False)]
        event = event_stub(youtube_id="abc123", youtube_offset_seconds=0)
        self.assert_same_html(rows, {"event": event})

    def test_division_guest(self):
        rows = [make_row(division="Guest")]
        self.assert_same_html(rows, {"hasdivision": True})

    def test_values_are_escaped(self):
        html_out, _ = render_both([make_row()], {})
        self.assertNotIn("<script>", self.norm(html_out))
        self.assertIn("&lt;script&gt;", self.norm(html_out))
