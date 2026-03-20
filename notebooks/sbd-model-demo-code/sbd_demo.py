from __future__ import annotations

"""
Сквозной (end-to-end) демо-тест сценария v2.0.

Эквивалентен тому, что выполняет `run_demo()` в `notebooks/sbd-model-demo.ipynb`,
но оформлен как отдельный python-скрипт, чтобы его можно было запускать извне.
"""

import multiprocessing as mp
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from actions import RECEIVE_ORDER
from broker import VABSBroker
from entities import (
    AggregatorEntity,
    ATMEntity,
    AgroDroneEntity,
    CustomerEntity,
    DevelopersEntity,
    DronePortEntity,
    ExecutorEntity,
    InsurerEntity,
    NUSEntity,
    RegulatorEntity,
    SITLEntity,
)
from messages import BROKER_STOP_ACTION, STOP_ACTION, make_request, new_correlation_id


def build_world() -> Dict[str, Any]:
    """Создаёт минимальный набор тестовых данных для сценария."""
    return {
        "aggregator_constants": {"agro": ["SG_ID_CONSTR_010"]},
        "executor_ids": ["executor_1", "executor_2"],
        "system_security_goals": {
            "executor_1": ["SG_ID_AUTH_001", "SG_ID_SAF_002", "SG_ID_CONSTR_010"],
            "executor_2": ["SG_ID_AUTH_001", "SG_ID_SAF_002"],
        },
        "executors": {
            "executor_1": {
                "system_security_goals": ["SG_ID_AUTH_001", "SG_ID_SAF_002", "SG_ID_CONSTR_010"]
            },
            "executor_2": {"system_security_goals": ["SG_ID_AUTH_001", "SG_ID_SAF_002"]},
        },
        "default_return_port": "droneport_B",
        "dronports": {
            "droneport_A": {
                "uas": [
                    {
                        "uas_id": "uas_A_01",
                        "model_id": "agro-model-1",
                        "supported_task_types": ["agro"],
                        "base_cost": 9000.0,
                    },
                    {
                        "uas_id": "uas_A_02",
                        "model_id": "agro-model-2",
                        "supported_task_types": ["agro"],
                        "base_cost": 10500.0,
                    },
                ]
            },
            "droneport_B": {
                "uas": [
                    {
                        "uas_id": "uas_B_11",
                        "model_id": "agro-model-3",
                        "supported_task_types": ["agro"],
                        "base_cost": 9500.0,
                    }
                ]
            },
        },
        "landing_sites": {
            # mapping: order_id -> droneport_id -> landing_coordinates
            "ORDER-DEMO-001": {
                "droneport_A": [55.75, 37.61],
                "droneport_B": [55.76, 37.62],
            }
        },
    }


def _wait_for_rpc_main(
    reply_queue: Any,
    *,
    correlation_id: str,
    expected_sender: Optional[str],
    timeout_s: float,
) -> Dict[str, Any]:
    """Ожидает RPC-response по correlation_id."""
    deadline = time.time() + timeout_s
    while True:
        if time.time() > deadline:
            raise TimeoutError(
                f"Timeout waiting response corr={correlation_id} expected_sender={expected_sender}"
            )
        try:
            msg = reply_queue.get(timeout=0.2)
        except Exception:
            continue

        if not isinstance(msg, dict):
            continue
        if msg.get("correlation_id") != correlation_id:
            continue
        if expected_sender is not None and msg.get("sender") != expected_sender:
            continue
        return msg.get("payload", {})


