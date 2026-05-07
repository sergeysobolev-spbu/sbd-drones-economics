#!/usr/bin/env python3
"""Сводный отчёт по прогону tcb-test: покрытие по доменам Docker/ДВБ и оценка стоимости (tcb_metrics.json)."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from tcb_container_domains import CONTAINER_TCB_PYTHON_DOMAINS  # noqa: E402
from tcb_metrics import _iter_py_files  # noqa: E402


def _normalize_rel(path_str: str) -> str | None:
    ps = path_str.replace("\\", "/")
    if ps.startswith("src/"):
        return ps
    p = Path(path_str).resolve()
    try:
        return p.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return None


def parse_cobertura(xml_path: Path) -> dict[str, tuple[int, int]]:
    """По файлам: (покрытые строки, всего измеренных строк)."""
    tree = ET.parse(xml_path)
    root_el = tree.getroot()
    by_file: dict[str, tuple[int, int]] = {}
    for cls in root_el.iter("class"):
        fn = cls.get("filename") or ""
        if not fn:
            continue
        rel = _normalize_rel(fn) or fn.replace("\\", "/")
        cov = 0
        tot = 0
        for line in cls.iter("line"):
            tot += 1
            try:
                hits = int(line.get("hits") or 0)
            except ValueError:
                hits = 0
            if hits > 0:
                cov += 1
        if rel in by_file:
            c0, t0 = by_file[rel]
            by_file[rel] = (c0 + cov, t0 + tot)
        else:
            by_file[rel] = (cov, tot)
    return by_file


def domain_coverage_rows(by_file: dict[str, tuple[int, int]]) -> list[tuple[str, str, float | None, int, int]]:
    rows: list[tuple[str, str, float | None, int, int]] = []
    for d in CONTAINER_TCB_PYTHON_DOMAINS:
        svc = str(d["compose_service"])
        specs = [str(x) for x in d["python_path_specs"]]
        files = _iter_py_files(specs)
        cov = tot = 0
        for f in files:
            rel = f.relative_to(ROOT).as_posix()
            c, t = by_file.get(rel, (0, 0))
            cov += c
            tot += t
        pct: float | None = (100.0 * cov / tot) if tot else None
        rationale = str(d.get("rationale_ru", ""))
        rows.append((svc, rationale, pct, cov, tot))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage", type=Path, required=True, help="Cobertura XML от pytest-cov")
    ap.add_argument("--metrics", type=Path, required=True, help="docs/tcb_metrics.json")
    ap.add_argument("--out", type=Path, required=True, help="Markdown отчёт")
    args = ap.parse_args()

    by_file = parse_cobertura(args.coverage.resolve())
    cov_total = sum(c for c, _ in by_file.values())
    lines_total = sum(t for _, t in by_file.values())
    overall = (100.0 * cov_total / lines_total) if lines_total else None

    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    t12 = metrics.get("tcb_cost_task12") or {}
    ipc14 = metrics.get("tcb_ipc_topology_task14") or {}
    after = t12.get("task12_after_snapshot") or {}
    score = after.get("estimated_tcb_cost_score")
    allow_n = after.get("allow_rules_count")
    union_sloc = after.get("union_backend_python_sloc")
    gw_imp = after.get("gateway_direct_service_imports_in_server_py")

    ipc_by_svc = {str(x.get("compose_service")): x for x in (ipc14.get("per_domain") or []) if x.get("compose_service")}
    ipc_edges_n = ipc14.get("deduped_directed_edge_count")

    cov_rel = args.coverage.resolve().relative_to(ROOT.resolve())
    met_rel = args.metrics.resolve().relative_to(ROOT.resolve())
    rows = domain_coverage_rows(by_file)
    lines: list[str] = [
        "# Сводный отчёт ДВБ (последний `make tcb-test`)",
        "",
        f"- **Сформирован:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"- **Cobertura:** `{cov_rel}`",
        f"- **Метрики:** `{met_rel}` (`tcb_cost_task12`, `tcb_ipc_topology_task14`)",
        "",
        "## Общее покрытие измеренных строк (все файлы в отчёте coverage)",
        "",
    ]
    if overall is not None:
        lines.append(f"**{overall:.1f}%** строк с ненулевым hit ({cov_total} / {lines_total}).")
    else:
        lines.append("Нет измеренных строк в XML.")
    lines.extend(["", "## Домены безопасности: покрытие, IPC, цели безопасности", ""])
    if ipc_edges_n is not None:
        lines.append(
            f"Уникальных **ориентированных** связей между доменами (по allow-политикам, без умножения на действие): **{ipc_edges_n}**. "
            "Методика — `methodology_ru` в `tcb_metrics.json` → `tcb_ipc_topology_task14`."
        )
        lines.append("")
    lines.append(
        "| Сервис compose | Покрытие | Покрыто / всего | Входящие IPC (число соседей) | Исходящие IPC | Влияние на цели безопасности | Назначение (кратко) |"
    )
    lines.append("|---|---:|---:|---:|---:|---|---|")
    for svc, rationale, pct, c, t in rows:
        prc = f"{pct:.1f}%" if pct is not None else "—"
        cnt = f"{c} / {t}" if t else "—"
        rshort = rationale.replace("|", "\\|")[:80] + ("…" if len(rationale) > 80 else "")
        ipc_row = ipc_by_svc.get(svc) or {}
        inc = ipc_row.get("inbound_distinct_peers")
        outc = ipc_row.get("outbound_distinct_peers")
        inc_s = str(inc) if isinstance(inc, int) else "—"
        out_s = str(outc) if isinstance(outc, int) else "—"
        goals = ipc_row.get("security_goals_ru") or []
        if isinstance(goals, list) and goals:
            gtxt = "; ".join(str(g).replace("|", "\\|")[:120] for g in goals[:3])
            if len(goals) > 3:
                gtxt += "…"
        else:
            gtxt = "—"
        lines.append(f"| `{svc}` | {prc} | {cnt} | {inc_s} | {out_s} | {gtxt} | {rshort} |")
    lines.extend(
        [
            "",
            "Строки **общего ядра `shared`** входят в объём каждого домена (как в `python_path_specs`); "
            "проценты по строкам просуммированы по всем файлам спецификации домена. "
            "IPC: соседи по дедуплицированным парам доменов из политик (`ipc_inbound_request`, ответы `ipc_response`, запросы шлюза).",
            "",
            "## Оценка стоимости текущей реализации ДВБ (Задача 12)",
            "",
        ]
    )
    if score is not None:
        lines.append(f"- **`estimated_tcb_cost_score`:** {score}")
    else:
        lines.append("- **`estimated_tcb_cost_score`:** нет в JSON (запустите `make tcb-metrics`).")
    lines.extend(
        [
            f"- **`allow_rules_count`:** {allow_n if allow_n is not None else '—'}",
            f"- **`union_backend_python_sloc` (объединённый backend):** {union_sloc if union_sloc is not None else '—'}",
            f"- **Шлюз импортирует домены в `server.py`:** {gw_imp if gw_imp is not None else '—'}",
            "",
            "Формула и трактовка: поле `formula_ru` в `tcb_cost_task12`, текст — [`docs/tcb_assessment.md`](../tcb_assessment.md).",
        ]
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Written {args.out.resolve().relative_to(ROOT.resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
