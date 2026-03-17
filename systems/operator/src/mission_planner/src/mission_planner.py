"""
Mission Planner Component

Основной компонент планировщика миссий, объединяющий Core и Service.
Обрабатывает сообщения от системной шины и управляет миссиями.
"""
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus
from systems.operator.src.topics import ComponentTopics, SystemTopics

from .mission_planner_core import MissionPlannerCore
from .mission_planner_service import MissionPlannerService


class MissionPlanner(BaseComponent):
    """
    Компонент планировщика миссий
    
    Обрабатывает:
    - Создание и валидацию планов полета
    - Управление жизненным циклом миссий
    - Интеграцию с Fleet Manager для резервирования БАС
    - Мониторинг активных миссий
    """
    
    def __init__(self, component_id: str, bus: SystemBus):
        """
        Инициализация компонента
        
        Args:
            component_id: Идентификатор компонента
            bus: Системная шина
        """
        super().__init__(component_id, bus)
        
        # Инициализация Core и Service
        self.core = MissionPlannerCore()
        self.service = MissionPlannerService(self.core)
        
        # Топики
        self.topic = ComponentTopics.get_mission_planner()
        self.fleet_topic = ComponentTopics.get_fleet_manager()
        self.security_topic = ComponentTopics.get_security_monitor()
        
        # Периодические задачи
        self.cleanup_task = None
        self.monitoring_task = None
        
    def start(self):
        """Запуск компонента"""
        super().start()
        
        # Подписка на топики
        self._subscribe_to_topics()
        
        # Запуск периодических задач
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self.monitoring_task = asyncio.create_task(self._monitor_active_missions())
        
        self.logger.info("Mission Planner started", extra={
            'component_id': self.component_id,
            'topic': self.topic
        })
    
    def stop(self):
        """Остановка компонента"""
        # Отмена периодических задач
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        super().stop()
        self.logger.info("Mission Planner stopped")
    
    def _subscribe_to_topics(self):
        """Подписка на необходимые топики"""
        # Подписка на команды миссий
        self.bus.subscribe(self.topic, self._handle_message)
        
        # Подписка на ответы от Fleet Manager
        fleet_response_topic = f"{self.fleet_topic}.response.{self.component_id}"
        self.bus.subscribe(fleet_response_topic, self._handle_fleet_response)
        
        self.logger.info("Subscribed to topics", extra={
            'topics': [self.topic, fleet_response_topic]
        })
    
    async def _handle_message(self, message: Dict[str, Any]):
        """
        Обработка входящих сообщений
        
        Args:
            message: Входящее сообщение
        """
        try:
            msg_type = message.get('type')
            payload = message.get('payload', {})
            metadata = message.get('metadata', {})
            
            # Извлекаем контекст трассировки
            trace_context = self._extract_trace_context(metadata)
            
            self.logger.info(f"Handling message: {msg_type}", extra={
                'trace_id': trace_context.trace_id,
                'span_id': trace_context.span_id,
                'message_type': msg_type
            })
            
            # Маршрутизация по типу сообщения
            if msg_type == 'create_mission':
                await self._handle_create_mission(payload, trace_context)
            elif msg_type == 'update_mission':
                await self._handle_update_mission(payload, trace_context)
            elif msg_type == 'approve_mission':
                await self._handle_approve_mission(payload, trace_context)
            elif msg_type == 'start_mission':
                await self._handle_start_mission(payload, trace_context)
            elif msg_type == 'complete_mission':
                await self._handle_complete_mission(payload, trace_context)
            elif msg_type == 'abort_mission':
                await self._handle_abort_mission(payload, trace_context)
            elif msg_type == 'get_mission':
                await self._handle_get_mission(payload, trace_context)
            elif msg_type == 'list_missions':
                await self._handle_list_missions(payload, trace_context)
            elif msg_type == 'create_template':
                await self._handle_create_template(payload, trace_context)
            elif msg_type == 'create_from_template':
                await self._handle_create_from_template(payload, trace_context)
            elif msg_type == 'get_statistics':
                await self._handle_get_statistics(payload, trace_context)
            else:
                self.logger.warning(f"Unknown message type: {msg_type}", extra={
                    'trace_id': trace_context.trace_id
                })
                
        except Exception as e:
            self.logger.error(f"Error handling message: {e}", exc_info=True, extra={
                'trace_id': trace_context.trace_id if 'trace_context' in locals() else 'unknown'
            })
    
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