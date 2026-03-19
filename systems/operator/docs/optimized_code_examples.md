# Примеры оптимизированного кода для запроса №2

## 1. Минимизация Security Monitor (Доверенный домен D0_CRITICAL)

### До оптимизации (монолитный Security Monitor)
```python
# security_monitor.py - ВСЁ в доверенном домене
class SecurityMonitor:
    def __init__(self):
        self.policies = self._load_policies()
        self.logger = logging.getLogger(__name__)
        self.metrics = MetricsCollector()  # Некритичный функционал
        self.notifier = NotificationService()  # Некритичный функционал
        
    def validate_command(self, command, context):
        # Критичная логика
        if not self._check_authentication(context):
            self._log_violation("AUTH_FAILED", command)  # Смешивание логики
            self._send_alert("Authentication failed")  # Некритичный функционал
            return False
            
        if not self._check_policy(command, context):
            self._log_violation("POLICY_VIOLATION", command)
            self._update_metrics("policy_violations")  # Некритичный функционал
            return False
            
        # Логирование успеха - некритичный функционал
        self._log_success(command)
        return True
```

### После оптимизации (разделение на домены)

#### Доверенный домен (D0_CRITICAL) - только критичная логика
```python
# security_monitor_core.py - Минимальный TCB
from typing import Dict, Any, Tuple

class SecurityMonitorCore:
    """
    Ядро монитора безопасности - только критичные функции.
    Минимальный код в доверенном домене.
    """
    
    def __init__(self, policy_store: Dict[str, Any]):
        """
        Инициализация только с необходимыми данными.
        
        Args:
            policy_store: Неизменяемое хранилище политик
        """
        self._policies = policy_store
        # Никаких логгеров, метрик, нотификаций!
    
    def validate_command(self, command: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Валидация команды согласно политикам безопасности.
        
        Args:
            command: Команда для валидации
            context: Контекст выполнения (роли, права)
            
        Returns:
            (is_valid, reason) - результат валидации и причина отказа
        """
        # Проверка аутентификации
        if not self._is_authenticated(context):
            return False, "NOT_AUTHENTICATED"
        
        # Проверка авторизации
        if not self._is_authorized(command, context):
            return False, "NOT_AUTHORIZED"
        
        # Проверка политик
        policy_result = self._check_policies(command, context)
        if not policy_result[0]:
            return False, f"POLICY_VIOLATION:{policy_result[1]}"
        
        return True, "OK"
    
    def _is_authenticated(self, context: Dict[str, Any]) -> bool:
        """Проверка аутентификации - чистая функция."""
        return (
            context.get("authenticated", False) and
            context.get("session_valid", False)
        )
    
    def _is_authorized(self, command: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Проверка авторизации - чистая функция."""
        required_role = command.get("required_role", "operator")
        user_roles = context.get("roles", [])
        return required_role in user_roles
    
    def _check_policies(self, command: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
        """Проверка политик безопасности - чистая функция."""
        command_type = command.get("type")
        applicable_policies = self._policies.get(command_type, [])
        
        for policy in applicable_policies:
            if not self._evaluate_policy(policy, command, context):
                return False, policy.get("id", "UNKNOWN")
        
        return True, ""
    
    def _evaluate_policy(self, policy: Dict[str, Any], command: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Вычисление одной политики - чистая функция."""
        # Минимальная логика оценки политики
        rules = policy.get("rules", [])
        return all(self._evaluate_rule(rule, command, context) for rule in rules)
    
    def _evaluate_rule(self, rule: str, command: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Вычисление одного правила - чистая функция."""
        # Простая оценка правил без side effects
        # Реализация зависит от формата правил
        return True  # Заглушка
```

