# Team status

After kickoff, add module/file ownership here. Each person edits only their own section.

## Dima

- Current: Интегрирован модуль кандидатов Азима f740180 без конфликта. Seed42 PASS +475595, 16 пилотов/3 кампании; CSV обновлён. Новая серия20..29: 10/10 положительных, медиана+469900. SMS-контроллер e7c9f6f на тех же данных лучше: +603277, также10/10. Следующий приоритет — подтверждённый выбор выгодного канала.
- Ownership: agent.py, llm_advisor.py, scripts/, manifests, общие контракты и интеграция. candidate_model.py/analysis/ и затем web/ зарезервированы Азиму согласно ARCHITECTURE.
- Next: Проверять платный канал отдельными пилотами после дешёвой разведки; сравнить с SMS-контроллером на одинаковых данных. Проверять входящие изменения и делать checkpoint примерно каждые4 активные минуты. UI остаётся у Азима.
- Blockers: Требуется уточнение официального дедлайна/способа сдачи и расхождения guide/template по сети. Автономный режим обязателен. API-ключ не хранится в репозитории.

## Azim

- Current: candidate_model.py готов: 299 кандидатов, 160 сегментов, осторожные priors; 7/7 тестов. Интегрирован e7c9f6f Димы: offline seed42 PASS, net +599050, 16 пилотов/3 SMS-кампании, без warnings. Первый data checkpoint.
- Ownership: candidate_model.py, analysis/; затем web/ и README.md. Только свои LOG/HANDOFF и этот раздел STATUS.
- Next: Push data checkpoint; затем после pull web/ по DESIGN и README. Main/handoff сверять примерно каждые 5 минут; Диме пересоздать submission.csv после интеграции.
- Blockers: Mock-результат не предсказывает судейский; независимая проверка и сравнение контроллеров остаются у Димы. Изменения общего контракта не требуются.
