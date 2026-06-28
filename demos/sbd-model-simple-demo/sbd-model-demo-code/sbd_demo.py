from __future__ import annotations

"""
Демо сквозных сценариев (Запрос 10): онбординг (сертификация + закупка БАС),
затем агро-заказ заказчика. Состояние мира хранится в YAML.
"""

import sys
from pathlib import Path as _PathForSys

_DEMO_CODE_DIR = _PathForSys(__file__).resolve().parent
if str(_DEMO_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_DEMO_CODE_DIR))

import multiprocessing as mp
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from actions import (
    PLACE_ORDER,
    REQUEST_FIRMWARE_CERTIFICATION,
    REQUEST_UAS_PURCHASE,
    REQUEST_UAS_REGISTRATION,
)
from simple_broker import SimpleBroker
from entities import (
    ATMEntity,
    AggregatorEntity,
    AgroDroneEntity,
    CustomerEntity,
    DronePortEntity,
    GCSEntity,
    InsurerEntity,
    OperatorEntity,
    RegulatorEntity,
    SITLEntity,
    VendorUASEntity,
)
from messages import BROKER_STOP_ACTION, STOP_ACTION, make_request, new_correlation_id, new_trace_id
from world_state import (
    load_world_state,
    merge_onboarding_into_world,
    reset_context,
    save_world_state,
)

DEFAULT_STATE_FILENAME = "demo_state.yaml"


def default_state_path() -> Path:
    """Путь к YAML по умолчанию рядом с этим модулем."""
    return Path(__file__).resolve().parent / DEFAULT_STATE_FILENAME


class PipeQueue:
    """Очередь поверх multiprocessing.Pipe (обход ограничений семафоров в некоторых средах)."""

    def __init__(self, recv_end: Any, send_end: Any) -> None:
        self._recv = recv_end
        self._send = send_end

    @classmethod
    def create(cls, ctx: Any) -> "PipeQueue":
        recv_end, send_end = ctx.Pipe(duplex=False)
        return cls(recv_end, send_end)

    def put(self, item: Any) -> None:
        self._send.send(item)

    def get(self, timeout: Optional[float] = None) -> Any:
        if timeout is None:
            return self._recv.recv()
        if self._recv.poll(timeout):
            return self._recv.recv()
        raise TimeoutError("queue.get timeout")

    def get_nowait(self) -> Any:
        if not self._recv.poll(0):
            from queue import Empty

            raise Empty
        return self._recv.recv()


def _wait_for_rpc_main(
    reply_queue: Any,
    *,
    correlation_id: str,
    expected_sender: Optional[str],
    timeout_s: float,
) -> Dict[str, Any]:
    deadline = time.time() + timeout_s
    while True:
        if time.time() > deadline:
            raise TimeoutError(f"Timeout waiting response corr={correlation_id}")
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
        return msg


def _send_rpc_from_orchestrator(
    *,
    broker_in_queue: Any,
    reply_to: str,
    receiver: str,
    action: str,
    payload: Dict[str, Any],
) -> Tuple[str, str]:
    correlation_id = new_correlation_id()
    trace_id = new_trace_id()
    msg = make_request(
        sender="orchestrator",
        receiver=receiver,
        action=action,
        payload=payload,
        correlation_id=correlation_id,
        trace_id=trace_id,
        parent_span_id=None,
        reply_to=reply_to,
    ).to_dict()
    broker_in_queue.put(msg)
    return correlation_id, trace_id


