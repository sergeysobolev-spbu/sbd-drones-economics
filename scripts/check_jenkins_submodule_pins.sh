#!/usr/bin/env bash
# Проверка: gitlink каждого submodule в HEAD доступен на upstream remote.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if [ ! -f .gitmodules ]; then
  echo "check_jenkins_submodule_pins: нет .gitmodules — skip"
  exit 0
fi

fail=0
checked=0

while IFS= read -r entry; do
  name="${entry%% *}"
  path="${entry#* }"
  sha="$(git rev-parse "HEAD:${path}")"
  url="$(git config -f .gitmodules --get "submodule.${name}.url")"

  if [ -z "$url" ]; then
    echo "WARN: нет URL для submodule ${name} (${path})" >&2
    continue
  fi

  checked=$((checked + 1))
  echo "check_jenkins_submodule_pins: ${path} @ ${sha}"

  if git ls-remote --exit-code "$url" "$sha" >/dev/null 2>&1; then
    echo "  OK"
    continue
  fi
  if git ls-remote "$url" 2>/dev/null | awk '{print $1}' | grep -qx "$sha"; then
    echo "  OK (listed in ls-remote)"
    continue
  fi

  echo "ERROR: commit ${sha} для ${path} не найден на ${url}" >&2
  echo "  push upstream или repin gitlink в parent repo" >&2
  fail=1
done < <(
  git config -f .gitmodules --get-regexp '^submodule\..*\.path$' \
    | while read -r key relpath; do
        name="${key#submodule.}"
        name="${name%.path}"
        echo "${name} ${relpath}"
      done
)

if [ "$checked" -eq 0 ]; then
  echo "check_jenkins_submodule_pins: нет submodule в .gitmodules"
  exit 0
fi

if [ "$fail" -ne 0 ]; then
  echo "check_jenkins_submodule_pins: FAIL" >&2
  exit 1
fi

echo "check_jenkins_submodule_pins: OK — ${checked} submodule(s) reachable on remote"
