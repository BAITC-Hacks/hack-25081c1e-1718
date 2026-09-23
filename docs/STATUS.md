# Team status

After kickoff, add module/file ownership here. Each person edits only their own section.

## Dima

- Current: Принят финальный UI dadb2d3. Backend99d5303/a10dc23 проверен в настоящем браузере с OpenAI. Добавлен bounded exact portfolio и проверка подтверждений/пересечений; dev0..9/new50..59 совпали с92872b5 без нарушений. Три новых online/offline пары60..62: все планы валидны, OpenAI выше в3/3; это малая исследовательская выборка.
- Ownership: agent.py, llm_advisor.py, server.py, report_assistant.py, scripts/, manifests, API.md и общая интеграция. Азим: web/**, DESIGN/DEMO/README; candidate_model.py/analysis/ заморожены для проверки.
- Next: Release-генерация CSV, checkpoint, чистый checkout и standalone без helper-файлов, окончательный общий аудит. UI готов; Азиму переданы только неблокирующие уточнения карточек. Примерно каждые4 активные минуты Git-синхронизация.
- Blockers: Нет блокера реализации. Формат/дедлайн официальной загрузки ещё не подтверждены; пакет готовим локально, самостоятельно не отправляем. Mock net не является прогнозом реальной прибыли.

## Azim

- Current: После дизайна b1d4fbe выполнено уточнение пользователя: пакеты/месячные цены вместо tariff_N, понятные сегменты и объяснение денежных единиц. 23/23 Node, CSV/поиск/неизвестные и несколько тарифов, контраст пяти разделов, 375/768/1440 прошли. Принят core6550806; кандидаты/analysis заморожены.
- Ownership: web/**, docs/DESIGN.md, docs/DEMO.md, README.md, собственные LOG/HANDOFF и этот раздел STATUS. candidate_model.py/analysis не меняются в этом этапе.
- Next: Диме принять уточнение тарифов (git log -1 -- web/report.mjs); каталог только для отображения, HTTP/CSV контракт прежний. Завершить совместную интеграцию/release; core/CSV остаются у Димы. Сверка GitHub каждые4 активные минуты.
- Blockers: Mock-результат не предсказывает судейский; независимая проверка и сравнение контроллеров остаются у Димы. Изменения общего контракта не требуются.
