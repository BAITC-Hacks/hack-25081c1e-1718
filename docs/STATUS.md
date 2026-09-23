# Team status

After kickoff, add module/file ownership here. Each person edits only their own section.

## Dima

- Current: Интегрированы f740180/217e338 Азима. Разведка выбирает сильнейший доступный канал в15% бюджета, платное усиление проверяется попарно; seed42 PASS+685150,20 пилотов/3 кампании. Девять новых40,41,43..49:9/9 положительных, медиана+657090 против предыдущей+582083. Проверяемый атомарный экспорт опубликован678eb7b.
- Ownership: agent.py, llm_advisor.py, scripts/, manifests, общие контракты и интеграция. candidate_model.py/analysis/ и затем web/ зарезервированы Азиму согласно ARCHITECTURE.
- Next: Новый этап по запросу пользователя (>2 часов): Дима делает server.py, report_assistant.py, качество ядра и API.md. Азим независимо улучшает web/**, DESIGN, DEMO и README; candidate_model/analysis заморожены для сравнения. Контракт API и120-минутный план публикуются первыми, чтобы UI не ждал backend. Четырёхминутная синхронизация сохранена.
- Blockers: Требуется уточнение официального дедлайна/способа сдачи и расхождения guide/template по сети. Автономный режим обязателен. API-ключ не хранится в репозитории.

## Azim

- Current: Приняты 9f8d1da и ca9bac0/API. Разрабатываю рабочее место маркетолога: компактная навигация, обзор и карточки, затем запуск/API/вопросы. DESIGN обновлён; кандидатный модуль и analysis заморожены.
- Ownership: web/**, docs/DESIGN.md, docs/DEMO.md, README.md, собственные LOG/HANDOFF и этот раздел STATUS. candidate_model.py/analysis не меняются в этом этапе.
- Next: Первый checkpoint каркаса на реальном JSON, затем adapter api.mjs/integration.mjs и панель агента по API.md, затем проверки/DEMO. Диме учесть эти два JS-модуля в static allowlist. Сверять GitHub каждые4 активные минуты.
- Blockers: Mock-результат не предсказывает судейский; независимая проверка и сравнение контроллеров остаются у Димы. Изменения общего контракта не требуются.
