import {t, registerMessages, getLanguage, getLocale, onLanguageChange, localizedError} from "./i18n.mjs";

registerMessages({
  "нет данных": "дерек жоқ",
  "Текущий тариф": "Қазіргі тариф",
  "Доход с абонента": "Абоненттен түсетін кіріс",
  "Интернет": "Интернет",
  "Звонки": "Қоңыраулар",
  "ожидается строка": "жол болуы керек",
  "ожидается конечное число или null": "шекті сан немесе null болуы керек",
  "ожидается целое неотрицательное число или null": "теріс емес бүтін сан немесе null болуы керек",
  "ожидается массив": "массив болуы керек",
  "массив превышает 10 000 записей": "массивте 10 000-нан астам жазба бар",
  "ожидается объект": "нысан болуы керек",
  "ожидается непустая строка": "бос емес жол болуы керек",
  "ожидается объект с остатками ресурсов": "қалған ресурстары бар нысан болуы керек",
  "ожидается массив строк": "жолдар массиві болуы керек",
  "массив превышает 1 000 предупреждений": "массивте 1 000-нан астам ескерту бар",
  "не более 20 записей диагностики": "диагностикада 20-дан көп жазба болмауы керек",
  "не более 64 причин": "64-тен көп себеп болмауы керек",
  "ожидается true или false": "true немесе false болуы керек",
  "Поле «{path}»: {expected}. Выберите корректный отчёт версии 1.0.": "«{path}» өрісі: {expected}. 1.0 нұсқасындағы дұрыс есепті таңдаңыз.",
  "Отчёт должен быть JSON-объектом. Выберите report.json, созданный агентом.": "Есеп JSON нысаны болуы керек. Агент жасаған report.json файлын таңдаңыз.",
  "Версия отчёта не поддерживается. Ожидается schema_version: «1.0».": "Есептің бұл нұсқасына қолдау көрсетілмейді. schema_version мәні «1.0» болуы керек.",
  "Не удалось прочитать JSON. Проверьте формат файла и выберите report.json ещё раз.": "JSON файлын оқу мүмкін болмады. Файл пішімін тексеріп, report.json файлын қайта таңдаңыз.",
  "{value} ден. ед.": "{value} ақша бірл.",
  "Неизвестный тариф: {code}": "Белгісіз тариф: {code}",
  "Параметры не указаны": "Параметрлері көрсетілмеген",
  "В справочнике нет этого кода.": "Анықтамалықта бұл код жоқ.",
  "Тариф №{n}": "№{n} тариф",
  "{n} ГБ": "{n} ГБ",
  "Без пакета интернета": "Интернет пакеті жоқ",
  "{n} мин": "{n} мин",
  "{n} мин, включая городские": "{n} мин, қалалық нөмірлерді қоса",
  "без пакета минут": "минуттар пакеті жоқ",
  "{n} минут на других операторов": "Басқа операторларға {n} минут",
  "{n} минут на других операторов и городские номера (общий пакет)": "Басқа операторларға және қалалық нөмірлерге {n} минут (ортақ пакет)",
  "{price}/мес.": "{price}/ай",
  "Без абонентской платы": "Абоненттік төлемсіз",
  "{n} МБ интернета": "{n} МБ интернет",
  "Интернет не включён в пакет": "Интернет пакетке кірмейді",
  "Минуты не включены в пакет": "Минуттар пакетке кірмейді",
  "или": "немесе",
  "Любой текущий тариф": "Кез келген қазіргі тариф",
  "Низкий доход с абонента": "Абоненттен түсетін кіріс: төмен",
  "Средний доход с абонента": "Абоненттен түсетін кіріс: орташа",
  "Высокий доход с абонента": "Абоненттен түсетін кіріс: жоғары",
  "Средний месячный доход с абонента за 3 месяца: меньше 1 000 денежных единиц.": "Соңғы 3 айдағы бір абоненттен түсетін орташа айлық кіріс: 1 000 ақша бірлігінен аз.",
  "Средний месячный доход с абонента за 3 месяца: от 1 000 до 5 000 денежных единиц.": "Соңғы 3 айдағы бір абоненттен түсетін орташа айлық кіріс: 1 000–5 000 ақша бірлігі.",
  "Средний месячный доход с абонента за 3 месяца: больше 5 000 денежных единиц.": "Соңғы 3 айдағы бір абоненттен түсетін орташа айлық кіріс: 5 000 ақша бірлігінен көп.",
  "Не пользуются интернетом": "Интернетті пайдаланбайды",
  "Мало пользуются интернетом": "Интернетті аз пайдаланады",
  "Активно пользуются интернетом": "Интернетті белсенді пайдаланады",
  "0 МБ в месяц.": "Айына 0 МБ.",
  "Больше 0, до 2 000 МБ в месяц.": "Айына 0 МБ-тан көп, 2 000 МБ-қа дейін.",
  "Больше 2 000 МБ в месяц.": "Айына 2 000 МБ-тан көп.",
  "Редко звонят": "Сирек қоңырау шалады",
  "Умеренно звонят": "Орташа жиілікпен қоңырау шалады",
  "Часто звонят": "Жиі қоңырау шалады",
  "Меньше 100 минут в месяц.": "Айына 100 минуттан аз.",
  "От 100 до 400 минут в месяц.": "Айына 100–400 минут.",
  "Больше 400 минут в месяц.": "Айына 400 минуттан көп.",
  "Неизвестный сегмент: {value}": "Белгісіз сегмент: {value}",
  "Описание этого значения не передано.": "Бұл мәннің сипаттамасы берілмеген.",
  "Завершён": "Аяқталды",
  "Ошибка": "Қате",
  "Пропущен": "Өткізіп жіберілді",
  "Резервная стратегия": "Қосалқы стратегия",
  "Проверка пройдена": "Тексеруден өтті",
  "Проверка не пройдена": "Тексеруден өтпеді",
  "Автономный режим": "Автономды режим",
  "Ключ API не задан": "API кілті берілмеген",
  "Ошибка ответа API": "API жауабында қате бар",
  "Истекло время ожидания": "Күту уақыты аяқталды",
  "Ошибка сети": "Желі қатесі",
  "Ошибка запроса к API": "API сұрауының қатесі",
  "Достигнут лимит вызовов советника": "Кеңесшіге сұрау жіберу шегіне жетті",
  "Некорректные входные данные советника": "Кеңесшіге берілген деректер дұрыс емес",
  "Нет кандидатов для советника": "Кеңесшіге арналған нұсқалар жоқ",
  "Ответ модели не соответствует допустимому выбору кандидатов": "Модель жауабы рұқсат етілген нұсқаларға сәйкес келмейді",
  "Некорректный ответ API": "API жауабы дұрыс емес",
  "Некорректный JSON ответа": "Жауаптағы JSON дұрыс емес",
  "Выбор гипотез": "Жорамалдарды іріктеу",
  "Пересмотр после пилотов": "Сынақтардан кейін қайта қарау",
  "Исторический приор недоступен.": "Тарихи деректерге негізделген бастапқы баға қолжетімсіз.",
  "Недоступна зависимость модуля кандидатов; использована резервная генерация.": "Нұсқалар модуліне қажетті құрамдас қолжетімсіз; қосалқы құру тәсілі қолданылды.",
  "Модуль кандидатов завершился с ошибкой; использована резервная генерация.": "Нұсқалар модулі қатемен аяқталды; қосалқы құру тәсілі қолданылды.",
  "Модуль не вернул допустимых кандидатов; использована резервная генерация.": "Модуль жарамды нұсқаларды қайтармады; қосалқы құру тәсілі қолданылды.",
  "Нет поддерживаемого канала для кампаний.": "Науқандар үшін қолдау көрсетілетін арна жоқ.",
  "Нет положительного плана по осторожной оценке. Выбрана резервная кампания; положительный эффект не гарантирован.": "Сақтықпен бағалағанда оң нәтиже беретін жоспар жоқ. Қосалқы науқан таңдалды; оң әсерге кепілдік берілмейді.",
  "Резервная кампания не подтверждена наблюдением пилота.": "Қосалқы науқан сынақ нәтижесімен расталмаған.",
  "Неопределённость — приблизительный запас для планирования по публичному шаблону. Это не калиброванный доверительный интервал.": "Белгісіздік көрсеткіші — ашық үлгі негізінде жоспарлауда қолданылатын шамамен түзету. Бұл калибрленген сенімділік аралығы емес.",
  "Пилот завершился с ошибкой: {reason}.": "Сынақ қатемен аяқталды: {reason}.",
  "Push-уведомление": "Push хабарламасы",
  "Звонок оператора": "Оператор қоңырауы",
  "Цифровая реклама": "Цифрлық жарнама"
});

