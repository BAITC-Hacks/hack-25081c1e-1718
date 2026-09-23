// The report is data, never markup. Keep parsing independent from the DOM.
export const MISSING = "нет данных";
export const MAX_FILE_BYTES = 10 * 1024 * 1024;
export const CAMPAIGN_COLUMNS = Object.freeze([
  "campaign_name", "filter_current_tariff", "filter_arpu_segment",
  "filter_data_segment", "filter_call_segment", "target_tariff", "channel",
]);
export const FILTER_LABELS = Object.freeze({
  filter_current_tariff: "Текущий тариф",
  filter_arpu_segment: "ARPU",
  filter_data_segment: "Интернет",
  filter_call_segment: "Звонки",
});

const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
export const isNumber = (value) => typeof value === "number" && Number.isFinite(value);
const absent = (value) => value === undefined || value === null;

function fail(path, expected) {
  throw new Error(`Поле «${path}»: ${expected}. Выберите корректный отчёт версии 1.0.`);
}

function optionalString(value, path) {
  if (!absent(value) && typeof value !== "string") fail(path, "ожидается строка");
}

function numericFields(value, keys, path) {
  for (const key of keys) {
    if (!absent(value[key]) && !isNumber(value[key])) fail(`${path}.${key}`, "ожидается конечное число или null");
  }
}

function arrayOfObjects(value, path, required = false) {
  if (absent(value) && !required) return [];
  if (!Array.isArray(value)) fail(path, "ожидается массив");
  if (value.length > 10000) fail(path, "массив превышает 10 000 записей");
  value.forEach((item, i) => { if (!object(item)) fail(`${path}[${i}]`, "ожидается объект"); });
  return value;
}

export function validateReport(report) {
  if (!object(report)) throw new Error("Отчёт должен быть JSON-объектом. Выберите report.json, созданный агентом.");
  if (report.schema_version !== "1.0") {
    throw new Error("Версия отчёта не поддерживается. Ожидается schema_version: «1.0».");
  }
  if (typeof report.engine !== "string" || !report.engine.trim()) fail("engine", "ожидается непустая строка");
  const campaigns = arrayOfObjects(report.campaigns, "campaigns", true);
  campaigns.forEach((campaign, i) => {
    for (const key of ["target_tariff", "channel"]) {
      if (typeof campaign[key] !== "string" || !campaign[key].trim()) fail(`campaigns[${i}].${key}`, "ожидается непустая строка");
    }
    for (const key of [...CAMPAIGN_COLUMNS, "candidate_id", "rationale"]) optionalString(campaign[key], `campaigns[${i}].${key}`);
  });
  const pilots = arrayOfObjects(report.pilots, "pilots", true);
  pilots.forEach((pilot, i) => {
    for (const key of ["candidate_id", "target_tariff", "channel", "status", "rationale"]) optionalString(pilot[key], `pilots[${i}].${key}`);
    numericFields(pilot, ["requested_n", "n_customers", "cost", "observed_lift_ratio", "observed_lift_total", "remaining_budget", "remaining_contacts"], `pilots[${i}]`);
    if (!absent(pilot.filters)) {
      if (!object(pilot.filters)) fail(`pilots[${i}].filters`, "ожидается объект");
      for (const key of Object.keys(FILTER_LABELS)) optionalString(pilot.filters[key], `pilots[${i}].filters.${key}`);
    }
  });
  if (!object(report.resources)) fail("resources", "ожидается объект с остатками ресурсов");
  numericFields(report.resources, ["remaining_budget", "remaining_contacts", "pilots_left"], "resources");
  if (!absent(report.planned_resources)) {
    if (!object(report.planned_resources)) fail("planned_resources", "ожидается объект");
    numericFields(report.planned_resources, ["remaining_budget", "remaining_contacts", "pilots_left"], "planned_resources");
  }
  if (!absent(report.evaluation)) {
    if (!object(report.evaluation)) fail("evaluation", "ожидается объект");
    numericFields(report.evaluation, ["net_arpu_gain", "n_pilots", "n_campaigns_including_pilots"], "evaluation");
    optionalString(report.evaluation.status, "evaluation.status");
  }
  arrayOfObjects(report.allocation, "allocation").forEach((allocation, i) => {
    for (const key of ["candidate_id", "campaign_name", "channel", "rationale"]) optionalString(allocation[key], `allocation[${i}].${key}`);
    numericFields(allocation, ["audience_size", "communication_cost", "posterior_mean", "uncertainty", "n_customers", "estimated_net", "conservative_net", "repeats"], `allocation[${i}]`);
  });
  for (const key of ["events", "advisor"]) {
    arrayOfObjects(report[key], key).forEach((entry, i) => {
      for (const field of ["role", "phase", "status", "reason", "summary", "action", "model"]) optionalString(entry[field], `${key}[${i}].${field}`);
    });
  }
  if (!absent(report.warnings)) {
    if (!Array.isArray(report.warnings) || !report.warnings.every((warning) => typeof warning === "string")) fail("warnings", "ожидается массив строк");
    if (report.warnings.length > 1000) fail("warnings", "массив превышает 1 000 предупреждений");
  }
  for (const key of ["generated_at", "uncertainty_note", "candidate_source", "resource_stage"]) optionalString(report[key], key);
  numericFields(report, ["seed", "candidate_count", "elapsed_seconds"], "report");
  if (!absent(report.synthetic) && typeof report.synthetic !== "boolean") fail("synthetic", "ожидается true или false");
  return report;
}

