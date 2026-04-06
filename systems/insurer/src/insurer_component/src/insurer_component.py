"""
InsurerComponent -- бизнес-логика страховщика.

Реализует две модели страхования:

1. Годовое страхование (Pannual) — КАСКО/hull, оформляется при регистрации дрона:
       Pannual = Vdrone × Rbase_hull × Kfleet_history

2. Миссионное страхование (Pmission) — рассчитывается смарт-контрактом перед каждым вылетом:
       Pmission = Vcargo × Rrisk_class × Kenv × Kincident_history
   где:
       Kincident_history = Kbase + (Incidents / Total_Missions) × L

Интеграция с Fabric-леджером:
    Если задана переменная ENABLE_FABRIC_LEDGER=true, после каждого успешного
    оформления полиса компонент публикует запись в systems.dummy_fabric (fire-and-forget).
    Основная операция не блокируется и не падает, если Fabric недоступен.
"""
import os
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus

from systems.insurer.src.insurer_component.topics import (
    ComponentTopics,
    ExternalTopics,
    InsurerActions,
)

_FABRIC_ENABLED = os.environ.get("ENABLE_FABRIC_LEDGER", "false").lower() == "true"


class InsurerComponent(BaseComponent):

    # --- Годовое страхование (hull/КАСКО) ---

    # Базовые ставки корпуса по типу дрона (Rbase_hull)
    HULL_RATE_BY_TYPE: Dict[str, Decimal] = {
        "inspector": Decimal("0.05"),
        "delivery": Decimal("0.08"),
        "firefighter": Decimal("0.12"),
    }
    HULL_RATE_DEFAULT = Decimal("0.07")

    # Kfleet_history — коэффициент надёжности флота
    KFLEET_NEW = Decimal("1.0")       # < 10 полётов, статистика не накоплена
    KFLEET_DISCOUNT = Decimal("0.8")  # > 100 полётов, аварийность < 2%
    KFLEET_PENALTY = Decimal("1.5")   # аварийность > 5%

    POLICY_ANNUAL_DURATION_DAYS = 365

    # --- Миссионное страхование ---

    # Базовая вероятность отказа по типу дрона (Rrisk_class)
    RISK_CLASS_RATE: Dict[str, Decimal] = {
        "inspector": Decimal("0.01"),
        "delivery": Decimal("0.08"),
        "firefighter": Decimal("0.12"),
    }
    RISK_CLASS_RATE_DEFAULT = Decimal("0.08")

    # Kenv (1.0–2.0) — коэффициент сложности среды (по умолчанию нейтральный)
    KENV_DEFAULT = Decimal("1.0")

    # Kincident_history параметры
    KBASE_DEFAULT = Decimal("1.0")    # базовое значение для нового дрона
    KBASE_IDEAL = Decimal("0.8")      # для дронов с идеальной историей (N >= 500)
    IDEAL_MISSIONS_THRESHOLD = 500
    LEVERAGE_DEFAULT = Decimal("1.0") # коэффициент чувствительности (L)

    POLICY_MISSION_DURATION_DAYS = 1  # миссионный полис активен на время миссии

    # --- Обратная совместимость (устаревшая КБМ-модель) ---
    BASE_COST = Decimal("1000.00")
    BASE_KBM = Decimal("1.00")
    POLICY_DURATION_DAYS = 30
    KBM_INCIDENT_MULTIPLIER = Decimal("1.10")

    def __init__(self, component_id: str, bus: SystemBus):
        # Хранилища полисов и инцидентов
        self._policies: Dict[str, Dict[str, Any]] = {}
        self._incidents: Dict[str, Dict[str, Any]] = {}

        # Статистика по дронам: { drone_id: {"total_missions": int, "incidents": int} }
        self._drone_stats: Dict[str, Dict[str, int]] = {}

        # Legacy КБМ
        self._kbm_history: list = []
        self._manufacturer_kbms: Dict[str, Decimal] = {}
        self._operator_kbms: Dict[str, Decimal] = {}

        super().__init__(
            component_id=component_id,
            component_type="insurer_component",
            topic=ComponentTopics.INSURER_COMPONENT,
            bus=bus,
        )

    # -------------------------------------------------------------------------
    # Fabric dual-write (fire-and-forget)
    # -------------------------------------------------------------------------

    def _try_fabric(self, action: str, payload: Dict[str, Any]) -> None:
        """
        Публикует событие в systems.dummy_fabric (fire-and-forget).

        Не блокирует основную операцию: ошибки только логируются.
        Активируется через переменную окружения ENABLE_FABRIC_LEDGER=true.
        """
        if not _FABRIC_ENABLED:
            return
        try:
            self.bus.publish(
                ExternalTopics.FABRIC,
                {
                    "action": action,
                    "sender": self.component_id,
                    "payload": payload,
                },
            )
        except Exception as exc:
            print(f"[{self.component_id}] Fabric write skipped ({action}): {exc}")

    def _register_handlers(self):
        self.register_handler(InsurerActions.ANNUAL_INSURANCE, self._handle_annual_insurance)
        self.register_handler(InsurerActions.MISSION_INSURANCE, self._handle_mission_insurance)
        self.register_handler(InsurerActions.REPORT_INCIDENT, self._handle_incident)
        self.register_handler(InsurerActions.TERMINATE_POLICY, self._handle_terminate)
        # Обратная совместимость
        self.register_handler(InsurerActions.CALCULATE_POLICY, self._handle_calculate_legacy)
        self.register_handler(InsurerActions.PURCHASE_POLICY, self._handle_purchase_legacy)

    # -------------------------------------------------------------------------
    # Годовое страхование (Pannual)
    # -------------------------------------------------------------------------

    def _get_hull_rate(self, drone_type: str) -> Decimal:
        return self.HULL_RATE_BY_TYPE.get(drone_type.lower(), self.HULL_RATE_DEFAULT)

    def _get_kfleet_history(self, drone_id: str) -> Decimal:
        """
        Kfleet_history по статистике дрона:
          - 1.0  если < 10 полётов (нет статистики)
          - 0.8  если > 100 полётов и аварийность < 2%
          - 1.5  если аварийность > 5%
        """
        stats = self._drone_stats.get(drone_id, {"total_missions": 0, "incidents": 0})
        total = stats["total_missions"]
        incidents = stats["incidents"]

        if total < 10:
            return self.KFLEET_NEW

        accident_rate = incidents / total
        if accident_rate > 0.05:
            return self.KFLEET_PENALTY
        if total > 100 and accident_rate < 0.02:
            return self.KFLEET_DISCOUNT
        return self.KFLEET_NEW

    def _calculate_annual_premium(
        self,
        drone_value: Decimal,
        drone_type: str,
        drone_id: str,
    ) -> Decimal:
        """Pannual = Vdrone × Rbase_hull × Kfleet_history"""
        r_hull = self._get_hull_rate(drone_type)
        k_fleet = self._get_kfleet_history(drone_id)
        return (drone_value * r_hull * k_fleet).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _handle_annual_insurance(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Оформление годового полиса КАСКО при регистрации дрона.

        Ожидаемый payload:
          - drone_id       (str)   идентификатор дрона
          - drone_value    (float) рыночная стоимость аппарата (Vdrone)
          - drone_type     (str)   тип дрона: inspector / delivery / firefighter
          - operator_id    (str)   идентификатор эксплуатанта
          - hull_rate      (float, optional) переопределить Rbase_hull вручную
        """
        payload = message.get("payload", {})
        drone_id = payload.get("drone_id", "")
        operator_id = payload.get("operator_id", "")
        drone_value = Decimal(str(payload.get("drone_value", 0)))
        drone_type = str(payload.get("drone_type", "delivery")).lower()

        if not drone_id:
            raise ValueError("drone_id is required")
        if drone_value <= 0:
            raise ValueError("drone_value must be positive")

        # Переопределение hull rate вручную (необязательно)
        if "hull_rate" in payload:
            r_hull = Decimal(str(payload["hull_rate"]))
        else:
            r_hull = self._get_hull_rate(drone_type)

        k_fleet = self._get_kfleet_history(drone_id)
        premium = (drone_value * r_hull * k_fleet).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        policy_id = str(uuid.uuid4())
        policy_number = f"ANN-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        policy = {
            "id": policy_id,
            "policy_number": policy_number,
            "policy_type": "annual",
            "drone_id": drone_id,
            "operator_id": operator_id,
            "drone_value": str(drone_value),
            "drone_type": drone_type,
            "hull_rate": str(r_hull),
            "kfleet_history": str(k_fleet),
            "premium": str(premium),
            "coverage_amount": str(drone_value),
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=self.POLICY_ANNUAL_DURATION_DAYS)).isoformat(),
            "status": "active",
        }
        self._policies[policy_id] = policy

        result = {
            "policy_id": policy_id,
            "policy_number": policy_number,
            "policy_type": "annual",
            "drone_id": drone_id,
            "premium": str(premium),
            "hull_rate": str(r_hull),
            "kfleet_history": str(k_fleet),
            "coverage_amount": str(drone_value),
            "start_date": policy["start_date"],
            "end_date": policy["end_date"],
            "status": "active",
        }

        # Фиксация годового страхования в Fabric-леджере (fire-and-forget)
        self._try_fabric("create_insurance", {
            "drone_id": drone_id,
            "insurer_id": operator_id or self.component_id,
            "coverage_amount": float(drone_value),
            "incident_count": 0,
            "valid_from": policy["start_date"],
            "valid_to": policy["end_date"],
        })

        return result

    # -------------------------------------------------------------------------
    # Миссионное страхование (Pmission)
    # -------------------------------------------------------------------------

    def _get_risk_class_rate(self, drone_type: str) -> Decimal:
        return self.RISK_CLASS_RATE.get(drone_type.lower(), self.RISK_CLASS_RATE_DEFAULT)

    def _get_kbase(self, drone_id: str) -> Decimal:
        stats = self._drone_stats.get(drone_id, {"total_missions": 0, "incidents": 0})
        if stats["total_missions"] >= self.IDEAL_MISSIONS_THRESHOLD and stats["incidents"] == 0:
            return self.KBASE_IDEAL
        return self.KBASE_DEFAULT

    def _calculate_kincident_history(self, drone_id: str, leverage: Optional[Decimal] = None) -> Decimal:
        """
        Kincident_history = Kbase + (Incidents / Total_Missions) × L

        Для нового дрона (0 вылетов): возвращает Kbase = 1.0
        """
        if leverage is None:
            leverage = self.LEVERAGE_DEFAULT

        stats = self._drone_stats.get(drone_id, {"total_missions": 0, "incidents": 0})
        total = stats["total_missions"]
        incidents = stats["incidents"]
        kbase = self._get_kbase(drone_id)

        if total == 0:
            return kbase

        k = kbase + Decimal(str(incidents)) / Decimal(str(total)) * leverage
        return k.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    def _calculate_mission_premium(
        self,
        cargo_value: Decimal,
        drone_type: str,
        kenv: Decimal,
        drone_id: str,
        leverage: Optional[Decimal] = None,
    ) -> Decimal:
        """Pmission = Vcargo × Rrisk_class × Kenv × Kincident_history"""
        r_risk = self._get_risk_class_rate(drone_type)
        k_incident = self._calculate_kincident_history(drone_id, leverage)
        return (cargo_value * r_risk * kenv * k_incident).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def _handle_mission_insurance(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Оформление миссионного полиса перед каждым вылетом.

        Ожидаемый payload:
          - order_id       (str)   идентификатор заказа/миссии
          - drone_id       (str)   идентификатор дрона
          - cargo_value    (float) объявленная ценность груза (Vcargo)
          - drone_type     (str)   тип дрона: inspector / delivery / firefighter
          - env_factor     (float, optional) Kenv, коэффициент сложности среды (1.0–2.0)
          - leverage       (float, optional) L, коэффициент чувствительности
          - operator_id    (str, optional)
        """
        payload = message.get("payload", {})
        order_id = payload.get("order_id", "")
        drone_id = payload.get("drone_id", "")
        operator_id = payload.get("operator_id", "")
        cargo_value = Decimal(str(payload.get("cargo_value", 0)))
        drone_type = str(payload.get("drone_type", "delivery")).lower()
        kenv = Decimal(str(payload.get("env_factor", self.KENV_DEFAULT)))
        leverage = Decimal(str(payload.get("leverage", self.LEVERAGE_DEFAULT)))

        if not order_id:
            raise ValueError("order_id is required")
        if cargo_value <= 0:
            raise ValueError("cargo_value must be positive")

        r_risk = self._get_risk_class_rate(drone_type)
        k_incident = self._calculate_kincident_history(drone_id, leverage)
        premium = (cargo_value * r_risk * kenv * k_incident).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        policy_id = str(uuid.uuid4())
        policy_number = f"MSN-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        policy = {
            "id": policy_id,
            "policy_number": policy_number,
            "policy_type": "mission",
            "order_id": order_id,
            "drone_id": drone_id,
            "operator_id": operator_id,
            "cargo_value": str(cargo_value),
            "drone_type": drone_type,
            "risk_class_rate": str(r_risk),
            "kenv": str(kenv),
            "kincident_history": str(k_incident),
            "premium": str(premium),
            "coverage_amount": str(cargo_value),
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=self.POLICY_MISSION_DURATION_DAYS)).isoformat(),
            "status": "active",
        }
        self._policies[policy_id] = policy

        # Увеличиваем счётчик вылетов дрона
        self._increment_drone_missions(drone_id)

        result = {
            "policy_id": policy_id,
            "policy_number": policy_number,
            "policy_type": "mission",
            "order_id": order_id,
            "drone_id": drone_id,
            "premium": str(premium),
            "risk_class_rate": str(r_risk),
            "kenv": str(kenv),
            "kincident_history": str(k_incident),
            "coverage_amount": str(cargo_value),
            "start_date": policy["start_date"],
            "end_date": policy["end_date"],
            "status": "active",
        }

        # Фиксация миссионного полиса в Fabric-леджере (fire-and-forget).
        # Используем order_id как идентификатор записи — тот же ID будет
        # использован агрегатором при записи заказа в Fabric.
        self._try_fabric("create_insurance", {
            "drone_id": drone_id,
            "insurer_id": operator_id or self.component_id,
            "coverage_amount": float(cargo_value),
            "incident_count": self._drone_stats.get(drone_id, {}).get("incidents", 0),
            "valid_from": policy["start_date"],
            "valid_to": policy["end_date"],
        })

        return result

    # -------------------------------------------------------------------------
    # Инциденты и завершение полисов
    # -------------------------------------------------------------------------

    def _increment_drone_missions(self, drone_id: str) -> None:
        if drone_id not in self._drone_stats:
            self._drone_stats[drone_id] = {"total_missions": 0, "incidents": 0}
        self._drone_stats[drone_id]["total_missions"] += 1

    def _increment_drone_incidents(self, drone_id: str) -> None:
        if drone_id not in self._drone_stats:
            self._drone_stats[drone_id] = {"total_missions": 0, "incidents": 0}
        self._drone_stats[drone_id]["incidents"] += 1

    def _handle_incident(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка инцидента: регистрация и пересчёт статистики дрона.

        Payload:
          - order_id       (str) для поиска активного полиса
          - drone_id       (str, optional) если не указан — берётся из полиса
          - damage_amount  (float)
          - incident       (dict, optional) детали инцидента
        """
        payload = message.get("payload", {})
        order_id = payload.get("order_id", "")
        damage_amount = Decimal(str(payload.get("damage_amount", 0)))
        incident_data = payload.get("incident", {})

        policy = self._find_policy_by_order(order_id)
        if not policy:
            raise ValueError(f"no active policy for order {order_id}")

        drone_id = payload.get("drone_id") or policy.get("drone_id", "")
        operator_id = payload.get("operator_id") or policy.get("operator_id", "")

        incident_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        incident_record = {
            "id": incident_id,
            "order_id": order_id,
            "policy_id": policy["id"],
            "drone_id": drone_id,
            "damage_amount": str(damage_amount),
            "incident_date": now.isoformat(),
            "status": "processed",
            "details": incident_data,
        }
        self._incidents[incident_id] = incident_record

        # Обновляем статистику дрона (влияет на Kincident_history и Kfleet_history)
        self._increment_drone_incidents(drone_id)

        new_k_incident = self._calculate_kincident_history(drone_id)
        new_k_fleet = self._get_kfleet_history(drone_id)

        # Legacy КБМ (обратная совместимость)
        manufacturer_id = payload.get("manufacturer_id", operator_id)
        old_m_kbm = self._get_manufacturer_kbm(manufacturer_id)
        new_m_kbm = (old_m_kbm * self.KBM_INCIDENT_MULTIPLIER).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        self._manufacturer_kbms[manufacturer_id] = new_m_kbm

        old_o_kbm = self._get_operator_kbm(operator_id)
        new_o_kbm = (old_o_kbm * self.KBM_INCIDENT_MULTIPLIER).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        self._operator_kbms[operator_id] = new_o_kbm

        return {
            "incident_id": incident_id,
            "order_id": order_id,
            "drone_id": drone_id,
            "payment_amount": str(damage_amount),
            "new_kincident_history": str(new_k_incident),
            "new_kfleet_history": str(new_k_fleet),
            "status": "processed",
        }

    def _handle_terminate(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Завершение полиса по order_id."""
        payload = message.get("payload", {})
        order_id = payload.get("order_id", "")

        policy = self._find_policy_by_order(order_id)
        if not policy:
            raise ValueError(f"no active policy for order {order_id}")

        policy["status"] = "terminated"
        policy["end_date"] = datetime.now(timezone.utc).isoformat()

        return {
            "policy_id": policy["id"],
            "order_id": order_id,
            "status": "terminated",
        }

    def _find_policy_by_order(self, order_id: str) -> Optional[dict]:
        for policy in self._policies.values():
            if policy.get("order_id") == order_id and policy["status"] == "active":
                return policy
        return None

    # -------------------------------------------------------------------------
    # Legacy handlers (обратная совместимость)
    # -------------------------------------------------------------------------

    def _get_manufacturer_kbm(self, manufacturer_id: str) -> Decimal:
        return self._manufacturer_kbms.get(manufacturer_id, self.BASE_KBM)

    def _get_operator_kbm(self, operator_id: str) -> Decimal:
        return self._operator_kbms.get(operator_id, self.BASE_KBM)

    def _handle_calculate_legacy(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Расчёт стоимости полиса (устаревший метод, КБМ-модель)."""
        payload = message.get("payload", {})
        manufacturer_id = payload.get("manufacturer_id", "")
        operator_id = payload.get("operator_id", "")
        m_kbm = self._get_manufacturer_kbm(manufacturer_id)
        o_kbm = self._get_operator_kbm(operator_id)
        cost = (self.BASE_COST * m_kbm * o_kbm).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            "calculated_cost": str(cost),
            "manufacturer_kbm": str(m_kbm),
            "operator_kbm": str(o_kbm),
            "coverage_amount": str(payload.get("coverage_amount", 0)),
        }

    def _handle_purchase_legacy(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Покупка страхового полиса (устаревший метод, КБМ-модель)."""
        payload = message.get("payload", {})
        order_id = payload.get("order_id", "")
        operator_id = payload.get("operator_id", "")
        drone_id = payload.get("drone_id", "")
        manufacturer_id = payload.get("manufacturer_id", operator_id)
        coverage_amount = Decimal(str(payload.get("coverage_amount", 0)))

        if not order_id:
            raise ValueError("order_id is required")

        m_kbm = self._get_manufacturer_kbm(manufacturer_id)
        o_kbm = self._get_operator_kbm(operator_id)
        cost = (self.BASE_COST * m_kbm * o_kbm).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        policy_id = str(uuid.uuid4())
        policy_number = f"POL-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)

        policy = {
            "id": policy_id,
            "policy_number": policy_number,
            "policy_type": "legacy",
            "order_id": order_id,
            "manufacturer_id": manufacturer_id,
            "operator_id": operator_id,
            "drone_id": drone_id,
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=self.POLICY_DURATION_DAYS)).isoformat(),
            "cost": str(cost),
            "coverage_amount": str(coverage_amount if coverage_amount else cost * 10),
            "status": "active",
        }
        self._policies[policy_id] = policy

        return {
            "policy_id": policy_id,
            "policy_number": policy_number,
            "order_id": order_id,
            "start_date": policy["start_date"],
            "end_date": policy["end_date"],
            "cost": str(cost),
            "status": "active",
        }
