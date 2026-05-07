"""Domain models and validation helpers for the UAS development company."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from shared.tcb.cb_constants import normalize_canonical_security_goals
from shared.topics import Roles


def _require(value: str, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


@dataclass(frozen=True)
class UserAccount:
    """System user with an assigned role and password hash."""

    username: str
    role: str
    password_hash: str
    is_active: bool = True

    def __post_init__(self) -> None:
        _require(self.username, "username")
        _require(self.password_hash, "password_hash")
        if self.role not in Roles.ALL:
            raise ValueError(f"unsupported role: {self.role}")


@dataclass(frozen=True)
class FirmwareVersion:
    """Firmware submitted for certification (локальный артефакт или сборка из репозитория по коммиту)."""

    firmware_id: str
    supplier: str
    drone_type: str
    version: str
    security_goals: tuple[str, ...]
    authenticity_proof: str
    firmware_hash: str = ""
    source_repo_url: str = ""
    source_commit: str = ""

    def __post_init__(self) -> None:
        _require(self.firmware_id, "firmware_id")
        _require(self.supplier, "supplier")
        _require(self.drone_type, "drone_type")
        _require(self.version, "version")
        _require(self.authenticity_proof, "authenticity_proof")
        h = str(self.firmware_hash or "").strip()
        repo = str(self.source_repo_url or "").strip()
        commit = str(self.source_commit or "").strip()
        if not h and (not repo or not commit):
            raise ValueError("нужно указать firmware_hash или пару source_repo_url + source_commit")
        if not self.security_goals:
            raise ValueError("security_goals are required")
        normalize_canonical_security_goals(self.security_goals, allow_empty=False)


@dataclass(frozen=True)
class CertificationRequest:
    """Certification request tracked by the developer company."""

    request_id: str
    firmware_id: str
    requested_by: str
    status: str
    certification_cost: float

    def __post_init__(self) -> None:
        _require(self.request_id, "request_id")
        _require(self.firmware_id, "firmware_id")
        _require(self.requested_by, "requested_by")
        _require(self.status, "status")
        if self.certification_cost < 0:
            raise ValueError("certification_cost must be non-negative")


@dataclass(frozen=True)
class Certificate:
    """Signed certificate received from the regulator."""

    certificate_id: str
    firmware_id: str
    security_goals: tuple[str, ...]
    signed_by: str

    def __post_init__(self) -> None:
        _require(self.certificate_id, "certificate_id")
        _require(self.firmware_id, "firmware_id")
        _require(self.signed_by, "signed_by")
        if not self.security_goals:
            raise ValueError("security_goals are required")
        normalize_canonical_security_goals(self.security_goals, allow_empty=False)


@dataclass(frozen=True)
class DroneRegistryRecord:
    """Registered certified drone available for sale or already sold."""

    serial_number: str
    drone_type: str
    firmware_id: str
    certificate_id: str
    security_goals: tuple[str, ...]
    price: float
    status: str = "available"

    def __post_init__(self) -> None:
        _require(self.serial_number, "serial_number")
        _require(self.drone_type, "drone_type")
        _require(self.firmware_id, "firmware_id")
        _require(self.certificate_id, "certificate_id")
        _require(self.status, "status")
        # ЦБ экземпляра могут быть пустыми; непустой набор — только ЦБ-1…ЦБ-3 и подмножество сертификата (ТБ-2).
        if self.price < 0:
            raise ValueError("price must be non-negative")
        normalize_canonical_security_goals(self.security_goals, allow_empty=True)


@dataclass(frozen=True)
class PurchaseOrder:
    """Purchase order created by an operator."""

    order_id: str
    serial_number: str
    operator_username: str

    def __post_init__(self) -> None:
        _require(self.order_id, "order_id")
        _require(self.serial_number, "serial_number")
        _require(self.operator_username, "operator_username")


@dataclass(frozen=True)
class SecurityEvent:
    """Security event stored in the local audit log."""

    event_type: str
    severity: str
    source: str
    subject: str
    details: str = ""

    def __post_init__(self) -> None:
        _require(self.event_type, "event_type")
        _require(self.severity, "severity")
        _require(self.source, "source")
        _require(self.subject, "subject")


def normalize_goals(goals: Iterable[str]) -> tuple[str, ...]:
    """Нормализация целей прошивки/сертификата: непустое множество из {ЦБ-1, ЦБ-2, ЦБ-3}."""
    return normalize_canonical_security_goals(goals, allow_empty=False)


def normalize_drone_goals(goals: Iterable[str]) -> tuple[str, ...]:
    """Цели экземпляра: только {ЦБ-1…ЦБ-3}; пустой набор допустим."""
    return normalize_canonical_security_goals(goals, allow_empty=True)
