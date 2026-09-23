import { createApiClient } from "./api.mjs";
import { getCurrentReport, importReport, showAppNotice, focusEvidence } from "./app.mjs";
import { findAllocation } from "./report.mjs";
import { registerMessages, t, getLanguage, setLocalizedText } from "./i18n.mjs";

registerMessages({
  "Не удалось выполнить запрос. Повторите попытку.": "Сұрауды орындау мүмкін болмады. Қайталап көріңіз.",
  "Локальный API недоступен": "Жергілікті API қолжетімсіз",
  "Сервер подключён · ключ OpenAI не настроен": "Сервер қосылған · OpenAI кілті бапталмаған",
  "Сервер подключён · OpenAI выключен на сервере": "Сервер қосылған · серверде OpenAI өшірілген",
  "Сервер подключён · OpenAI настроен": "Сервер қосылған · OpenAI бапталған",
  "Запустите локальный сервер по README или откройте сохранённый report.json.": "README нұсқаулығы бойынша жергілікті серверді іске қосыңыз немесе сақталған report.json файлын ашыңыз.",
  "OpenAI недоступен. Настройте ключ в окружении сервера или выберите автономный режим.": "OpenAI қолжетімсіз. Кілтті сервер ортасында баптаңыз немесе автономды режимді таңдаңыз.",
  "Настройки OpenAI доступны. Успех вызова будет известен после запуска.": "OpenAI баптаулары қолжетімді. Сұраудың сәтті орындалғаны іске қосқаннан кейін белгілі болады.",
  "Автономный анализ работает без запросов к OpenAI.": "Автономды талдау OpenAI сұрауларынсыз жұмыс істейді.",
  "По текущему отчёту": "Ағымдағы есеп бойынша",
  "Отчёт не выбран": "Есеп таңдалмаған",
  "Отчёт из файла · доступен для просмотра": "Файлдағы есеп · қарауға болады",
  "Кампаний: {campaigns} · пилотов: {pilots}": "Науқандар: {campaigns} · сынақтар: {pilots}",
  "Запустите анализ или загрузите отчёт сервера, чтобы задать вопрос.": "Сұрақ қою үшін талдауды іске қосыңыз немесе сервердегі есепті жүктеңіз.",
  "Для вопросов нужен отчёт сервера. Загрузите его кнопкой выше или запустите анализ.": "Сұрақ қою үшін сервердегі есеп қажет. Оны жоғарыдағы батырмамен жүктеңіз немесе талдауды іске қосыңыз.",
  "Для ответа нужен локальный API. Открытый отчёт сохранён.": "Жауап алу үшін жергілікті API қажет. Ашық есеп сақталды.",
  "Каждый вопрос рассматривается отдельно, по текущему отчёту.": "Әр сұрақ ағымдағы есеп бойынша жеке қарастырылады.",
  "Сервер пока отвечает только на русском. Интерфейс переведён; язык ответа агента недоступен.": "Сервер әзірге тек орысша жауап береді. Интерфейс аударылған; агенттің қазақша жауабы әзірге қолжетімсіз.",
  "Проверяем подключение…": "Қосылымды тексеріп жатырмыз…",
  "Новый запуск не подтверждён": "Жаңа іске қосу расталмады",
  "Сервер показывает предыдущий расчёт. Можно загрузить его отчёт или вручную повторить запуск.": "Сервер алдыңғы есептеуді көрсетіп тұр. Оның есебін жүктеуге немесе қайта іске қосуға болады.",
  "Активный запуск не найден": "Орындалып жатқан есептеу табылмады",
  "Сервер не подтверждает прежний запуск. Можно загрузить его последний снимок или запустить анализ вручную.": "Сервер бұрынғы іске қосуды растамайды. Соңғы есепті жүктеуге немесе талдауды өзіңіз іске қосуға болады.",
  "{message} Импорт отчёта остаётся доступен.": "{message} Есепті импорттауға әлі де болады.",
  "Сохранённый снимок сервера": "Серверде сақталған есеп",
  "Текущий прогон": "Ағымдағы есептеу",
  "На сервере уже другой снимок. Загрузите последний отчёт отдельно; он не будет выдан за результат этого запуска.": "Серверде басқа есеп бар. Соңғы есепті бөлек жүктеңіз; ол осы іске қосудың нәтижесі ретінде көрсетілмейді.",
  "Снимок сервера загружен": "Сервердегі есеп жүктелді",
  "Открыт сохранённый отчёт сервера. Теперь можно задавать вопросы об этом снимке.": "Серверде сақталған есеп ашылды. Енді осы есеп туралы сұрақ қоюға болады.",
  "Анализ завершён. Показан проверенный отчёт этого запуска.": "Талдау аяқталды. Осы іске қосудың тексерілген есебі көрсетілді.",
  "Анализ завершён": "Талдау аяқталды",
  "Результат расчёта получен от локального сервера. Реальные рассылки не выполнялись.": "Есептеу нәтижесі жергілікті серверден алынды. Нақты хабарламалар жіберілген жоқ.",
  "Анализ завершился ошибкой. {message}": "Талдау қатемен аяқталды. {message}",
  "Повторите запуск.": "Қайта іске қосыңыз.",
  "Не удалось завершить анализ": "Талдауды аяқтау мүмкін болмады",
  "Предыдущий отчёт, если он был открыт, остаётся сохранённым. {message}": "Бұрын ашылған есеп сақталады. {message}",
  "Анализ выполняется · расчёт и проверка кампаний. Ожидаем результат сервера.": "Талдау орындалуда · науқандар есептеліп, тексерілуде. Сервер нәтижесін күтіп отырмыз.",
  "Ожидание статуса затянулось. Проверьте соединение; повторный анализ пока заблокирован.": "Күйді күту ұзаққа созылды. Қосылымды тексеріңіз; талдауды қайта іске қосу әзірге бұғатталған.",
  "{message} Нажмите «Проверить подключение», чтобы продолжить наблюдение за тем же запуском.": "{message} Осы іске қосуды бақылауды жалғастыру үшін «Қосылымды тексеру» батырмасын басыңыз.",
  "{message} Можно отдельно загрузить последний снимок сервера или проверить подключение.": "{message} Сервердегі соңғы есепті бөлек жүктеуге немесе қосылымды тексеруге болады.",
  "Не удалось получить результат": "Нәтижені алу мүмкін болмады",
  "Новый запуск не отправлен повторно. Сохранённый открытый отчёт не изменён.": "Жаңа іске қосу қайта жіберілген жоқ. Ашық сақталған есеп өзгермеді.",
  "Передаём запуск локальному серверу…": "Іске қосу сұрауын жергілікті серверге жіберіп жатырмыз…",
  "Исход отправки неизвестен. Проверяем состояние сервера без повторного запуска…": "Жіберу нәтижесі белгісіз. Қайта іске қоспай, сервер күйін тексеріп жатырмыз…",
  "Не удалось подтвердить исход отправки. Проверьте подключение; повторный запуск заблокирован.": "Жіберу нәтижесін растау мүмкін болмады. Қосылымды тексеріңіз; қайта іске қосу бұғатталған.",
  "{message} Выберите доступный режим и повторите действие.": "{message} Қолжетімді режимді таңдап, әрекетті қайталаңыз.",
  "Загружаем снимок сервера…": "Сервердегі есепті жүктеп жатырмыз…",
  "Загружаем отчёт": "Есеп жүктелуде",
  "Получаем последний сохранённый снимок сервера.": "Серверде сақталған соңғы есепті алып жатырмыз.",
  "Не удалось загрузить снимок": "Есепті жүктеу мүмкін болмады",
  "{message} Открытый отчёт не изменён.": "{message} Ашық есеп өзгермеді.",
  "Вы": "Сіз",
  "Изучаю данные отчёта…": "Есеп деректерін зерттеп жатырмын…",
  "Готовит ответ": "Жауап дайындалуда",
  "Агент готовит ответ по текущему отчёту…": "Агент ағымдағы есеп бойынша жауап дайындап жатыр…",
  "Автономный ответ": "Автономды жауап",
  "Tariflow · Автономный ответ": "Tariflow · Автономды жауап",
  "Ответ готов. Ссылки под ним открывают данные отчёта.": "Жауап дайын. Оның астындағы сілтемелер есеп деректерін ашады.",
  "Tariflow · ответ не получен": "Tariflow · жауап алынбады",
  "Повторить вопрос": "Сұрақты қайталау",
  "Ответ не получен": "Жауап алынбады",
  "Вопрос сохранён. Повторите его кнопкой в сообщении.": "Сұрақ сақталды. Оны хабарламадағы батырмамен қайталаңыз.",
  "Введите вопрос от 1 до 2000 символов.": "Ұзындығы 1–2000 таңба болатын сұрақ енгізіңіз.",
  "Итог расчёта": "Есептеу нәтижесі",
  "Ресурсы": "Ресурстар",
  "План ресурсов": "Ресурстар жоспары",
  "Кампания {number}": "Науқан {number}",
  "Пилот {number}": "Сынақ {number}",
  "{label} · исходная подпись, ссылка недоступна": "{label} · бастапқы атау, сілтеме қолжетімсіз",
  "{label} · данные сервера": "{label} · сервер деректері",
  "Ответ на русском": "Жауап орыс тілінде",
  "Ответ на казахском": "Жауап қазақ тілінде",
  "Язык ответа не указан сервером": "Сервер жауап тілін көрсетпеді",
  "Сервер пока отвечает только на русском; этот ответ не переведён.": "Сервер әзірге тек орысша жауап береді; бұл жауап аударылған жоқ.",
  "Сообщение сервера: {message}": "Сервер хабарламасы: {message}",
  "Данные сервера": "Сервер деректері",
  "Сохранённого отчёта пока нет. Сначала запустите анализ.": "Сақталған есеп әзірге жоқ. Алдымен талдауды іске қосыңыз.",
  "Выбранный отчёт не найден. Загрузите актуальный снимок сервера.": "Таңдалған есеп табылмады. Сервердегі өзекті есепті жүктеңіз.",
  "Запуск не найден. Проверьте подключение к серверу.": "Іске қосу табылмады. Серверге қосылымды тексеріңіз.",
  "Сервер уже выполняет анализ. Дождитесь его завершения.": "Сервер талдауды орындап жатыр. Оның аяқталуын күтіңіз.",
  "Сервер уже готовит ответ. Дождитесь его завершения.": "Сервер жауап дайындап жатыр. Оның аяқталуын күтіңіз.",
  "OpenAI на сервере недоступен. Выберите автономный режим.": "Серверде OpenAI қолжетімсіз. Автономды режимді таңдаңыз.",
});

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
let snapshotLoading = false;

