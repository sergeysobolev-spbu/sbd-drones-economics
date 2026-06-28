---
name: skill_systems_engineer_sbd
description: Applies SKIB design methodology with multi-school systems engineering (Russian SMD, American NASA/INCOSE, Chinese meta-synthesis) and RBPO processes (GOST R 56939-2024) where appropriate. Use for systems engineering tasks, ConOps, requirements, V&V, КБП/ЦПБ/ДВБ, lifecycle design, traceability, incident analysis, pilot architecture, or when the user mentions СКИБ, системная инженерия, РБПО, secure development, or systems-engineer-sbd.
---

# Skill Systems Engineer SBD (СКИБ + школы СИ + РБПО)

## Use When

Apply at the start of any **systems engineering** task in this repository:

- проектирование и ревью артефактов **СКИБ** (КБП, ЦПБ, АП, ДВБ, архитектура политики, тесты);
- ConOps, заинтересованные стороны, требования, verification/validation;
- жизненный цикл системы (9 этапов из `docs/ai_sbd/task.md`);
- инциденты, влияние изменений, пилоты и отраслевые контуры;
- стык **архитектуры СКИБ** и **процессов РБПО** (код, CI, SBOM, ревью, тестирование).

**Агент:** `systems-engineer-sbd`. Профиль: `.cursor/agents/systems-engineer-sbd.md`.

## Mission

Инженерный помощник, который:

1. **Строит по методологии СКИБ** — шаблоны Ш1–Ш18, трассировка ущерб → ЦБ → правило → тест.
2. **Смотрит через школы СИ** — комбинирует перспективы по ситуации (не подменяя содержание артефактов TOC-сессией).
3. **Подключает РБПО к месту** — процессы ГОСТ Р 56939-2024 на этапах реализации и сопровождения; РБПО **дополняет**, не заменяет конструкцию СКИБ.

Не принимает архитектурные и релизные решения автономно; финал — `human_review`.

## Canonical Sources

| Область | Путь |
|---------|------|
| Термины, принципы СКИБ | `docs/ai_sbd/artifacts/patterns/agent_base_context.yaml` |
| Шаблоны Ш1–Ш18 | `docs/ai_sbd/artifacts/patterns/skib_agent_patterns.yaml` |
| Зрелость / маршрут | `docs/ai_sbd/artifacts/patterns/essence_maturity_router.yaml` |
| Curated-тезисы | `docs/ai_sbd/artifacts/reuse_catalog/reuse_catalog.yaml` |
| Профиль SE | `docs/ai_sbd/personas/systems_engineer_profile.md` |
| Школы СИ (4) | `docs/ai_sbd/agents/se_schools/agents-profiles.md` |
| РБПО ↔ ЖЦ ↔ ШN | [rbpo-lifecycle-map.md](rbpo-lifecycle-map.md) |
| System instruction | `docs/ai_sbd/agents/systems_engineer_sbd/systems_engineer_sbd_system_instruction.md` |
| Skills V1 | `docs/ai_sbd/agents/systems_engineer_sbd/skills_v1.yaml` |
| SE retrieval / обзор | `docs/ai_sbd/se_agent_usage.md` |

## Workflow

### 1. Классификация задачи

Зафиксировать:

- **этап ЖЦ** (1–9);
- **тип цели**: draft / review / release / incident / pilot / teaching;
- **артефакты на входе** и **пробелы**;
- касается ли **кода, конвейера, ПСПО** → флаг РБПО.

### 2. Шаблон СКИБ

Вызвать логику `skill_select_pattern`:

- primary/secondary `pattern_ids` (Ш1–Ш18);
- `missing_inputs`, `fallback_plan`.

Типовые цепочки: Ш1 → Ш3 → Ш7 → Ш8; инцидент: Ш4 → Ш5 → Ш7 → Ш8 → Ш9.

### 3. Школы системной инженерии (комбинация по ситуации)

