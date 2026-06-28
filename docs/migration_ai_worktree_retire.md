<!-- doc-meta: status=active version=1.0 updated=2026-06-28 -->

# Вывод worktree `sbd-drones-economics-ai`

**Дата:** 2026-06-28  
**Канон:** [`sbd-drones-economics`](../) (единственный локальный каталог)  
**Remote:** `git@gitflic-lk.ru:security-by-design-demos-developers/sbd-drones-economics.git`

## Pre-flight (фаза 0)

| Проверка | Результат |
|----------|-----------|
| HEAD `-economics` vs `-ai` | `f1c044e5` — совпадает |
| `git ls-files` diff | 0 строк |
| Tracked content | идентичен |

## Local rescue (фаза 1)

| Артефакт | Действие |
|----------|----------|
| `ci/jenkins/.env` | **Скопирован** из `-ai` в `-economics` (локально, вне git) |
| `docker/.env` | Уже был в `-economics`; в `-ai` отсутствует |
| `systems/analytics/` (untracked в `-ai`) | **Не переносить** — старее `systems/DroneAnalytics` |
| `systems/agregator/` (untracked в `-ai`) | **Не переносить** — дубликат `systems/Agregator` |
| `systems/DronePortGCS/` (untracked в `-ai`) | **Не переносить** — канон split `gcs` + `drone_port` |
| `demos/.../simulation.log`, `.pytest_cache` | **Не переносить** — ephemeral |
| Личные WIP `.md` | Не найдено вне tracked docs |

## Нормализация (фаза 2)

- `git submodule update --init --recursive`
- Удалён orphan `systems/analytics/` (gitlink без содержимого)
- `systems/insurer` — pin по `master`
- `bash scripts/check_jenkins_submodule_pins.sh`

## Gates перед удалением `-ai`

| Gate | Результат |
|------|-----------|
| `make ports-check` | ✅ OK |
| `make unit-test` | ✅ 70 passed |
| `make ci-config-check` | ⚠️ FAIL — `check_jenkins_submodule_pins` (upstream commits не на remote; pre-existing) |

## Удаление worktree

**Выполнено 2026-06-28:** каталог `/home/user/projects/sbd-drones-economics/sbd-drones-economics-ai` удалён (`rm -rf`).

Remote GitFlic **не удалять**.