def _launch(world: Dict[str, Any]) -> Dict[str, Any]:
    ctx = mp.get_context("fork")
    broker_in_queue = PipeQueue.create(ctx)
    notebooks_dir = Path(__file__).resolve().parents[1]
    log_path = str(notebooks_dir / "simulation.log")

    entity_ids = [
        "customer",
        "aggregator",
        "operator_1",
        "operator_2",
        "insurer",
        "vendor_uas",
        "droneport_A",
        "droneport_B",
        "gcs",
        "agro_drone",
        "sitl",
        "atm",
        "regulator",
    ]
    inbox_queues = {eid: PipeQueue.create(ctx) for eid in entity_ids}
    reply_queues = {eid: PipeQueue.create(ctx) for eid in entity_ids}
    orchestrator_reply_name = "reply_orchestrator"
    orchestrator_reply_queue = PipeQueue.create(ctx)

    def reply_name(entity_id: str) -> str:
        return f"reply_{entity_id}"

    broker = SimpleBroker(broker_in_queue=broker_in_queue, log_path=log_path, poll_sleep_s=0.01)
    for eid in entity_ids:
        broker.register_queue(eid, inbox_queues[eid])
        broker.register_queue(reply_name(eid), reply_queues[eid])
    broker.register_queue(orchestrator_reply_name, orchestrator_reply_queue)
    broker.start()

    procs: List[mp.Process] = [
        CustomerEntity(
            entity_id="customer",
            inbox_queue=inbox_queues["customer"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["customer"],
            reply_queue_name=reply_name("customer"),
            world=world,
        ),
        AggregatorEntity(
            entity_id="aggregator",
            inbox_queue=inbox_queues["aggregator"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["aggregator"],
            reply_queue_name=reply_name("aggregator"),
            world=world,
        ),
        InsurerEntity(
            entity_id="insurer",
            inbox_queue=inbox_queues["insurer"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["insurer"],
            reply_queue_name=reply_name("insurer"),
            world=world,
        ),
        VendorUASEntity(
            entity_id="vendor_uas",
            inbox_queue=inbox_queues["vendor_uas"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["vendor_uas"],
            reply_queue_name=reply_name("vendor_uas"),
            world=world,
        ),
        GCSEntity(
            entity_id="gcs",
            inbox_queue=inbox_queues["gcs"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["gcs"],
            reply_queue_name=reply_name("gcs"),
            world=world,
        ),
        AgroDroneEntity(
            entity_id="agro_drone",
            inbox_queue=inbox_queues["agro_drone"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["agro_drone"],
            reply_queue_name=reply_name("agro_drone"),
            world=world,
        ),
        SITLEntity(
            entity_id="sitl",
            inbox_queue=inbox_queues["sitl"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["sitl"],
            reply_queue_name=reply_name("sitl"),
            world=world,
        ),
        ATMEntity(
            entity_id="atm",
            inbox_queue=inbox_queues["atm"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["atm"],
            reply_queue_name=reply_name("atm"),
            world=world,
        ),
        RegulatorEntity(
            entity_id="regulator",
            inbox_queue=inbox_queues["regulator"],
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queues["regulator"],
            reply_queue_name=reply_name("regulator"),
            world=world,
        ),
    ]
    for op_id in world["operator_ids"]:
        procs.append(
            OperatorEntity(
                entity_id=op_id,
                inbox_queue=inbox_queues[op_id],
                broker_in_queue=broker_in_queue,
                reply_queue=reply_queues[op_id],
                reply_queue_name=reply_name(op_id),
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
    for p in procs:
        p.start()
    return {
        "broker": broker,
        "broker_in_queue": broker_in_queue,
        "procs": procs,
        "entity_ids": entity_ids,
        "orchestrator_reply_name": orchestrator_reply_name,
        "orchestrator_reply_queue": orchestrator_reply_queue,
    }


def _shutdown(runtime: Dict[str, Any]) -> None:
    for eid in runtime["entity_ids"]:
        runtime["broker_in_queue"].put(
            {
                "sender": "orchestrator",
                "receiver": eid,
                "action": STOP_ACTION,
                "payload": {},
                "correlation_id": "stop",
                "trace_id": "stop",
                "span_id": "stop",
                "parent_span_id": None,
                "message_type": "request",
            }
        )
    runtime["broker_in_queue"].put(
        {
            "sender": "orchestrator",
            "receiver": "__broker__",
            "action": BROKER_STOP_ACTION,
            "payload": {},
            "correlation_id": "stop",
            "trace_id": "stop",
            "span_id": "stop",
            "parent_span_id": None,
            "message_type": "request",
        }
    )
    for p in runtime["procs"]:
        p.join(timeout=5.0)
    runtime["broker"].join(timeout=5.0)


def scenario_certification_and_purchase(
    *,
    yaml_path: str | Path,
    world: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Сценарий 1: сертификация прошивки, регистрация одной БАС, закупка N БАС у VendorUAS.

    После остановки процессов мержит артефакты в world и пишет YAML.
    """
    path = Path(yaml_path)
    if world is None:
        world = load_world_state(path)

    runtime = _launch(world)
    out_q = runtime["orchestrator_reply_queue"]
    out_name = runtime["orchestrator_reply_name"]
    in_q = runtime["broker_in_queue"]
    result: Optional[Dict[str, Any]] = None

    try:
        cert_corr, cert_trace = _send_rpc_from_orchestrator(
            broker_in_queue=in_q,
            reply_to=out_name,
            receiver="vendor_uas",
            action=REQUEST_FIRMWARE_CERTIFICATION,
            payload={
                "firmware_version": "2.1.0",
                "vendor_code": "SBD",
                "uas_type": "AGRO",
                "artifacts": ["report.pdf", "tests.json"],
            },
        )
        cert_msg = _wait_for_rpc_main(
            out_q, correlation_id=cert_corr, expected_sender="vendor_uas", timeout_s=60.0
        )
        assert cert_msg["trace_id"] == cert_trace
        firmware_cert = cert_msg["payload"]["firmware_certification_result"]
        assert firmware_cert["approved"] is True

        reg_corr, reg_trace = _send_rpc_from_orchestrator(
            broker_in_queue=in_q,
            reply_to=out_name,
            receiver="vendor_uas",
            action=REQUEST_UAS_REGISTRATION,
            payload={
                "firmware_version": "2.1.0",
                "vendor_code": "SBD",
                "uas_type": "AGRO",
                "imei": "356938035643809",
            },
        )
        reg_msg = _wait_for_rpc_main(
            out_q, correlation_id=reg_corr, expected_sender="vendor_uas", timeout_s=60.0
        )
        assert reg_msg["trace_id"] == reg_trace
        registered_uas_id = reg_msg["payload"]["registered_uas_id"]
        assert re.fullmatch(r"UAS-[A-Z0-9_]+-[A-Z0-9_]+-\d{6}", registered_uas_id)

        purchase_corr, purchase_trace = _send_rpc_from_orchestrator(
            broker_in_queue=in_q,
            reply_to=out_name,
            receiver="operator_1",
            action=REQUEST_UAS_PURCHASE,
            payload={
                "quantity": 2,
                "target_droneport_id": "droneport_B",
                "vendor_code": "SBD",
                "uas_type": "AGRO",
                "firmware_version": "2.1.0",
                "model_id": "agro-model-new",
                "supported_task_types": ["agro"],
                "base_cost": 9800.0,
                "imeis": ["356938035643810", "356938035643811"],
            },
        )
        purchase_msg = _wait_for_rpc_main(
            out_q, correlation_id=purchase_corr, expected_sender="operator_1", timeout_s=60.0
        )
        assert purchase_msg["trace_id"] == purchase_trace
        purchased_ids = purchase_msg["payload"]["uas_purchase_result"]["registered_uas_ids"]
        for uid in purchased_ids:
            assert re.fullmatch(r"UAS-[A-Z0-9_]+-[A-Z0-9_]+-\d{6}", uid)
        assert purchase_msg["payload"]["attachment"]["droneport_id"] == "droneport_B"
        assert purchase_msg["payload"]["attachment"]["assigned_count"] == 2
        uas_items = purchase_msg["payload"].get("purchased_uas_items", [])

        result = {
            "firmware_cert": firmware_cert,
            "standalone_registration": {
                "registered_uas_id": registered_uas_id,
                "imei": "356938035643809",
                "uas_type": "AGRO",
                "vendor_code": "SBD",
                "firmware_version": "2.1.0",
            },
            "purchase": {
                "registered_uas_ids": purchased_ids,
                "droneport_id": "droneport_B",
                "uas_items": uas_items,
                "imeis": ["356938035643810", "356938035643811"],
                "uas_type": "AGRO",
                "vendor_code": "SBD",
                "firmware_version": "2.1.0",
            },
        }
    finally:
        _shutdown(runtime)

    if result is not None:
        merge_onboarding_into_world(world, result)
        save_world_state(path, world)
    return result if result is not None else {}


def scenario_customer_agro_order(
    *,
    yaml_path: str | Path,
    world: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Сценарий 2: заказ заказчика на обработку поля, полный e2e до посадки.

    Читает накопленное состояние из YAML (уже сертифицированные/купленные БАС).
    """
    path = Path(yaml_path)
    if world is None:
        world = load_world_state(path)

    runtime = _launch(world)
    out_q = runtime["orchestrator_reply_queue"]
    out_name = runtime["orchestrator_reply_name"]
    in_q = runtime["broker_in_queue"]
    result: Optional[Dict[str, Any]] = None

    try:
        order_corr, order_trace = _send_rpc_from_orchestrator(
            broker_in_queue=in_q,
            reply_to=out_name,
            receiver="customer",
            action=PLACE_ORDER,
            payload={
                "order": {
                    "id": "ORDER-DEMO-001",
                    "scenario_type": "agro",
                    "destination": {"lat": 55.75, "lon": 37.61},
                    "return_port": "droneport_B",
                    "coverage": {
                        "min_payload": 3.5,
                        "min_range": 1.0,
                        "min_battery": 0.8,
                    },
                },
                "scenario_security_goals": ["SG_ID_AUTH_001", "SG_ID_SAF_002"],
                "max_price": 999999.0,
            },
        )
        final_msg = _wait_for_rpc_main(
            out_q, correlation_id=order_corr, expected_sender="customer", timeout_s=180.0
        )
        assert final_msg["trace_id"] == order_trace
        final_payload = final_msg["payload"]
        assert final_payload.get("status") == "ok", final_payload
        completed = final_payload["order_execution_completed"]
        expected_coords = world["landing_sites"]["ORDER-DEMO-001"]["droneport_B"]
        assert completed["landing_coordinates"] == expected_coords

        result = {"final_order_result": final_payload}
    finally:
        _shutdown(runtime)

    if result is not None:
        save_world_state(path, world)
    return result if result is not None else {}


def run_all_demo(*, yaml_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Сброс YAML, онбординг, агро-заказ — один вызов для CLI."""
    path = Path(yaml_path) if yaml_path is not None else default_state_path()
    reset_context(path)
    onboarding = scenario_certification_and_purchase(yaml_path=path)
    agro = scenario_customer_agro_order(yaml_path=path)
    return {"onboarding": onboarding, "agro_order": agro}


def run_scenario() -> Dict[str, Any]:
    """Обратная совместимость: полный прогон как run_all_demo."""
    return run_all_demo()


def main() -> None:
    print(run_all_demo())


if __name__ == "__main__":
    main()
