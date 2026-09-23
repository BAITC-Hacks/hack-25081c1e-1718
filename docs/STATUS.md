# Team status

After kickoff, add module/file ownership here. Each person edits only their own section.

## Dima

- Current: Эксперимент b0975ab и freeze e8353df проверены на dev 0–9 и holdout 100–119; gate не пройден, Agent() сохраняет baseline/template. Отдельно OpenAI выиграл 3/3 пары 120–122 при ровно шести обращениях советника. Отчёты и источники числовых ответов улучшены. По запросу из задачи Азима добавляется ru/kk для чата.
- Ownership: agent.py, llm_advisor.py, server.py, report_assistant.py, scripts/ и общие контракты. Азим — web/DESIGN/DEMO/README; candidate_model.py/analysis и данные остаются замороженными.
- Next: Проверить реальные ru/kk комментарии модели на опубликованном коде; интегрировать диагностику и язык Азима; пересобрать финальный CSV/standalone и пакет. Чистая поставка 33a7152 и регрессия baseline 0–9 уже подтверждены.
- Blockers: Нет. Рост экономики не подтверждён, экспериментальные режимы по умолчанию не включаются. Послеholdout параметры не подбираем. Новые поля отчёта/источники/единицы готовы.

## Azim

- Current: Tariflow UI9d748c7 принят Димой; favicon38c673a и очистка навигацииd8931c3 опубликованы. По запросу пользователя удалена подсказка Enter/Shift+Enter, счётчик сохранён справа; браузер375/768/1440 и ARIA проверены. Подтянут e8353df; backend, кандидаты и данные в этой правке не менялись.
- Ownership: web/**, docs/DESIGN.md, docs/DEMO.md, README.md, собственные LOG/HANDOFF и этот раздел STATUS. candidate_model.py/analysis не меняются в этом этапе.
- Next: Правка подписей публикуется отдельным законченным checkpoint. Далее согласованный этап диагностики качества по docs/QUALITY_STAGE.md в своей зоне, отдельный от этой правки. Сверка GitHub каждые4активные минуты.
- Blockers: В зоне Азима нет. Чистыйrelease и независимая проверка остаются у Димы; UIQA не является обещанием реальной прибыли или судейского результата.
