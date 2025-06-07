from rest_framework import status
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None and response.status_code == status.HTTP_403_FORBIDDEN:
        request = context.get("request")
        if request is not None:
            host = request.build_absolute_uri("/")[:-1]
            login_url = f"{host}/admin/login/?next=/v1/"
        else:
            login_url = "/admin/login/?next=/v1/"
        response.data = {
            "message": "You are not authorized to access this resource.",
            "login_url": login_url,
        }
    return response
