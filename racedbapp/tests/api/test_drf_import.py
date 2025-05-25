def test_drf_can_be_imported():
    try:
        import rest_framework  # noqa: F401
    except ImportError:
        assert False, "Django REST framework is not installed or cannot be imported"


def test_drf_nested_can_be_imported():
    try:
        import rest_framework_nested.routers  # noqa: F401
    except ImportError:
        assert False, "drf-nested-routers is not installed or cannot be imported"