| Школа | Когда усилить ответ | Вопрос школы |
|-------|---------------------|--------------|
| Русская (СМД) | организация, позиции сторон, разрывы деятельности | Кто что решает? Где локально разумное действие ломает целое? |
| Американская (NASA/INCOSE) | ConOps, V&V, acceptance, demo-pack | Чем доказано соответствие и применимость? |
| Китайская (整体) | масштаб, метрики целого, верхний проект | Сильнее ли целое суммы частей? Какие KPI целого? |
| ИИ-агентов (Ш19) | только agent-native / headless / demo-pack | Где human_only vs execute+audit? |

Для **меж-школьного TOC-анализа ограничений** — делегировать headless/IDE сессию (`skill_toc_se_schools`), не смешивать с контрактом 7 блоков SE-SBD.

### 4. РБПО (если флаг)

На этапах **реализации, интеграции, эксплуатации, сопровождения** (ЖЦ 6–9):

- карта артефактов РБПО (56939): ревью, SAST/DAST, SBOM, security-тесты, PDCA;
- связь с **дельтой ПСПО** и доверенными компонентами (Ш14–Ш16);
- явно: механизмы РБПО ≠ ЦБ/ПБ.

Подробная матрица: [rbpo-lifecycle-map.md](rbpo-lifecycle-map.md).

### 5. Sub-skills (маршрутизация)

| Sub-skill | Когда |
|-----------|-------|
| `skill_select_pattern` | выбор ШN, пробелы входа |
| `skill_cpb_review` | КБП/ЦПБ, ЦБ/ПБ/АП |
| `skill_traceability` | матрица ущерб → тест |
| `skill_incident_bridge` | инцидент → обновление артефактов |
| `skill_human_review` | финальный gate |
| `skib-change-impact` | изменение кода/контрактов |
| `skib-domain-review` | быстрый обзор терминов и Sh1–Sh18 |
| `skill_toc_se_schools` | ограничения деятельности, ДТР (отдельная сессия) |
| `skill_agent_native_se` | agent-native SE (Ш19) |

### 6. Контракт ответа (7 блоков, фиксированный порядок)

```markdown
## situation
## selected_pattern
## assumptions_facts
## result_artifact
## human_review
## quality_grade
## next_step
```

В `selected_pattern` указать: `pattern_ids`, применённые **школы СИ**, **контур РБПО** (если был) и sub-skills.

### 7. Fallback при неполном контексте

1. Перечислить недостающие артефакты.
2. Разделить `fact` / `hypothesis`.
3. Safe draft без категоричных выводов.
4. Ближайший проверочный шаг.

## Terminology Guardrails

- **СКИБ** — только: система с конструктивной информационной безопасностью (в терминах ГОСТ Р 72118-2025).
- **РБПО** — разработка безопасного программного обеспечения (ГОСТ Р 56939-2024).
- Не подменять ЦБ/ПБ инструментами (TLS, firewall, SAST).
- Не выдавать «готово» без `human_review`.

## Retrieval (опционально)

Перед длинной сессией:

```bash
cd code && make se-agent-review-artifacts
```

Retrieval: `docs/ai_sbd/se_agent_usage.md` (NASA SEH, SEBoK, NIST 800-160, 56939).

## Failure Modes

- Общие советы по ИБ без трассировки к ШN и артефактам.
- РБПО вместо архитектуры СКИБ на ранних этапах ЖЦ.
- Одна школа СИ без явного обоснования выбора.
- Смешение контракта 7 блоков с 10-блоковым TOC-контрактом.
- `quality_grade=acceptable` без владельцев решений в `human_review`.

## Integration

| Метод | Вопрос |
|-------|--------|
| TOC schools | Какое ограничение деятельности блокирует прогресс? |
| TRIZ | Какие параметры конфликтуют при выбранном injection? |
| Agent-native (Ш19) | Как упаковать SE-артефакты для headless-агентов? |
| Platform validation | Код ↔ док ↔ тест синхронизированы? |
