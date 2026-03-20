"""Kafka SystemBus."""
import json
import logging
import threading
import time
import asyncio
import os
from typing import Callable, Dict, Any, Optional
from uuid import uuid4
from concurrent.futures import Future

try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import KafkaError, NoBrokersAvailable, KafkaConnectionError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

from broker.src.system_bus import SystemBus
from broker.config import get_kafka_bootstrap

logger = logging.getLogger(__name__)


class KafkaSystemBus(SystemBus):
    def _get_connect_deadline_s(self) -> float:
        """
        Максимальное время ожидания доступности брокера при старте.

        Нужен из-за типичной гонки старта docker-compose: приложения поднимаются
        быстрее Kafka и первое подключение может дать ECONNREFUSED/NoBrokersAvailable.
        """
        try:
            return float(os.getenv("KAFKA_CONNECT_TIMEOUT_S", "30"))
        except ValueError:
            return 30.0

    def _wait_for_broker(self, op_name: str, fn) -> Any:
        deadline = time.time() + self._get_connect_deadline_s()
        delay_s = 0.2
        last_exc: Optional[BaseException] = None

        while time.time() < deadline:
            try:
                return fn()
            except (NoBrokersAvailable, KafkaConnectionError) as e:
                last_exc = e
                time.sleep(delay_s)
                delay_s = min(delay_s * 1.7, 2.0)

        if last_exc is not None:
            raise last_exc
        raise TimeoutError(f"Kafka broker not available during {op_name}")

    def __init__(
        self, 
        bootstrap_servers: str = None, 
        client_id: str = "system_bus",
        group_id: str = None,
        username: str = None,
        password: str = None,
        event_journal_topic: Optional[str] = None,
    ):
        if not KAFKA_AVAILABLE:
            raise ImportError(
                "kafka-python is not installed. Install it with: pip install kafka-python"
            )

        self.bootstrap_servers = bootstrap_servers or get_kafka_bootstrap()
        self.client_id = client_id
        self.group_id = group_id or f"{client_id}_group"
        self.username = username or os.environ.get("BROKER_USER")
        self.password = password or os.environ.get("BROKER_PASSWORD")
        self._producer: Optional[KafkaProducer] = None
        self._consumers: Dict[str, KafkaConsumer] = {}
        self._callbacks: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self._consumer_threads: Dict[str, threading.Thread] = {}
        self._running: Dict[str, bool] = {}
        self._pending_requests: Dict[str, Future] = {}
        self._pending_lock = threading.Lock()
        self._reply_topic = f"replies.{client_id}.{uuid4().hex[:8]}"
        self._started = False
        # Dependency inversion: Kafka bus не должен знать про конкретные топики/классы
        # подсистем Эксплуатанта. Вместо импортов из `systems.operator` используем
        # инъекцию (параметр/ENV) топика EventJournal.
        system_id = os.getenv("SYSTEM_ID", "operator-default")
        self.event_journal_topic = (
            event_journal_topic
            or os.getenv("EVENT_JOURNAL_TOPIC")
            or f"{system_id}.event_journal"
        )

    def _get_sasl_config(self) -> dict:
        """SASL-конфиг для producer/consumer, если заданы username/password."""
        if self.username and self.password:
            return {
                'security_protocol': 'SASL_PLAINTEXT',
                'sasl_mechanism': 'PLAIN',
                'sasl_plain_username': self.username,
                'sasl_plain_password': self.password
            }
        return {}

    def _init_producer(self):
        """Создаёт Kafka producer при первой отправке."""
        if self._producer is None:
            def _create():
                config = {
                    'bootstrap_servers': self.bootstrap_servers,
                    'client_id': self.client_id,
                    'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
                    'acks': 'all',
                    **self._get_sasl_config()
                }
                return KafkaProducer(**config)

            self._producer = self._wait_for_broker("producer_init", _create)

    def start(self) -> None:
        """Запускает bus, создаёт reply-топик и подписывается на ответы."""
        if self._started:
            return
        self._init_producer()
        # Дождаться Kafka на старте: даже если producer создан, первый send может упасть.
        def _ensure_send():
            self._producer.send(self._reply_topic, {"_init": True}).get(timeout=10)
            return True

        try:
            self._wait_for_broker("initial_send", _ensure_send)
        except Exception:
            # Не фейлим старт, если топик не удалось "прогреть" с первого раза:
            # подписка на reply topic ниже создаст consumer и будет повторять подключение.
            pass
        self._producer.flush()
        time.sleep(1.0)
        self.subscribe(self._reply_topic, self._handle_reply)
        
        self._started = True
        print(f"KafkaSystemBus started. Reply topic: {self._reply_topic}")

    def stop(self) -> None:
        """Останавливает consumers и producer."""
        for topic in list(self._running.keys()):
            self._running[topic] = False
        for topic, thread in list(self._consumer_threads.items()):
            thread.join(timeout=2)
        for consumer in self._consumers.values():
            try:
                consumer.close()
            except Exception:
                pass
        if self._producer:
            try:
                self._producer.close()
            except Exception:
                pass
        
        self._consumers.clear()
        self._callbacks.clear()
        self._consumer_threads.clear()
        self._running.clear()
        self._started = False
        
        print("KafkaSystemBus stopped")

    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """Публикует сообщение в топик."""
        self._init_producer()
        try:
            future = self._producer.send(topic, message)
            future.get(timeout=10)
            return True
        except KafkaError as e:
            print(f"Error publishing to Kafka topic {topic}: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error publishing to {topic}: {e}")
            return False

    def _consumer_loop(self, topic: str):
        """Цикл чтения сообщений из топика и вызова callback."""
        consumer = self._consumers.get(topic)
        callback = self._callbacks.get(topic)
        
        if not consumer or not callback:
            return
        for _ in range(3):
            consumer.poll(timeout_ms=500)
        
        while self._running.get(topic, False):
            try:
                messages = consumer.poll(timeout_ms=1000)
                for topic_partition, records in messages.items():
                    for record in records:
                        try:
                            message = record.value
                            callback(message)
                        except Exception as e:
                            print(f"Error processing message from {topic}: {e}")
            except Exception as e:
                if self._running.get(topic, False):
                    print(f"Error in consumer loop for {topic}: {e}")
                    time.sleep(1)

    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """Подписывается на топик, callback вызывается при получении сообщения."""
        if topic in self._callbacks:
            print(f"Already subscribed to {topic}")
            return True
        
        self._callbacks[topic] = callback
        try:
            is_reply_topic = topic.startswith("replies.")
            group_suffix = str(uuid4())[:8] if is_reply_topic else "v1"
            
            config = {
                'bootstrap_servers': self.bootstrap_servers,
                'client_id': f"{self.client_id}_{topic.replace('.', '_')}",
                'group_id': f"{self.group_id}_{topic.replace('.', '_')}_{group_suffix}",
                'value_deserializer': lambda m: json.loads(m.decode('utf-8')),
                'auto_offset_reset': 'earliest',
                'enable_auto_commit': True,
                **self._get_sasl_config()
            }
            def _create_consumer():
                return KafkaConsumer(topic, **config)

            consumer = self._wait_for_broker(f"consumer_init:{topic}", _create_consumer)
            self._consumers[topic] = consumer
            self._running[topic] = True
            thread = threading.Thread(
                target=self._consumer_loop,
                args=(topic,),
                daemon=True,
                name=f"kafka-consumer-{topic}"
            )
            thread.start()
            self._consumer_threads[topic] = thread
            time.sleep(2.0)
            return True
        except Exception as e:
            print(f"Error subscribing to {topic}: {e}")
            return False

    def unsubscribe(self, topic: str) -> bool:
        """Отписывается от топика."""
        self._running[topic] = False
        
        if topic in self._consumer_threads:
            thread = self._consumer_threads[topic]
            thread.join(timeout=2)
            del self._consumer_threads[topic]
        
        if topic in self._callbacks:
            del self._callbacks[topic]
        
        if topic in self._consumers:
            try:
                self._consumers[topic].close()
            except Exception:
                pass
            del self._consumers[topic]
        
        return True

    def _handle_reply(self, message: Dict[str, Any]):
        """Обрабатывает входящий ответ по correlation_id, завершает pending Future."""
        correlation_id = message.get("correlation_id")
        if not correlation_id:
            return
        
        with self._pending_lock:
            if correlation_id in self._pending_requests:
                future = self._pending_requests.pop(correlation_id)
                future.set_result(message)

    def request(
        self, 
        topic: str, 
        message: Dict[str, Any], 
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """Синхронный request/response: отправляет запрос, ждёт ответ до timeout."""
        if not self._started:
            self.start()
        correlation_id = str(uuid4())
        source_component = message.get("sender") or "system_bus"
        try:
            from sdk.event_emitter import emit_event

            emit_event(
                self,
                self.event_journal_topic,
                "ipc_request",
                severity="info",
                source_component=source_component,
                payload={
                    "topic": topic,
                    "action": message.get("action"),
                    "sender": message.get("sender"),
                    "correlation_id": correlation_id,
                    "timeout_s": timeout,
                },
            )
        except Exception:
            # IPC logging не должен ломать бизнес-логику
            pass

        future: Future = Future()
        with self._pending_lock:
            self._pending_requests[correlation_id] = future
        request_message = {
            **message,
            "correlation_id": correlation_id,
            "reply_to": self._reply_topic
        }
        if not self.publish(topic, request_message):
            with self._pending_lock:
                self._pending_requests.pop(correlation_id, None)
            try:
                from sdk.event_emitter import emit_event

                emit_event(
                    self,
                    self.event_journal_topic,
                    "ipc_response",
                    severity="error",
                    source_component=source_component,
                    payload={
                        "topic": topic,
                        "action": message.get("action"),
                        "sender": message.get("sender"),
                        "correlation_id": correlation_id,
                        "success": False,
                        "error": "publish_failed",
                    },
                )
            except Exception:
                pass
            return None
        try:
            result = future.result(timeout=timeout)
            try:
                from sdk.event_emitter import emit_event

                emit_event(
                    self,
                    self.event_journal_topic,
                    "ipc_response",
                    severity="info" if (result or {}).get("success", True) else "error",
                    source_component=source_component,
                    payload={
                        "topic": topic,
                        "action": message.get("action"),
                        "sender": message.get("sender"),
                        "correlation_id": correlation_id,
                        "response": (result or {}).get("payload") if isinstance(result, dict) else result,
                        "success": (result or {}).get("success", True) if isinstance(result, dict) else True,
                        "error": (result or {}).get("error") if isinstance(result, dict) else None,
                    },
                )
            except Exception:
                pass
            return result
        except TimeoutError:
            with self._pending_lock:
                self._pending_requests.pop(correlation_id, None)
            print(f"Request to {topic} timed out after {timeout}s")
            try:
                from sdk.event_emitter import emit_event

                emit_event(
                    self,
                    self.event_journal_topic,
                    "ipc_response",
                    severity="error",
                    source_component=source_component,
                    payload={
                        "topic": topic,
                        "action": message.get("action"),
                        "sender": message.get("sender"),
                        "correlation_id": correlation_id,
                        "success": False,
                        "error": "timeout",
                    },
                )
            except Exception:
                pass
            return None
        except Exception as e:
            with self._pending_lock:
                self._pending_requests.pop(correlation_id, None)
            print(f"Error waiting for response: {e}")
            try:
                from sdk.event_emitter import emit_event

                emit_event(
                    self,
                    self.event_journal_topic,
                    "ipc_response",
                    severity="error",
                    source_component=source_component,
                    payload={
                        "topic": topic,
                        "action": message.get("action"),
                        "sender": message.get("sender"),
                        "correlation_id": correlation_id,
                        "success": False,
                        "error": str(e),
                    },
                )
            except Exception:
                pass
            return None

    def request_async(
        self, 
        topic: str, 
        message: Dict[str, Any], 
        timeout: float = 30.0
    ) -> asyncio.Future:
        """Асинхронная обёртка над request()."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(
            None, 
            lambda: self.request(topic, message, timeout)
        )
