import {
  MAX_FILE_BYTES, MISSING, FILTER_LABELS, parseReport, validateReport, number, money, ratio,
  isNumber, displayText, findAllocation, campaignMatches, campaignsToCsv, translate, channelLabel,
} from "./report.mjs";

const $ = (id) => document.getElementById(id);
let currentReport = null;
let loading = false;
const VIEW_LABELS = { overview: "Обзор", campaigns: "Кампании", pilots: "Пилоты", ask: "Спросить агента", limitations: "О результате" };

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setText(id, text) { $(id).textContent = text; }

export function getCurrentReport() { return currentReport; }
export function showAppNotice(kind, title, description = "") { setNotice(kind, title, description); }

function showView(view, focus = true) {
  if (!Object.hasOwn(VIEW_LABELS, view)) return false;
  document.querySelectorAll("[data-panel]").forEach((panel) => { panel.hidden = panel.dataset.panel !== view; });
  document.querySelectorAll(".nav-link").forEach((link) => {
    const active = link.dataset.view === view;
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  setText("view-label", VIEW_LABELS[view]);
  if (focus) {
    if ($("load-status").classList.contains("notice-success")) setNotice("", "");
    $("main").focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  document.dispatchEvent(new CustomEvent("arpu:view-changed", {detail:{view}}));
  return true;
}

function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#i-${name}`);
  svg.append(use);
  return svg;
}

export function focusEvidence(ref) {
  if (!currentReport || typeof ref !== "string") return false;
  let view, target;
  const campaign = /^campaigns\[(\d+)\]$/.exec(ref);
  const pilot = /^pilots\[(\d+)\]$/.exec(ref);
  if (campaign && Number(campaign[1]) < currentReport.campaigns.length) {
    $("campaign-search").value = "";
    $("campaign-channel").value = "";
    renderCampaigns();
    view = "campaigns"; target = $(`campaign-${Number(campaign[1])}`);
  } else if (pilot && Number(pilot[1]) < currentReport.pilots.length) {
    $("pilot-status").value = "";
    renderPilots();
    view = "pilots"; target = $(`pilot-${Number(pilot[1])}`);
  } else if (ref === "evaluation.net_arpu_gain" || ref === "evaluation") {
    view = "overview"; target = $("evaluation-summary");
  } else if (ref === "resources") {
    view = "overview"; target = $("resources");
  } else if (ref === "planned_resources") {
    view = "overview"; target = $("planned-resources");
  } else if (ref === "warnings") {
    view = "limitations"; target = $("warnings-panel");
  } else if (ref === "advisor") {
    view = "limitations"; target = $("advisor-panel"); target.open = true;
  }
  if (!target) return false;
  showView(view, false);
  target.setAttribute("tabindex", "-1");
  target.focus({ preventScroll: true });
  target.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" });
  target.classList.add("evidence-highlight");
  setTimeout(() => target.classList.remove("evidence-highlight"), 3500);
  return true;
}

function setNotice(kind, title, description = "") {
  const notice = $("load-status");
  notice.hidden = !kind;
  notice.className = `notice notice-${kind || "neutral"}`;
  notice.setAttribute("role", kind === "error" ? "alert" : "status");
  setText("status-title", title);
  setText("status-description", description);
  $("status-description").hidden = !description;
  $("retry-button").hidden = kind !== "error";
}

function setLoading(value) {
  loading = value;
  document.querySelectorAll("[data-open], #load-static").forEach((button) => { button.disabled = value; });
  $("main").setAttribute("aria-busy", String(value));
}

function setReportVisible(value) {
  document.body.classList.toggle("report-loaded", value);
  $("report-view").hidden = !value;
  $("empty-state").hidden = value;
  $("nav-campaign-count").hidden = !value;
  $("clear-report").disabled = !value;
}

function formatDate(value) {
  if (typeof value !== "string" || !value.trim()) return MISSING;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return `${value} (формат времени не распознан)`;
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", timeZoneName: "short",
  }).format(date);
}

function addDefinition(dl, title, value) {
  const group = element("div");
  group.append(element("dt", "", title), element("dd", "", value));
  dl.append(group);
}

