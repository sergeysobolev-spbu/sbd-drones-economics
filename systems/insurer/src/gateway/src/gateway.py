"""
InsurerGateway -- координатор системы страховщика.

Проксирует bus-запросы к InsurerComponent.
"""
from typing import Optional

from sdk.base_gateway import BaseGateway
from broker.system_bus import SystemBus

from systems.insurer.src.gateway.topics import (
    SystemTopics,
    ComponentTopics,
    GatewayActions,
)


class InsurerGateway(BaseGateway):

    ACTION_ROUTING = {
        GatewayActions.CALCULATE_POLICY: ComponentTopics.INSURER_COMPONENT,
        GatewayActions.PURCHASE_POLICY: ComponentTopics.INSURER_COMPONENT,
        GatewayActions.REPORT_INCIDENT: ComponentTopics.INSURER_COMPONENT,
        GatewayActions.TERMINATE_POLICY: ComponentTopics.INSURER_COMPONENT,
    }

    PROXY_TIMEOUT = 10.0

    def __init__(
        self,
        system_id: str,
        bus: SystemBus,
        health_port: Optional[int] = None,
    ):
        super().__init__(
            system_id=system_id,
            system_type="insurer",
            topic=SystemTopics.INSURER,
            bus=bus,
            health_port=health_port,
        )
