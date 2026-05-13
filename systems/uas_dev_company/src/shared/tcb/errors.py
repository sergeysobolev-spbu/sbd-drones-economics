"""Ошибки авторизации в контуре ДВБ."""


class AuthorizationError(PermissionError):
    """Raised when a user is not allowed to perform an operation."""
