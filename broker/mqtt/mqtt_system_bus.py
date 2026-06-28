"""MQTT SystemBus."""
import json
import logging
import threading
import time
import asyncio
import os
from typing import Callable, Dict, Any, Optional
from uuid import uuid4
from concurrent.futures import Future, ThreadPoolExecutor

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

from broker.src.system_bus import SystemBus

logger = logging.getLogger(__name__)


class MQTTSystemBus(SystemBus):

    def __init__(
        self, 
        broker: str = None, 
        port: int = None, 
        client_id: str = "system_bus",
        qos: int = 1,
        username: str = None,
        password: str = None,
        event_journal_topic: Optional[str] = None,
    ):
        if not MQTT_AVAILABLE:
            raise ImportError(
                "paho-mqtt is not installed. Install it with: pip install paho-mqtt"
            )

        self.broker = broker or os.environ.get("MQTT_BROKER", "localhost")
        self.port = port or int(os.environ.get("MQTT_PORT", "1883"))
        self.client_id = f"{client_id}_{uuid4().hex[:8]}"
        self.qos = qos
        self.username = username or os.environ.get("BROKER_USER")
        self.password = password or os.environ.get("BROKER_PASSWORD")
        self._client: Optional[mqtt.Client] = None
        self._callbacks: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self._callbacks_lock = threading.Lock()
        self._pending_requests: Dict[str, Future] = {}
        self._pending_lock = threading.Lock()
        self._reply_topic = f"replies/{self.client_id}"
        self._connected = False
        self._started = False
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="mqtt_cb")
        # Dependency inversion: MQTT bus не должен импортировать конкретные
        # топики/классы подсистем Эксплуатанта. Используем инъекцию (параметр/ENV).
        system_id = os.getenv("SYSTEM_ID", "operator-default")
        self.event_journal_topic = (
            event_journal_topic
            or os.getenv("EVENT_JOURNAL_TOPIC")
            or f"{system_id}.event_journal"
        )

    def _topic_to_mqtt(self, topic: str) -> str:
        # Java insurer и Go Agregator подписываются на топики с точками
        # (systems.insurer, components.agregator.*). В MQTT точка — валидный
        # символ, а слэш — иерархический разделитель для wildcard. Имена
        # топиков проекта не иерархические, поэтому пропускаем as-is.
        return topic

    def _mqtt_to_topic(self, mqtt_topic: str) -> str:
        return mqtt_topic

    def _on_connect(self, client, userdata, flags, rc, *args, **kwargs):
        """Callback подключения к broker, переподписка на топики."""
        rc_value = rc if isinstance(rc, int) else getattr(rc, 'value', 0)
        if rc_value == 0:
            self._connected = True
            print(f"MQTTSystemBus connected to {self.broker}:{self.port}")
            with self._callbacks_lock:
                for topic in self._callbacks.keys():
                    mqtt_topic = self._topic_to_mqtt(topic)
                    client.subscribe(mqtt_topic, qos=self.qos)
        else:
            self._connected = False
            print(f"Failed to connect to MQTT broker, return code {rc}")

    def _on_disconnect(self, client, userdata, *args, **kwargs):
        """Callback отключения от broker."""
        self._connected = False
        rc = args[0] if args else 0
        if isinstance(rc, int) and rc != 0:
            print(f"Unexpected MQTT disconnect, code {rc}. Attempting reconnect...")

    def _on_message(self, client, userdata, msg):
        try:
            topic = self._mqtt_to_topic(msg.topic)
            message = json.loads(msg.payload.decode('utf-8'))
            correlation_id = message.get("correlation_id")
            if correlation_id:
                with self._pending_lock:
                    if correlation_id in self._pending_requests:
                        future = self._pending_requests.pop(correlation_id)
                        future.set_result(message)
                        return
            with self._callbacks_lock:
                callback = self._callbacks.get(topic)
                if callback:
                    self._executor.submit(self._safe_callback, topic, callback, message)
                    return
        except json.JSONDecodeError as e:
            print(f"Error decoding MQTT message: {e}")
        except Exception as e:
            print(f"Error processing MQTT message: {e}")

    def _safe_callback(self, topic: str, callback: Callable, message: Dict[str, Any]):
        try:
            callback(message)
        except Exception as e:
            print(f"Error in callback for {topic}: {e}")

    def start(self) -> None:
        """Подключается к MQTT broker и подписывается на reply-топик."""
        if self._started:
            return
        self._client = mqtt.Client(
            client_id=self.client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        if self.username and self.password:
            self._client.username_pw_set(self.username, self.password)
        
        try:
            self._client.connect(self.broker, self.port, keepalive=60)
            self._client.loop_start()
            timeout = 10
            while not self._connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
            
            if not self._connected:
                raise ConnectionError(f"Failed to connect to MQTT broker at {self.broker}:{self.port}")
            self.subscribe(self._reply_topic, lambda msg: None)
            self._started = True
            print(f"MQTTSystemBus started. Reply topic: {self._reply_topic}")
            
        except Exception as e:
            raise ConnectionError(f"Failed to start MQTT SystemBus: {e}")

    def stop(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
        self._executor.shutdown(wait=True)
        self._callbacks.clear()
        self._connected = False
        self._started = False
        print("MQTTSystemBus stopped")

    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """Публикует сообщение в топик (dot-notation)."""
        if not self._started:
            self.start()
        
        mqtt_topic = self._topic_to_mqtt(topic)
        payload = json.dumps(message).encode('utf-8')
        
        try:
            result = self._client.publish(mqtt_topic, payload, qos=self.qos)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True
            else:
                print(f"Failed to publish to {mqtt_topic}, rc={result.rc}")
                return False
        except Exception as e:
            print(f"Error publishing to {mqtt_topic}: {e}")
            return False

    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """Подписывается на топик, callback вызывается при получении сообщения."""
        if not self._started and topic != self._reply_topic:
            self.start()
        
        mqtt_topic = self._topic_to_mqtt(topic)
        
        with self._callbacks_lock:
            self._callbacks[topic] = callback
        
        if self._client and self._connected:
            result, mid = self._client.subscribe(mqtt_topic, qos=self.qos)
            if result == mqtt.MQTT_ERR_SUCCESS:
                return True
            else:
                print(f"Failed to subscribe to {mqtt_topic}, rc={result}")
                return False
        return True

    def unsubscribe(self, topic: str) -> bool:
        mqtt_topic = self._topic_to_mqtt(topic)
        
        with self._callbacks_lock:
            self._callbacks.pop(topic, None)
        
        if self._client and self._connected:
            result, mid = self._client.unsubscribe(mqtt_topic)
            return result == mqtt.MQTT_ERR_SUCCESS
        
        return True

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
        future: Future = Future()
        
        with self._pending_lock:
            self._pending_requests[correlation_id] = future
        
        request_message = {
            **message,
            "correlation_id": correlation_id,
            "reply_to": self._reply_topic
        }

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
            pass
        
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
