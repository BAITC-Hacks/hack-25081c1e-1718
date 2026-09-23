# Team status

After kickoff, add module/file ownership here. Each person edits only their own section.

## Dima

- Current: Принят UI Азима 1775bc5. Реализованы server.py и report_assistant.py: запуск расчёта, неизменяемый проверенный снимок и ответы OpenAI со ссылками. Реальные offline/online сценарии прошли; online advisor completed в обеих фазах, чат mode=openai. Ключ только в процессе. Основной автономный алгоритм пока 92872b5.
- Ownership: agent.py, llm_advisor.py, server.py, report_assistant.py, scripts/, manifests, API.md и общая интеграция. Азим: web/**, DESIGN/DEMO/README; candidate_model.py/analysis/ заморожены на время сравнения ядра.
- Next: Опубликовать backend; сравнить улучшение финального выбора кампаний; принять API-интерфейс Азима и проверить общий сценарий. Примерно каждые 4 активные минуты fetch и законченный проверенный checkpoint.
- Blockers: Формат/дедлайн сдачи и расхождение guide/template по сети ещё уточняются. UI-интеграция выполняется Азимом; backend её больше не блокирует. Mock net не является прогнозом реальной прибыли.

## Azim

- Current: Каркас1775bc5 и API2625ecc опубликованы, финальная полировка/README/DEMO готовы. Принят a10dc23: реальный путь run→report→chat→источники прошёл, net+685150/20пилотов/3кампании.21/21 unit,9/9 fixture-сценариев, контраст/клавиатура/снимки375–1440 проверены. Кандидаты/analysis заморожены.
- Ownership: web/**, docs/DESIGN.md, docs/DEMO.md, README.md, собственные LOG/HANDOFF и этот раздел STATUS. candidate_model.py/analysis не меняются в этом этапе.
- Next: Диме принять финальный UI checkpoint и проверить online-путь на своей конфигурации; core/CSV/release остаются у Димы. Таймаут30сек из QUESTIONS выполнен. Сверка GitHub каждые4 активные минуты до командной интеграции.
- Blockers: Mock-результат не предсказывает судейский; независимая проверка и сравнение контроллеров остаются у Димы. Изменения общего контракта не требуются.
