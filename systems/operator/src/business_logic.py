"""
Business Logic - бизнес-логика системы Эксплуатант

Компонент уровня D2_OPERATIONAL, отвечающий за экономические расчёты,
проверку маржинальности и формирование коммерческих предложений.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus
from systems.operator.src.topics import (
    ComponentTopics,
    BusinessLogicActions,
    SecurityMonitorActions,
    SystemTopics
)


@dataclass
class CostBreakdown:
    """Разбивка затрат на миссию"""
    uas_depreciation: float  # Амортизация БАС
    battery_usage: float  # Износ батареи
    maintenance: float  # Обслуживание
    insurance: float  # Страховка
    operator_salary: float  # Зарплата оператора
    infrastructure: float  # Инфраструктура
    total: float  # Общая стоимость


@dataclass
class Proposal:
    """Коммерческое предложение"""
    id: str
    order_id: str
    mission_id: str
    price: float
    cost: float
    margin: float
    margin_percent: float
    delivery_time: str
    valid_until: str
    cost_breakdown: CostBreakdown
    created_at: str


class BusinessLogic(BaseComponent):
    """
    Бизнес-логика - обеспечивает экономическую эффективность операций
    """
    
    def __init__(self, component_id: str, bus: SystemBus):
        self.logger = logging.getLogger(f"BusinessLogic.{component_id}")
        
        # Экономические параметры (для прототипа)
        self.economic_params = {
            "min_margin_percent": 10.0,  # Минимальная маржа 10%
            "uas_cost_per_hour": {
                "light_cargo": 500.0,  # руб/час
                "heavy_cargo": 1500.0,
                "agro": 1000.0,
                "inspector": 800.0
            },
            "battery_cost_per_cycle": 50.0,  # руб
            "insurance_rate": 0.02,  # 2% от стоимости заказа
            "operator_hourly_rate": 1000.0,  # руб/час
            "infrastructure_overhead": 0.15  # 15% накладные расходы
        }
        
        # История предложений
        self.proposals: Dict[str, Proposal] = {}
        
        # Кеш страховых котировок
        self.insurance_cache: Dict[str, Dict[str, Any]] = {}
        
        super().__init__(
            component_id=component_id,
            component_type="business_logic",
            topic=ComponentTopics.BUSINESS_LOGIC,
            bus=bus
        )
        
        self.logger.info(f"Business Logic {component_id} initialized")
    
    def _register_handlers(self):
        """Регистрация обработчиков"""
        self.register_handler(BusinessLogicActions.CALCULATE_COST, self._handle_calculate_cost)
        self.register_handler(BusinessLogicActions.CHECK_PROFITABILITY, self._handle_check_profitability)
        self.register_handler(BusinessLogicActions.REQUEST_INSURANCE_QUOTE, self._handle_request_insurance_quote)
        self.register_handler(BusinessLogicActions.CREATE_PROPOSAL, self._handle_create_proposal)
        self.register_handler(BusinessLogicActions.VALIDATE_ECONOMICS, self._handle_validate_economics)
    
    def _handle_calculate_cost(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Расчёт стоимости миссии"""
        payload = message.get("payload", {})
        mission_details = payload.get("mission_details", {})
        
        if not mission_details:
            return {"error": "Mission details required"}
        
        # Извлекаем параметры миссии
        uas_type = mission_details.get("uas_type", "light_cargo")
        distance = mission_details.get("distance", 0)
        flight_time_hours = mission_details.get("flight_time_minutes", 30) / 60
        payload_weight = mission_details.get("payload_weight", 0)
        
        # Расчёт компонентов стоимости
        
        # 1. Амортизация БАС
        uas_hourly_cost = self.economic_params["uas_cost_per_hour"].get(uas_type, 500)
        uas_depreciation = uas_hourly_cost * flight_time_hours
        
        # 2. Износ батареи
        battery_cycles = flight_time_hours * 2  # Примерно 2 цикла на час полёта
        battery_usage = battery_cycles * self.economic_params["battery_cost_per_cycle"]
        
        # 3. Обслуживание (пропорционально времени полёта)
        maintenance = flight_time_hours * 200  # 200 руб/час
        
        # 4. Страховка (будет уточнена при запросе котировки)
        estimated_order_value = distance * 100 + payload_weight * 50  # Примерная оценка
        insurance = estimated_order_value * self.economic_params["insurance_rate"]
        
        # 5. Зарплата оператора
        operator_salary = flight_time_hours * self.economic_params["operator_hourly_rate"]
        
        # 6. Накладные расходы
        subtotal = uas_depreciation + battery_usage + maintenance + insurance + operator_salary
        infrastructure = subtotal * self.economic_params["infrastructure_overhead"]
        
        # Общая стоимость
        total_cost = subtotal + infrastructure
        
        cost_breakdown = CostBreakdown(
            uas_depreciation=round(uas_depreciation, 2),
            battery_usage=round(battery_usage, 2),
            maintenance=round(maintenance, 2),
            insurance=round(insurance, 2),
            operator_salary=round(operator_salary, 2),
            infrastructure=round(infrastructure, 2),
            total=round(total_cost, 2)
        )
        
        self.logger.info(f"Calculated cost for mission: {total_cost:.2f} RUB")
        
        return {
            "cost_breakdown": asdict(cost_breakdown),
            "total_cost": cost_breakdown.total,
            "cost_per_km": round(cost_breakdown.total / max(distance, 1), 2)
        }
    
    def _handle_check_profitability(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Проверка маржинальности"""
        payload = message.get("payload", {})
        price = payload.get("price", 0)
        cost = payload.get("cost", 0)
        
        if price <= 0 or cost < 0:
            return {
                "profitable": False,
                "reason": "Invalid price or cost"
            }
        
        margin = price - cost
        margin_percent = (margin / price) * 100 if price > 0 else 0
        
        min_margin = self.economic_params["min_margin_percent"]
        profitable = margin_percent >= min_margin
        
        # Проверяем через монитор безопасности
        security_check = self._validate_with_security_monitor({
            "action": "check_profitability",
            "sender": message.get("sender", "business_logic"),
            "price": price,
            "cost": cost
        }, {
            "order": {
                "price": price,
                "cost": cost
            }
        })
        
        if not security_check.get("allowed", True):
            return {
                "profitable": False,
                "reason": "Security policy violation",
                "violations": security_check.get("violations", [])
            }
        
        result = {
            "profitable": profitable,
            "margin": round(margin, 2),
            "margin_percent": round(margin_percent, 2),
            "min_margin_percent": min_margin
        }
        
        if not profitable:
            result["reason"] = f"Margin {margin_percent:.1f}% is below minimum {min_margin}%"
            result["suggested_price"] = round(cost / (1 - min_margin/100), 2)
        
        return result
    
    def _handle_request_insurance_quote(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Запрос страховой котировки"""
        payload = message.get("payload", {})
        mission_details = payload.get("mission_details", {})
        
        if not mission_details:
            return {"error": "Mission details required"}
        
        # Формируем запрос для страховой компании
        insurance_request = {
            "mission_type": mission_details.get("type", "cargo_delivery"),
            "distance": mission_details.get("distance", 0),
            "payload_value": mission_details.get("payload_value", 0),
            "uas_type": mission_details.get("uas_type", "light_cargo"),
            "flight_time_minutes": mission_details.get("flight_time_minutes", 30),
            "operator_id": "OPERATOR-001",
            "coverage_type": "comprehensive"
        }
        
        # В реальной системе здесь был бы запрос к страховой компании
        # Для прототипа используем упрощённый расчёт
        
        base_rate = 0.02  # 2% базовая ставка
        
        # Корректировки на основе рисков
        risk_multiplier = 1.0
        
        # Тип миссии
        if insurance_request["mission_type"] == "inspection":
            risk_multiplier *= 0.8  # Меньше риск
        elif insurance_request["mission_type"] == "agro_spraying":
            risk_multiplier *= 1.2  # Больше риск (химикаты)
        
        # Дистанция
        if insurance_request["distance"] > 50:
            risk_multiplier *= 1.1
        
        # Тип БАС
        if insurance_request["uas_type"] == "heavy_cargo":
            risk_multiplier *= 1.3
        
        final_rate = base_rate * risk_multiplier
        premium = insurance_request["payload_value"] * final_rate
        
        quote = {
            "quote_id": f"INS-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "premium": round(premium, 2),
            "rate": round(final_rate * 100, 3),  # В процентах
            "coverage_amount": insurance_request["payload_value"],
            "valid_until": datetime.utcnow().isoformat(),
            "terms": [
                "Coverage for cargo damage/loss",
                "Third party liability",
                "Emergency landing coverage"
            ]
        }
        
        # Кешируем котировку
        cache_key = f"{mission_details.get('mission_id', 'unknown')}"
        self.insurance_cache[cache_key] = quote
        
        self.logger.info(f"Insurance quote: {premium:.2f} RUB (rate: {final_rate*100:.3f}%)")
        
        return quote
    
    def _handle_create_proposal(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Создание коммерческого предложения"""
        payload = message.get("payload", {})
        order = payload.get("order", {})
        mission_details = payload.get("mission_details", {})
        
        if not all([order, mission_details]):
            return {"error": "Order and mission details required"}
        
        # Рассчитываем стоимость
        cost_result = self._handle_calculate_cost({
            "payload": {"mission_details": mission_details}
        })
        
        if "error" in cost_result:
            return cost_result
        
        total_cost = cost_result["total_cost"]
        cost_breakdown = CostBreakdown(**cost_result["cost_breakdown"])
        
        # Определяем цену с учётом минимальной маржи
        min_margin = self.economic_params["min_margin_percent"]
        min_price = total_cost / (1 - min_margin/100)
        
        # Учитываем рыночную цену если она выше
        market_price = order.get("market_price", min_price)
        proposed_price = max(min_price, market_price * 0.95)  # 5% скидка от рынка
        
        # Проверяем маржинальность
        margin = proposed_price - total_cost
        margin_percent = (margin / proposed_price) * 100
        
        profitability_check = self._handle_check_profitability({
            "payload": {
                "price": proposed_price,
                "cost": total_cost
            }
        })
        
        if not profitability_check["profitable"]:
            return {
                "error": "Cannot create profitable proposal",
                "details": profitability_check
            }
        
        # Создаём предложение
        proposal = Proposal(
            id=f"PROP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            order_id=order.get("id", "unknown"),
            mission_id=mission_details.get("mission_id", "unknown"),
            price=round(proposed_price, 2),
            cost=round(total_cost, 2),
            margin=round(margin, 2),
            margin_percent=round(margin_percent, 2),
            delivery_time=mission_details.get("end_time", ""),
            valid_until=datetime.utcnow().isoformat(),
            cost_breakdown=cost_breakdown,
            created_at=datetime.utcnow().isoformat()
        )
        
        self.proposals[proposal.id] = proposal
        
        self.logger.info(f"Created proposal {proposal.id}: price={proposed_price:.2f}, margin={margin_percent:.1f}%")
        
        return {
            "proposal_id": proposal.id,
            "price": proposal.price,
            "margin_percent": proposal.margin_percent,
            "delivery_time": proposal.delivery_time,
            "valid_until": proposal.valid_until
        }
    
    def _handle_validate_economics(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация экономических параметров заказа"""
        payload = message.get("payload", {})
        order = payload.get("order", {})
        proposal_id = payload.get("proposal_id")
        
        validation_results = []
        
        # Проверка 1: Существование предложения
        if proposal_id:
            proposal = self.proposals.get(proposal_id)
            if not proposal:
                validation_results.append({
                    "check": "proposal_exists",
                    "passed": False,
                    "reason": f"Proposal {proposal_id} not found"
                })
            else:
                validation_results.append({
                    "check": "proposal_exists",
                    "passed": True,
                    "proposal_id": proposal_id
                })
                
                # Проверка 2: Актуальность предложения
                try:
                    valid_until = datetime.fromisoformat(proposal.valid_until.replace('Z', '+00:00'))
                    if valid_until < datetime.utcnow():
                        validation_results.append({
                            "check": "proposal_validity",
                            "passed": False,
                            "reason": "Proposal has expired"
                        })
                    else:
                        validation_results.append({
                            "check": "proposal_validity",
                            "passed": True
                        })
                except:
                    validation_results.append({
                        "check": "proposal_validity",
                        "passed": False,
                        "reason": "Invalid validity date"
                    })
                
                # Проверка 3: Маржинальность
                if proposal.margin_percent >= self.economic_params["min_margin_percent"]:
                    validation_results.append({
                        "check": "margin_requirement",
                        "passed": True,
                        "margin_percent": proposal.margin_percent
                    })
                else:
                    validation_results.append({
                        "check": "margin_requirement",
                        "passed": False,
                        "reason": f"Margin {proposal.margin_percent}% below minimum"
                    })
        
        # Проверка 4: Страховое покрытие
        if order:
            payload_value = order.get("payload_value", 0)
            if payload_value > 0:
                # Проверяем наличие страховой котировки
                cache_key = order.get("mission_id", "unknown")
                if cache_key in self.insurance_cache:
                    validation_results.append({
                        "check": "insurance_coverage",
                        "passed": True,
                        "insurance_quote_id": self.insurance_cache[cache_key]["quote_id"]
                    })
                else:
                    validation_results.append({
                        "check": "insurance_coverage",
                        "passed": False,
                        "reason": "No insurance quote available"
                    })
        
        # Общий результат
        all_passed = all(r.get("passed", False) for r in validation_results)
        
        return {
            "valid": all_passed,
            "validation_results": validation_results
        }
    
    def _validate_with_security_monitor(self, request: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Валидация через монитор безопасности"""
        try:
            response = self.bus.request(
                ComponentTopics.SECURITY_MONITOR,
                {
                    "action": SecurityMonitorActions.VALIDATE_REQUEST,
                    "sender": self.component_id,
                    "payload": {
                        "request": request,
                        "context": context or {}
                    }
                },
                timeout=5.0
            )
            
            if response and response.get("success"):
                return response.get("payload", {})
            
            return {"allowed": False, "error": "Security monitor not responding"}
            
        except Exception as e:
            self.logger.error(f"Security validation error: {e}")
            return {"allowed": False, "error": str(e)}
    
    def get_economics_statistics(self) -> Dict[str, Any]:
        """Получение экономической статистики"""
        if not self.proposals:
            return {
                "total_proposals": 0,
                "average_margin_percent": 0,
                "total_revenue": 0,
                "total_cost": 0,
                "total_margin": 0
            }
        
        total_revenue = sum(p.price for p in self.proposals.values())
        total_cost = sum(p.cost for p in self.proposals.values())
        total_margin = total_revenue - total_cost
        
        margins = [p.margin_percent for p in self.proposals.values()]
        average_margin = sum(margins) / len(margins) if margins else 0
        
        return {
            "total_proposals": len(self.proposals),
            "average_margin_percent": round(average_margin, 2),
            "total_revenue": round(total_revenue, 2),
            "total_cost": round(total_cost, 2),
            "total_margin": round(total_margin, 2),
            "proposals_by_margin": {
                "below_15%": len([m for m in margins if m < 15]),
                "15-25%": len([m for m in margins if 15 <= m < 25]),
                "above_25%": len([m for m in margins if m >= 25])
            }
        }