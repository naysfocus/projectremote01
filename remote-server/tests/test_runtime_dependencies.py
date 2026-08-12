def test_session_middleware_runtime_dependency_is_available():
    import itsdangerous  # noqa: F401
    from starlette.middleware.sessions import SessionMiddleware

    assert SessionMiddleware is not None


def test_integration_encryption_dependency_is_available():
    from cryptography.fernet import Fernet

    assert Fernet is not None
