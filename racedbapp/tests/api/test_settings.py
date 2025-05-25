from django.conf import settings


def test_rest_framework_renderers():
    renderers = settings.REST_FRAMEWORK.get("DEFAULT_RENDERER_CLASSES", [])
    assert "rest_framework.renderers.JSONRenderer" in renderers, (
        "JSONRenderer must be enabled in DEFAULT_RENDERER_CLASSES"
    )
    assert "rest_framework.renderers.BrowsableAPIRenderer" in renderers, (
        "BrowsableAPIRenderer must be enabled in DEFAULT_RENDERER_CLASSES"
    )
