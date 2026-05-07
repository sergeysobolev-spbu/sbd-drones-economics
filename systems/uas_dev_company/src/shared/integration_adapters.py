"""Порты интеграции с Регулятором, Эксплуатантом, Дронопортом и DroneAnalytics (тестовые моки реализуют те же методы)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RegulatorPort(Protocol):
    """Брокерный контракт Регулятора (синхронное поднятие в тестах)."""

    def certify_firmware(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """Сертификация прошивки; envelope содержит payload с метаданными прошивки и correlation_id."""

    def register_drone_instance(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """Регистрация экземпляра; ответ: status, registration_id, registration_version, reason_code."""

    def reregister_drone_instance(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """Перерегистрация владельца после продажи."""

    def report_critical_vulnerability(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """Уведомление об уязвимости; ответ: decision, effective_security_goals (опционально), reason_code."""


@runtime_checkable
class OperatorFleetPort(Protocol):
    """Проекция событий для парка Эксплуатанта."""

    def import_drone_reregistered(self, envelope: dict[str, Any]) -> None:
        """Импорт события drone_reregistered (или эквивалента)."""

    def apply_regulator_firmware_decision(self, envelope: dict[str, Any]) -> None:
        """Массовое обновление после отзыва/смены ЦБ по прошивке."""


@runtime_checkable
class DronePortPort(Protocol):
    """Доставка / постановка дрона в дронпорт назначения через брокер."""

    def accept_delivered_drone(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """Подтверждение приёма дрона в порту; ответ: status ok|rejected, reason_code."""


@runtime_checkable
class DroneAnalyticsPort(Protocol):
    """Центральный журнал (HTTP /log/event или фейк)."""

    def post_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Отправить EventLogItem (dict); возвращает {ok: bool, error?: str, status_code?: int}."""
