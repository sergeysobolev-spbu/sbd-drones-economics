"""
BusinessLogicService - операционная логика бизнес-компонента

Домен безопасности: D2_OPERATIONAL
Упрощенные расчеты и mock интеграции для внешних систем
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import uuid
from dataclasses import dataclass, asdict

from .business_logic_core import BusinessLogicCore


@dataclass
class CostBreakdown:
    """Упрощенная разбивка затрат"""
    uas_cost: float  # Стоимость использования БАС
    operator_cost: float  # Стоимость работы оператора
    insurance_cost: float  # Страховка
    total: float  # Общая стоимость


@dataclass
class Proposal:
    """Коммерческое предложение"""
    id: str
    order_id: str
    price: float
    cost: float
    margin_percent: float
    valid_until: str
    created_at: str


class MockInsuranceProvider:
    """Mock провайдер страховых услуг"""
    
    @staticmethod
    def get_quote(mission_data: Dict[str, Any]) -> Dict[str, Any]:
        """Получить страховую котировку (заглушка)"""
        # Простой расчет: 2% от стоимости груза
        cargo_value = mission_data.get("cargo_value", 10000)
        premium = cargo_value * 0.02
        
        return {
            "quote_id": f"INS-{uuid.uuid4().hex[:8]}",
            "premium": round(premium, 2),
            "coverage": cargo_value,
            "valid_until": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }


class MockBankingGateway:
    """Mock банковский шлюз"""
    
    @staticmethod
    def process_payment(payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработать платеж (заглушка)"""
        return {
            "transaction_id": f"TXN-{uuid.uuid4().hex[:8]}",
            "status": "approved",
            "amount": payment_data.get("amount", 0),
            "timestamp": datetime.utcnow().isoformat()
        }


class MockTaxService:
    """Mock налоговый сервис"""
    
    @staticmethod
    def calculate_tax(amount: float) -> Dict[str, Any]:
        """Рассчитать налог (заглушка)"""
        # НДС 20%
        vat = amount * 0.20
        
        return {
            "vat": round(vat, 2),
            "total_with_tax": round(amount + vat, 2)
        }