#### Недоверенный домен (D2_OPERATIONAL) - вспомогательная логика
```python
# security_monitor_service.py - Некритичные функции
import logging
from datetime import datetime
from typing import Dict, Any, Optional

class SecurityMonitorService:
    """
    Сервисный слой монитора безопасности.
    Содержит всю некритичную логику: логирование, метрики, уведомления.
    """
    
    def __init__(self, core: SecurityMonitorCore, event_bus: Any):
        self.core = core  # Ссылка на ядро
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        self._metrics = {
            "total_validations": 0,
            "failed_validations": 0,
            "policy_violations": {}
        }
    
    async def process_command(self, command: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Обработка команды с полным циклом логирования и уведомлений.
        """
        start_time = datetime.utcnow()
        
        # Вызов критичной функции
        is_valid, reason = self.core.validate_command(command, context)
        
        # Некритичная обработка результата
        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Логирование
        self._log_validation(command, context, is_valid, reason, elapsed_ms)
        
        # Обновление метрик
        self._update_metrics(is_valid, reason)
        
        # Отправка событий
        await self._emit_security_event(command, context, is_valid, reason)
        
        # Уведомления при нарушениях
        if not is_valid and self._should_alert(reason):
            await self._send_alert(command, context, reason)
        
        return is_valid
    
    def _log_validation(self, command: Dict[str, Any], context: Dict[str, Any], 
                       is_valid: bool, reason: str, elapsed_ms: float):
        """Детальное логирование валидации."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "command_type": command.get("type"),
            "user_id": context.get("user_id"),
            "is_valid": is_valid,
            "reason": reason,
            "elapsed_ms": elapsed_ms
        }
        
        if is_valid:
            self.logger.info(f"Command validated successfully", extra=log_data)
        else:
            self.logger.warning(f"Command validation failed: {reason}", extra=log_data)
    
    def _update_metrics(self, is_valid: bool, reason: str):
        """Обновление метрик."""
        self._metrics["total_validations"] += 1
        
        if not is_valid:
            self._metrics["failed_validations"] += 1
            
            if reason.startswith("POLICY_VIOLATION:"):
                policy_id = reason.split(":", 1)[1]
                self._metrics["policy_violations"][policy_id] = \
                    self._metrics["policy_violations"].get(policy_id, 0) + 1
    
    async def _emit_security_event(self, command: Dict[str, Any], context: Dict[str, Any],
                                   is_valid: bool, reason: str):
        """Публикация события безопасности."""
        event = {
            "type": "security.validation",
            "timestamp": datetime.utcnow().isoformat(),
            "command": command,
            "context": {
                "user_id": context.get("user_id"),
                "roles": context.get("roles", [])
            },
            "result": {
                "is_valid": is_valid,
                "reason": reason
            }
        }
        
        await self.event_bus.publish("security.events", event)
    
    def _should_alert(self, reason: str) -> bool:
        """Определение необходимости отправки алерта."""
        critical_reasons = ["NOT_AUTHENTICATED", "PRIVILEGE_ESCALATION"]
        return any(cr in reason for cr in critical_reasons)
    
    async def _send_alert(self, command: Dict[str, Any], context: Dict[str, Any], reason: str):
        """Отправка алерта службе безопасности."""
        alert = {
            "severity": "HIGH",
            "type": "security_violation",
            "reason": reason,
            "command": command.get("type"),
            "user": context.get("user_id"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.event_bus.publish("security.alerts", alert)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик для мониторинга."""
        return {
            "metrics": self._metrics,
            "health": "healthy",
            "uptime_seconds": self._get_uptime()
        }
```

## 2. Оптимизированная структура Fleet Manager