// The report is data, never markup. Keep parsing independent from the DOM.
export let MISSING = t("нет данных");
onLanguageChange(() => { MISSING = t("нет данных"); });
export const MAX_FILE_BYTES = 10 * 1024 * 1024;
export const CAMPAIGN_COLUMNS = Object.freeze([
  "campaign_name", "filter_current_tariff", "filter_arpu_segment",
  "filter_data_segment", "filter_call_segment", "target_tariff", "channel",
]);
export const FILTER_LABELS = Object.freeze({
  get filter_current_tariff() { return t("Текущий тариф"); },
  get filter_arpu_segment() { return t("Доход с абонента"); },
  get filter_data_segment() { return t("Интернет"); },
  get filter_call_segment() { return t("Звонки"); },
});

const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
export const isNumber = (value) => typeof value === "number" && Number.isFinite(value);
const absent = (value) => value === undefined || value === null;

function fail(path, expected) {
  throw localizedError("Поле «{path}»: {expected}. Выберите корректный отчёт версии 1.0.", {path, expected:() => t(expected)});
}

function optionalString(value, path) {
  if (!absent(value) && typeof value !== "string") fail(path, "ожидается строка");
}

function numericFields(value, keys, path) {
  for (const key of keys) {
    if (!absent(value[key]) && !isNumber(value[key])) fail(`${path}.${key}`, "ожидается конечное число или null");
  }
}