function makeSegment(filters = {}) {
  const container = element("div");
  container.append(element("div", "segment-title", filters.filter_current_tariff || "Все текущие тарифы"));
  const tags = element("div", "segment-tags");
  for (const [key, label] of Object.entries(FILTER_LABELS)) {
    if (key !== "filter_current_tariff" && typeof filters[key] === "string" && filters[key]) {
      tags.append(element("span", "segment-tag", `${label} · ${filters[key]}`));
    }
  }
  if (!tags.childElementCount) tags.append(element("span", "cell-subtext", "Без дополнительных фильтров"));
  container.append(tags);
  return container;
}

function numericCell(main, secondary, className = "") {
  const cell = element("td", "numeric");
  cell.append(element("strong", className, main));
  if (secondary) cell.append(element("span", "cell-subtext", secondary));
  return cell;
}

function effectClass(value) {
  return isNumber(value) && value !== 0 ? (value > 0 ? "positive" : "negative") : "";
}

function campaignDetails(campaign, allocation) {
  const details = element("details", "row-details");
  details.append(element("summary", "", "Основания и оценки"));
  const dl = element("dl");
  addDefinition(dl, "Название кампании", displayText(campaign.campaign_name));
  if (allocation) {
    addDefinition(dl, "Оценка изменения ARPU", ratio(allocation.posterior_mean));
    addDefinition(dl, "Приблизительный запас неопределённости", isNumber(allocation.uncertainty) ? `${number(allocation.uncertainty * 100, 2)} п. п.` : MISSING);
    addDefinition(dl, "Контактов в наблюдениях", number(allocation.n_customers));
    addDefinition(dl, "Количество пилотов по гипотезе", number(allocation.repeats));
  } else {
    addDefinition(dl, "Распределение", "Нет однозначно связанных оценок этой кампании в отчёте.");
  }
  details.append(dl);
  const rationale = campaign.rationale || allocation?.rationale;
  if (rationale) details.append(element("p", "", rationale));
  return details;
}

function campaignPilotIndices(campaign) {
  // Match the hypothesis AND channel; pilots on another channel are not evidence.
  const allocation = findAllocation(campaign, currentReport?.allocation ?? []);
  const derived = (
    typeof campaign.campaign_name === "string" && campaign.campaign_name.startsWith("compass_")
      ? campaign.campaign_name.slice(8) : null
  );
  if (campaign.candidate_id && derived && campaign.candidate_id !== derived) return [];
  const id = allocation?.candidate_id || campaign.candidate_id || derived;
  if (!id) return [];
  return currentReport.pilots.map((pilot, index) => ({ pilot, index }))
    .filter(({ pilot }) => pilot.candidate_id === id && pilot.channel === campaign.channel && pilot.status === "completed")
    .map(({ index }) => index);
}

function campaignEvidence(campaign) {
  const box = element("div", "campaign-evidence");
  const indices = campaignPilotIndices(campaign);
  box.append(element("span", "", indices.length ? "Наблюдения этого канала:" : "Нет завершённых пилотов этой гипотезы и канала в отчёте."));
  indices.forEach((index) => {
    const link = element("button", "evidence-link", `Пилот ${index + 1}`);
    link.type = "button";
    link.addEventListener("click", () => focusEvidence(`pilots[${index}]`));
    box.append(link);
  });
  return box;
}

