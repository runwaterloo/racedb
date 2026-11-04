from django.http import HttpResponse, HttpResponsePermanentRedirect

from racedbapp.shared.tracing import tracer


class TracingMiddleware:
    """Open one span around the whole middleware chain.

    Attached first (after whitenoise/prometheus-before), so queries made
    by SessionMiddleware, AuthenticationMiddleware, etc. nest under it
    instead of appearing as bare root-level SELECTs in traces. The view
    span becomes its child, keeping the whole tree coherent.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with tracer.start_as_current_span("request: middleware chain"):
            return self.get_response(request)

# Paths unauthenticated users may still reach on the gated QA site:
# the login page and its static assets, plus "/admin/" (exact match) so
# its 302 redirect to /admin/login/ works in a browser.
ALLOWED_EXACT = ("/admin/",)
ALLOWED_PREFIXES = ("/admin/login",)


class QaAuthGateMiddleware:
    """
    Reject unauthenticated requests. Attached only where SETTINGS=dev
    (racedb.runwaterloo.com, the QA site) via settings.py, so production
    carries no added per-request cost and no Host detection is needed.

    Requests without a session cookie are rejected without any DB access:
    SessionMiddleware only loads a session when a cookie is present.
    Rejections are a bare 401 — no redirect, so crawlers don't fan out to
    the login page.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/admin":
            return HttpResponsePermanentRedirect("/admin/")
        if request.path in ALLOWED_EXACT or request.path.startswith(ALLOWED_PREFIXES):
            return self.get_response(request)

        if request.user.is_authenticated:
            return self.get_response(request)

        return HttpResponse("Unauthorized", status=401)