function countFields(value, keys, path) {
  for (const key of keys) {
    if (!absent(value[key]) && (!Number.isSafeInteger(value[key]) || value[key] < 0)) fail(`${path}.${key}`, "ожидается целое неотрицательное число или null");
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
  if (!object(report)) throw localizedError("Отчёт должен быть JSON-объектом. Выберите report.json, созданный агентом.");
  if (report.schema_version !== "1.0") {
    throw localizedError("Версия отчёта не поддерживается. Ожидается schema_version: «1.0».");
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
    optionalString(report.evaluation.scope, "evaluation.scope");
  }
  arrayOfObjects(report.allocation, "allocation").forEach((allocation, i) => {
    for (const key of ["candidate_id", "campaign_name", "channel", "rationale", "uncertainty_method"]) optionalString(allocation[key], `allocation[${i}].${key}`);
    numericFields(allocation, ["audience_size", "communication_cost", "posterior_mean", "uncertainty", "template_uncertainty", "sample_std", "empirical_se", "n_customers", "estimated_net", "conservative_net", "repeats"], `allocation[${i}]`);
    if (!absent(allocation.pilot_refs)) {
      if (!Array.isArray(allocation.pilot_refs) || !allocation.pilot_refs.every((ref) => typeof ref === "string")) fail(`allocation[${i}].pilot_refs`, "ожидается массив строк");
      if (allocation.pilot_refs.length > 20) fail(`allocation[${i}].pilot_refs`, "не более 20 записей диагностики");
    }
  });
  if (!absent(report.selection_diagnostics)) {
    const selection = report.selection_diagnostics;
    if (!object(selection)) fail("selection_diagnostics", "ожидается объект");
    countFields(selection, ["generated_candidates", "tested_candidates", "tested_variants", "confirmed_variants", "selected_variants", "unexplored_candidates"], "selection_diagnostics");
    if (!absent(selection.reason_counts)) {
      if (!object(selection.reason_counts)) fail("selection_diagnostics.reason_counts", "ожидается объект");
      if (Object.keys(selection.reason_counts).length > 64) fail("selection_diagnostics.reason_counts", "не более 64 причин");
      countFields(selection.reason_counts, Object.keys(selection.reason_counts), "selection_diagnostics.reason_counts");
    }
    if (Array.isArray(selection.variants) && selection.variants.length > 20) fail("selection_diagnostics.variants", "не более 20 записей диагностики");
    arrayOfObjects(selection.variants, "selection_diagnostics.variants").forEach((variant, i) => {
      for (const key of ["candidate_id", "channel", "reason"]) optionalString(variant[key], `selection_diagnostics.variants[${i}].${key}`);
      countFields(variant, ["repeats"], `selection_diagnostics.variants[${i}]`);
      numericFields(variant, ["conservative_net"], `selection_diagnostics.variants[${i}]`);
      if (!absent(variant.selected) && typeof variant.selected !== "boolean") fail(`selection_diagnostics.variants[${i}].selected`, "ожидается true или false");
      if (!absent(variant.pilot_refs)) {
        if (!Array.isArray(variant.pilot_refs) || !variant.pilot_refs.every((ref) => typeof ref === "string")) fail(`selection_diagnostics.variants[${i}].pilot_refs`, "ожидается массив строк");
        if (variant.pilot_refs.length > 20) fail(`selection_diagnostics.variants[${i}].pilot_refs`, "не более 20 записей диагностики");
      }
    });
    if (!absent(selection.strategy_config)) {
      if (!object(selection.strategy_config)) fail("selection_diagnostics.strategy_config", "ожидается объект");
      for (const key of ["exploration_policy", "uncertainty_mode", "pilot_sizing"]) optionalString(selection.strategy_config[key], `selection_diagnostics.strategy_config.${key}`);
    }
  }
  if (!absent(report.forecast_summary)) {
    if (!object(report.forecast_summary)) fail("forecast_summary", "ожидается объект");
    numericFields(report.forecast_summary, ["estimated_net", "conservative_net", "communication_cost"], "forecast_summary");
    countFields(report.forecast_summary, ["campaign_count"], "forecast_summary");
    for (const key of ["scope", "comparison_to_evaluation"]) optionalString(report.forecast_summary[key], `forecast_summary.${key}`);
  }
  if (!absent(report.strategy_config)) {
    if (!object(report.strategy_config)) fail("strategy_config", "ожидается объект");
    for (const key of ["exploration_policy", "uncertainty_mode", "pilot_sizing"]) optionalString(report.strategy_config[key], `strategy_config.${key}`);
  }
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
    throw localizedError("Не удалось прочитать JSON. Проверьте формат файла и выберите report.json ещё раз.");
  }
  return validateReport(report);
}

