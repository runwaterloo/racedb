import pytest

from racedbapp.admin import delete_all_results_for_event
from racedbapp.models import Event, Result


class DummyRequest:
    def __init__(self, user):
        self.user = user
        self._messages = []

    def _get_messages(self):
        return self._messages

    def __getattr__(self, name):
        return None


class DummyModelAdmin:
    def __init__(self):
        self.messages = []

    def message_user(self, request, message):
        self.messages.append(message)


@pytest.mark.django_db
def test_delete_all_results_for_event(create_category, create_event, create_result):
    """
    Test deleting all results for a specific event.
    This test creates a category, two events, and two results,
    then deletes results for one of the events and checks that only one result remains."""
    category = create_category()
    event1 = create_event(name_suffix="a")
    event2 = create_event(name_suffix="b")
    create_result(category=category, event=event1)
    create_result(category=category, event=event2)
    assert Result.objects.count() == 2
    queryset = Event.objects.filter(id=event1.id)
    modeladmin = DummyModelAdmin()
    request = DummyRequest(user=None)
    delete_all_results_for_event(modeladmin, request, queryset)
    assert Result.objects.count() == 1