function renderOverview(report) {
  const recommendations = $("recommendations");
  recommendations.replaceChildren();
  const ranked = report.campaigns.map((campaign, index) => ({ campaign, index, allocation: findAllocation(campaign, report.allocation ?? []) }))
    .sort((a, b) => {
      const left = a.allocation?.conservative_net;
      const right = b.allocation?.conservative_net;
      if (isNumber(left) && isNumber(right)) return right - left;
      if (isNumber(left)) return -1;
      if (isNumber(right)) return 1;
      return a.index - b.index;
    }).slice(0, 3);
  ranked.forEach(({ campaign, index, allocation }, rank) => {
    const card = element("button", "recommendation-card");
    card.type = "button";
    card.setAttribute("aria-label", `Открыть кампанию ${index + 1}: ${campaign.filter_current_tariff || "Все тарифы"} → ${campaign.target_tariff}, ${channelLabel(campaign.channel)}`);
    const text = element("span", "recommendation-text");
    text.append(element("strong", "", `${campaign.filter_current_tariff || "Все тарифы"} → ${campaign.target_tariff}`));
    const segment = Object.entries(FILTER_LABELS)
      .filter(([key]) => key !== "filter_current_tariff" && campaign[key])
      .map(([key, label]) => `${label}: ${campaign[key]}`).join(" · ");
    text.append(element("span", "recommendation-segment", segment || "Все сегменты"));
    const evidence = campaignPilotIndices(campaign).length;
    text.append(element("span", "", `${channelLabel(campaign.channel)} · ${evidence ? `наблюдений: ${number(evidence)}` : "нет связанных наблюдений"}`));
    const effect = element("span", "recommendation-effect");
    effect.append(element("strong", effectClass(allocation?.conservative_net), money(allocation?.conservative_net)), element("span", "", "осторожная оценка"));
    card.append(element("span", "recommendation-rank", String(rank + 1).padStart(2, "0")), text, effect);
    card.addEventListener("click", () => focusEvidence(`campaigns[${index}]`));
    recommendations.append(card);
  });
  if (!ranked.length) {
    const empty = element("div", "panel inline-empty");
    empty.append(element("h3", "", "План кампаний не сформирован"), element("p", "", "Прогон не готов к отправке. Проверьте предупреждения и наблюдения пилотов."));
    recommendations.append(empty);
  }
  const risks = $("risk-summary");
  risks.replaceChildren();
  const messages = [];
  if (report.campaigns.length === 0) messages.push("В отчёте нет финального плана.");
  if (isNumber(report.evaluation?.net_arpu_gain) && report.evaluation.net_arpu_gain < 0) messages.push("Фактический чистый прирост этого прогона отрицательный.");
  if (!isNumber(report.evaluation?.net_arpu_gain)) messages.push("Итог расчёта недоступен.");
  messages.push(...(report.warnings ?? []).map(translate));
  if (ranked.some(({ allocation }) => !allocation)) messages.push("Для части кампаний нет однозначно связанных плановых оценок.");
  if (!messages.length) messages.push("Агент не записал предупреждений. Это не гарантия положительного эффекта.");
  messages.slice(0, 2).forEach((message) => risks.append(element("li", "", message)));
  risks.append(element("li", "", "Плановые оценки приблизительны. Результат пилота не гарантирует эффект всей кампании."));
}

function renderCampaigns() {
  if (!currentReport) return;
  const query = $("campaign-search").value;
  const channel = $("campaign-channel").value;
  const campaigns = currentReport.campaigns.map((campaign, index) => ({ campaign, index })).filter(({ campaign }) => campaignMatches(campaign, query, channel));
  const rows = $("campaign-cards");
  rows.replaceChildren();
  campaigns.forEach(({ campaign, index }) => {
    const allocation = findAllocation(campaign, currentReport.allocation ?? []);
    const row = element("article", "campaign-card");
    row.id = `campaign-${index}`;
    row.tabIndex = -1;
    const header = element("div", "campaign-card-header");
    const heading = element("div", "campaign-card-heading");
    heading.append(element("p", "eyebrow", `Кампания ${String(index + 1).padStart(2, "0")}`),
      element("h2", "", `${campaign.filter_current_tariff || "Все текущие тарифы"} → ${campaign.target_tariff}`),
      element("span", "channel-chip", channelLabel(campaign.channel)));
    const effect = element("div", "campaign-effect");
    effect.append(element("span", "", "Прогноз чистого эффекта"), element("strong", effectClass(allocation?.estimated_net), money(allocation?.estimated_net)),
      element("span", "effect-secondary", `Осторожная оценка: ${money(allocation?.conservative_net)}`));
    header.append(heading, effect);
    const facts = element("div", "campaign-facts");
    const segment = element("div");
    segment.append(element("span", "campaign-fact-label", "Аудитория"));
    const tags = element("div", "segment-tags");
    for (const [key, label] of Object.entries(FILTER_LABELS)) {
      if (key !== "filter_current_tariff" && campaign[key]) tags.append(element("span", "segment-tag", `${label} · ${campaign[key]}`));
    }
    if (!tags.childElementCount) tags.append(element("span", "small-note", "Без дополнительных фильтров"));
    segment.append(tags);
    const reach = element("div");
    reach.append(element("span", "campaign-fact-label", "Плановый охват"), element("strong", "", `${number(allocation?.audience_size)}${isNumber(allocation?.audience_size) ? " контактов" : ""}`));
    const cost = element("div");
    cost.append(element("span", "campaign-fact-label", "Расходы на коммуникацию"), element("strong", "", money(allocation?.communication_cost)));
    facts.append(segment, reach, cost);
    row.append(header, facts, campaignEvidence(campaign), campaignDetails(campaign, allocation));
    rows.append(row);
  });
  setText("campaign-result-count", `Показано ${number(campaigns.length)} из ${number(currentReport.campaigns.length)}`);
  $("campaign-cards").hidden = campaigns.length === 0;
  $("campaign-empty").hidden = campaigns.length !== 0;
  setText("campaign-empty-title", currentReport.campaigns.length ? "По этим условиям кампаний нет" : "План кампаний не сформирован");
  setText("campaign-empty-description", currentReport.campaigns.length
    ? "Измените запрос или выберите другой канал. Полный план доступен в экспорте."
    : "В отчёте нет финальных кампаний. Прогон не готов к отправке: проверьте предупреждения и результаты пилотов.");
}

