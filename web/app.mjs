import {
  MAX_FILE_BYTES, MISSING, FILTER_LABELS, parseReport, number, money, ratio,
  isNumber, displayText, findAllocation, campaignMatches, campaignsToCsv, translate, channelLabel,
} from "./report.mjs";

const $ = (id) => document.getElementById(id);
let currentReport = null;
let loading = false;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setText(id, text) { $(id).textContent = text; }

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
  $("report-view").hidden = !value;
  $("empty-state").hidden = value;
  $("nav-campaign-count").hidden = !value;
  document.querySelectorAll("[data-report-link]").forEach((link) => {
    if (value) link.removeAttribute("aria-disabled");
    else link.setAttribute("aria-disabled", "true");
  });
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

function renderCampaigns() {
  if (!currentReport) return;
  const query = $("campaign-search").value;
  const channel = $("campaign-channel").value;
  const campaigns = currentReport.campaigns.filter((campaign) => campaignMatches(campaign, query, channel));
  const rows = $("campaign-rows");
  rows.replaceChildren();
  campaigns.forEach((campaign) => {
    const allocation = findAllocation(campaign, currentReport.allocation ?? []);
    const row = element("tr");
    const segment = element("td", "segment-cell");
    segment.append(makeSegment(campaign), campaignDetails(campaign, allocation));
    const target = element("td");
    target.append(element("span", "target-tariff", campaign.target_tariff));
    const channelCell = element("td");
    channelCell.append(element("span", "channel-chip", channelLabel(campaign.channel)));
    row.append(segment, target, channelCell,
      numericCell(number(allocation?.audience_size), "контактов"),
      numericCell(money(allocation?.communication_cost), "на коммуникацию"),
      numericCell(money(allocation?.estimated_net), `Осторожная: ${money(allocation?.conservative_net)}`),
    );
    rows.append(row);
  });
  setText("campaign-result-count", `Показано ${number(campaigns.length)} из ${number(currentReport.campaigns.length)}`);
  $("campaign-table-wrap").hidden = campaigns.length === 0;
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
  if (!isNumber(report.evaluation?.net_arpu_gain)) list.append(element("li", "", "Чистый прирост evaluator недоступен. Плановые оценки не заменяют фактическую оценку прогона."));
  if (!report.planned_resources) list.append(element("li", "", "Остатки после финального плана не переданы; лимиты этого этапа нельзя оценить по отчёту."));
  if (report.synthetic === false) list.append(element("li", "warning", "Файл не отмечен как синтетический. Этот интерфейс предназначен для учебного кейса HackAlem AI."));
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

function renderReport(report, source) {
  currentReport = report;
  setText("run-badge", "Сохранённый прогон");
  $("run-badge").className = "badge badge-neutral";
  setText("meta-source", source);
  setText("meta-seed", number(report.seed));
  setText("meta-time", formatDate(report.generated_at));
  setText("meta-engine", report.engine);
  setText("metric-net", money(report.evaluation?.net_arpu_gain));
  setText("evaluation-status", isNumber(report.evaluation?.net_arpu_gain)
    ? (report.evaluation?.status ? translate(report.evaluation.status) : "Фактическая оценка синтетического прогона")
    : "Оценка evaluator отсутствует");
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
  setReportVisible(true);
}

async function loadReport(readText, source) {
  if (loading) return;
  setLoading(true);
  setNotice("loading", "Читаем отчёт…", "Проверяем версию и структуру данных.");
  try {
    const text = await readText();
    if (new TextEncoder().encode(text).byteLength > MAX_FILE_BYTES) throw new Error("Файл больше 10 МБ. Выберите меньший отчёт.");
    const report = parseReport(text);
    renderReport(report, source);
    setNotice("success", "Отчёт загружен", "Открыт сохранённый прогон. Новый расчёт и рассылки не запускаются.");
  } catch (error) {
    currentReport = null;
    setReportVisible(false);
    setText("run-badge", "Отчёт не загружен");
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

document.querySelectorAll(".nav-link").forEach((link) => {
  link.addEventListener("click", (event) => {
    if (link.getAttribute("aria-disabled") === "true") { event.preventDefault(); return; }
    document.querySelectorAll(".nav-link").forEach((other) => other.classList.remove("active"));
    link.classList.add("active");
  });
});
setReportVisible(false);
