# Team status

After kickoff, add module/file ownership here. Each person edits only their own section.

## Dima

- Current: Эксперимент b0975ab и freeze e8353df проверены на dev 0–9 и holdout 100–119; gate не пройден, Agent() сохраняет baseline/template. Отдельно OpenAI выиграл 3/3 пары 120–122 при ровно шести обращениях советника. Отчёты и источники числовых ответов улучшены. По запросу из задачи Азима добавляется ru/kk для чата.
- Ownership: agent.py, llm_advisor.py, server.py, report_assistant.py, scripts/ и общие контракты. Азим — web/DESIGN/DEMO/README; candidate_model.py/analysis и данные остаются замороженными.
- Next: Двуязычный UI db56214 принят: 33 Node-теста и обзор 375/768/1440 PASS. Исправлены вопросы о рисках/пилотах и термины из QUESTIONS 16:38; текущих quality/API-тестов 59. Чистый standalone/CSV и официальный --runs10 подтверждены. Аудит в JUDGING_AUDIT.md; Азиму остаются диагностические блоки QUALITY_STAGE и актуальные README/DEMO.
- Blockers: Своих нет. Все 5 must-have проверены; 100 баллов обещать нельзя. Рост от нового алгоритма не подтверждён, baseline сохранён. Двуязычие опубликовано; диагностический UI и обновление результатов README/DEMO ещё нужны. Способ и факт финальной загрузки организаторам не подтверждены.

## Azim

- Current: Опубликован db56214: по прямому запросу пользователя готов RU/KK Tariflow: переключатель, полный UI, тарифы/сегменты/ошибки и интеграция согласованного языка чата. Принят backend161473c.33 Node, 6 сценариев чата, 4 проверки крайних состояний, 375/768/1440 и реальныйKKofflineответ с собственнымиpilots17/18 PASS.
- Ownership: web/**, docs/DESIGN.md, docs/DEMO.md, README.md, собственные LOG/HANDOFF и этот раздел STATUS. candidate_model.py/analysis и данные заморожены.
- Next: Диме исправить конкретные KK routing/терминологию поQUESTIONS16:38; Азиму проверить интеграцию. Затем отдельный QUALITY_STAGE UI по согласованным полям. Сверка GitHub каждые4активные минуты.
- Blockers: UI готов; перед полным закрытием двуязычного сценария ждём исправления вопросов о рисках/сынақ/байланысу в зонеДимы. Финальныйrelease остаётся уДимы. Экономическийgate не пройден, baseline сохраняется.