class BusinessLogicService:
    """
    Сервисный слой бизнес-логики
    
    Содержит упрощенную операционную логику и интеграции
    с внешними системами (mock)
    """
    
    def __init__(self, core: BusinessLogicCore):
        self.logger = logging.getLogger(f"{__name__}.BusinessLogicService")
        self.core = core
        
        # Mock провайдеры
        self.insurance = MockInsuranceProvider()
        self.banking = MockBankingGateway()
        self.tax_service = MockTaxService()
        
        # Хранилище предложений (в памяти)
        self.proposals: Dict[str, Proposal] = {}
        
        # Упрощенные тарифы
        self.rates = {
            "uas_per_km": 50.0,  # руб/км
            "operator_per_hour": 1000.0,  # руб/час
            "base_fee": 500.0  # базовая ставка
        }
        
        self.logger.info("BusinessLogicService initialized with mock providers")
    
    def calculate_mission_cost(self, mission_data: Dict[str, Any]) -> CostBreakdown:
        """
        Упрощенный расчет стоимости миссии
        
        Args:
            mission_data: Данные миссии
            
        Returns:
            CostBreakdown: Разбивка затрат
        """
        # Извлекаем параметры
        distance = mission_data.get("distance", 10)  # км
        duration_minutes = mission_data.get("duration", 30)  # минуты
        cargo_value = mission_data.get("cargo_value", 10000)  # руб
        
        # Упрощенные расчеты
        uas_cost = self.rates["uas_per_km"] * distance + self.rates["base_fee"]
        operator_cost = self.rates["operator_per_hour"] * (duration_minutes / 60)
        
        # Получаем страховку через mock
        insurance_quote = self.insurance.get_quote(mission_data)
        insurance_cost = insurance_quote["premium"]
        
        total = uas_cost + operator_cost + insurance_cost
        
        return CostBreakdown(
            uas_cost=round(uas_cost, 2),
            operator_cost=round(operator_cost, 2),
            insurance_cost=round(insurance_cost, 2),
            total=round(total, 2)
        )
    
    def create_proposal(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создать коммерческое предложение
        
        Args:
            order_data: Данные заказа
            
        Returns:
            Dict с предложением или ошибкой
        """
        # Рассчитываем стоимость
        cost_breakdown = self.calculate_mission_cost(order_data.get("mission_data", {}))
        cost = cost_breakdown.total
        
        # Определяем минимальную цену
        min_price = self.core.calculate_min_price(cost)
        
        # Предлагаем цену с небольшой наценкой сверх минимальной
        proposed_price = min_price * 1.05  # +5% к минимальной цене
        
        # Проверяем маржу
        margin_check = self.core.validate_margin(proposed_price, cost)
        
        if not margin_check.is_valid:
            return {
                "error": "Невозможно создать прибыльное предложение",
                "reason": margin_check.reason
            }
        
        # Создаем предложение
        proposal = Proposal(
            id=f"PROP-{uuid.uuid4().hex[:8]}",
            order_id=order_data.get("order_id", "unknown"),
            price=round(proposed_price, 2),
            cost=cost,
            margin_percent=margin_check.margin_percent,
            valid_until=(datetime.utcnow() + timedelta(hours=24)).isoformat(),
            created_at=datetime.utcnow().isoformat()
        )
        
        # Сохраняем в памяти
        self.proposals[proposal.id] = proposal
        
        self.logger.info(f"Created proposal {proposal.id} with margin {proposal.margin_percent}%")
        
        return {
            "proposal": asdict(proposal),
            "cost_breakdown": asdict(cost_breakdown)
        }
    
    def process_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработать заказ (упрощенная логика)
        
        Args:
            order_data: Данные заказа
            
        Returns:
            Dict с результатом обработки
        """
        proposal_id = order_data.get("proposal_id")
        
        if not proposal_id or proposal_id not in self.proposals:
            return {"error": "Предложение не найдено"}
        
        proposal = self.proposals[proposal_id]
        
        # Проверяем актуальность предложения
        valid_until = datetime.fromisoformat(proposal.valid_until.replace('Z', '+00:00'))
        if valid_until < datetime.utcnow():
            return {"error": "Предложение истекло"}
        
        # Рассчитываем налог
        tax_info = self.tax_service.calculate_tax(proposal.price)
        
        # Обрабатываем платеж через mock
        payment_result = self.banking.process_payment({
            "amount": tax_info["total_with_tax"],
            "order_id": order_data.get("order_id")
        })
        
        return {
            "status": "processed",
            "proposal_id": proposal_id,
            "payment": payment_result,
            "tax": tax_info,
            "total_amount": tax_info["total_with_tax"]
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получить упрощенную статистику
        
        Returns:
            Dict со статистикой
        """
        if not self.proposals:
            return {
                "total_proposals": 0,
                "average_margin": 0,
                "total_value": 0
            }
        
        margins = [p.margin_percent for p in self.proposals.values()]
        prices = [p.price for p in self.proposals.values()]
        
        return {
            "total_proposals": len(self.proposals),
            "average_margin": round(sum(margins) / len(margins), 2),
            "total_value": round(sum(prices), 2),
            "active_proposals": len([
                p for p in self.proposals.values()
                if datetime.fromisoformat(p.valid_until.replace('Z', '+00:00')) > datetime.utcnow()
            ])
        }
    
    def validate_with_limits(self, price: float, cost: float) -> Dict[str, Any]:
        """
        Валидация с учетом экономических ограничений
        
        Args:
            price: Предлагаемая цена
            cost: Себестоимость
            
        Returns:
            Dict с результатом валидации
        """
        # Используем core для проверки
        margin_check = self.core.validate_margin(price, cost)
        limits = self.core.get_economic_limits()
        
        return {
            "valid": margin_check.is_valid,
            "margin_percent": margin_check.margin_percent,
            "limits": limits,
            "suggested_price": self.core.calculate_min_price(cost) if not margin_check.is_valid else None
        }