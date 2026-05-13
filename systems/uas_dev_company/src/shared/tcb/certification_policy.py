"""Нормализация статусов ответов Регулятора для сертификации и регистрации."""

from __future__ import annotations


def regulator_certify_status_ok(status: str) -> bool:
    return str(status or "").lower() in {"certified", "registered", "accepted"}


def regulator_register_status_ok(status: str) -> bool:
    return str(status or "").lower() in {"registered", "accepted", "reregistered"}


def regulator_reregistration_status_ok(status: str) -> bool:
    return str(status or "").lower() in {"reregistered", "registered", "accepted"}