function pilotDetails(pilot) {
  const details = element("details", "row-details");
  details.append(element("summary", "", "Ресурсы после пилота"));
  const dl = element("dl");
  addDefinition(dl, "Бюджет", money(pilot.remaining_budget));
  addDefinition(dl, "Контакты", number(pilot.remaining_contacts));
  addDefinition(dl, "Наблюдённый суммарный эффект", money(pilot.observed_lift_total));
  addDefinition(dl, "Гипотеза", displayText(pilot.candidate_id));
  details.append(dl);
  return details;
}

function renderPilots() {
  if (!currentReport) return;
  const status = $("pilot-status").value;
  const pilots = currentReport.pilots.map((pilot, index) => ({ pilot, index })).filter(({ pilot }) => !status || pilot.status === status);
  const rows = $("pilot-rows");
  rows.replaceChildren();
  pilots.forEach(({ pilot, index }) => {
    const row = element("tr");
    row.id = `pilot-${index}`;
    row.tabIndex = -1;
    const segment = element("td", "segment-cell");
    segment.append(makeSegment(pilot.filters ?? {}));
    segment.append(element("div", "cell-subtext", `→ ${displayText(pilot.target_tariff)}`));
    segment.append(pilotDetails(pilot));
    const channel = element("td");
    channel.append(element("span", "channel-chip", channelLabel(pilot.channel)));
    const state = element("td");
    const badge = pilot.status === "completed" ? "badge-success" : pilot.status === "failed" ? "badge-error" : "badge-neutral";
    state.append(element("span", `badge ${badge}`, translate(pilot.status)));
    row.append(element("td", "", String(index + 1)), segment, channel,
      numericCell(number(pilot.n_customers), `Запрошено: ${number(pilot.requested_n)}`),
      numericCell(ratio(pilot.observed_lift_ratio), "к ARPU", effectClass(pilot.observed_lift_ratio)),
      numericCell(money(pilot.cost)), state);
    rows.append(row);
  });
  $("pilot-empty").hidden = pilots.length !== 0;
  $("pilot-table-wrap").hidden = pilots.length === 0;
}