### Разделение на домены безопасности
```python
# fleet_manager_core.py - Доверенный домен (D1_TRUSTED)
class FleetManagerCore:
    """Критичные функции управления парком БАС."""
    
    def __init__(self, certificate_validator: CertificateValidator):
        self._validator = certificate_validator
        self._fleet_state = {}  # Минимальное состояние
    
    def authorize_uas_operation(self, uas_id: str, operation: str, operator_id: str) -> Tuple[bool, str]:
        """Авторизация операции с БАС - критичная функция."""
        # Проверка сертификата
        if not self._validator.is_certified(uas_id):
            return False, "UAS_NOT_CERTIFIED"
        
        # Проверка состояния
        if not self._is_operational(uas_id):
            return False, "UAS_NOT_OPERATIONAL"
        
        # Проверка прав оператора
        if not self._can_operate(operator_id, uas_id):
            return False, "OPERATOR_NOT_AUTHORIZED"
        
        return True, "OK"
    
    def _is_operational(self, uas_id: str) -> bool:
        """Проверка операционной готовности БАС."""
        state = self._fleet_state.get(uas_id, {})
        return (
            state.get("status") == "ready" and
            state.get("battery_level", 0) > 20 and
            not state.get("maintenance_required", False)
        )
    
    def _can_operate(self, operator_id: str, uas_id: str) -> bool:
        """Проверка прав оператора на управление БАС."""
        # Минимальная логика проверки прав
        return True  # Заглушка


# fleet_manager_service.py - Недоверенный домен (D2_OPERATIONAL)
class FleetManagerService:
    """Некритичные функции управления парком."""
    
    def __init__(self, core: FleetManagerCore):
        self.core = core
        self._telemetry_cache = {}
        self._mission_history = {}
        self._maintenance_scheduler = MaintenanceScheduler()
    
    async def select_best_uas(self, mission_requirements: Dict[str, Any]) -> Optional[str]:
        """Выбор оптимального БАС для миссии - бизнес-логика."""
        available_uas = await self._get_available_uas()
        
        # Фильтрация по требованиям
        suitable_uas = []
        for uas_id in available_uas:
            # Проверка через ядро
            is_authorized, _ = self.core.authorize_uas_operation(
                uas_id, "mission", "system"
            )
            
            if is_authorized and self._meets_requirements(uas_id, mission_requirements):
                suitable_uas.append(uas_id)
        
        # Выбор оптимального
        if suitable_uas:
            return self._select_optimal(suitable_uas, mission_requirements)
        
        return None
    
    def _meets_requirements(self, uas_id: str, requirements: Dict[str, Any]) -> bool:
        """Проверка соответствия БАС требованиям миссии."""
        telemetry = self._telemetry_cache.get(uas_id, {})
        
        # Проверка дальности
        if requirements.get("range_km", 0) > telemetry.get("max_range_km", 0):
            return False
        
        # Проверка полезной нагрузки
        if requirements.get("payload_kg", 0) > telemetry.get("max_payload_kg", 0):
            return False
        
        return True
    
    def _select_optimal(self, uas_list: List[str], requirements: Dict[str, Any]) -> str:
        """Выбор оптимального БАС из списка подходящих."""
        # Простая оптимизация по остатку заряда
        best_uas = None
        best_battery = 0
        
        for uas_id in uas_list:
            battery = self._telemetry_cache.get(uas_id, {}).get("battery_level", 0)
            if battery > best_battery:
                best_battery = battery
                best_uas = uas_id
        
        return best_uas
```

## 3. Оптимизированный Business Logic

