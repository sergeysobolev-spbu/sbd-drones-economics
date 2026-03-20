"""Экспорт сущностей для notebook demo code."""

from .customer import CustomerEntity
from .aggregator import AggregatorEntity
from .operator import OperatorEntity
from .insurer import InsurerEntity
from .developers import DevelopersEntity
from .droneport import DronePortEntity
from .nus import NUSEntity
from .agro_drone import AgroDroneEntity
from .sitl import SITLEntity
from .atm import ATMEntity
from .regulator import RegulatorEntity

__all__ = [
    "CustomerEntity",
    "AggregatorEntity",
    "OperatorEntity",
    "InsurerEntity",
    "DevelopersEntity",
    "DronePortEntity",
    "NUSEntity",
    "AgroDroneEntity",
    "SITLEntity",
    "ATMEntity",
    "RegulatorEntity",
]

