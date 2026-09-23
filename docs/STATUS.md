# Team status

After kickoff, add module/file ownership here. Each person edits only their own section.

## Dima

- Current: Интегрированы f740180/217e338 Азима. Разведка выбирает сильнейший доступный канал в15% бюджета, платное усиление проверяется попарно; seed42 PASS+685150,20 пилотов/3 кампании. Девять новых40,41,43..49:9/9 положительных, медиана+657090 против предыдущей+582083. Проверяемый атомарный экспорт опубликован678eb7b.
- Ownership: agent.py, llm_advisor.py, scripts/, manifests, общие контракты и интеграция. candidate_model.py/analysis/ и затем web/ зарезервированы Азиму согласно ARCHITECTURE.
- Next: Собрать standalone agent.py со всеми модулями для официального формата сдачи, проверить изолированный запуск и CSV. Сверкаmain и checkpoint примерно каждые4 активные минуты. UI/candidate_model остаются у Азима; контракт1.0 сохранён.
- Blockers: Требуется уточнение официального дедлайна/способа сдачи и расхождения guide/template по сети. Автономный режим обязателен. API-ключ не хранится в репозитории.

## Azim

- Current: Data f740180 опубликован (7/7 тестов, 299 кандидатов/160 сегментов). Web/README готовы: импорт реального JSON, ресурсы двух этапов, пилоты/кампании/CSV; 8/8 тестов и Chromium375/768/1440. Подтянут678eb7b: seed42 net+644555,20 пилотов/3 кампании, warnings=[], validation.valid=true. Новый provenance/validation совместим; UI checkpoint.
- Ownership: candidate_model.py, analysis/; затем web/ и README.md. Только свои LOG/HANDOFF и этот раздел STATUS.
- Next: Диме подтянуть UI checkpoint и проверить совместный запуск по README; final release/CSV и выбор стратегии ведёт Дима. Сверять main/handoff примерно каждые4 активные минуты во время активной совместной работы.
- Blockers: Mock-результат не предсказывает судейский; независимая проверка и сравнение контроллеров остаются у Димы. Изменения общего контракта не требуются.
