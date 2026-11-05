import json
import logging
import os
import time

from django.http import HttpResponse, HttpResponsePermanentRedirect

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


# --- Request logging middleware (prototype) ---

_reqlog = logging.getLogger("racedb.request")

# Paths not worth logging: internal + django-prometheus scrape endpoint.
_SKIP_PREFIXES = ("/static/", "/favicon", "/metrics")


class RequestLoggingMiddleware:
    """
    One structured JSON line per request, written at the end of the
    middleware chain so the timer covers everything (all middleware,
    view, template, middleware-on-the-way-out).

    Trace linkage: if TRACING=on the OTel Django instrumentation opened
    its span BEFORE middlewares run, so the current span here is the
    request span and carries trace_id/span_id for Loki<->Tempo joins.

    If tracing is off (TRACING != on) the span context is invalid —
    emit "-" so the JSON keys stay consistent in both modes.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.urls import resolve
        from opentelemetry import trace as _trace

        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)

        if any(request.path.startswith(p) for p in _SKIP_PREFIXES):
            return response

        try:
            match = resolve(request.path)
            view = match.view_name or "-"
            kwargs = match.kwargs or {}
        except Exception:
            view, kwargs = "-", {}

        span = _trace.get_current_span()
        sc = span.get_span_context() if span else None
        if sc and sc.is_valid:
            trace_id = f"{sc.trace_id:032x}"
            span_id = f"{sc.span_id:016x}"
        else:
            trace_id = span_id = "-"

        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        client_ip = xff.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "-")

        entry = {
            "date-time": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.gmtime()
            ),
            "env": os.getenv("SETTINGS", "none"),
            "method": request.method,
            "path": request.path,
            "qstring": request.META.get("QUERY_STRING", ""),
            "status": response.status_code,
            "duration_ms": duration_ms,
            "view": view,
            "view_kwargs": kwargs,
            "trace_id": trace_id,
            "span_id": span_id,
            "client_ip": client_ip,
            "user_agent": (request.META.get("HTTP_USER_AGENT", "") or "-")[:200],
        }
        try:
            entry["response_bytes"] = len(response.content)
        except Exception:
            entry["response_bytes"] = None

        if response.status_code >= 500:
            _reqlog.error(json.dumps(entry))
        else:
            _reqlog.info(json.dumps(entry))
        return response

