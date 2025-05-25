import pytest
from django.contrib.admin.sites import AdminSite

from racedbapp.admin import RwmemberAdmin
from racedbapp.models import Rwmember


@pytest.mark.django_db
def test_member_tags_method(create_rwmember, create_tag):
    # Create a member and a tag, and assign the tag to the member
    member = create_rwmember(name_suffix="A", active=True)
    tag = create_tag(name="TestTag", auto_select=True)
    member.tags.add(tag)
    admin = RwmemberAdmin(Rwmember, AdminSite())
    result = admin.member_tags(member)
    assert "TestTag" in result
    # Also test with no tags
    member.tags.clear()
    result = admin.member_tags(member)
    assert result == ""
