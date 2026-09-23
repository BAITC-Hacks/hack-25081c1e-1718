# Team status

After kickoff, add module/file ownership here. Each person edits only their own section.

## Dima

- Current: Разведка выбирает самый дешёвый доступный канал. Seed42: PASS +41 157, 16 пилотов/2 кампании, расходы 0. Seed0..9: медиана +16 068, 7/10 положительных; отложенные10..19: +1 170, 5/10. Устойчивость ещё недостаточна. Усилены release/benchmark; синхронизация теперь примерно каждые4 активные минуты.
- Ownership: agent.py, llm_advisor.py, scripts/, manifests, общие контракты и интеграция. candidate_model.py/analysis/ и затем web/ зарезервированы Азиму согласно ARCHITECTURE.
- Next: Независимо улучшать цену/остановку разведки и распределение; сравнить на отложенных seed; поддерживать готовый контракт интеграции candidate_model.py. Работа не ожидает коммитов Азима.
- Blockers: Требуется уточнение официального дедлайна/способа сдачи и расхождения guide/template по сети. Автономный режим обязателен. API-ключ не хранится в репозитории.

## Azim

- Current: candidate_model.py готов: 299 кандидатов, 160 сегментов, осторожные priors; 7/7 тестов. Интегрирован e7c9f6f Димы: offline seed42 PASS, net +599050, 16 пилотов/3 SMS-кампании, без warnings. Первый data checkpoint.
- Ownership: candidate_model.py, analysis/; затем web/ и README.md. Только свои LOG/HANDOFF и этот раздел STATUS.
- Next: Push data checkpoint; затем после pull web/ по DESIGN и README. Main/handoff сверять примерно каждые 5 минут; Диме пересоздать submission.csv после интеграции.
- Blockers: Mock-результат не предсказывает судейский; независимая проверка и сравнение контроллеров остаются у Димы. Изменения общего контракта не требуются.