function renderPilotChart(report) {
  const chart = $("pilot-chart");
  chart.replaceChildren();
  const known = report.pilots.filter((pilot) => isNumber(pilot.observed_lift_ratio));
  // A compact chart is useful only for a modest run; the table always has every record.
  const show = known.length > 0 && report.pilots.length <= 40;
  $("pilot-chart-panel").hidden = !show;
  if (!show) return;
  const maximum = Math.max(...known.map((pilot) => Math.abs(pilot.observed_lift_ratio)), .00001);
  report.pilots.forEach((pilot, index) => {
    const slot = element("div", "pilot-bar-slot");
    slot.title = `Пилот ${index + 1}: ${ratio(pilot.observed_lift_ratio)}`;
    if (isNumber(pilot.observed_lift_ratio)) {
      const value = pilot.observed_lift_ratio;
      const bar = element("span", `pilot-bar${value < 0 ? " pilot-bar-negative" : ""}${value === 0 ? " pilot-bar-zero" : ""}`);
      bar.style.setProperty("--height", `${Math.abs(value) / maximum * 45}%`);
      slot.append(bar);
    }
    chart.append(slot);
  });
}

function fillSelect(id, values, label) {
  const select = $(id);
  while (select.options.length > 1) select.remove(1);
  [...new Set(values.filter((value) => typeof value === "string" && value))].sort().forEach((value) => {
    const option = element("option", "", label(value));
    option.value = value;
    select.append(option);
  });
  select.value = "";
}

function renderLimits(report) {
  const list = $("warnings-list");
  list.replaceChildren();
  const warnings = report.warnings ?? [];
  if (warnings.length) warnings.forEach((warning) => list.append(element("li", "warning", translate(warning))));
  else list.append(element("li", "", Array.isArray(report.warnings) ? "Агент не записал предупреждений в этот отчёт." : "Предупреждения не переданы в отчёте."));
  if (report.campaigns.length === 0) list.append(element("li", "warning", "Нет финальных кампаний: результат прогона неполный."));
  if (report.campaigns.length > 10) list.append(element("li", "warning", "В отчёте больше 10 кампаний. Проверьте допустимый размер финального плана."));
  if (!isNumber(report.evaluation?.net_arpu_gain)) list.append(element("li", "", "Итог расчёта недоступен. Прогнозы кампаний не заменяют его."));
  if (!report.planned_resources) list.append(element("li", "", "Остатки после финального плана не переданы; лимиты этого этапа нельзя оценить по отчёту."));
  const negativeResources = [report.resources, report.planned_resources].some((resources) => resources && ["remaining_budget", "remaining_contacts", "pilots_left"].some((key) => isNumber(resources[key]) && resources[key] < 0));
  if (negativeResources) list.append(element("li", "warning", "В отчёте есть отрицательный остаток ресурсов. Проверьте соблюдение лимитов перед использованием плана."));
  list.append(element("li", "", "Расходы включают повторные контакты. Охваты отдельных кампаний нельзя считать уникальной аудиторией всего плана."));
  setText("uncertainty-note", report.uncertainty_note ? translate(report.uncertainty_note) : "Оценка неопределённости не передана. Не интерпретируйте пилотный эффект как гарантированный результат.");

  const advisor = $("advisor-content");
  advisor.replaceChildren();
  (report.advisor ?? []).forEach((entry) => {
    const block = element("article", "advisor-entry");
    block.append(element("h3", "", `${translate(entry.phase)} · ${translate(entry.status)}`));
    if (entry.reason) block.append(element("p", "", translate(entry.reason)));
    if (entry.model) block.append(element("p", "", `Модель: ${entry.model}`));
    if (entry.summary) block.append(element("p", "", entry.summary));
    advisor.append(block);
  });
  (report.events ?? []).filter((event) => event.summary).forEach((event) => {
    const block = element("article", "advisor-entry");
    block.append(element("h3", "", event.phase ? translate(event.phase) : "Пояснение агента"), element("p", "", event.summary));
    advisor.append(block);
  });
  if (!advisor.childElementCount) advisor.append(element("p", "advisor-entry", "В этом отчёте нет статусов или пояснений советника."));
}

