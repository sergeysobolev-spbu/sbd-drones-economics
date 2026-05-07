#!/usr/bin/env python3
"""Метрики ДВБ (TCB): размер файлов, приблизительная цикломатическая сложность, импорты, allow-политики.

Запуск из каталога systems/uas_dev_company:
  PYTHONPATH=src python scripts/tcb_metrics.py --baseline
  PYTHONPATH=src python scripts/tcb_metrics.py --target
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from tcb_container_domains import (
    CONTAINER_NON_PYTHON,
    CONTAINER_TCB_PYTHON_DOMAINS,
    compose_service_names,
    expected_compose_services,
)
from tcb_ipc_topology import build_ipc_topology_task14

# Baseline: общий доверенный контур до декомпозиции (план Задачи 10).
BASELINE_PATHS = [
    "src/shared/security_monitor.py",
    "src/shared/security_policies.py",
    "src/shared/component_base.py",
    "src/shared/services.py",
    "src/shared/models.py",
    "src/shared/storage.py",
    "src/shared/topics.py",
    "src/shared/integration_adapters.py",
    "src/shared/jwt_tokens.py",
]

# Target: минимальное policy/IPC ядро после выноса чистых политик в shared/tcb/.
TARGET_PATHS = [
    "src/shared/tcb",
    "src/shared/security_monitor.py",
    "src/shared/security_policies.py",
    "src/shared/component_base.py",
    "src/shared/jwt_tokens.py",
    "src/shared/models.py",
]


def _iter_py_files(specs: list[str]) -> list[Path]:
    out: list[Path] = []
    for s in specs:
        p = ROOT / s
        if p.is_dir():
            out.extend(sorted(p.rglob("*.py")))
        else:
            if p.suffix == ".py" and p.is_file():
                out.append(p)
    # уникальные
    seen: set[Path] = set()
    uniq: list[Path] = []
    for f in out:
        rp = f.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(f)
    return uniq


def _sloc_loc(text: str) -> tuple[int, int]:
    lines = text.splitlines()
    loc = len(lines)
    sloc = sum(1 for ln in lines if ln.strip() and not ln.lstrip().startswith("#"))
    return loc, sloc


class CyclomaticVisitor(ast.NodeVisitor):
    """Упрощённая метрика по ветвлениям (близко к McCabe, без полного соответствия)."""

    def __init__(self) -> None:
        self.decisions = 0

    def visit_If(self, node: ast.If) -> None:
        self.decisions += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.decisions += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.decisions += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.decisions += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.decisions += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.decisions += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:  # py3.10+
        self.decisions += sum(1 for _c in node.cases if _c.guard is not None)
        self.decisions += len(node.cases)
        self.generic_visit(node)


def _func_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    v = CyclomaticVisitor()
    v.visit(node)
    return 1 + v.decisions


def _collect_imports(tree: ast.AST) -> set[str]:
    mods: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for alias in n.names:
                base = (alias.name or "").split(".")[0]
                if base:
                    mods.add(base)
        elif isinstance(n, ast.ImportFrom):
            if n.module:
                base = n.module.split(".")[0]
                if base:
                    mods.add(base)
    return mods


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


@dataclass
class FileMetrics:
    path: str
    loc: int
    sloc: int
    functions: int
    sum_complexity: int
    max_complexity: int
    functions_over_10: int
    imports: list[str]


def analyze_file(path: Path) -> FileMetrics:
    text = path.read_text(encoding="utf-8")
    loc, sloc = _sloc_loc(text)
    tree = ast.parse(text, filename=str(path))
    imports = sorted(_collect_sup_stdlib_imports(_collect_imports(tree)))

    func_nodes: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_nodes.append(n)

    complexities = [_func_complexity(f) for f in func_nodes]
    over10 = sum(1 for c in complexities if c > 10)
    return FileMetrics(
        path=_relative_path(path),
        loc=loc,
        sloc=sloc,
        functions=len(func_nodes),
        sum_complexity=sum(complexities) if complexities else 0,
        max_complexity=max(complexities) if complexities else 0,
        functions_over_10=over10,
        imports=imports,
    )


_STDLIB = {
    "abc",
    "aifc",
    "argparse",
    "array",
    "ast",
    "asyncio",
    "base64",
    "binascii",
    "bisect",
    "builtins",
    "bz2",
    "collections",
    "compileall",
    "contextlib",
    "copy",
    "csv",
    "dataclasses",
    "datetime",
    "decimal",
    "enum",
    "fractions",
    "functools",
    "glob",
    "gzip",
    "hashlib",
    "hmac",
    "importlib",
    "inspect",
    "io",
    "itertools",
    "json",
    "keyword",
    "linecache",
    "logging",
    "math",
    "msilib",
    "multiprocessing",
    "numbers",
    "operator",
    "os",
    "pathlib",
    "pickle",
    "platform",
    "queue",
    "random",
    "re",
    "secrets",
    "shlex",
    "shutil",
    "signal",
    "socket",
    "sqlite3",
    "ssl",
    "stat",
    "string",
    "struct",
    "subprocess",
    "sys",
    "tempfile",
    "textwrap",
    "threading",
    "time",
    "token",
    "tokenize",
    "tomllib",
    "traceback",
    "typing",
    "unicodedata",
    "unittest",
    "urllib",
    "uuid",
    "warnings",
    "weakref",
    "xml",
    "zipfile",
    "zoneinfo",
}


def _collect_sup_stdlib_imports(mods: set[str]) -> set[str]:
    """Внешние (не stdlib) top-level имена; typing_extensions считается внешним."""
    return {m for m in mods if m not in _STDLIB and m != "__future__"}


def _core_aggregate(file_metrics: list[FileMetrics]) -> dict[str, int | list[str]]:
    ext_imports: set[str] = set()
    for f in file_metrics:
        ext_imports.update(f.imports)
    return {
        "file_count": len(file_metrics),
        "total_loc": sum(f.loc for f in file_metrics),
        "total_sloc": sum(f.sloc for f in file_metrics),
        "total_functions": sum(f.functions for f in file_metrics),
        "sum_complexity": sum(f.sum_complexity for f in file_metrics),
        "max_complexity": max((f.max_complexity for f in file_metrics), default=0),
        "functions_over_10": sum(f.functions_over_10 for f in file_metrics),
        "external_imports": sorted(ext_imports),
    }


def analyze_bundle(label: str, path_specs: list[str]) -> dict:
    files = _iter_py_files(path_specs)
    file_metrics = [analyze_file(p) for p in files]
    agg_core = _core_aggregate(file_metrics)
    agg: dict = {
        "label": label,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **agg_core,
    }
    # allow-политики IPC
    sys.path.insert(0, str(ROOT / "src"))
    from shared.security_policies import canonical_allow_rule_tuples  # noqa: E402

    rules = canonical_allow_rule_tuples()
    agg["allow_policy_rules_count"] = len(rules)
    return {
        "aggregate": agg,
        "files": [asdict(f) for f in file_metrics],
    }


def build_container_isolation_assessment() -> dict:
    """Задача 11: ДБ в контейнерах; при ЦБ-критичном коде весь домен — ДВБ; IPC под монитором."""
    compose_yml = ROOT / "docker-compose.yml"
    observed = compose_service_names(compose_yml)
    expected = expected_compose_services()
    python_domains: list[dict] = []
    for d in CONTAINER_TCB_PYTHON_DOMAINS:
        specs = [str(x) for x in d["python_path_specs"]]
        files = _iter_py_files(specs)
        fms = [analyze_file(p) for p in files]
        python_domains.append(
            {
                "compose_service": d["compose_service"],
                "whole_domain_in_tcb": d["whole_domain_in_tcb"],
                "in_cb123_tcb_union": d.get("in_cb123_tcb_union", True),
                "maps_to_cb": list(d.get("maps_to_cb") or []),
                "rationale_ru": d["rationale_ru"],
                "python_path_specs": specs,
                "aggregate": _core_aggregate(fms),
            }
        )
    union_specs: list[str] = []
    seen_specs: set[str] = set()
    for d in CONTAINER_TCB_PYTHON_DOMAINS:
        for s in d["python_path_specs"]:
            s = str(s)
            if s not in seen_specs:
                seen_specs.add(s)
                union_specs.append(s)
    union_files = _iter_py_files(union_specs)
    union_fms = [analyze_file(p) for p in union_files]

    cb123_specs: list[str] = []
    seen_cb: set[str] = set()
    for d in CONTAINER_TCB_PYTHON_DOMAINS:
        if not d.get("in_cb123_tcb_union", True):
            continue
        for s in d["python_path_specs"]:
            s = str(s)
            if s not in seen_cb:
                seen_cb.add(s)
                cb123_specs.append(s)
    cb123_files = _iter_py_files(cb123_specs)
    cb123_fms = [analyze_file(p) for p in cb123_files]
    return {
        "task": "Задача 11 — изоляция ДБ в Docker и ДВБ по контейнеру",
        "rule_ru": (
            "Домены безопасности изолированы процессами контейнеров; у контейнера один уровень "
            "критичности; наличие ЦБ-критичной логики переводит весь домен в ДВБ. Обмен между "
            "Python-доменами в профилях kafka/mqtt идёт через брокер и security_monitor (шлюз не "
            "вызывает воркеры напрямую при UAS_GATEWAY_BACKEND=bus)."
        ),
        "compose_services_observed": observed,
        "compose_service_set_matches_model": sorted(observed) == sorted(expected),
        "non_python_domains": CONTAINER_NON_PYTHON,
        "python_domains_tcb": python_domains,
        "union_unique_backend_python_scope": {
            "deduped_path_specs": union_specs,
            "note_ru": "Объединение всех Python-доменов прототипа (операционный охват).",
            "aggregate": _core_aggregate(union_fms),
        },
        "union_cb123_python_scope": {
            "deduped_path_specs": cb123_specs,
            "note_ru": (
                "Задача 15: объединение путей только доменов, отнесённых к реализации официальных ЦБ-1…ЦБ-3 "
                "для оценки стоимости ДВБ; домены «только ТБ» исключены."
            ),
            "aggregate": _core_aggregate(cb123_fms),
        },
        "dockerfile_shared_note_ru": (
            "Каждый образ копирует `systems/uas_dev_company` целиком; сертификационный анализ "
            "привязывает доверие к границе процесса и к фактически исполняемым модулям, "
            "но наличие общего `shared` в образе сохраняет общий объём кода для всех воркеров."
        ),
    }


TASK12_NORMATIVE_BASELINE: dict[str, str | int | bool] = {
    "label": "task12_baseline_before_refactor",
    "description_ru": (
        "Нормативная точка «до» Задачи 12: монолит сервисов в одном shared/services.py, "
        "14 allow-правил (update_user, list_drones без отдельных узких действий), "
        "шлюз по умолчанию sqlite и прямой импорт всех доменных сервисов из gateway/server.py; "
        "метрика контейнеров использовала весь src/shared на домен."
    ),
    "allow_policy_rules_count": 14,
    "distinct_gateway_proxy_actions": 13,
    "gateway_server_default_backend": "sqlite",
    "gateway_server_imported_domain_service_symbols": True,
    "per_domain_metric_used_full_src_shared_tree": True,
}


def _gateway_server_imports_domain_packages() -> bool:
    """Прямой импорт пакетов доменов из gateway/server.py (нежелательно в bus-контуре)."""
    path = ROOT / "src/gateway/server.py"
    text = path.read_text(encoding="utf-8")
    markers = (
        "user_management",
        "certification_service",
        "drone_registry",
        "purchase_service",
        "firmware_ingestion",
        "audit_log",
        "UserService",
        "FirmwareService",
    )
    return any(m in text for m in markers)


def build_task12_assessment(container_block: dict) -> dict:
    """Методика стоимости ДВБ после Задачи 12 (политики, связность шлюза, per-domain объём)."""
    sys.path.insert(0, str(ROOT / "src"))
    from shared.security_policies import full_policy_dicts  # noqa: E402
    from shared.topics import Actions, ComponentTopics  # noqa: E402

    rows = full_policy_dicts()
    g = ComponentTopics.API_GATEWAY
    gw_targets = [r for r in rows if r["sender"] == g and r["action"] != Actions.PROXY_REQUEST]
    actions = {r["action"] for r in gw_targets}
    topics = {r["topic"] for r in gw_targets}
    narrow_actions = {
        Actions.ENABLE_USER,
        Actions.DISABLE_USER,
        Actions.REPORT_CRITICAL_VULNERABILITY,
        Actions.LIST_REGISTERED_DRONES,
    }
    narrow_in_policy = narrow_actions & actions

    per_domain_sloc_cb123 = sum(
        int((d.get("aggregate") or {}).get("total_sloc") or 0)
        for d in container_block.get("python_domains_tcb") or []
        if d.get("in_cb123_tcb_union", True)
    )
    union_sloc_cb123 = int(
        (container_block.get("union_cb123_python_scope") or {}).get("aggregate", {}).get("total_sloc") or 0
    )
    union_sloc_all = int(
        (container_block.get("union_unique_backend_python_scope") or {}).get("aggregate", {}).get("total_sloc") or 0
    )
    gateway_imports_domains = _gateway_server_imports_domain_packages()
    w_sloc, w_rules, w_gateway_import_penalty = 0.02, 0.35, 12.0
    estimated = w_sloc * union_sloc_cb123 + w_rules * len(rows) + (w_gateway_import_penalty if gateway_imports_domains else 0.0)

    after = {
        "allow_rules_count": len(rows),
        "gateway_proxy_target_rows": len(gw_targets),
        "distinct_topics_in_gateway_allow": len(topics),
        "distinct_actions_in_gateway_allow": len(actions),
        "narrow_action_tokens_present": sorted(narrow_in_policy),
        "policy_granularity_index": round(len(actions) / len(gw_targets), 4) if gw_targets else 0.0,
        "union_backend_python_sloc": union_sloc_cb123,
        "union_all_system_backend_python_sloc": union_sloc_all,
        "sum_per_domain_aggregate_sloc_cb123_only": per_domain_sloc_cb123,
        "gateway_direct_service_imports_in_server_py": gateway_imports_domains,
        "gateway_default_backend": "bus",
        "per_domain_python_path_model": "component_dir_plus_shared_core",
        "tcb_cost_union_scope_ru": (
            "Задача 15: union_backend_python_sloc — дедупликация по доменам с in_cb123_tcb_union; "
            "полный операционный объём — union_all_system_backend_python_sloc."
        ),
        "estimated_tcb_cost_score": round(estimated, 3),
    }
    before = TASK12_NORMATIVE_BASELINE
    delta = {
        "allow_rules_count_delta": int(after["allow_rules_count"]) - int(before["allow_policy_rules_count"]),
        "gateway_domain_imports_addressed": bool(before["gateway_server_imported_domain_service_symbols"])
        and not after["gateway_direct_service_imports_in_server_py"],
    }
    return {
        "task": "Задача 12 — гранулярность политик, слабые связи доменов, методика стоимости ДВБ",
        "formula_ru": (
            "estimated_tcb_cost_score = 0.02 * union_backend_python_sloc + 0.35 * allow_rules_count "
            "+ (12.0 если gateway/server.py импортирует пакеты доменов; иначе 0). "
            "**union_backend_python_sloc** после Задачи 15 — SLOC объединения **только** доменов `in_cb123_tcb_union` "
            "(реализация официальных ЦБ-1…ЦБ-3), без учёта доменов «только ТБ». "
            "Число allow-правил IPC включает нормативные политики Задачи 14. Штраф — связность шлюза с доменами в одном файле."
        ),
        "task12_baseline_snapshot": before,
        "task12_after_snapshot": after,
        "task12_delta_baseline_to_after": delta,
    }


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _delta(before: dict, after: dict) -> dict:
    ba = before.get("aggregate", {})
    aa = after.get("aggregate", {})
    keys = [
        "file_count",
        "total_loc",
        "total_sloc",
        "total_functions",
        "sum_complexity",
        "max_complexity",
        "functions_over_10",
        "allow_policy_rules_count",
    ]
    out: dict = {}
    for k in keys:
        b, a = ba.get(k), aa.get(k)
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            out[k] = {"before": b, "after": a, "delta": a - b}
    bi = set(ba.get("external_imports") or [])
    ai = set(aa.get("external_imports") or [])
    out["external_imports_added"] = sorted(ai - bi)
    out["external_imports_removed"] = sorted(bi - ai)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="TCB metrics for uas_dev_company")
    parser.add_argument("--baseline", action="store_true", help="Write baseline_tcb snapshot")
    parser.add_argument("--target", action="store_true", help="Write target_tcb snapshot + delta")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs" / "tcb_metrics.json",
        help="Output JSON path",
    )
    args = parser.parse_args()
    if not args.baseline and not args.target:
        parser.error("specify --baseline and/or --target")

    data = _load_json(args.out)
    if args.baseline:
        data["baseline_tcb"] = analyze_bundle("baseline_tcb", BASELINE_PATHS)
        data["delta_baseline_to_target"] = None
    if args.target:
        data["target_tcb"] = analyze_bundle("target_tcb", TARGET_PATHS)
        b = data.get("baseline_tcb") or {}
        t = data.get("target_tcb") or {}
        if b and t:
            data["delta_baseline_to_target"] = _delta(b, t)

    container_block = build_container_isolation_assessment()
    data["container_isolation_tcb_task11"] = container_block
    data["tcb_cost_task12"] = build_task12_assessment(container_block)
    sys.path.insert(0, str(ROOT / "src"))
    from shared.security_policies import full_policy_dicts as _full_policies  # noqa: E402

    data["tcb_ipc_topology_task14"] = build_ipc_topology_task14(_full_policies())

    _write_json(args.out, data)
    print(f"Written {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
