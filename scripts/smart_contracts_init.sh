#!/usr/bin/env bash
# Инициализация Hyperledger Fabric для смарт-контрактов sbd-drones-economics.
#
# Что делает:
#   1. Подтягивает submodule fabric-network (если ещё не клонирован).
#   2. Ставит бинарники Fabric и docker-образы через fabric-network/network/start.sh install.
#
# Сеть не поднимается — для запуска используйте `make smart-contract-up`
# (или fabric-network/network/start.sh up напрямую).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SUBMODULE_PATH="fabric-network"
NETWORK_DIR="$REPO_ROOT/$SUBMODULE_PATH/network"

cd "$REPO_ROOT"

echo "=== [1/2] Инициализация submodule $SUBMODULE_PATH ==="
if [ ! -f "$NETWORK_DIR/start.sh" ]; then
    git submodule update --init --recursive "$SUBMODULE_PATH"
else
    # submodule уже инициализирован — синхронизируем на актуальный коммит из .gitmodules
    git submodule update --recursive "$SUBMODULE_PATH"
fi

if [ ! -x "$NETWORK_DIR/start.sh" ]; then
    echo "ERROR: $NETWORK_DIR/start.sh не найден или не исполняемый" >&2
    exit 1
fi

echo "=== [2/2] Установка Fabric (binaries + docker images) ==="
cd "$NETWORK_DIR"
./start.sh install

echo ""
echo "=== Готово ==="
echo "Дальше:"
echo "  make smart-contract-up           # поднять сеть Fabric + chaincode"
echo "  make e2e-smart-contracts         # полный цикл: init+up+stand+test+teardown"
