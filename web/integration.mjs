import { createApiClient } from "./api.mjs";
import { getCurrentReport, importReport, showAppNotice, focusEvidence } from "./app.mjs";
import { findAllocation } from "./report.mjs";

const $ = id => document.getElementById(id);
// Leave time for the server's bounded 20-second OpenAI request and fallback.
const api = createApiClient({ timeoutMs: 30000 });
let health = null;
let activeRun = null;
let polling = false;
let connecting = false;
let chatBusy = false;
let snapshotId = null;
let reportGeneration = 0;
let serverImport = false;
let chatSequence = 0;

function text(id, value) { const node = $(id); if (node) node.textContent = value; }
function message(error) { return error instanceof Error ? error.message : "Не удалось выполнить запрос. Повторите попытку."; }
function selectedMode() { return $("analysis-mode").value; }
function canOpenAI() { return !!(health?.openai.configured && health?.openai.enabled); }
function updateControls() {
  const runAllowed = !!health?.capabilities.run && !activeRun && !connecting;
  $("run-analysis").disabled = !runAllowed || (selectedMode() === "openai" && !canOpenAI());
  $("analysis-mode").disabled = !!activeRun;
  $("run-seed").disabled = !!activeRun;
  $("ask-agent").disabled = !health?.capabilities.chat || !snapshotId || chatBusy || !!activeRun;
  $("agent-question").disabled = !snapshotId || chatBusy || !!activeRun;
  if ($("load-server-report")) $("load-server-report").disabled = !health || !!activeRun || connecting || chatBusy;
  if ($("retry-api")) $("retry-api").disabled = connecting || polling;
}
function connectionText() {
  if (!health) return "Локальный API недоступен";
  if (!health.openai.configured) return "Сервер подключён · ключ OpenAI не настроен";
  if (!health.openai.enabled) return "Сервер подключён · OpenAI выключен на сервере";
  return "Сервер подключён · OpenAI настроен";
}
function modeHint() {
  if (activeRun) return;
  if (!health) text("analysis-status", "Запустите локальный сервер по README или откройте сохранённый report.json.");
  else if (selectedMode() === "openai" && !canOpenAI()) text("analysis-status", "OpenAI недоступен. Настройте ключ в окружении сервера или выберите автономный режим.");
  else text("analysis-status", selectedMode() === "openai"
    ? "Настройки OpenAI доступны. Успех вызова будет известен после запуска."
    : "Автономный анализ работает без запросов к OpenAI.");
}
function clearAnswer() {
  chatSequence++;
  text("agent-answer", "");
  $("agent-evidence").replaceChildren();
  text("agent-mode", "Ответ ещё не получен");
}
function chatHint() {
  if (!getCurrentReport()) text("agent-status", "Сначала запустите анализ или загрузите снимок сервера.");
  else if (!snapshotId) text("agent-status", "Этот отчёт импортирован локально. Для вопросов загрузите снимок сервера или запустите новый анализ; ваш файл не отправляется.");
  else if (!health) text("agent-status", "Для ответа нужен локальный API. Открытый отчёт сохранён.");
  else text("agent-status", "Ответ будет основан на этом снимке. Фактический режим указан под ответом.");
}
document.addEventListener("arpu:report-loaded", () => {
  reportGeneration++;
  if (!serverImport) snapshotId = null;
  clearAnswer(); chatHint(); updateControls();
});
document.addEventListener("arpu:report-cleared", () => {
  reportGeneration++; snapshotId = null; clearAnswer(); chatHint(); updateControls();
});
async function displaySnapshot(payload, source) {
  serverImport = true;
  snapshotId = payload.report_id;
  try { await importReport(payload.report, source); }
  catch (error) { snapshotId = null; throw error; }
  finally { serverImport = false; }
  chatHint(); updateControls();
}
async function refreshHealth({resume = true} = {}) {
  if (connecting) return;
  connecting = true;
  text("api-status", "Проверяем подключение…");
  updateControls();
  try {
    health = await api.health();
    text("api-status", connectionText());
    if (resume) {
      if (health.run.state === "running" || (activeRun && health.run.state !== "idle")) {
        activeRun = health.run.run_id;
      } else if (activeRun && health.run.state === "idle") {
        activeRun = null;
        showAppNotice("info", "Активный запуск не найден", "Сервер не подтверждает прежний запуск. Можно загрузить его последний снимок или запустить анализ вручную.");
      }
    }
  } catch (error) {
    health = null;
    text("api-status", "Локальный API недоступен");
    text("analysis-status", message(error) + " Импорт отчёта остаётся доступен.");
  } finally {
    connecting = false; updateControls(); modeHint(); chatHint();
  }
  if (resume && activeRun && health && !polling) await pollRun(activeRun);
}
async function loadSnapshot(expectedId = null, source = "Сохранённый снимок сервера") {
  const payload = await api.report();
  if (expectedId !== null && payload.report_id !== expectedId) {
    throw new Error("На сервере уже другой снимок. Загрузите последний отчёт отдельно; он не будет выдан за результат этого запуска.");
  }
  await displaySnapshot(payload, source);
  if (source !== "Текущий прогон") showAppNotice("success", "Снимок сервера загружен", "Открыт сохранённый отчёт сервера. Теперь можно задавать вопросы об этом снимке.");
}
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function pollRun(id) {
  if (polling) return;
  polling = true; updateControls();
  const deadline = Date.now() + 330000;
  try {
    while (activeRun === id) {
      const run = await api.run(id);
      if (run.state === "completed") {
        activeRun = null;
        await loadSnapshot(run.report_id, "Текущий прогон");
        text("analysis-status", "Анализ завершён. Показан проверенный отчёт этого запуска.");
        showAppNotice("success", "Анализ завершён", "Результат расчёта получен от локального сервера. Реальные рассылки не выполнялись.");
        return;
      }
      if (run.state === "failed") {
        activeRun = null;
        text("analysis-status", "Анализ завершился ошибкой. " + (run.error?.message || "Повторите запуск."));
        showAppNotice("error", "Не удалось завершить анализ", "Предыдущий отчёт, если он был открыт, остаётся сохранённым. " + (run.error?.message || ""));
        return;
      }
      text("analysis-status", "Анализ выполняется · расчёт и проверка кампаний. Ожидаем результат сервера.");
      if (Date.now() >= deadline) throw new Error("Ожидание статуса затянулось. Проверьте соединение; повторный анализ пока заблокирован.");
      await pause(1500);
    }
  } catch (error) {
    if (error?.status === 404) activeRun = null;
    text("analysis-status", message(error) + (activeRun
      ? " Нажмите «Проверить подключение», чтобы продолжить наблюдение за тем же запуском."
      : " Можно отдельно загрузить последний снимок сервера или проверить подключение."));
    showAppNotice("error", "Не удалось получить результат", "Новый запуск не отправлен повторно. Сохранённый открытый отчёт не изменён.");
  } finally { polling = false; updateControls(); }
}
$("run-analysis").addEventListener("click", async () => {
  if (activeRun || !health) return;
  const rawSeed = $("run-seed").value.trim();
  const seed = Number(rawSeed);
  if (!rawSeed || !Number.isInteger(seed) || seed < 0 || seed > 4294967295) {
    text("analysis-status", "Seed должен быть целым числом от 0 до 4294967295.");
    $("run-seed").focus(); return;
  }
  // Disable immediately: a second click must not start a duplicate calculation.
  activeRun = "pending";
  clearAnswer(); updateControls();
  text("analysis-status", "Передаём запуск локальному серверу…");
  try {
    const run = await api.startRun({mode:selectedMode(), seed});
    activeRun = run.run_id;
  } catch (error) {
    if (!error?.status || (error.status >= 200 && error.status < 300)) {
      activeRun = "unconfirmed";
      text("analysis-status", "Исход отправки неизвестен. Проверяем состояние сервера без повторного запуска…");
      await refreshHealth({resume:true});
      if (activeRun === "unconfirmed") text("analysis-status", "Не удалось подтвердить исход отправки. Проверьте подключение; повторный запуск заблокирован.");
      updateControls(); return;
    }
    activeRun = null;
    text("analysis-status", message(error));
    if (error?.status === 409) {
      await refreshHealth({resume:true});
      return;
    }
    if (error?.status === 503) {
      await refreshHealth({resume:false});
      text("analysis-status", message(error) + " Выберите доступный режим и повторите действие.");
    }
    updateControls(); return;
  }
  await pollRun(activeRun);
});
$("analysis-mode").addEventListener("change", () => { modeHint(); updateControls(); });
$("retry-api")?.addEventListener("click", () => refreshHealth());
$("load-server-report")?.addEventListener("click", async () => {
  $("load-server-report").disabled = true;
  text("agent-status", "Загружаем снимок сервера…");
  try { await loadSnapshot(); }
  catch (error) {
    text("agent-status", message(error));
    showAppNotice("error", "Не удалось загрузить снимок", message(error) + " Открытый отчёт не изменён.");
  } finally { updateControls(); }
});

