from collections import namedtuple
from urllib import parse

namedresult = namedtuple(
    "nr",
    [
        "place",
        "guntime",
        "athlete",
        "year",
        "category",
        "city",
        "age",
        "race_slug",
        "member",
    ],
)
namedteamrecord = namedtuple(
    "ntr",
    [
        "team_category_name",
        "team_category_slug",
        "total_time",
        "winning_team",
        "year",
        "avg_time",
        "race_slug",
    ],
)

class Choice():
    def __init__(self, name, url):
        self.name = name
        self.url = parse.quote_plus(url, safe="/&?=")

    def __eq__(self, other):
        return self.name == other.name and self.url == other.url

    def __lt__(self, other):
        return self.name < other.name

class Filter():
    def __init__(self, current, choices):
        self.current = current
        self.choices = choices

    def __eq__(self, other):
        return self.current == other.current and self.choices == other.choices