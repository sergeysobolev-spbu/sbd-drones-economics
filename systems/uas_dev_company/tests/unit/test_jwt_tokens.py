"""Тесты JWT для API-аутентификации."""

from __future__ import annotations

import pytest

from shared.jwt_tokens import TokenError, create_access_token, verify_access_token


def test_round_trip_payload():
    tok = create_access_token("secret-one", "alice", "разработчик")
    payload = verify_access_token("secret-one", tok)
    assert payload["sub"] == "alice"
    assert payload["role"] == "разработчик"


def test_wrong_secret():
    tok = create_access_token("secret-a", "u", "эксплуатант")
    with pytest.raises(TokenError):
        verify_access_token("secret-b", tok)


def test_empty_secret_rejected():
    with pytest.raises(ValueError):
        create_access_token("", "u", "администратор")
