import pytest

from auth import DEFAULT_SECRET_KEY, PRODUCTION_SECRET_KEY_ERROR, get_secret_key


def test_local_development_without_secret_key_uses_fallback():
    secret_key = get_secret_key({})

    assert secret_key == DEFAULT_SECRET_KEY


def test_render_without_secret_key_fails_fast():
    with pytest.raises(RuntimeError, match=PRODUCTION_SECRET_KEY_ERROR):
        get_secret_key({"RENDER": "true"})


def test_production_without_secret_key_fails_fast():
    with pytest.raises(RuntimeError, match=PRODUCTION_SECRET_KEY_ERROR):
        get_secret_key({"ENVIRONMENT": "production"})


def test_render_with_fallback_secret_key_fails_fast():
    with pytest.raises(RuntimeError, match=PRODUCTION_SECRET_KEY_ERROR):
        get_secret_key({"RENDER": "true", "SECRET_KEY": DEFAULT_SECRET_KEY})


def test_production_with_real_secret_key_works():
    secret_key = get_secret_key(
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a-strong-production-secret-key"
        }
    )

    assert secret_key == "a-strong-production-secret-key"