function evidenceTarget(ref, report) {
  if (!report || typeof ref !== "string") return null;
  if (["evaluation", "resources", "planned_resources"].includes(ref) && report[ref]) {
    return ref === "evaluation" ? "evaluation.net_arpu_gain" : ref;
  }
  const pilot = /^pilots\.(\d+)$/.exec(ref);
  if (pilot && Number(pilot[1]) < report.pilots.length) return "pilots[" + Number(pilot[1]) + "]";
  const allocation = /^allocation\.(\d+)$/.exec(ref);
  if (allocation && report.allocation?.[Number(allocation[1])]) {
    const row = report.allocation[Number(allocation[1])];
    const matches = report.campaigns.map((campaign, index) => ({campaign,index}))
      .filter(({campaign}) => findAllocation(campaign, report.allocation) === row);
    if (matches.length === 1) return "campaigns[" + matches[0].index + "]";
  }
  return null;
}
$("ask-agent").addEventListener("click", async () => {
  if (!snapshotId || chatBusy || activeRun || !health) return;
  const question = $("agent-question").value.trim();
  if (!question || question.length > 2000) {
    text("agent-status", "Введите вопрос от 1 до 2000 символов."); $("agent-question").focus(); return;
  }
  const askedSnapshot = snapshotId;
  const generation = reportGeneration;
  const sequence = ++chatSequence;
  chatBusy = true;
  text("agent-answer", ""); $("agent-evidence").replaceChildren();
  text("agent-mode", "Ожидаем фактический режим ответа");
  text("agent-status", "Агент готовит ответ по текущему отчёту…");
  updateControls();
  try {
    const answer = await api.chat({report_id:askedSnapshot, message:question});
    if (generation !== reportGeneration || sequence !== chatSequence || snapshotId !== askedSnapshot) return;
    text("agent-answer", answer.answer);
    text("agent-mode", answer.mode === "openai" ? "Ответ OpenAI" : "Автономный ответ");
    text("agent-status", answer.warnings?.length ? answer.warnings.join(" · ") : "Ответ получен. Откройте доказательства, чтобы проверить объяснение.");
    for (const citation of answer.citations) {
      const target = evidenceTarget(citation.ref, getCurrentReport());
      const node = document.createElement(target ? "button" : "span");
      node.textContent = citation.label || citation.ref;
      node.className = target ? "evidence-link" : "evidence-unavailable";
      if (target) { node.type = "button"; node.addEventListener("click", () => focusEvidence(target)); }
      else node.textContent += " · ссылка недоступна";
      $("agent-evidence").append(node);
    }
  } catch (error) {
    if (generation !== reportGeneration || sequence !== chatSequence) return;
    text("agent-mode", "Ответ не получен");
    text("agent-status", message(error));
  } finally { chatBusy = false; updateControls(); }
});
updateControls();
refreshHealth();
