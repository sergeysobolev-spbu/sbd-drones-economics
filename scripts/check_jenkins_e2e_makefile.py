#!/usr/bin/env python3
"""Проверка: e2e-codespace не хардкодит local-порты (8081/8088) — использует E2E_ENV/URL."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = ROOT / "Makefile"

FORBIDDEN = [
    re.compile(r"curl\s+-sf\s+http://localhost:8081"),
    re.compile(r"curl\s+-sf\s+http://localhost:8088"),
    re.compile(r"nc\s+-z\s+localhost\s+8081"),
]


def extract_target(name: str) -> list[str]:
    lines = MAKEFILE.read_text().splitlines()
    out: list[str] = []
    in_target = False
    for line in lines:
        if re.match(rf"^{name}:", line):
            in_target = True
            continue
        if in_target:
            if line and not line.startswith("\t") and not line.startswith(" "):
                if ":" in line.split("#")[0]:
                    break
            out.append(line)
    return out


def main() -> int:
    block = extract_target("e2e-codespace")
    if not block:
        print("ERROR: target e2e-codespace не найден в Makefile", file=sys.stderr)
        return 1
    text = "\n".join(block)
    errors = []
    for pat in FORBIDDEN:
        if pat.search(text):
            errors.append(f"hardcoded local port: {pat.pattern}")
    if "E2E_RUN_MODE=$(E2E_RUN_MODE)" not in text and "E2E_RUN_MODE=" not in text:
        errors.append("prepare_multi без E2E_RUN_MODE")
    if "$(E2E_ENV)" not in text and "E2E_ENV" not in text:
        errors.append("e2e-codespace не использует E2E_ENV")
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print("check_jenkins_e2e_makefile: OK — e2e-codespace использует E2E_RUN_MODE/E2E_ENV")
    return 0


if __name__ == "__main__":
    sys.exit(main())