export function parseReport(text) {
  let report;
  try {
    report = JSON.parse(text.replace(/^\uFEFF/, ""));
  } catch {
    throw new Error("Не удалось прочитать JSON. Проверьте формат файла и выберите report.json ещё раз.");
  }
  return validateReport(report);
}

export function number(value, digits = 0) {
  return isNumber(value) ? value.toLocaleString("ru-RU", { maximumFractionDigits: digits }) : MISSING;
}

export function money(value) {
  return isNumber(value) ? `${number(value, 0)} у. е.` : MISSING;
}

export function ratio(value) {
  return isNumber(value)
    ? value.toLocaleString("ru-RU", { style: "percent", maximumFractionDigits: 2, signDisplay: "exceptZero" })
    : MISSING;
}

export function displayText(value) {
  return typeof value === "string" && value.trim() ? value : MISSING;
}

export function findAllocation(campaign, allocation = []) {
  // Never assume that two independent arrays have matching positions.
  const identity = (row) => {
    const explicit = typeof row.candidate_id === "string" && row.candidate_id ? row.candidate_id : null;
    const derived = typeof row.campaign_name === "string" && row.campaign_name.startsWith("compass_")
      ? row.campaign_name.slice("compass_".length) || null : null;
    return { id: explicit || derived, conflict: !!(explicit && derived && explicit !== derived) };
  };
  const campaignIdentity = identity(campaign);
  if (campaignIdentity.conflict) return null;
  const matches = allocation.filter((row) => {
    if (row.channel !== campaign.channel) return false;
    const rowIdentity = identity(row);
    if (rowIdentity.conflict) return false;
    if (campaignIdentity.id || rowIdentity.id) {
      return !!campaignIdentity.id && campaignIdentity.id === rowIdentity.id;
    }
    return typeof row.campaign_name === "string" && !!row.campaign_name && row.campaign_name === campaign.campaign_name;
  });
  return matches.length === 1 ? matches[0] : null;
}

export function campaignMatches(campaign, query, channel) {
  if (channel && campaign.channel !== channel) return false;
  const text = CAMPAIGN_COLUMNS.map((key) => campaign[key] ?? "").join(" ").toLocaleLowerCase("ru-RU");
  return text.includes(query.trim().toLocaleLowerCase("ru-RU"));
}

function csvCell(value) {
  let text = typeof value === "string" ? value : "";
  // Quoting alone does not stop spreadsheet formulas. Neutralize control prefixes too.
  if (/^[\s\u0000-\u001f]*[=+\-@]/u.test(text) || /^[\t\r\n]/u.test(text)) text = `'${text}`;
  return `"${text.replace(/"/g, '""')}"`;
}

export function campaignsToCsv(campaigns) {
  return "\uFEFF" + [
    CAMPAIGN_COLUMNS.map(csvCell).join(","),
    ...campaigns.map((campaign) => CAMPAIGN_COLUMNS.map((key) => csvCell(campaign[key])).join(",")),
  ].join("\r\n") + "\r\n";
}

const TRANSLATIONS = Object.freeze({
  completed: "Завершён", failed: "Ошибка", skipped: "Пропущен", fallback: "Резервная стратегия",
  PASS: "Проверка пройдена", FAIL: "Проверка не пройдена",
  offline_mode: "Автономный режим", no_api_key: "Ключ API не задан", missing_api_key: "Ключ API не задан",
  http_error: "Ошибка ответа API", timeout: "Истекло время ожидания", network_error: "Ошибка сети",
  request_error: "Ошибка запроса к API", call_limit: "Достигнут лимит вызовов советника",
  invalid_inputs: "Некорректные входные данные советника", no_candidates: "Нет кандидатов для советника",
  invalid_model_output: "Ответ модели не соответствует допустимому выбору кандидатов",
  invalid_response: "Некорректный ответ API", invalid_json: "Некорректный JSON ответа",
  initial: "Выбор гипотез", feedback: "Пересмотр после пилотов",
  historical_prior_unavailable: "Исторический приор недоступен.",
  candidate_model_dependency_missing: "Недоступна зависимость модуля кандидатов; использована резервная генерация.",
  candidate_model_failed: "Модуль кандидатов завершился с ошибкой; использована резервная генерация.",
  candidate_model_no_valid_candidates: "Модуль не вернул допустимых кандидатов; использована резервная генерация.",
  no_supported_channels: "Нет поддерживаемого канала для кампаний.",
  no_positive_conservative_plan_fallback: "Нет положительного плана по осторожной оценке. Выбрана резервная кампания; положительный эффект не гарантирован.",
  unobserved_fallback: "Резервная кампания не подтверждена наблюдением пилота.",
  "Approximate planning margin from public template; not a calibrated confidence interval.": "Неопределённость — приблизительный запас для планирования по публичному шаблону. Это не калиброванный доверительный интервал.",
});

export function translate(value) {
  if (typeof value !== "string" || !value.trim()) return MISSING;
  if (Object.hasOwn(TRANSLATIONS, value)) return TRANSLATIONS[value];
  if (value.startsWith("pilot_failed_")) return `Пилот завершился с ошибкой: ${value.slice("pilot_failed_".length)}.`;
  return value;
}

export function channelLabel(value) {
  const labels = { sms: "SMS", push: "Push", call: "Звонок" };
  return Object.hasOwn(labels, value) ? labels[value] : displayText(value);
}