function renderResultSummary(report, source = "") {
  setText("result-source", report ? source : "Отчёт не выбран");
  setText("result-seed", report ? number(report.seed) : MISSING);
  setText("result-time", report ? formatDate(report.generated_at) : MISSING);
  setText("result-engine", report ? report.engine : MISSING);
  setText("result-budget-pilots", money(report?.resources?.remaining_budget));
  setText("result-budget-planned", money(report?.planned_resources?.remaining_budget));
  setText("result-contacts-pilots", number(report?.resources?.remaining_contacts));
  setText("result-contacts-planned", number(report?.planned_resources?.remaining_contacts));
  const hasNegative = [report?.resources, report?.planned_resources].some(resources => resources && ["remaining_budget", "remaining_contacts", "pilots_left"].some(key => isNumber(resources[key]) && resources[key] < 0));
  const needsReview = report && (!report.campaigns.length || report.campaigns.length > 10 || hasNegative || report.warnings?.length || report.validation?.valid === false);
  setText("result-verdict", !report ? "Нет отчёта" : needsReview ? "Проверьте ограничения" : "План готов к проверке");
}

function renderReport(report, source) {
  currentReport = report;
  setText("run-badge", source === "Текущий прогон" ? "Текущий прогон" : "Сохранённый прогон");
  $("run-badge").className = "badge badge-neutral";
  setText("meta-source", source);
  setText("meta-seed", number(report.seed));
  setText("meta-time", formatDate(report.generated_at));
  setText("meta-engine", report.engine);
  setText("overview-title", report.campaigns.length ? "Результаты анализа" : "План не сформирован");
  setText("overview-description", "Итог расчёта, рекомендованные кампании и доступные ресурсы.");
  setText("plan-summary", report.campaigns.length ? "План сформирован" : "План не сформирован");
  setText("metric-net", money(report.evaluation?.net_arpu_gain));
  setText("evaluation-status", isNumber(report.evaluation?.net_arpu_gain)
    ? (report.evaluation?.status ? translate(report.evaluation.status) : "Итог расчёта")
    : "Итог расчёта недоступен");
  setText("metric-campaigns", number(report.campaigns.length));
  setText("metric-pilots", number(report.pilots.length));
  const completed = report.pilots.filter((pilot) => pilot.status === "completed").length;
  const failed = report.pilots.filter((pilot) => pilot.status === "failed").length;
  const unknown = report.pilots.length - completed - failed;
  setText("pilot-completion", `Завершено: ${number(completed)} · ошибок: ${number(failed)}${unknown ? ` · другой/неизвестный статус: ${number(unknown)}` : ""}`);
  setText("metric-pilots-left", number(report.resources.pilots_left));
  setText("budget-pilots", money(report.resources.remaining_budget));
  setText("contacts-pilots", number(report.resources.remaining_contacts));
  setText("budget-planned", money(report.planned_resources?.remaining_budget));
  setText("contacts-planned", number(report.planned_resources?.remaining_contacts));
  setText("campaign-heading-count", number(report.campaigns.length));
  setText("nav-campaign-count", number(report.campaigns.length));
  setText("pilot-heading-count", number(report.pilots.length));
  $("export-csv").disabled = report.campaigns.length === 0;
  $("campaign-search").value = "";
  fillSelect("campaign-channel", report.campaigns.map((campaign) => campaign.channel), channelLabel);
  fillSelect("pilot-status", report.pilots.map((pilot) => pilot.status), translate);
  renderCampaigns();
  renderPilots();
  renderPilotChart(report);
  renderLimits(report);
  renderResultSummary(report, source);
  renderOverview(report);
  setReportVisible(true);
}

export function importReport(report, source = "Текущий прогон") {
  validateReport(report);
  renderReport(report, typeof source === "string" ? source : "Текущий прогон");
  showView("overview", false);
  document.dispatchEvent(new CustomEvent("arpu:report-loaded", { detail: { report, source } }));
  return report;
}

