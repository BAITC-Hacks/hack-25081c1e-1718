# Team status

After kickoff, add module/file ownership here. Each person edits only their own section.

## Dima

- Current: b0975ab реализовал три экспериментальных варианта и новые отчёты; e8353df зафиксировал empirical доholdout. Dev0–9 и независимая100–119 завершены, gate не пройден: ordinary Agent() сохраняет baseline/template. Результаты/хеши в QUALITY_RESULTS.md.
- Ownership: agent.py, llm_advisor.py, server.py, report_assistant.py, scripts/ и общие контракты. Азим — web/DESIGN/DEMO/README; candidate_model.py/analysis и данные остаются замороженными.
- Next: Три отдельные online/offlineпары120–122 (максимум6советов), регрессияbaseline, CSV/standalone/пакет и интеграция диагностикиАзима.
- Blockers: Нет. Рост экономики не подтверждён, экспериментальные режимы по умолчанию не включаются. Послеholdout параметры не подбираем. Новые поля отчёта/источники/единицы готовы.

## Azim

- Current: Tariflow UI9d748c7 принят Димой; favicon38c673a и очистка навигацииd8931c3 опубликованы. По запросу пользователя удалена подсказка Enter/Shift+Enter, счётчик сохранён справа; браузер375/768/1440 и ARIA проверены. Подтянут e8353df; backend, кандидаты и данные в этой правке не менялись.
- Ownership: web/**, docs/DESIGN.md, docs/DEMO.md, README.md, собственные LOG/HANDOFF и этот раздел STATUS. candidate_model.py/analysis не меняются в этом этапе.
- Next: Правка подписей публикуется отдельным законченным checkpoint. Далее согласованный этап диагностики качества по docs/QUALITY_STAGE.md в своей зоне, отдельный от этой правки. Сверка GitHub каждые4активные минуты.
- Blockers: В зоне Азима нет. Чистыйrelease и независимая проверка остаются у Димы; UIQA не является обещанием реальной прибыли или судейского результата.
