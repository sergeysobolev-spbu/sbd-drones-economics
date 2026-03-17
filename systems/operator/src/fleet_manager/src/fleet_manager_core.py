"""
Fleet Manager Core - критичные функции управления парком БАС
Доверенный домен D1_TRUSTED - минимальный код для безопасности
"""
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class UASStatus(Enum):
    """Статус БАС"""
    AVAILABLE = "available"
    RESERVED = "reserved"
    IN_MISSION = "in_mission"
    MAINTENANCE = "maintenance"
    CHARGING = "charging"
    ERROR = "error"


@dataclass
class UASState:
    """Минимальное состояние БАС для критичных проверок"""
    id: str
    status: UASStatus
    certificate_valid: bool
    certificate_expiry: str
    battery_level: float
    reserved_by: Optional[str] = None


class FleetManagerCore:
    """
    Ядро менеджера парка - только критичные функции безопасности.
    Минимальный код в доверенном домене D1_TRUSTED.
    """
    
    def __init__(self):
        """Инициализация с минимальным состоянием"""
        self._fleet_state: Dict[str, UASState] = {}
    
    def authorize_uas_operation(
        self, 
        uas_id: str, 
        operation: str, 
        operator_id: str
    ) -> Tuple[bool, str]:
        """
        Авторизация операции с БАС - критичная функция.
        
        Args:
            uas_id: Идентификатор БАС
            operation: Тип операции (reserve, mission, maintenance)
            operator_id: Идентификатор оператора
            
        Returns:
            (is_authorized, reason) - результат авторизации
        """
        # Проверка существования БАС
        if uas_id not in self._fleet_state:
            return False, "UAS_NOT_FOUND"
        
        uas = self._fleet_state[uas_id]
        
        # Проверка сертификата
        if not uas.certificate_valid:
            return False, "CERTIFICATE_INVALID"
        
        # Проверка срока сертификата
        if not self._is_certificate_valid(uas.certificate_expiry):
            return False, "CERTIFICATE_EXPIRED"
        
        # Проверка операций
        if operation == "reserve":
            if uas.status != UASStatus.AVAILABLE:
                return False, "UAS_NOT_AVAILABLE"
        
        elif operation == "mission":
            if uas.status not in [UASStatus.RESERVED, UASStatus.IN_MISSION]:
                return False, "UAS_NOT_READY_FOR_MISSION"
            if uas.battery_level < 0.3:
                return False, "BATTERY_TOO_LOW"
        
        elif operation == "release":
            if uas.reserved_by and uas.reserved_by != operator_id:
                return False, "NOT_AUTHORIZED_TO_RELEASE"
        
        return True, "OK"
    
    def reserve_uas(
        self, 
        uas_id: str, 
        mission_id: str, 
        operator_id: str
    ) -> Tuple[bool, str]:
        """
        Резервирование БАС - критичная операция.
        
        Args:
            uas_id: Идентификатор БАС
            mission_id: Идентификатор миссии
            operator_id: Идентификатор оператора
            
        Returns:
            (success, reason)
        """
        # Проверка авторизации
        authorized, reason = self.authorize_uas_operation(uas_id, "reserve", operator_id)
        if not authorized:
            return False, reason
        
        # Атомарное резервирование
        uas = self._fleet_state[uas_id]
        if uas.status != UASStatus.AVAILABLE:
            return False, "RACE_CONDITION_UAS_ALREADY_RESERVED"
        
        uas.status = UASStatus.RESERVED
        uas.reserved_by = mission_id
        
        return True, "OK"
    
    def release_uas(self, uas_id: str, operator_id: str) -> Tuple[bool, str]:
        """
        Освобождение БАС - критичная операция.
        
        Args:
            uas_id: Идентификатор БАС
            operator_id: Идентификатор оператора
            
        Returns:
            (success, reason)
        """
        # Проверка авторизации
        authorized, reason = self.authorize_uas_operation(uas_id, "release", operator_id)
        if not authorized:
            return False, reason
        
        # Атомарное освобождение
        uas = self._fleet_state[uas_id]
        uas.status = UASStatus.AVAILABLE
        uas.reserved_by = None
        
        return True, "OK"
    
    def update_uas_state(
        self, 
        uas_id: str, 
        updates: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Обновление критичного состояния БАС.
        
        Args:
            uas_id: Идентификатор БАС
            updates: Обновления состояния
            
        Returns:
            (success, reason)
        """
        if uas_id not in self._fleet_state:
            return False, "UAS_NOT_FOUND"
        
        uas = self._fleet_state[uas_id]
        
        # Обновляем только критичные поля
        if "status" in updates:
            try:
                uas.status = UASStatus(updates["status"])
            except ValueError:
                return False, "INVALID_STATUS"
        
        if "battery_level" in updates:
            battery = float(updates["battery_level"])
            if 0 <= battery <= 1:
                uas.battery_level = battery
            else:
                return False, "INVALID_BATTERY_LEVEL"
        
        if "certificate_valid" in updates:
            uas.certificate_valid = bool(updates["certificate_valid"])
        
        if "certificate_expiry" in updates:
            uas.certificate_expiry = updates["certificate_expiry"]
        
        return True, "OK"
    
    def add_uas(self, uas_id: str, initial_state: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Добавление нового БАС в парк.
        
        Args:
            uas_id: Идентификатор БАС
            initial_state: Начальное состояние
            
        Returns:
            (success, reason)
        """
        if uas_id in self._fleet_state:
            return False, "UAS_ALREADY_EXISTS"
        
        try:
            self._fleet_state[uas_id] = UASState(
                id=uas_id,
                status=UASStatus.AVAILABLE,
                certificate_valid=initial_state.get("certificate_valid", False),
                certificate_expiry=initial_state.get("certificate_expiry", ""),
                battery_level=initial_state.get("battery_level", 1.0)
            )
            return True, "OK"
        except Exception as e:
            return False, f"INVALID_STATE: {str(e)}"
    
    def get_uas_state(self, uas_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение состояния БАС для критичных проверок.
        
        Args:
            uas_id: Идентификатор БАС
            
        Returns:
            Состояние БАС или None
        """
        if uas_id not in self._fleet_state:
            return None
        
        uas = self._fleet_state[uas_id]
        return {
            "id": uas.id,
            "status": uas.status.value,
            "certificate_valid": uas.certificate_valid,
            "certificate_expiry": uas.certificate_expiry,
            "battery_level": uas.battery_level,
            "reserved_by": uas.reserved_by
        }
    
    def _is_certificate_valid(self, expiry_str: str) -> bool:
        """Проверка срока действия сертификата - чистая функция"""
        try:
            expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            return expiry > datetime.utcnow()
        except:
            return False