def run_scenario() -> Dict[str, Any]:
    """Запускает end-to-end сценарий и делает минимальные asserts."""
    world = build_world()

    ctx = mp.get_context("fork")
    broker_in_queue = ctx.Queue()

    # Лог-файл в notebooks/
    notebooks_dir = Path(__file__).resolve().parents[1]
    log_path = str(notebooks_dir / "simulation.log")

    entities_inbox_ids: List[str] = [
        "customer",
        "aggregator",
        "executor_1",
        "executor_2",
        "insurer",
        "developers",
        "droneport_A",
        "droneport_B",
        "nus",
        "agro_drone",
        "sitl",
        "atm",
        "regulator",
    ]

    def reply_name(entity_id: str) -> str:
        return f"reply_{entity_id}"

    inbox_queues: Dict[str, Any] = {eid: ctx.Queue() for eid in entities_inbox_ids}
    reply_queues: Dict[str, Any] = {eid: ctx.Queue() for eid in entities_inbox_ids}
    orchestrator_reply_name = "reply_orchestrator"
    orchestrator_reply_queue = ctx.Queue()

    broker = VABSBroker(
        broker_in_queue=broker_in_queue,
        log_path=log_path,
        poll_sleep_s=0.01,
    )

    # Регистрация очередей ВАБС до start()
    for eid in entities_inbox_ids:
        broker.register_queue(eid, inbox_queues[eid])
        broker.register_queue(reply_name(eid), reply_queues[eid])

    broker.register_queue(orchestrator_reply_name, orchestrator_reply_queue)
    broker.start()

    procs: List[mp.Process] = []

    procs.append(
        CustomerEntity(
            entity_id="customer",
            inbox_queue=inbox_queues["customer"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["customer"],
            reply_queue_name=reply_name("customer"),
            world=world,
        )
    )
    procs.append(
        AggregatorEntity(
            entity_id="aggregator",
            inbox_queue=inbox_queues["aggregator"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["aggregator"],
            reply_queue_name=reply_name("aggregator"),
            world=world,
        )
    )

    for ex_id in ["executor_1", "executor_2"]:
        procs.append(
            ExecutorEntity(
                entity_id=ex_id,
                inbox_queue=inbox_queues[ex_id],
                broker_in_queue=broker_in_queue,
                reply_queue=reply_queues[ex_id],
                reply_queue_name=reply_name(ex_id),
                world=world,
            )
        )

    procs.append(
        InsurerEntity(
            entity_id="insurer",
            inbox_queue=inbox_queues["insurer"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["insurer"],
            reply_queue_name=reply_name("insurer"),
            world=world,
        )
    )
    procs.append(
        DevelopersEntity(
            entity_id="developers",
            inbox_queue=inbox_queues["developers"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["developers"],
            reply_queue_name=reply_name("developers"),
            world=world,
        )
    )

    for dp_id in ["droneport_A", "droneport_B"]:
        procs.append(
            DronePortEntity(
                entity_id=dp_id,
                inbox_queue=inbox_queues[dp_id],
                broker_in_queue=broker_in_queue,
                reply_queue=reply_queues[dp_id],
                reply_queue_name=reply_name(dp_id),
                world=world,
            )
        )

    procs.append(
        NUSEntity(
            entity_id="nus",
            inbox_queue=inbox_queues["nus"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["nus"],
            reply_queue_name=reply_name("nus"),
            world=world,
        )
    )
    procs.append(
        AgroDroneEntity(
            entity_id="agro_drone",
            inbox_queue=inbox_queues["agro_drone"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["agro_drone"],
            reply_queue_name=reply_name("agro_drone"),
            world=world,
        )
    )
    procs.append(
        SITLEntity(
            entity_id="sitl",
            inbox_queue=inbox_queues["sitl"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["sitl"],
            reply_queue_name=reply_name("sitl"),
            world=world,
        )
    )
    procs.append(
        ATMEntity(
            entity_id="atm",
            inbox_queue=inbox_queues["atm"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["atm"],
            reply_queue_name=reply_name("atm"),
            world=world,
        )
    )
    procs.append(
        RegulatorEntity(
            entity_id="regulator",
            inbox_queue=inbox_queues["regulator"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["regulator"],
            reply_queue_name=reply_name("regulator"),
            world=world,
        )
    )

    for p in procs:
        p.start()

    order = {
        "id": "ORDER-DEMO-001",
        "scenario_type": "agro",
        "destination": {"lat": 55.75, "lon": 37.61},
        "return_port": "droneport_B",
        "coverage": {"min_payload": 3.5, "min_range": 1.0, "min_battery": 0.8},
    }
    scenario_security_goals = ["SG_ID_AUTH_001", "SG_ID_SAF_002"]
    max_price = 999999.0

    correlation_id = new_correlation_id()
    initial_msg = make_request(
        sender="orchestrator",
        receiver="customer",
        action=RECEIVE_ORDER,
        payload={
            "order": order,
            "scenario_security_goals": scenario_security_goals,
            "max_price": max_price,
        },
        correlation_id=correlation_id,
        reply_to=orchestrator_reply_name,
    ).to_dict()

    broker_in_queue.put(initial_msg)

    final_payload = _wait_for_rpc_main(
        orchestrator_reply_queue,
        correlation_id=correlation_id,
        expected_sender="customer",
        timeout_s=180.0,
    )

    # Ассёрты
    assert final_payload.get("status") == "ok", final_payload
    completed = final_payload.get("order_execution_completed")
    assert completed is not None

    coords = completed.get("landing_coordinates")
    assert coords is not None and isinstance(coords, list) and len(coords) == 2

    expected_coords = world["landing_sites"][order["id"]][order["return_port"]]
    assert coords == expected_coords, (coords, expected_coords)

    # Остановка всех сущностей и брокера
    for eid in entities_inbox_ids:
        broker_in_queue.put(
            {
                "sender": "orchestrator",
                "receiver": eid,
                "action": STOP_ACTION,
                "payload": {},
                "correlation_id": "stop",
                "message_type": "request",
            }
        )

    broker_in_queue.put(
        {
            "sender": "orchestrator",
            "receiver": "__broker__",
            "action": BROKER_STOP_ACTION,
            "payload": {},
            "correlation_id": "stop",
            "message_type": "request",
        }
    )

    for p in procs:
        p.join(timeout=5.0)
    broker.join(timeout=5.0)

    return final_payload


def main() -> None:
    """CLI entrypoint."""
    result = run_scenario()
    print("\n===== SBD DEMO RESULT =====")
    print(result)


if __name__ == "__main__":
    main()

