# Team status

After kickoff, add module/file ownership here. Each person edits only their own section.

## Dima

- Current: Принят UI Азима 1775bc5. Реализованы server.py и report_assistant.py: запуск расчёта, неизменяемый проверенный снимок и ответы OpenAI со ссылками. Реальные offline/online сценарии прошли; online advisor completed в обеих фазах, чат mode=openai. Ключ только в процессе. Основной автономный алгоритм пока 92872b5.
- Ownership: agent.py, llm_advisor.py, server.py, report_assistant.py, scripts/, manifests, API.md и общая интеграция. Азим: web/**, DESIGN/DEMO/README; candidate_model.py/analysis/ заморожены на время сравнения ядра.
- Next: Опубликовать backend; сравнить улучшение финального выбора кампаний; принять API-интерфейс Азима и проверить общий сценарий. Примерно каждые 4 активные минуты fetch и законченный проверенный checkpoint.
- Blockers: Формат/дедлайн сдачи и расхождение guide/template по сети ещё уточняются. UI-интеграция выполняется Азимом; backend её больше не блокирует. Mock net не является прогнозом реальной прибыли.

## Azim

- Current: Новый каркас1775bc5 опубликован: обзор, рекомендации/details, клавиатура/контраст/375–1440 проверены. API/panel готовы по ca9bac0:13/13 unit и9/9 браузерных сценариев на фикстурах; реальный backend проверим после публикации. Кандидаты/analysis заморожены.
- Ownership: web/**, docs/DESIGN.md, docs/DEMO.md, README.md, собственные LOG/HANDOFF и этот раздел STATUS. candidate_model.py/analysis не меняются в этом этапе.
- Next: Полировка/README/DEMO, интеграция реального сервера. Диме разрешить api.mjs/integration.mjs в static allowlist; контракт принят без изменений. Сверка GitHub каждые4 активные минуты.
- Blockers: Mock-результат не предсказывает судейский; независимая проверка и сравнение контроллеров остаются у Димы. Изменения общего контракта не требуются.