export function number(value, digits = 0) {
  return isNumber(value) ? value.toLocaleString(getLocale(), { maximumFractionDigits: digits }) : MISSING;
}

export function money(value, digits = 0) {
  return isNumber(value) ? t("{value} ден. ед.", {value:number(value, digits)}) : MISSING;
}

// Display-only copy of the public tariff_dictionary.csv. No effect on selection.
// [code number, MB, other-operator minutes, shared other/city minutes, monthly price]
const tariffRows = [
  [1,0,0,0,0], [2,2048,0,0,3140], [3,10240,80,0,5620.6],
  [4,4096,40,0,4678.6], [5,8192,80,0,5934.6], [6,8192,80,0,5934.6],
  [7,8192,80,0,5934.6], [8,8192,80,0,5934.6], [9,10240,150,0,4364.6],
  [10,12288,120,0,7504.6], [11,20480,200,0,9388.6], [12,30720,0,300,12528.6],
  [13,0,30,0,3108.6], [14,2048,80,0,7410.4], [15,0,50,0,3422.6],
  [16,12288,150,0,4364.6], [17,7168,40,0,4992.6], [18,12288,80,0,6248.6],
  [19,3072,80,0,6908], [20,15360,100,0,6562.6], [21,20480,200,0,6248.6],
];
export const TARIFF_CATALOG = Object.freeze(Object.fromEntries(tariffRows.map(([id, mb, minutes, sharedMinutes, price]) => [
  `tariff_${id}`, Object.freeze({mb, minutes, sharedMinutes, price}),
])));

export function tariffInfo(code, language = getLanguage()) {
  const tr = (source, params) => t(source, params, language);
  const row = typeof code === "string" && Object.hasOwn(TARIFF_CATALOG, code) ? TARIFF_CATALOG[code] : null;
  if (!row) return {name: tr("Неизвестный тариф: {code}", {code:displayText(code)}), package: tr("Параметры не указаны"), price: MISSING, description: tr("В справочнике нет этого кода.")};
  const name = tr("Тариф №{n}", {n:code.slice(7)});
  const data = row.mb ? tr("{n} ГБ", {n:number(row.mb / 1024, 2)}) : tr("Без пакета интернета");
  const calls = [row.minutes ? tr("{n} мин", {n:number(row.minutes)}) : "", row.sharedMinutes ? tr("{n} мин, включая городские", {n:number(row.sharedMinutes)}) : ""].filter(Boolean);
  const packageText = [data, ...(calls.length ? calls : [tr("без пакета минут")])].join(" · ");
  const callDetails = [row.minutes ? tr("{n} минут на других операторов", {n:number(row.minutes)}) : "", row.sharedMinutes ? tr("{n} минут на других операторов и городские номера (общий пакет)", {n:number(row.sharedMinutes)}) : ""].filter(Boolean);
  return {name, package:packageText, price: row.price ? tr("{price}/мес.", {price:money(row.price, 1)}) : tr("Без абонентской платы"),
    description: [row.mb ? tr("{n} МБ интернета", {n:number(row.mb)}) : tr("Интернет не включён в пакет"), ...(callDetails.length ? callDetails : [tr("Минуты не включены в пакет")])].join("; ")};
}

