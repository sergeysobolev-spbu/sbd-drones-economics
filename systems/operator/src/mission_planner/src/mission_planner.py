"""
Mission Planner Component (D1_TRUSTED).

Этот компонент должен соответствовать протоколу `sdk.base_component.BaseComponent`:
- сообщения маршрутизируются по полю `action`
- request/response идёт через `reply_to` + `correlation_id`

Файл ранее содержал альтернативный протокол (message['type'] и кастомный create_message),
что приводило к ошибкам рантайма (абстрактный `_register_handlers` и несовместимый __init__).
"""

from __future__ import annotations

import math
import os
import time
from typing import Any, Dict, Optional
from uuid import uuid4

from broker.system_bus import SystemBus
from sdk.base_component import BaseComponent
from systems.operator.src.topics import ComponentTopics, MissionPlannerActions


class MissionPlanner(BaseComponent):
    def __init__(self, component_id: str, bus: SystemBus):
        topic = ComponentTopics.get_mission_planner()
        super().__init__(
            component_id=component_id,
            component_type="mission_planner",
            topic=topic,
            bus=bus,
            enable_tracing=True,
        )

        # Простое хранилище миссий для интеграционного сценария.
        self._missions: Dict[str, Dict[str, Any]] = {}

    def _register_handlers(self):
        self.register_handler(MissionPlannerActions.CREATE_MISSION, self._handle_create_mission)
        self.register_handler(MissionPlannerActions.VALIDATE_MISSION, self._handle_validate_mission)
        self.register_handler(MissionPlannerActions.REQUEST_UTM_APPROVAL, self._handle_request_utm_approval)
        self.register_handler(MissionPlannerActions.UPDATE_MISSION_STATUS, self._handle_update_mission_status)
        self.register_handler(MissionPlannerActions.GET_MISSION_DETAILS, self._handle_get_mission_details)
        self.register_handler(MissionPlannerActions.CALCULATE_ROUTE, self._handle_calculate_route)
        self.register_handler(MissionPlannerActions.CHECK_AIRSPACE, self._handle_check_airspace)

    async def _handle_create_mission(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {}) or {}
        order = payload.get("order", {}) or {}

        mission_id = payload.get("mission_id") or f"MISSION-{uuid4().hex[:8].upper()}"
        distance_km = self._derive_distance_km(order)
        payload_weight = float(order.get("payload_weight", 0) or 0)

        self._missions[mission_id] = {
            "mission_id": mission_id,
            "status": "draft",
            "distance": distance_km,
            "payload_weight": payload_weight,
            "order_id": order.get("id"),
            "updated_at": time.time(),
        }

        return {"mission_id": mission_id, "status": "draft", "distance": distance_km}

    async def _handle_validate_mission(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {}) or {}
        mission_id = payload.get("mission_id")
        if not mission_id:
            return {"valid": False, "error": "mission_id is required"}

        # Упрощённая валидация для интеграционного сценария.
        return {"valid": True, "validation_results": []}

    async def _handle_get_mission_details(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {}) or {}
        mission_id = payload.get("mission_id")
        if not mission_id:
            return {"error": "mission_id is required"}

        mission = self._missions.get(mission_id)
        if not mission:
            return {"error": f"Mission {mission_id} not found"}

        return {
            "mission_id": mission_id,
            "distance": mission.get("distance", 0.0),
            "payload_weight": mission.get("payload_weight", 0.0),
        }

    async def _handle_request_utm_approval(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {}) or {}
        mission_id = payload.get("mission_id")
        if not mission_id:
            return {"approved": False, "error": "mission_id is required"}

        approval_id = f"UTM-APPROVAL-{uuid4().hex[:8].upper()}"
        return {"approved": True, "approval_id": approval_id, "mission_id": mission_id}

    async def _handle_update_mission_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {}) or {}
        mission_id = payload.get("mission_id")
        status = payload.get("status")
        if not mission_id or not status:
            return {"error": "mission_id and status are required"}

        mission = self._missions.setdefault(mission_id, {"mission_id": mission_id})
        mission["status"] = status
        mission["updated_at"] = time.time()
        if payload.get("reason"):
            mission["reason"] = payload.get("reason")
        return {"updated": True, "mission_id": mission_id, "status": status}

    async def _handle_calculate_route(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {}) or {}
        order = payload.get("order", {}) or {}
        distance_km = self._derive_distance_km(order)
        return {"distance": distance_km, "waypoints_count": 2}

    async def _handle_check_airspace(self, message: Dict[str, Any]) -> Dict[str, Any]:
        # Заглушка: в текущем интеграционном стенде считаем пространство доступным.
        return {"allowed": True, "restrictions": []}

    def _derive_distance_km(self, order: Dict[str, Any]) -> float:
        if "distance" in order and order["distance"] is not None:
            try:
                return float(order["distance"])
            except (TypeError, ValueError):
                pass

        start = order.get("start_location") or {}
        end = order.get("end_location") or {}
        try:
            lat1, lon1 = float(start["lat"]), float(start["lon"])
            lat2, lon2 = float(end["lat"]), float(end["lon"])
        except Exception:
            # Фоллбек на небольшой маршрут
            return float(os.getenv("DEFAULT_MISSION_DISTANCE_KM", "10.5"))

        return self._haversine_km(lat1, lon1, lat2, lon2)

    def _haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c
    
    async def _handle_create_mission(self, payload: Dict[str, Any], trace_context):
        """Обработка создания миссии"""
        span_id = self._generate_span_id()
        
        self.logger.info("Creating mission", extra={
            'trace_id': trace_context.trace_id,
            'span_id': span_id,
            'operator_id': payload.get('operator_id'),
            'uas_id': payload.get('uas_id')
        })
        
        # Создаем миссию
        result = await self.service.create_mission(payload)
        
        if result['success']:
            # Отправляем событие в Security Monitor
            await self._send_security_event('mission_created', {
                'mission_id': result['mission_id'],
                'operator_id': payload.get('operator_id'),
                'uas_id': payload.get('uas_id'),
                'status': result['status']
            }, trace_context)
            
            # Если миссия валидна, резервируем БАС
            if result['status'] in ['validated', 'approved']:
                await self._reserve_uas_for_mission(
                    result['mission_id'],
                    payload.get('uas_id'),
                    payload.get('takeoff_time'),
                    result['flight_parameters']['estimated_duration'],
                    trace_context
                )
        
        # Отправляем ответ
        response = self.create_message(
            msg_type='create_mission_response',
            payload=result,
            trace_context=trace_context
        )
        
        response_topic = payload.get('response_topic', f"{self.topic}.response")
        self.bus.publish(response_topic, response)
    
    async def _handle_update_mission(self, payload: Dict[str, Any], trace_context):
        """Обработка обновления миссии"""
        mission_id = payload.get('mission_id')
        updates = payload.get('updates', {})
        
        result = await self.service.update_mission(mission_id, updates)
        
        if result['success']:
            await self._send_security_event('mission_updated', {
                'mission_id': mission_id,
                'updates': list(updates.keys())
            }, trace_context)
        
        response = self.create_message(
            msg_type='update_mission_response',
            payload=result,
            trace_context=trace_context
        )
        
        response_topic = payload.get('response_topic', f"{self.topic}.response")
        self.bus.publish(response_topic, response)
    
    async def _handle_approve_mission(self, payload: Dict[str, Any], trace_context):
        """Обработка утверждения миссии"""
        mission_id = payload.get('mission_id')
        approver_id = payload.get('approver_id')
        
        result = await self.service.approve_mission(mission_id, approver_id)
        
        if result['success']:
            await self._send_security_event('mission_approved', {
                'mission_id': mission_id,
                'approver_id': approver_id
            }, trace_context)
        
        response = self.create_message(
            msg_type='approve_mission_response',
            payload=result,
            trace_context=trace_context
        )
        
        response_topic = payload.get('response_topic', f"{self.topic}.response")
        self.bus.publish(response_topic, response)
    
    async def _handle_start_mission(self, payload: Dict[str, Any], trace_context):
        """Обработка запуска миссии"""
        mission_id = payload.get('mission_id')
        
        result = await self.service.start_mission(mission_id)
        
        if result['success']:
            await self._send_security_event('mission_started', {
                'mission_id': mission_id,
                'started_at': result['started_at']
            }, trace_context)
            
            # Уведомляем Fleet Manager о начале миссии
            mission = self.service.get_mission(mission_id)
            if mission:
                await self._notify_mission_start(
                    mission_id,
                    mission['uas_id'],
                    trace_context
                )
        
        response = self.create_message(
            msg_type='start_mission_response',
            payload=result,
            trace_context=trace_context
        )
        
        response_topic = payload.get('response_topic', f"{self.topic}.response")
        self.bus.publish(response_topic, response)
    
    async def _handle_complete_mission(self, payload: Dict[str, Any], trace_context):
        """Обработка завершения миссии"""
        mission_id = payload.get('mission_id')
        completion_data = payload.get('completion_data', {})
        
        result = await self.service.complete_mission(mission_id, completion_data)
        
        if result['success']:
            await self._send_security_event('mission_completed', {
                'mission_id': mission_id,
                'completed_at': result['completed_at']
            }, trace_context)
            
            # Освобождаем БАС
            mission = self.service.get_mission(mission_id)
            if mission:
                await self._release_uas(
                    mission['uas_id'],
                    mission_id,
                    trace_context
                )
        
        response = self.create_message(
            msg_type='complete_mission_response',
            payload=result,
            trace_context=trace_context
        )
        
        response_topic = payload.get('response_topic', f"{self.topic}.response")
        self.bus.publish(response_topic, response)
    
    async def _handle_abort_mission(self, payload: Dict[str, Any], trace_context):
        """Обработка прерывания миссии"""
        mission_id = payload.get('mission_id')
        reason = payload.get('reason', 'Unknown')
        
        result = await self.service.abort_mission(mission_id, reason)
        
        if result['success']:
            await self._send_security_event('mission_aborted', {
                'mission_id': mission_id,
                'reason': reason
            }, trace_context)
            
            # Освобождаем БАС
            mission = self.service.get_mission(mission_id)
            if mission:
                await self._release_uas(
                    mission['uas_id'],
                    mission_id,
                    trace_context
                )
        
        response = self.create_message(
            msg_type='abort_mission_response',
            payload=result,
            trace_context=trace_context
        )
        
        response_topic = payload.get('response_topic', f"{self.topic}.response")
        self.bus.publish(response_topic, response)
    
    async def _handle_get_mission(self, payload: Dict[str, Any], trace_context):
        """Обработка получения информации о миссии"""
        mission_id = payload.get('mission_id')
        
        mission = self.service.get_mission(mission_id)
        
        response = self.create_message(
            msg_type='get_mission_response',
            payload={
                'success': mission is not None,
                'mission': mission,
                'error': f'Mission {mission_id} not found' if mission is None else None
            },
            trace_context=trace_context
        )
        
        response_topic = payload.get('response_topic', f"{self.topic}.response")
        self.bus.publish(response_topic, response)
    
    async def _handle_list_missions(self, payload: Dict[str, Any], trace_context):
        """Обработка получения списка миссий"""
        filters = payload.get('filters', {})
        
        missions = self.service.list_missions(filters)
        
        response = self.create_message(
            msg_type='list_missions_response',
            payload={
                'success': True,
                'missions': missions,
                'count': len(missions)
            },
            trace_context=trace_context
        )
        
        response_topic = payload.get('response_topic', f"{self.topic}.response")
        self.bus.publish(response_topic, response)
    
    async def _handle_create_template(self, payload: Dict[str, Any], trace_context):
        """Обработка создания шаблона"""
        result = await self.service.create_template(payload)
        
        response = self.create_message(
            msg_type='create_template_response',
            payload=result,
            trace_context=trace_context
        )
        
        response_topic = payload.get('response_topic', f"{self.topic}.response")
        self.bus.publish(response_topic, response)
    
    async def _handle_create_from_template(self, payload: Dict[str, Any], trace_context):
        """Обработка создания миссии из шаблона"""
        template_id = payload.get('template_id')
        mission_data = payload.get('mission_data', {})
        
        result = await self.service.create_mission_from_template(template_id, mission_data)
        
        if result['success']:
            await self._send_security_event('mission_created_from_template', {
                'mission_id': result['mission_id'],
                'template_id': template_id
            }, trace_context)
        
        response = self.create_message(
            msg_type='create_from_template_response',
            payload=result,
            trace_context=trace_context
        )
        
        response_topic = payload.get('response_topic', f"{self.topic}.response")
        self.bus.publish(response_topic, response)
    
    async def _handle_get_statistics(self, payload: Dict[str, Any], trace_context):
        """Обработка получения статистики"""
        stats = self.service.get_statistics()
        
        response = self.create_message(
            msg_type='get_statistics_response',
            payload={
                'success': True,
                'statistics': stats
            },
            trace_context=trace_context
        )
        
        response_topic = payload.get('response_topic', f"{self.topic}.response")
        self.bus.publish(response_topic, response)
    
    async def _handle_fleet_response(self, message: Dict[str, Any]):
        """Обработка ответов от Fleet Manager"""
        msg_type = message.get('type')
        payload = message.get('payload', {})
        metadata = message.get('metadata', {})
        
        trace_context = self._extract_trace_context(metadata)
        
        self.logger.info(f"Received fleet response: {msg_type}", extra={
            'trace_id': trace_context.trace_id,
            'response_type': msg_type
        })
        
        # Обрабатываем ответы на резервирование
        if msg_type == 'reserve_uas_response':
            if not payload.get('success'):
                # Если не удалось зарезервировать БАС, отменяем миссию
                mission_id = metadata.get('mission_id')
                if mission_id:
                    await self.service.abort_mission(
                        mission_id,
                        f"Failed to reserve UAS: {payload.get('error')}"
                    )
    
    async def _reserve_uas_for_mission(self, mission_id: str, uas_id: str,
                                      start_time: float, duration: float,
                                      trace_context):
        """Резервирование БАС для миссии"""
        message = self.create_message(
            msg_type='reserve_uas',
            payload={
                'uas_id': uas_id,
                'start_time': start_time,
                'duration': duration,
                'purpose': f'Mission {mission_id}',
                'response_topic': f"{self.fleet_topic}.response.{self.component_id}"
            },
            trace_context=trace_context
        )
        
        # Добавляем mission_id в метаданные для обработки ответа
        message['metadata']['mission_id'] = mission_id
        
        self.bus.publish(self.fleet_topic, message)
    
    async def _notify_mission_start(self, mission_id: str, uas_id: str, trace_context):
        """Уведомление Fleet Manager о начале миссии"""
        message = self.create_message(
            msg_type='mission_started',
            payload={
                'mission_id': mission_id,
                'uas_id': uas_id,
                'timestamp': datetime.now().timestamp()
            },
            trace_context=trace_context
        )
        
        self.bus.publish(self.fleet_topic, message)
    
    async def _release_uas(self, uas_id: str, mission_id: str, trace_context):
        """Освобождение БАС после миссии"""
        message = self.create_message(
            msg_type='release_uas',
            payload={
                'uas_id': uas_id,
                'mission_id': mission_id,
                'timestamp': datetime.now().timestamp()
            },
            trace_context=trace_context
        )
        
        self.bus.publish(self.fleet_topic, message)
    
    async def _send_security_event(self, event_type: str, event_data: Dict[str, Any],
                                 trace_context):
        """Отправка события в Security Monitor"""
        message = self.create_message(
            msg_type='security_event',
            payload={
                'event_type': event_type,
                'component': 'mission_planner',
                'data': event_data,
                'timestamp': datetime.now().timestamp()
            },
            trace_context=trace_context
        )
        
        self.bus.publish(self.security_topic, message)
    
    async def _periodic_cleanup(self):
        """Периодическая очистка старых миссий"""
        while True:
            try:
                await asyncio.sleep(3600)  # Каждый час
                
                self.logger.info("Running periodic cleanup")
                await self.service.cleanup_old_missions()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup: {e}", exc_info=True)
    
    async def _monitor_active_missions(self):
        """Мониторинг активных миссий"""
        while True:
            try:
                await asyncio.sleep(60)  # Каждую минуту
                
                # Получаем статистику
                stats = self.service.get_statistics()
                active_count = stats.get('active_missions', 0)
                
                if active_count > 0:
                    self.logger.info(f"Active missions: {active_count}", extra={
                        'active_missions': active_count,
                        'total_missions': stats.get('total_missions', 0)
                    })
                
                # Проверяем таймауты миссий
                # В реальной системе здесь была бы более сложная логика
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in mission monitoring: {e}", exc_info=True)