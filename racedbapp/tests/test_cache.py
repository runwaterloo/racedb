import uuid

from django.core.cache import cache


def test_cache_set_and_get_behavior():
    key = f"test_key_{uuid.uuid4()}"
    value = "value1"
    cache.set(key, value)
    get_result = cache.get(key)
    assert get_result == value
