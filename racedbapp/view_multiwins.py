import urllib
from collections import namedtuple
from operator import attrgetter

from django.shortcuts import render

from racedbapp.shared.types import Choice, Filter

from .shared import shared


def index(request):
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    gender = False
    if "gender" in qstring:
        gender = qstring["gender"][0]
    namedwinner = namedtuple("nw", ["rank", "wins", "gender", "athlete", "member"])
    malewinnersdict, femalewinnersdict = shared.getwinnersdict()
    femalewinnerscount = {}
    femalewinners = []
    for k, v in femalewinnersdict.items():
        if v.athlete.lower() in femalewinnerscount:
            femalewinnerscount[v.athlete.lower()] += 1
        else:
            femalewinnerscount[v.athlete.lower()] = 1
    for k, v in femalewinnerscount.items():
        femalewinners.append(namedwinner(0, v, "F", k.title(), False))
    malewinnerscount = {}
    for k, v in malewinnersdict.items():
        if v.athlete.lower() in malewinnerscount:
            malewinnerscount[v.athlete.lower()] += 1
        else:
            malewinnerscount[v.athlete.lower()] = 1
    malewinners = []
    for k, v in malewinnerscount.items():
        malewinners.append(namedwinner(0, v, "M", k.title(), False))
    combinedwinners = malewinners + femalewinners
    winners = []
    member_dict = shared.get_member_dict()
    seen_members = {}
    for i in combinedwinners:
        if gender:
            if i.gender.lower() != gender:
                continue
        member = False
        if i.athlete.lower() in member_dict:
            member = member_dict[i.athlete.lower()]
            if member in seen_members:
                seen_members[member] += i.wins
                thiswins = seen_members[member]
                winners = [x for x in winners if x.member != member]
            else:
                seen_members[member] = i.wins
                thiswins = i.wins
        else:
            thiswins = i.wins
        winners.append(namedwinner(0, thiswins, i.gender, i.athlete, member))
    winners = sorted(winners, key=attrgetter("athlete"))
    winners = sorted(winners, key=attrgetter("wins"), reverse=True)
    winners = [x for x in winners if x.wins > 1]
    finalwinners = []
    wins = 999999
    for c, w in enumerate(winners):
        if w.wins < wins:
            wins = w.wins
            rank = c + 1
        finalwinners.append(namedwinner(rank, w.wins, w.gender, w.athlete, w.member))
    genderfilter = get_genderfilter(gender)
    context = {"winners": finalwinners, "genderfilter": genderfilter}
    return render(request, "racedbapp/multiwins.html", context)


def get_genderfilter(gender):
    choices = []
    if gender:
        choices.append(Choice("", "/multiwins"))
        if gender == "m":
            current = "Male"
        else:
            current = "Female"
    else:
        current = ""
    if gender != "f":
        choices.append(Choice("Female", "/multiwins?gender=f"))
    if gender != "m":
        choices.append(Choice("Male", "/multiwins?gender=m"))
    genderfilter = Filter(current, choices)
    return genderfilter