function localize(node, source, params = {}) {
  // Getters resolve nested localized errors again when i18n refreshes this binding.
  const values = typeof params === "function" ? Object.defineProperties({}, Object.fromEntries(
    Object.keys(params()).map(key => [key, {enumerable:true, get:() => params()[key]}]),
  )) : params;
  setLocalizedText(node, source, values);
}
function text(id, source, params = {}) { const node = $(id); if (node) localize(node, source, params); }
const SERVER_ERROR_MESSAGES = Object.freeze({
  no_report:"Сохранённого отчёта пока нет. Сначала запустите анализ.",
  report_not_found:"Выбранный отчёт не найден. Загрузите актуальный снимок сервера.",
  run_not_found:"Запуск не найден. Проверьте подключение к серверу.",
  run_busy:"Сервер уже выполняет анализ. Дождитесь его завершения.",
  chat_busy:"Сервер уже готовит ответ. Дождитесь его завершения.",
  openai_unavailable:"OpenAI на сервере недоступен. Выберите автономный режим.",
});
function message(error) {
  if (!(error instanceof Error)) return t("Не удалось выполнить запрос. Повторите попытку.");
  if (error.serverMessage && Object.hasOwn(SERVER_ERROR_MESSAGES, error.code)) return t(SERVER_ERROR_MESSAGES[error.code]);
  return error.serverMessage ? t("Сообщение сервера: {message}", {message:error.message}) : t(error.source || error.message, error.params || {});
}
function errorText(id, error, source = "{message}") { text(id, source, () => ({message:message(error)})); }
function notice(kind, title, description = "", params = {}) {
  showAppNotice(kind, t(title), t(description, typeof params === "function" ? params() : params));
  text("status-title", title); text("status-description", description, params);
}
function selectedMode() { return $("analysis-mode").value; }
function canOpenAI() { return !!(health?.openai.configured && health?.openai.enabled); }
function updateControls() {
  const runAllowed = !!health?.capabilities.run && !activeRun && !connecting && !snapshotLoading;
  $("run-analysis").disabled = !runAllowed || (selectedMode() === "openai" && !canOpenAI());
  $("analysis-mode").disabled = !!activeRun;
  $("run-seed").disabled = !!activeRun;
  $("ask-agent").disabled = !health?.capabilities.chat || !snapshotId || chatBusy || !!activeRun || snapshotLoading;
  $("agent-question").disabled = !snapshotId || !!activeRun;
  $("chat-clear").disabled = chatBusy || !chatTurns.length;
  document.querySelectorAll(".chat-retry").forEach(button => { button.disabled = chatBusy || !!activeRun || snapshotLoading || !health?.capabilities.chat; });
  for (const id of ["load-server-report", "load-latest-report"]) {
    if ($(id)) $(id).disabled = !health || !!activeRun || connecting || chatBusy || snapshotLoading;
  }
  if ($("retry-api")) $("retry-api").disabled = connecting || polling;
  refreshLanguageHint();
}
function refreshLanguageHint() {
  let node = $("agent-language-note");
  if (!node) { node = document.createElement("p"); node.id = "agent-language-note"; node.className = "small-note"; $("agent-status").after(node); }
  node.hidden = getLanguage() !== "kk" || !health || !!health.capabilities.chat_languages?.includes("kk");
  localize(node, "Сервер пока отвечает только на русском. Интерфейс переведён; язык ответа агента недоступен.");
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
  text("chat-source", !report ? "Отчёт не выбран" : !snapshotId ? "Отчёт из файла · доступен для просмотра" : "Кампаний: {campaigns} · пилотов: {pilots}", {campaigns:report?.campaigns.length, pilots:report?.pilots.length});
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
        notice("info", "Новый запуск не подтверждён", "Сервер показывает предыдущий расчёт. Можно загрузить его отчёт или вручную повторить запуск.");
      } else if (health.run.state === "running" || (activeRun && health.run.state !== "idle")) {
        activeRun = health.run.run_id;
      } else if (activeRun && health.run.state === "idle") {
        activeRun = null;
        notice("info", "Активный запуск не найден", "Сервер не подтверждает прежний запуск. Можно загрузить его последний снимок или запустить анализ вручную.");
      }
    }
    knownRunId = health.run.run_id;
  } catch (error) {
    health = null;
    text("api-status", "Локальный API недоступен");
    errorText("analysis-status", error, "{message} Импорт отчёта остаётся доступен.");
  } finally {
    connecting = false; updateControls(); modeHint(); chatHint();
  }
  if (resume && activeRun && health && !polling) await pollRun(activeRun);
}
async function loadSnapshot(expectedId = null, source = "Сохранённый снимок сервера", expectedGeneration = null) {
  const payload = await api.report();
  // A file imported while this GET was pending remains the user's latest choice.
  if (expectedGeneration !== null && reportGeneration !== expectedGeneration) return;
  if (expectedId !== null && payload.report_id !== expectedId) {
    throw new Error("На сервере уже другой снимок. Загрузите последний отчёт отдельно; он не будет выдан за результат этого запуска.");
  }
  await displaySnapshot(payload, source);
  if (source !== "Текущий прогон") notice("success", "Снимок сервера загружен", "Открыт сохранённый отчёт сервера. Теперь можно задавать вопросы об этом снимке.");
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
        notice("success", "Анализ завершён", "Результат расчёта получен от локального сервера. Реальные рассылки не выполнялись.");
        return;
      }
      if (run.state === "failed") {
        activeRun = null;
        const failure = () => ({message:run.error?.message ? t("Сообщение сервера: {message}", {message:run.error.message}) : t("Повторите запуск.")});
        text("analysis-status", "Анализ завершился ошибкой. {message}", failure);
        notice("error", "Не удалось завершить анализ", "Предыдущий отчёт, если он был открыт, остаётся сохранённым. {message}", failure);
        return;
      }
      text("analysis-status", "Анализ выполняется · расчёт и проверка кампаний. Ожидаем результат сервера.");
      if (Date.now() >= deadline) throw new Error("Ожидание статуса затянулось. Проверьте соединение; повторный анализ пока заблокирован.");
      await pause(1500);
    }
  } catch (error) {
    if (error?.status === 404) activeRun = null;
    errorText("analysis-status", error, activeRun
      ? "{message} Нажмите «Проверить подключение», чтобы продолжить наблюдение за тем же запуском."
      : "{message} Можно отдельно загрузить последний снимок сервера или проверить подключение.");
    notice("error", "Не удалось получить результат", "Новый запуск не отправлен повторно. Сохранённый открытый отчёт не изменён.");
  } finally { polling = false; updateControls(); }
}
$("run-analysis").addEventListener("click", async () => {
  if (activeRun || !health || snapshotLoading) return;
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
    errorText("analysis-status", error);
    if (error?.status === 409) {
      await refreshHealth({resume:true});
      return;
    }
    if (error?.status === 503) {
      await refreshHealth({resume:false});
      errorText("analysis-status", error, "{message} Выберите доступный режим и повторите действие.");
    }
    updateControls(); return;
  }
  await pollRun(activeRun);
});
$("analysis-mode").addEventListener("change", () => { modeHint(); updateControls(); });
$("retry-api")?.addEventListener("click", () => refreshHealth());
async function openLatestReport() {
  if (snapshotLoading || !health || activeRun || chatBusy) return;
  snapshotLoading = true; updateControls();
  const generation = reportGeneration;
  text("agent-status", "Загружаем снимок сервера…");
  notice("info", "Загружаем отчёт", "Получаем последний сохранённый снимок сервера.");
  try { await loadSnapshot(null, "Сохранённый снимок сервера", generation); }
  catch (error) {
    if (generation !== reportGeneration) return;
    errorText("agent-status", error);
    notice("error", "Не удалось загрузить снимок", "{message} Открытый отчёт не изменён.", () => ({message:message(error)}));
  } finally { snapshotLoading = false; updateControls(); }
}
$("load-server-report")?.addEventListener("click", openLatestReport);
$("load-latest-report")?.addEventListener("click", openLatestReport);

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
function chatNode(className, value, tag = "div", params = {}) {
  const node = document.createElement(tag);
  node.className = className;
  if (value !== undefined) localize(node, value, params);
  return node;
}
function dataNode(className, value) {
  const node = chatNode(className);
  node.textContent = value;
  return node;
}
function citationLabel(ref, target) {
  if (ref === "evaluation") return ["Итог расчёта", {}];
  if (ref === "resources") return ["Ресурсы", {}];
  if (ref === "planned_resources") return ["План ресурсов", {}];
  const campaign = /^campaigns\[(\d+)\]$/.exec(target);
  if (campaign) return ["Кампания {number}", {number:Number(campaign[1]) + 1}];
  const pilot = /^pilots\[(\d+)\]$/.exec(target);
  if (pilot) return ["Пилот {number}", {number:Number(pilot[1]) + 1}];
  return null;
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
  user.append(chatNode("message-meta", "Вы"), dataNode("message-body", question));
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
  if (!snapshotId || chatBusy || activeRun || snapshotLoading || !health?.capabilities.chat || turn.reportId !== snapshotId) return;
  const askedSnapshot = snapshotId;
  const generation = reportGeneration;
  const sequence = ++chatSequence;
  const requestedLanguage = getLanguage();
  const sentLanguage = health.capabilities.chat_languages?.includes(requestedLanguage) ? requestedLanguage : undefined;
  chatBusy = true;
  turn.assistant.classList.add("is-pending");
  turn.assistant.replaceChildren(chatNode("message-meta", "Tariflow"), chatNode("message-body", "Изучаю данные отчёта…"));
  turn.assistant.setAttribute("aria-busy", "true");
  text("agent-mode", "Готовит ответ");
  text("agent-status", "Агент готовит ответ по текущему отчёту…");
  updateControls(); scrollConversation();
  try {
    const payload = {report_id:askedSnapshot, message:turn.question};
    if (sentLanguage) payload.language = sentLanguage;
    const answer = await api.chat(payload);
    if (generation !== reportGeneration || sequence !== chatSequence || snapshotId !== askedSnapshot) return;
    const label = answer.mode === "openai" ? "OpenAI" : "Автономный ответ";
    const answerLanguage = answer.language ?? sentLanguage ?? "ru";
    const languageLabel = answerLanguage === "kk" ? "Ответ на казахском" : answerLanguage === "ru" ? "Ответ на русском" : "Язык ответа не указан сервером";
    turn.assistant.replaceChildren(chatNode("message-meta", "Tariflow · {mode} · {language}", "div", () => ({mode:t(label), language:t(languageLabel)})), dataNode("message-body", answer.answer));
    const evidence = chatNode("message-evidence");
    for (const citation of answer.citations) {
      const target = evidenceTarget(citation.ref, getCurrentReport());
      const node = document.createElement(target ? "button" : "span");
      node.className = target ? "evidence-link" : "evidence-unavailable";
      if (target) {
        const caption = citationLabel(citation.ref, target);
        if (caption) localize(node, caption[0], caption[1]);
        else localize(node, "{label} · данные сервера", {label:citation.label || citation.ref});
        node.type = "button"; node.addEventListener("click", () => focusEvidence(target));
      } else localize(node, "{label} · исходная подпись, ссылка недоступна", {label:citation.label || citation.ref});
      evidence.append(node);
    }
    if (evidence.childElementCount) turn.assistant.append(evidence);
    if (answer.warnings?.length) {
      turn.assistant.append(chatNode("message-warning-label", "Данные сервера"), dataNode("message-warning", answer.warnings.join(" · ")));
    }
    if (requestedLanguage === "kk" && !sentLanguage) turn.assistant.append(chatNode("message-warning", "Сервер пока отвечает только на русском; этот ответ не переведён."));
    text("agent-mode", label);
    text("agent-status", "Ответ готов. Ссылки под ним открывают данные отчёта.");
  } catch (error) {
    if (generation !== reportGeneration || sequence !== chatSequence || snapshotId !== askedSnapshot) return;
    turn.assistant.replaceChildren(chatNode("message-meta", "Tariflow · ответ не получен"), chatNode("message-warning", "{message}", "div", () => ({message:message(error)})));
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
  if (!snapshotId || chatBusy || activeRun || snapshotLoading || !health?.capabilities.chat) return;
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
document.addEventListener("tariflow:language-changed", () => {
  // The shared i18n bindings update system labels. Keep draft, report and answers intact.
  refreshLanguageHint();
});
updateControls();
updateDraft();
chatHint();
refreshHealth();
