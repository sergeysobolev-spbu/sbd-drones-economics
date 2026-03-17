"""
BusinessLogicCore - критическое ядро бизнес-логики

Домен безопасности: D0_CRITICAL
Минимальная логика для проверки экономических ограничений
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging


@dataclass
class MarginValidation:
    """Результат проверки маржинальности"""
    is_valid: bool
    margin_percent: float
    min_required: float
    reason: Optional[str] = None


class BusinessLogicCore:
    """
    Критическое ядро бизнес-логики
    
    Содержит только минимально необходимую логику для обеспечения
    экономической безопасности операций
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.BusinessLogicCore")
        
        # Критические параметры (неизменяемые)
        self._MIN_MARGIN_PERCENT = 10.0  # Минимальная маржа 10%
        self._MAX_DISCOUNT_PERCENT = 5.0  # Максимальная скидка 5%
        
        self.logger.info("BusinessLogicCore initialized")
    
    def validate_margin(self, price: float, cost: float) -> MarginValidation:
        """
        Проверка минимальной маржинальности
        
        Args:
            price: Цена для клиента
            cost: Себестоимость
            
        Returns:
            MarginValidation: Результат проверки
        """
        # Базовая валидация входных данных
        if price <= 0:
            return MarginValidation(
                is_valid=False,
                margin_percent=0.0,
                min_required=self._MIN_MARGIN_PERCENT,
                reason="Цена должна быть положительной"
            )
        
        if cost < 0:
            return MarginValidation(
                is_valid=False,
                margin_percent=0.0,
                min_required=self._MIN_MARGIN_PERCENT,
                reason="Себестоимость не может быть отрицательной"
            )
        
        # Расчет маржи
        margin = price - cost
        margin_percent = (margin / price) * 100 if price > 0 else 0
        
        # Проверка минимальной маржи
        is_valid = margin_percent >= self._MIN_MARGIN_PERCENT
        
        reason = None
        if not is_valid:
            reason = f"Маржа {margin_percent:.1f}% ниже минимальной {self._MIN_MARGIN_PERCENT}%"
        
        return MarginValidation(
            is_valid=is_valid,
            margin_percent=round(margin_percent, 2),
            min_required=self._MIN_MARGIN_PERCENT,
            reason=reason
        )
    
    def validate_discount(self, original_price: float, discounted_price: float) -> Dict[str, Any]:
        """
        Проверка допустимости скидки
        
        Args:
            original_price: Исходная цена
            discounted_price: Цена со скидкой
            
        Returns:
            Dict с результатом проверки
        """
        if original_price <= 0:
            return {
                "valid": False,
                "reason": "Исходная цена должна быть положительной"
            }
        
        if discounted_price <= 0:
            return {
                "valid": False,
                "reason": "Цена со скидкой должна быть положительной"
            }
        
        discount_percent = ((original_price - discounted_price) / original_price) * 100
        
        if discount_percent > self._MAX_DISCOUNT_PERCENT:
            return {
                "valid": False,
                "discount_percent": round(discount_percent, 2),
                "max_allowed": self._MAX_DISCOUNT_PERCENT,
                "reason": f"Скидка {discount_percent:.1f}% превышает максимальную {self._MAX_DISCOUNT_PERCENT}%"
            }
        
        return {
            "valid": True,
            "discount_percent": round(discount_percent, 2)
        }
    
    def calculate_min_price(self, cost: float) -> float:
        """
        Расчет минимальной цены с учетом требуемой маржи
        
        Args:
            cost: Себестоимость
            
        Returns:
            float: Минимальная допустимая цена
        """
        if cost < 0:
            raise ValueError("Себестоимость не может быть отрицательной")
        
        # Минимальная цена = себестоимость / (1 - маржа%)
        min_price = cost / (1 - self._MIN_MARGIN_PERCENT / 100)
        
        return round(min_price, 2)
    
    def validate_order_economics(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Комплексная проверка экономических параметров заказа
        
        Args:
            order_data: Данные заказа
            
        Returns:
            Dict с результатами проверки
        """
        validations = []
        
        # Извлечение данных
        price = order_data.get("price", 0)
        cost = order_data.get("cost", 0)
        has_discount = order_data.get("has_discount", False)
        
        # Проверка маржи
        margin_check = self.validate_margin(price, cost)
        validations.append({
            "check": "margin",
            "passed": margin_check.is_valid,
            "details": {
                "margin_percent": margin_check.margin_percent,
                "min_required": margin_check.min_required,
                "reason": margin_check.reason
            }
        })
        
        # Проверка скидки (если есть)
        if has_discount:
            original_price = order_data.get("original_price", price)
            discount_check = self.validate_discount(original_price, price)
            validations.append({
                "check": "discount",
                "passed": discount_check["valid"],
                "details": discount_check
            })
        
        # Общий результат
        all_passed = all(v["passed"] for v in validations)
        
        return {
            "valid": all_passed,
            "validations": validations,
            "min_price_required": self.calculate_min_price(cost) if cost > 0 else None
        }
    
    def get_economic_limits(self) -> Dict[str, float]:
        """
        Получение экономических ограничений
        
        Returns:
            Dict с ограничениями
        """
        return {
            "min_margin_percent": self._MIN_MARGIN_PERCENT,
            "max_discount_percent": self._MAX_DISCOUNT_PERCENT
        }