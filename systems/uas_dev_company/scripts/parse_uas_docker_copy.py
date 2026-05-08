"""Парсинг COPY для узких Dockerfile UAS Dev Company (Задача 24).

Приводит пути ``systems/uas_dev_company/<rel>`` к относительным от ROOT
(``systems/uas_dev_company``): ``<rel>``. Учитываются только источники под ``src/``.

Использование: см. ``tcb_metrics.build_container_isolation_assessment``.
"""

from __future__ import annotations

import re
from pathlib import Path

# Корень приложения для метрик относительно этого файла: .../systems/uas_dev_company
_SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = _SCRIPTS_DIR.parent

_REPO_PREFIX = "systems/uas_dev_company/"


def _join_dockerfile_continuations(text: str) -> str:
    """Склеить строки с отступным ``\\``, как в Dockerfile."""
    out: list[str] = []
    buf: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if buf:
            buf.append(line.lstrip())
        else:
            buf.append(line)
        if line.endswith("\\"):
            continue
        out.append(" ".join(buf))
        buf = []
    if buf:
        out.append(" ".join(buf))
    return "\n".join(out)


def _substitute_worker_domain(tok: str, domain_pkg: str) -> str:
    return tok.replace("${DOMAIN}", domain_pkg)


def _normalize_source(tok: str) -> str | None:
    t = tok.strip()
    if not t.startswith(_REPO_PREFIX):
        return None
    rel = t[len(_REPO_PREFIX) :].lstrip()
    if not rel.startswith("src/"):
        return None
    return rel


def _parse_copy_instruction(line_stripped: str) -> tuple[list[str], str] | None:
    """Разобрать одну директиву COPY (без ключей --chmod и т.д.).

    Возвращает (список источников, destination) только если назначение — абсолютный путь
    вида ``/app/...`` как в узких образах (последний токен).
    """
    if not line_stripped.upper().startswith("COPY "):
        return None
    body = line_stripped[5:].strip()
    tokens = re.findall(r'"([^"]*)"|(\S+)', body)
    parts: list[str] = []
    for q1, bare in tokens:
        parts.append(q1 if q1 else bare)
    if len(parts) < 2:
        return None
    dest = parts[-1]
    if not dest.startswith("/"):
        # COPY src dest без абсолютного dest или не наш формат
        return None
    return parts[:-1], dest


def collect_copy_sources_from_text(
    dockerfile_text: str,
    *,
    domain_pkg: str | None = None,
) -> tuple[list[str], list[str]]:
    """Список спецификаций под ROOT: файлы (.py или каталоги ``src/shared/tcb`` и т.д.).

    ``domain_pkg``: для ``worker.Dockerfile`` подставить вместо ``${DOMAIN}``.

    Не раскрывает содержимое каталогов: для ``src/foo`` добавляется ``src/foo``.
    Спецификации можно передать в ``tcb_metrics._iter_py_files``.
    Оба возвращаемых значения содержат дубликаты между COPY; финальную дедупликацию
    делает вызывающий код при необходимости.

    Также вернуть необработанные src-токены, если нужна отладка (второе значение).
    """
    lines = _join_dockerfile_continuations(dockerfile_text).splitlines()
    raw_src: list[str] = []
    specs: list[str] = []

    def consider_source(tok: str) -> None:
        if domain_pkg is not None:
            tok = _substitute_worker_domain(tok, domain_pkg)
        n = _normalize_source(tok)
        if n is None:
            return
        raw_src.append(n)
        if n.endswith(".py"):
            specs.append(n)
            return
        # каталог только под src/shared/tcb или целые пакеты ``src/domain``
        if n.startswith("src/"):
            specs.append(n)

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.upper().startswith("COPY ") and "--from=" not in stripped_line:
            parsed = _parse_copy_instruction(stripped_line)
            if parsed is None:
                continue
            sources, _dest = parsed
            for s in sources:
                consider_source(s)

    return specs, raw_src


def worker_image_path_specs(domain_pkg: str) -> list[str]:
    """Спецификации Python-области узкого воркера (как ``python_path_specs``)."""
    path = ROOT / "docker/worker.Dockerfile"
    text = path.read_text(encoding="utf-8")
    specs, _ = collect_copy_sources_from_text(text, domain_pkg=domain_pkg)
    dedup: list[str] = []
    seen: set[str] = set()
    for s in specs:
        if s not in seen:
            seen.add(s)
            dedup.append(s)
    return dedup


def api_gateway_bus_path_specs() -> list[str]:
    path = ROOT / "src/gateway/docker/Dockerfile"
    specs, _ = collect_copy_sources_from_text(path.read_text(encoding="utf-8"))
    return _dedup(specs)


def security_monitor_path_specs() -> list[str]:
    path = ROOT / "src/security_monitor/docker/Dockerfile"
    specs, _ = collect_copy_sources_from_text(path.read_text(encoding="utf-8"))
    return _dedup(specs)


def _dedup(specs: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in specs:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def docker_path_specs_for_compose_service(compose_service: str) -> list[str]:
    """Список директорий/файлов ``src/**`` как в Dockerfile для узкого сервиса."""
    if compose_service.endswith("_worker"):
        pkg = compose_service[: -len("_worker")]
        return worker_image_path_specs(pkg)
    if compose_service == "api_gateway":
        return api_gateway_bus_path_specs()
    if compose_service == "security_monitor":
        return security_monitor_path_specs()
    raise ValueError(f"нет узкого Dockerfile для compose-сервиса {compose_service!r}")