export function tariffCodes(value) {
  return typeof value === "string" ? value.split(";").map(code => code.trim()).filter(Boolean) : [];
}

export function tariffLabel(value, language = getLanguage()) {
  const tr = (source, params) => t(source, params, language);
  const codes = tariffCodes(value);
  return codes.length ? codes.map(code => { const info = tariffInfo(code, language); return `${info.name}: ${info.package}`; }).join(` ${tr("или")} `) : tr("Любой текущий тариф");
}

const SEGMENTS = {
  filter_arpu_segment: {
    LOW: ["Низкий доход с абонента", "Средний месячный доход с абонента за 3 месяца: меньше 1 000 денежных единиц."],
    MID: ["Средний доход с абонента", "Средний месячный доход с абонента за 3 месяца: от 1 000 до 5 000 денежных единиц."],
    HIGH: ["Высокий доход с абонента", "Средний месячный доход с абонента за 3 месяца: больше 5 000 денежных единиц."],
  },
  filter_data_segment: {
    NON_USER: ["Не пользуются интернетом", "0 МБ в месяц."],
    LITE: ["Мало пользуются интернетом", "Больше 0, до 2 000 МБ в месяц."],
    HEAVY: ["Активно пользуются интернетом", "Больше 2 000 МБ в месяц."],
  },
  filter_call_segment: {
    LOW: ["Редко звонят", "Меньше 100 минут в месяц."],
    MEDIUM: ["Умеренно звонят", "От 100 до 400 минут в месяц."],
    HIGH: ["Часто звонят", "Больше 400 минут в месяц."],
  },
};

export function segmentInfo(key, value, language = getLanguage()) {
  const tr = (source, params) => t(source, params, language);
  const group = Object.hasOwn(SEGMENTS, key) ? SEGMENTS[key] : null;
  const entry = group && Object.hasOwn(group, value) ? group[value] : null;
  return entry ? {label:tr(entry[0]), description:tr(entry[1])} : {label:tr("Неизвестный сегмент: {value}", {value:displayText(value)}), description:tr("Описание этого значения не передано.")};
}

export function ratio(value) {
  return isNumber(value)
    ? value.toLocaleString(getLocale(), { style: "percent", maximumFractionDigits: 2, signDisplay: "exceptZero" })
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
  // Search both vocabularies so changing the interface language retains useful results.
  const descriptions = ["ru", "kk"].flatMap(language => [tariffLabel(campaign.filter_current_tariff, language), tariffLabel(campaign.target_tariff, language), channelLabel(campaign.channel, language),
    ...Object.keys(SEGMENTS).filter(key => campaign[key]).map(key => segmentInfo(key, campaign[key], language).label)]);
  const text = [...CAMPAIGN_COLUMNS.map((key) => campaign[key] ?? ""), ...descriptions].join(" ").toLocaleLowerCase(getLocale());
  return text.includes(query.trim().toLocaleLowerCase(getLocale()));
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
  if (Object.hasOwn(TRANSLATIONS, value)) return t(TRANSLATIONS[value]);
  if (value.startsWith("pilot_failed_")) return t("Пилот завершился с ошибкой: {reason}.", {reason:value.slice("pilot_failed_".length)});
  return value;
}

export function channelLabel(value, language = getLanguage()) {
  const tr = (source, params) => t(source, params, language);
  const labels = { sms: "SMS", push: "Push-уведомление", call: "Звонок оператора", digital_ads: "Цифровая реклама" };
  return Object.hasOwn(labels, value) ? tr(labels[value]) : displayText(value);
}
