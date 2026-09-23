# Отчёт Tariflow — схема 1.0

`Agent.last_report` содержит результаты публичных пилотов и план. Экспортёр добавляет
seed, время, `synthetic=true`, результат evaluator, `provenance` и `validation`.
Минимальные поля: `schema_version`, `engine`, `campaigns`, `pilots`, `resources`.
Отсутствующие необязательные поля не заменяются выдуманными значениями.

- `campaigns`: точный возвращённый список кампаний.
- `pilots`: запросы и ответы; `candidate_id`, `target_tariff`, `filters`, `channel`,
  `status`, фактический `n_customers`, `requested_n`, `observed_lift_ratio`,
  необязательные `cost`, `observed_lift_total`, остатки после пилота.
- `resources`: остатки **после пилотов**, до финального плана.
- `planned_resources`: остатки после запланированных финальных кампаний.
- `allocation`: оценки, охват и расходы финальных кампаний; это прогноз.
- `evaluation.net_arpu_gain`: фактический чистый прирост из публичного evaluator.
- `events`, `advisor`, `warnings`: наблюдаемые действия, статусы и ограничения.
- `portfolio_selection`: метод выбора, число вариантов и осторожная оценка набора.
- `provenance`, `validation`: версия/хеши и результаты независимых проверок плана.

Числа конечны, JSON не содержит NaN/Infinity. Личные идентификаторы абонентов и
внутренние множества `members` в диагностические записи не экспортируются.

## Совместимый контракт report1.0

Все новые поля необязательны. Старый JSON показывает «нет данных» для отсутствующих
диагностик. HTTP/CSV/Agent.act сохраняются. UI не пересчитывает экономику.

### selection_diagnostics

Числа: generated_candidates, tested_candidates (уникальные candidate_id с завершённым
пилотом), tested_variants (candidate_id+channel), confirmed_variants (два завершённых
пилота), selected_variants, unexplored_candidates. Подтверждение само по себе не
означает положительный эффект. reason_counts — количества по причинам ниже.

variants — до20 исследованных вариантов. Каждая запись:
candidate_id, channel, repeats, conservative_net, selected (boolean), reason,
pilot_refs (например pilots.16; UI это пилот17). Нет customerIDs/members.

Причины: selected, mandatory_fallback, insufficient_pilots, nonpositive_estimate,
overlap, budget, contacts, not_selected. Приоритет объяснения отклонения:
недостаточно пилотов → неположительная оценка → пересечение → бюджет → контакты
→ другая причина выбора. Фактический выбранный вариант/mandatory fallback помечаются
перед этими проверками. Отсутствие источников не заменять придуманными пилотами.

### Диагностика allocation

Существующие поля сохраняются. Добавляются template_uncertainty, sample_std,
empirical_se (доли, не проценты), uncertainty_method:
template_floor или max_template_empirical. repeats и n_customers уже существуют;
n_customers — сумма размеров пилотов, не гарантированное число уникальных абонентов.
Отображать «эвристический запас неопределённости», не доверительный интервал.

### forecast_summary и evaluation

forecast_summary: scope="final_campaigns_only", estimated_net, conservative_net,
communication_cost, campaign_count, comparison_to_evaluation="not_comparable".
Это суммы оценок **только финальных кампаний**, без добавления эффектов пилотов.
evaluation.scope="pilots_and_final_deduplicated" — фактический итог всей симуляции.
Разницу этих величин не показывать как ошибку прогноза. Общая подпись метрики:
«Прирост выручки за вычетом расходов на коммуникации».

Новые допустимые ссылки Q&A: selection_diagnostics («Исследование») и
forecast_summary («Прогноз плана»). Клиент связывает их с соответствующими блоками;
пока поле отсутствует, ссылка не создаётся. Прежние refs сохраняются.

strategy_config: exploration_policy=baseline|balanced|confirmation_first,
uncertainty_mode=template|empirical, pilot_sizing=fixed|adaptive.
Обычный режим — baseline/template/fixed; это технические сведения.


Протокол снимков и вопросов — [API](API.md). Примеры числовых результатов —
[VALIDATION](VALIDATION.md).