### Четкое разделение критичной и некритичной логики
```python
# business_logic_core.py - Критичные бизнес-правила (D2_OPERATIONAL)
class BusinessLogicCore:
    """Критичные бизнес-правила - минимальный код."""
    
    def __init__(self, min_margin: float = 0.1):
        self._min_margin = min_margin
    
    def validate_order_profitability(self, order: Dict[str, Any], costs: Dict[str, Any]) -> Tuple[bool, float]:
        """Проверка прибыльности заказа - критичное правило."""
        revenue = order.get("price", 0)
        total_cost = sum(costs.values())
        
        if revenue <= 0 or total_cost < 0:
            return False, 0.0
        
        margin = (revenue - total_cost) / revenue if revenue > 0 else 0
        
        return margin >= self._min_margin, margin


# business_logic_service.py - Вспомогательная бизнес-логика
class BusinessLogicService:
    """Некритичная бизнес-логика и оптимизации."""
    
    def __init__(self, core: BusinessLogicCore):
        self.core = core
        self._pricing_engine = PricingEngine()
        self._cost_calculator = CostCalculator()
        self._analytics = AnalyticsService()
    
    async def process_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Полная обработка заказа с оптимизациями."""
        # Расчет затрат
        costs = await self._calculate_costs(order)
        
        # Критичная проверка прибыльности
        is_profitable, margin = self.core.validate_order_profitability(order, costs)
        
        if not is_profitable:
            # Попытка оптимизации
            optimized_costs = await self._optimize_costs(order, costs)
            is_profitable, margin = self.core.validate_order_profitability(order, optimized_costs)
            
            if is_profitable:
                costs = optimized_costs
        
        # Аналитика
        await self._analytics.record_order_analysis(order, costs, margin)
        
        return {
            "accepted": is_profitable,
            "margin": margin,
            "costs": costs,
            "optimizations_applied": costs != await self._calculate_costs(order)
        }
    
    async def _calculate_costs(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Расчет затрат на выполнение заказа."""
        return {
            "fuel": await self._cost_calculator.calculate_fuel_cost(order),
            "operator": await self._cost_calculator.calculate_operator_cost(order),
            "maintenance": await self._cost_calculator.calculate_maintenance_cost(order),
            "insurance": await self._cost_calculator.calculate_insurance_cost(order)
        }
    
    async def _optimize_costs(self, order: Dict[str, Any], initial_costs: Dict[str, Any]) -> Dict[str, Any]:
        """Оптимизация затрат для повышения маржинальности."""
        optimized = initial_costs.copy()
        
        # Оптимизация маршрута для экономии топлива
        optimized_route = await self._pricing_engine.optimize_route(order)
        if optimized_route:
            optimized["fuel"] *= 0.85  # 15% экономии
        
        # Группировка заказов
        if await self._can_batch_order(order):
            optimized["operator"] *= 0.7  # 30% экономии
        
        return optimized
```

## 4. Пример интеграции компонентов

```python
# operator_system.py - Интеграция всех компонентов
class OperatorSystem:
    """Главный класс системы Эксплуатант."""
    
    def __init__(self):
        # Инициализация ядер (доверенные домены)
        self.security_core = SecurityMonitorCore(self._load_policies())
        self.fleet_core = FleetManagerCore(CertificateValidator())
        self.business_core = BusinessLogicCore(min_margin=0.1)
        
        # Инициализация сервисов (недоверенные домены)
        self.security_service = SecurityMonitorService(self.security_core, self.event_bus)
        self.fleet_service = FleetManagerService(self.fleet_core)
        self.business_service = BusinessLogicService(self.business_core)
        
        # Mission Planner - отдельный компонент
        self.mission_planner = MissionPlanner()
    
    async def handle_order(self, order: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка заказа с полным циклом проверок."""
        # 1. Проверка безопасности
        command = {"type": "process_order", "order_id": order["id"]}
        if not await self.security_service.process_command(command, context):
            return {"status": "rejected", "reason": "security_check_failed"}
        
        # 2. Анализ прибыльности
        business_result = await self.business_service.process_order(order)
        if not business_result["accepted"]:
            return {"status": "rejected", "reason": "not_profitable"}
        
        # 3. Выбор БАС
        mission_requirements = self._extract_requirements(order)
        selected_uas = await self.fleet_service.select_best_uas(mission_requirements)
        if not selected_uas:
            return {"status": "rejected", "reason": "no_suitable_uas"}
        
        # 4. Планирование миссии
        mission_plan = await self.mission_planner.create_plan(order, selected_uas)
        
        return {
            "status": "accepted",
            "uas_id": selected_uas,
            "mission_plan": mission_plan,
            "expected_margin": business_result["margin"]
        }
```

## Ключевые принципы оптимизации

1. **Минимизация TCB**: В доверенном домене только критичные функции без побочных эффектов
2. **Чистые функции**: Критичные функции не имеют состояния и побочных эффектов
3. **Разделение ответственности**: Логирование, метрики, уведомления - в недоверенном домене
4. **Простота проверки**: Критичный код легко тестировать и верифицировать
5. **Изоляция доменов**: Минимальное взаимодействие между доменами через четкие интерфейсы