def test_drf_can_be_imported():
    try:
        import rest_framework  # noqa: F401
    except ImportError:
        assert False, "Django REST framework is not installed or cannot be imported"
