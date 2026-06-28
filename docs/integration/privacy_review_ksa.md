# Privacy review: `docs/slides/ksa/`

<!-- doc-meta: status=active version=1.0 updated=2026-06-28 -->

**Вердикт:** **BLOCK merge** каталога `docs/slides/ksa/` в открытый репозиторий без санитизации.

## Область проверки

| Путь | Тип | Риск |
|------|-----|------|
| `docs/slides/ksa/ЗУНы/resources/final_results_2026/evaluation/*.csv` | Оценки студентов | **Высокий** — персональные данные |
| `docs/slides/ksa/ЗУНы/resources/final_results_2026/*Ответы*.csv` | Ответы на формы (ФИО, email) | **Критический** |
| `docs/slides/ksa/ЗУНы/resources/participation_tracking/participation.csv` | Участие в занятиях | **Высокий** |
| `docs/slides/ksa/ЗУНы.zip` (~97 MB) | Архив nested repo | **Критический** — может содержать всё выше |
| `docs/slides/ksa/ЗУНы/.git` | Nested git | **Высокий** — история может содержать PII |
| `docs/slides/ksa/ЗУНы/.venv/` | Локальное venv | **Средний** — не должно быть в git |

## Рекомендации

1. **Не merge** в `master` / публичный remote до:
   - запуска `scripts/anonymize_personal_names.py` (есть в nested repo);
   - удаления raw CSV с ответами форм;
   - замены на агрегированные статистики без идентификаторов.
2. Добавить в `.gitignore`:
   ```
   docs/slides/ksa/ЗУНы/.venv/
   docs/slides/ksa/ЗУНы.zip
   docs/slides/ksa/**/final_results_*/
   docs/slides/ksa/**/*Ответы*.csv
   ```
3. Учебные slides без PII (72118, SBOM, TARA) — **отдельный PR-A4**, без `ksa/`.
4. Nested repo `ЗУНы` — хранить во **внутреннем** git или submodule с access control.

## human_review

- **Владелец:** методист / DPO курса
- **Статус:** выполнено оркестратором; ожидает решения владельца
