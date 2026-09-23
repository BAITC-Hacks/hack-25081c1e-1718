# Team status

After kickoff, add module/file ownership here. Each person edits only their own section.

## Dima

- Current: Начат утверждённый 90-минутный этап качества (15:56 UTC+5). Принят Tariflow UI9d748c7. Полный baseline4473540; новые поля описаны в QUALITY_STAGE.md.
- Ownership: agent.py, llm_advisor.py, server.py, report_assistant.py, scripts/, manifests и общие контракты. Workers имеют исключительные agent.py+test_quality_policy и quality_benchmark+test_quality_benchmark. Азим — web/DESIGN/DEMO/README; candidate_model.py/analysis и данные заморожены.
- Next: Три варианта на dev0–9 → фиксация одного → независимые100–119 → только принятие по gate. Азим параллельно отображает диагностику, причины исключения и разные области прогноза/факта. Потом online120–122 и выпуск.
- Blockers: Нет. Новая политика пока не является production-default. При провале gate сохраняем baseline и выпускаем улучшения отчёта. Официальную загрузку выполняет команда.

## Azim

- Current: По выбору пользователя готов Tariflow: SVG-знак F, mobile5разделов, читаемые KPI, исходные номера кампаний, вопрос из карточки и загрузка последнего снимка.23/23Node,6chatregressions,новыеUX/raceпроверки,контраст5разделов,375/768/1440 и реальныйoffline run→campaign1→pilots17/18 прошли. Приняты e978571/a55d02b/4473540 Димы; core6550806 и кандидаты заморожены.
- Ownership: web/**, docs/DESIGN.md, docs/DEMO.md, README.md, собственные LOG/HANDOFF и этот раздел STATUS. candidate_model.py/analysis не меняются в этом этапе.
- Next: Диме принять Tariflow UI (git log -1 -- web/index.html), завершить release/общую интеграцию. Новых HTTPпутей/контрактов нет, machineIDs прежние. Сверка GitHub каждые4активные минуты.
- Blockers: В зоне Азима нет. Чистыйrelease и независимая проверка остаются у Димы; UIQA не является обещанием реальной прибыли или судейского результата.
