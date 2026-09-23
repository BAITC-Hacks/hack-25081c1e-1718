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
let chatReportId = null;
let chatTurns = [];
let knownRunId = null;
let previousRunId = null;

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
  $("agent-question").disabled = !snapshotId || !!activeRun;
  $("chat-clear").disabled = chatBusy || !chatTurns.length;
  document.querySelectorAll(".chat-retry").forEach(button => { button.disabled = chatBusy || !!activeRun || !health?.capabilities.chat; });
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
function clearConversation() {
  chatSequence++;
  chatTurns = [];
  $("chat-messages").replaceChildren($("chat-empty"));
  $("chat-empty").hidden = false;
  $("agent-question").value = "";
  updateDraft();
  text("agent-mode", "По текущему отчёту");
}
function chatHint() {
  const report = getCurrentReport();
  text("chat-source", !report ? "Отчёт не выбран" : !snapshotId ? "Отчёт из файла · доступен для просмотра" : `Кампаний: ${report.campaigns.length} · пилотов: ${report.pilots.length}`);
  if (!report) text("agent-status", "Запустите анализ или загрузите отчёт сервера, чтобы задать вопрос.");
  else if (!snapshotId) text("agent-status", "Для вопросов нужен отчёт сервера. Загрузите его кнопкой выше или запустите анализ.");
  else if (!health) text("agent-status", "Для ответа нужен локальный API. Открытый отчёт сохранён.");
  else text("agent-status", "Каждый вопрос рассматривается отдельно, по текущему отчёту.");
}
document.addEventListener("arpu:report-loaded", () => {
  if (!serverImport) snapshotId = null;
  if (!serverImport || chatReportId !== snapshotId) {
    reportGeneration++; clearConversation();
  }
  chatReportId = snapshotId;
  chatHint(); updateControls();
});
document.addEventListener("arpu:report-cleared", () => {
  reportGeneration++; snapshotId = null; chatReportId = null; clearConversation(); chatHint(); updateControls();
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
      if (activeRun === "unconfirmed" && health.run.run_id === previousRunId && health.run.state !== "running") {
        activeRun = null;
        showAppNotice("info", "Новый запуск не подтверждён", "Сервер показывает предыдущий расчёт. Можно загрузить его отчёт или вручную повторить запуск.");
      } else if (health.run.state === "running" || (activeRun && health.run.state !== "idle")) {
        activeRun = health.run.run_id;
      } else if (activeRun && health.run.state === "idle") {
        activeRun = null;
        showAppNotice("info", "Активный запуск не найден", "Сервер не подтверждает прежний запуск. Можно загрузить его последний снимок или запустить анализ вручную.");
      }
    }
    knownRunId = health.run.run_id;
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
  previousRunId = knownRunId;
  updateControls();
  text("analysis-status", "Передаём запуск локальному серверу…");
  try {
    const run = await api.startRun({mode:selectedMode(), seed});
    activeRun = run.run_id;
    knownRunId = run.run_id;
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
function updateDraft() {
  text("chat-count", `${$("agent-question").value.length} / 2000`);
}
function chatNode(className, value, tag = "div") {
  const node = document.createElement(tag);
  node.className = className;
  if (value !== undefined) node.textContent = value;
  return node;
}
function scrollConversation() {
  $("chat-messages").scrollTop = $("chat-messages").scrollHeight;
}
document.addEventListener("arpu:view-changed", event => {
  if (event.detail.view === "ask") requestAnimationFrame(scrollConversation);
});
window.addEventListener("resize", () => {
  if (!$("ask").hidden) requestAnimationFrame(scrollConversation);
});
function addTurn(question) {
  const user = chatNode("chat-message is-user");
  user.append(chatNode("message-meta", "Вы"), chatNode("message-body", question));
  const assistant = chatNode("chat-message is-assistant");
  const turn = {question, reportId:snapshotId, user, assistant};
  chatTurns.push(turn);
  // Local page memory only. Bound long sessions without discarding the current turn.
  if (chatTurns.length > 20) {
    const oldest = chatTurns.shift(); oldest.user.remove(); oldest.assistant.remove();
  }
  $("chat-empty").hidden = true;
  $("chat-messages").append(user, assistant);
  return turn;
}
async function askQuestion(turn) {
  if (!snapshotId || chatBusy || activeRun || !health?.capabilities.chat || turn.reportId !== snapshotId) return;
  const askedSnapshot = snapshotId;
  const generation = reportGeneration;
  const sequence = ++chatSequence;
  chatBusy = true;
  turn.assistant.classList.add("is-pending");
  turn.assistant.replaceChildren(chatNode("message-meta", "Compass"), chatNode("message-body", "Изучаю данные отчёта…"));
  turn.assistant.setAttribute("aria-busy", "true");
  text("agent-mode", "Готовит ответ");
  text("agent-status", "Агент готовит ответ по текущему отчёту…");
  updateControls(); scrollConversation();
  try {
    const answer = await api.chat({report_id:askedSnapshot, message:turn.question});
    if (generation !== reportGeneration || sequence !== chatSequence || snapshotId !== askedSnapshot) return;
    const label = answer.mode === "openai" ? "OpenAI" : "Автономный ответ";
    turn.assistant.replaceChildren(chatNode("message-meta", `Compass · ${label}`), chatNode("message-body", answer.answer));
    const evidence = chatNode("message-evidence");
    for (const citation of answer.citations) {
      const target = evidenceTarget(citation.ref, getCurrentReport());
      const node = document.createElement(target ? "button" : "span");
      node.textContent = citation.label || citation.ref;
      node.className = target ? "evidence-link" : "evidence-unavailable";
      if (target) { node.type = "button"; node.addEventListener("click", () => focusEvidence(target)); }
      else node.textContent += " · ссылка недоступна";
      evidence.append(node);
    }
    if (evidence.childElementCount) turn.assistant.append(evidence);
    if (answer.warnings?.length) turn.assistant.append(chatNode("message-warning", answer.warnings.join(" · ")));
    text("agent-mode", label);
    text("agent-status", "Ответ готов. Ссылки под ним открывают данные отчёта.");
  } catch (error) {
    if (generation !== reportGeneration || sequence !== chatSequence || snapshotId !== askedSnapshot) return;
    turn.assistant.replaceChildren(chatNode("message-meta", "Compass · ответ не получен"), chatNode("message-warning", message(error)));
    const retry = chatNode("button button-secondary chat-retry", "Повторить вопрос", "button");
    retry.type = "button";
    retry.addEventListener("click", () => askQuestion(turn));
    turn.assistant.append(retry);
    text("agent-mode", "Ответ не получен");
    text("agent-status", "Вопрос сохранён. Повторите его кнопкой в сообщении.");
  } finally {
    turn.assistant.classList.remove("is-pending");
    turn.assistant.removeAttribute("aria-busy");
    chatBusy = false; updateControls(); scrollConversation();
  }
}
$("chat-form").addEventListener("submit", event => {
  event.preventDefault();
  if (!snapshotId || chatBusy || activeRun || !health?.capabilities.chat) return;
  const question = $("agent-question").value.trim();
  if (!question || question.length > 2000) {
    text("agent-status", "Введите вопрос от 1 до 2000 символов."); $("agent-question").focus(); return;
  }
  const turn = addTurn(question);
  $("agent-question").value = ""; updateDraft();
  askQuestion(turn);
});
$("agent-question").addEventListener("input", updateDraft);
$("agent-question").addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault(); $("chat-form").requestSubmit();
  }
});
$("chat-clear").addEventListener("click", () => {
  if (chatBusy) return;
  clearConversation(); chatHint(); updateControls(); $("agent-question").focus();
});
updateControls();
updateDraft();
chatHint();
refreshHealth();
