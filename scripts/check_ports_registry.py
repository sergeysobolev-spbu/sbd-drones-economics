#!/usr/bin/env python3
"""Проверка реестра портов: нет коллизий в e2e_ports.*.env и local↔jenkins."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORTS_DOC = PROJECT_ROOT / "docs" / "ports.md"
ENV_FILES = (
    PROJECT_ROOT / "config" / "e2e_ports.local.env",
    PROJECT_ROOT / "config" / "e2e_ports.jenkins.env",
)

IGNORE_PORT_KEYS: frozenset[str] = frozenset()


def _parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key:
            out[key] = value
    return out


def _port_keys(env: dict[str, str]) -> dict[str, int]:
    ports: dict[str, int] = {}
    for key, value in env.items():
        if not key.endswith("_PORT") or key in IGNORE_PORT_KEYS:
            continue
        if not value.isdigit():
            continue
        ports[key] = int(value)
    return ports


def find_intra_profile_conflicts(ports: dict[str, int], profile: str) -> list[str]:
    by_value: dict[int, set[str]] = {}
    for key, num in ports.items():
        by_value.setdefault(num, set()).add(key)

    errors: list[str] = []
    for num, keys in sorted(by_value.items()):
        if len(keys) <= 1:
            continue
        errors.append(
            f"{profile}: порт {num} занят несколькими сервисами "
            f"({', '.join(sorted(keys))}); см. docs/ports.md"
        )
    return errors


def find_cross_profile_conflicts(
    local_ports: dict[str, int], jenkins_ports: dict[str, int]
) -> list[str]:
    overlap = sorted(set(local_ports.values()) & set(jenkins_ports.values()))
    if not overlap:
        return []
    return [
        f"local и jenkins: общие значения портов {overlap} — профили должны быть разведены"
    ]


def check_ports_doc(env_ports: dict[str, int]) -> list[str]:
    if not PORTS_DOC.is_file():
        return [f"отсутствует {PORTS_DOC.relative_to(PROJECT_ROOT)}"]
    text = PORTS_DOC.read_text(encoding="utf-8")
    missing: list[str] = []
    for key, num in sorted(env_ports.items()):
        if key in IGNORE_PORT_KEYS:
            continue
        if str(num) not in text:
            missing.append(f"{key}={num} не найден в docs/ports.md")
    return missing


def main() -> int:
    errors: list[str] = []

    for path in ENV_FILES:
        ports = _port_keys(_parse_env(path))
        profile = path.stem.replace("e2e_ports.", "")
        errors.extend(find_intra_profile_conflicts(ports, profile))

    local = _port_keys(_parse_env(ENV_FILES[0]))
    jenkins = _port_keys(_parse_env(ENV_FILES[1]))
    errors.extend(find_cross_profile_conflicts(local, jenkins))
    errors.extend(check_ports_doc(local))

    if errors:
        print("ports-check: FAILED", file=sys.stderr)
        for line in errors:
            print(f"  - {line}", file=sys.stderr)
        return 1

    print(
        f"ports-check: OK — {len(local)} local + {len(jenkins)} jenkins портов, "
        "коллизий нет; docs/ports.md согласован с e2e_ports.local.env"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
