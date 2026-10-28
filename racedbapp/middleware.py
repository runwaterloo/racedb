from django.conf import settings
from django.http import HttpResponse

# Paths on gated hosts that unauthenticated users may still reach.
ALLOWED_PATH_PREFIXES = (
    "/admin/login",
)


class QaAuthGateMiddleware:
    """
    Reject unauthenticated requests to gated hosts (e.g. the QA site at
    racedb.runwaterloo.com). Hosts not listed in QA_AUTH_HOSTS are passed
    through untouched, so production is unaffected. Gated requests that are
    not on the allowlist and have no authenticated session get a bare 401 —
    no redirect, so crawlers don't fan out to a login page.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        gated_hosts = getattr(settings, "QA_AUTH_HOSTS", [])
        if request.get_host() not in gated_hosts:
            return self.get_response(request)

        path = request.path
        if path.startswith(ALLOWED_PATH_PREFIXES):
            return self.get_response(request)

        if request.user.is_authenticated:
            return self.get_response(request)

        return HttpResponse("Unauthorized", status=401)
