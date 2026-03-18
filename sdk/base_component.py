"""
Базовый класс для компонентов, использующих SystemBus.

Аналогичен BaseSystem, но без health check и run_forever.
Поддерживает сквозную трассировку через trace_id, span_id, parent_span_id.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional
import uuid
import time
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from broker.system_bus import SystemBus
from sdk.messages import create_response


class TraceContext:
    """Контекст трассировки для отслеживания цепочки вызовов"""
    
    def __init__(self, trace_id: Optional[str] = None, 
                 span_id: Optional[str] = None,
                 parent_span_id: Optional[str] = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.span_id = span_id or str(uuid.uuid4())
        self.parent_span_id = parent_span_id
        self.start_time = time.time()
    
    def create_child_span(self) -> 'TraceContext':
        """Создать дочерний span для вложенной операции"""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=str(uuid.uuid4()),
            parent_span_id=self.span_id
        )
    
    def to_dict(self) -> Dict[str, str]:
        """��реобразовать контекст в словарь для передачи в сообщениях"""
        return {
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'parent_span_id': self.parent_span_id
        }
    
    @classmethod
    def from_message(cls, message: Dict[str, Any]) -> 'TraceContext':
        """Извлечь контекст трассировки из сообщения"""
        return cls(
            trace_id=message.get('trace_id'),
            span_id=message.get('span_id'),
            parent_span_id=message.get('parent_span_id')
        )


class BaseComponent(ABC):
    """
    Абстрактный базовый класс для компонентов дрона.

    Компонент:
    - Подключается к SystemBus (единая шина с системами)
    - Подписывается на свой топик (components.{component_type})
    - Обрабатывает сообщения через маршрутизацию по action
    - Отвечает через reply_to (request/response) или publish
    - Поддерживает сквозную трассировку операций
    """

    def __init__(
        self,
        component_id: str,
        component_type: str,
        topic: str,
        bus: SystemBus,
        enable_tracing: bool = True,
    ):
        self.component_id = component_id
        self.component_type = component_type
        self.topic = topic
        self.bus = bus
        self.enable_tracing = enable_tracing

        self._handlers: Dict[str, Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]] = {}
        self._running = False
        
        # Настройка логирования
        self.logger = logging.getLogger(f"{self.component_type}.{self.component_id}")
        self.logger.setLevel(logging.INFO)

        self._setup_handlers()
        self._register_handlers()

    def _setup_handlers(self):
        """Базовые обработчики."""
        self.register_handler("ping", self._handle_ping)
        self.register_handler("get_status", self._handle_get_status)

    @abstractmethod
    def _register_handlers(self):
        """Регистрирует обработчики конкретного компонента."""
        pass

    def register_handler(
        self,
        action: str,
        handler: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]],
    ):
        """Регистрирует обработчик для action."""
        self._handlers[action] = handler

    def _extract_trace_context(self, message: Dict[str, Any]) -> TraceContext:
        """Извлечь или создать контекст трассировки из сообщения"""
        if self.enable_tracing:
            return TraceContext.from_message(message)
        return TraceContext()
    
    def _inject_trace_context(self, message: Dict[str, Any], context: TraceContext) -> Dict[str, Any]:
        """Добавить контекст трассировки в исходящее сообщение"""
        if self.enable_tracing:
            message.update(context.to_dict())
        return message
    
    def _log_with_trace(self, level: str, message: str, context: TraceContext, **kwargs):
        """Логирование с контекстом трассировки"""
        extra = {
            'trace_id': context.trace_id,
            'span_id': context.span_id,
            'parent_span_id': context.parent_span_id,
            'component_id': self.component_id,
            'component_type': self.component_type,
            **kwargs
        }
        
        if level == 'debug':
            self.logger.debug(message, extra=extra)
        elif level == 'info':
            self.logger.info(message, extra=extra)
        elif level == 'warning':
            self.logger.warning(message, extra=extra)
        elif level == 'error':
            self.logger.error(message, extra=extra)

    def _handle_message(self, message: Dict[str, Any]):
        """Маршрутизация входящего сообщения по action с поддержкой трассировки."""
        # Извлекаем контекст трассировки
        trace_context = self._extract_trace_context(message)
        
        action = message.get("action")
        if not action:
            self._log_with_trace('warning', f"Message without action: {message}", trace_context)
            return

        # Создаем дочерний span для обработки
        handler_context = trace_context.create_child_span()
        
        handler = self._handlers.get(action)
        if not handler:
            self._log_with_trace('warning', f"Unknown action: {action}", handler_context)
            if message.get("reply_to"):
                error_response = {"error": f"Unknown action: {action}"}
                self._inject_trace_context(error_response, handler_context)
                self.bus.respond(message, error_response, action="error")
            return

        try:
            # Логируем начало обработки
            self._log_with_trace('info', f"Handling action: {action}", handler_context, 
                               action=action, sender=message.get('sender'))
            
            start_time = time.time()
            result = handler(message)
            if asyncio.iscoroutine(result):
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    result = asyncio.run(result)
                else:
                    # Callback might be invoked from a thread that already has a running loop.
                    # Run the coroutine in a separate thread to preserve sync handler contract.
                    with ThreadPoolExecutor(max_workers=1) as ex:
                        result = ex.submit(asyncio.run, result).result()
            duration = time.time() - start_time
            
            # Логируем успешное завершение
            self._log_with_trace('info', f"Action {action} completed", handler_context,
                               action=action, duration_ms=int(duration * 1000))
            
            if message.get("reply_to") and result is not None:
                response = create_response(
                    correlation_id=message.get("correlation_id"),
                    payload=result,
                    sender=self.component_id,
                    success=True,
                )
                # Добавляем контекст трассировки в ответ
                self._inject_trace_context(response, handler_context)
                self.bus.publish(message["reply_to"], response)
        except Exception as e:
            # Логируем ошибку
            self._log_with_trace('error', f"Error handling {action}: {e}", handler_context,
                               action=action, error=str(e))
            
            if message.get("reply_to"):
                response = create_response(
                    correlation_id=message.get("correlation_id"),
                    payload={},
                    sender=self.component_id,
                    success=False,
                    error=str(e),
                )
                # Добавляем контекст трассировки в ответ об ошибке
                self._inject_trace_context(response, handler_context)
                self.bus.publish(message["reply_to"], response)

    def _handle_ping(self, message: Dict[str, Any]) -> Dict[str, Any]:
        return {"pong": True, "component_id": self.component_id}

    def _handle_get_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type,
            "topic": self.topic,
            "running": self._running,
            "handlers": list(self._handlers.keys()),
        }

    def create_message(self, action: str, payload: Dict[str, Any], 
                      trace_context: Optional[TraceContext] = None) -> Dict[str, Any]:
        """Создать сообщение с контекстом трассировки"""
        message = {
            'action': action,
            'payload': payload,
            'sender': self.component_id,
            'timestamp': time.time()
        }
        
        if trace_context and self.enable_tracing:
            # Создаем дочерний span для исходящего сообщения
            child_context = trace_context.create_child_span()
            self._inject_trace_context(message, child_context)
        
        return message
    
    def publish_event(self, topic: str, action: str, payload: Dict[str, Any],
                     trace_context: Optional[TraceContext] = None):
        """Опубликовать событие с трассировкой"""
        message = self.create_message(action, payload, trace_context)
        
        if self.enable_tracing and trace_context:
            self._log_with_trace('info', f"Publishing event to {topic}", trace_context,
                               action=action, target_topic=topic)
        
        self.bus.publish(topic, message)
    
    async def request_with_trace(self, topic: str, action: str, payload: Dict[str, Any],
                                trace_context: Optional[TraceContext] = None,
                                timeout: float = 5.0) -> Dict[str, Any]:
        """Отправить запрос с трассировкой и дождаться ответа"""
        message = self.create_message(action, payload, trace_context)
        
        if self.enable_tracing and trace_context:
            self._log_with_trace('info', f"Sending request to {topic}", trace_context,
                               action=action, target_topic=topic)
        
        response = await self.bus.request(topic, message, timeout=timeout)
        
        if self.enable_tracing and trace_context:
            self._log_with_trace('info', f"Received response from {topic}", trace_context,
                               action=action, success=response.get('success', False))
        
        return response

    def start(self):
        """Подписывается на топик и запускает шину."""
        self.bus.start()
        self.bus.subscribe(self.topic, self._handle_message)
        self._running = True
        
        if self.enable_tracing:
            self.logger.info(f"[{self.component_id}] Started with tracing enabled. Listening on topic: {self.topic}")
        else:
            print(f"[{self.component_id}] Started. Listening on topic: {self.topic}")

    def stop(self):
        """Отписывается и останавливает шину."""
        self._running = False
        self.bus.unsubscribe(self.topic)
        self.bus.stop()
        
        if self.enable_tracing:
            self.logger.info(f"[{self.component_id}] Stopped")
        else:
            print(f"[{self.component_id}] Stopped")
