from racedbapp.api.v1.serializers import V1DistanceSerializer, V1EventSerializer


def test_distance_serializer_results_url_no_request(db, create_distance):
    distance = create_distance()
    serializer = V1DistanceSerializer(distance, context={})
    data = serializer.data
    # When no request is in context, should return relative url
    assert data["results_url"] == f"/v1/distances/{distance.id}/results/"


def test_event_serializer_results_url_no_request(db, create_event):
    event = create_event()
    serializer = V1EventSerializer(event, context={})
    data = serializer.data
    # When no request is in context, should return relative url
    assert data["results_url"] == f"/v1/events/{event.id}/results/"
