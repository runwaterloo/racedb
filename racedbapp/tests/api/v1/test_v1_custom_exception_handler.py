from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from racedbapp.api.v1.exceptions import custom_exception_handler


def test_custom_exception_handler_no_request():
    exc = PermissionDenied()
    context = {"request": None}
    response = custom_exception_handler(exc, context)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["login_url"] == "/admin/login/?next=/v1/"
    assert response.data["detail"] == "Unauthorized. Login or provide a valid token."


def test_custom_exception_handler_response_none():
    # Pass an exception that DRF's exception_handler does not handle
    class NotHandledException(Exception):
        pass

    exc = NotHandledException()
    context = {}
    response = custom_exception_handler(exc, context)
    assert response is None