function clearReport() {
  currentReport = null;
  setReportVisible(false);
  $("export-csv").disabled = true;
  $("campaign-cards").replaceChildren();
  $("pilot-rows").replaceChildren();
  $("pilot-chart").replaceChildren();
  $("pilot-chart-panel").hidden = true;
  $("pilot-table-wrap").hidden = true;
  $("pilot-empty").hidden = false;
  $("campaign-empty").hidden = false;
  setText("campaign-empty-title", "План пока не загружен");
  setText("campaign-empty-description", "Запустите анализ или откройте готовый report.json, чтобы изучить рекомендации.");
  setText("campaign-result-count", "");
  $("campaign-search").value = "";
  fillSelect("campaign-channel", [], channelLabel);
  fillSelect("pilot-status", [], translate);
  setText("campaign-heading-count", "");
  setText("pilot-heading-count", "");
  setText("run-badge", "Отчёт не загружен");
  setText("overview-title", "Тарифные кампании");
  setText("overview-description", "Запустите анализ аудитории или откройте сохранённый план.");
  $("warnings-list").replaceChildren(element("li", "", "Откройте отчёт, чтобы увидеть ограничения фактического прогона."));
  $("advisor-content").replaceChildren(element("p", "advisor-entry", "Отчёт пока не загружен."));
  setText("uncertainty-note", "Неопределённость — приблизительный запас для планирования, а не доверительный интервал.");
  renderResultSummary(null);
  showView("overview", false);
  document.dispatchEvent(new CustomEvent("arpu:report-cleared"));
}

async function loadReport(readText, source) {
  if (loading) return;
  setLoading(true);
  setNotice("loading", "Читаем отчёт…", "Проверяем версию и структуру данных.");
  try {
    const text = await readText();
    if (new TextEncoder().encode(text).byteLength > MAX_FILE_BYTES) throw new Error("Файл больше 10 МБ. Выберите меньший отчёт.");
    const report = parseReport(text);
    importReport(report, source);
    setNotice("success", "Отчёт загружен", "Открыт сохранённый прогон. Новый расчёт и рассылки не запускаются.");
  } catch (error) {
    clearReport();
    setNotice("error", "Не удалось открыть отчёт", error instanceof Error ? error.message : "Выберите корректный report.json и повторите попытку.");
  } finally {
    setLoading(false);
    $("report-file").value = "";
  }
}

document.querySelectorAll("[data-open]").forEach((button) => {
  button.addEventListener("click", () => { if (!loading) $("report-file").click(); });
});
$("report-file").addEventListener("change", () => {
  const file = $("report-file").files?.[0];
  if (!file) return;
  loadReport(async () => {
    if (file.size > MAX_FILE_BYTES) throw new Error("Файл больше 10 МБ. Выберите меньший отчёт.");
    return file.text();
  }, `Импорт · ${file.name}`);
});
$("load-static").addEventListener("click", () => {
  loadReport(async () => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      // Fixed, same-origin local path. The imported file is never uploaded.
      const response = await fetch("./report.json", { cache: "no-store", signal: controller.signal, credentials: "omit", redirect: "error" });
      if (!response.ok) throw new Error("Сохранённый report.json не найден рядом со страницей. Откройте файл отчёта кнопкой «Открыть отчёт».");
      const length = Number(response.headers.get("content-length"));
      if (Number.isFinite(length) && length > MAX_FILE_BYTES) throw new Error("Файл больше 10 МБ. Выберите меньший отчёт.");
      return await response.text();
    } catch (error) {
      if (error?.name === "AbortError") throw new Error("Не удалось загрузить сохранённый отчёт за 10 секунд. Откройте файл вручную.");
      if (error instanceof TypeError) throw new Error("Сохранённый отчёт недоступен. Откройте файл вручную или запустите локальный веб-сервер по README.");
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }, "Сохранённый файл · report.json");
});
$("campaign-search").addEventListener("input", renderCampaigns);
$("campaign-channel").addEventListener("change", renderCampaigns);
$("pilot-status").addEventListener("change", renderPilots);
$("export-csv").addEventListener("click", () => {
  if (!currentReport?.campaigns.length) return;
  const blob = new Blob([campaignsToCsv(currentReport.campaigns)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = element("a");
  anchor.href = url;
  anchor.download = "arpu-compass-campaigns.csv";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

document.querySelectorAll("[data-view]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    showView(link.dataset.view);
  });
});
document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    $("agent-question").value = button.dataset.question;
    $("agent-question").dispatchEvent(new Event("input"));
    $("agent-question").focus();
  });
});
$("clear-report").addEventListener("click", () => {
  clearReport();
  setNotice("", "");
});
setReportVisible(false);
