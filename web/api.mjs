import { MAX_FILE_BYTES, validateReport } from "./report.mjs";
import { registerMessages, t } from "./i18n.mjs";

registerMessages({
  "Сервер вернул ответ неподдерживаемого формата. Обновите подключение и попробуйте ещё раз.": "Сервер қолдау көрсетілмейтін пішімде жауап берді. Қосылымды жаңартып, қайталап көріңіз.",
  "Снимок сервера не прошёл проверку отчёта версии 1.0. Предыдущий отчёт можно открыть из файла.": "Сервердегі есеп 1.0 нұсқасының тексеруінен өтпеді. Алдыңғы есепті файлдан ашуға болады.",
  "В этом браузере недоступно подключение к серверу.": "Бұл браузерде серверге қосылу мүмкін емес.",
  "Некорректное время ожидания сервера.": "Серверді күту уақыты дұрыс көрсетілмеген.",
  "Сервер не ответил вовремя. Проверьте подключение перед повтором действия.": "Сервер уақытында жауап бермеді. Әрекетті қайталамас бұрын қосылымды тексеріңіз.",
  "Локальный API недоступен. Запустите сервер Tariflow; импорт файла доступен без подключения.": "Жергілікті API қолжетімсіз. Tariflow серверін іске қосыңыз; файлды қосылымсыз импорттауға болады.",
  "Подключение к серверу изменилось.": "Серверге қосылым өзгерді.",
  "По этому адресу API недоступен. Запустите локальный сервер или откройте сохранённый report.json.": "Бұл мекенжайда API қолжетімсіз. Жергілікті серверді іске қосыңыз немесе сақталған report.json файлын ашыңыз.",
  "Не удалось получить полный ответ сервера. Проверьте подключение.": "Сервердің толық жауабын алу мүмкін болмады. Қосылымды тексеріңіз.",
  "Ответ сервера не удалось прочитать как JSON. Обновите подключение и попробуйте ещё раз.": "Сервер жауабын JSON ретінде оқу мүмкін болмады. Қосылымды жаңартып, қайталап көріңіз.",
  "Сервер не выполнил запрос (HTTP {status}). Попробуйте ещё раз.": "Сервер сұрауды орындамады (HTTP {status}). Қайталап көріңіз.",
  "Запрос превышает допустимые 16 КиБ.": "Сұрау рұқсат етілген 16 КиБ көлемінен асады.",
  "Подключение обновлено. Повторите действие вручную; запрос не был отправлен повторно.": "Қосылым жаңартылды. Әрекетті өзіңіз қайталаңыз; сұрау қайта жіберілген жоқ.",
  "Доступ к серверу изменился. Обновите подключение и повторите действие вручную.": "Серверге қолжетімділік өзгерді. Қосылымды жаңартып, әрекетті өзіңіз қайталаңыз.",
  "Выберите автономный режим или OpenAI.": "Автономды режимді немесе OpenAI таңдаңыз.",
  "Seed должен быть целым числом от 0 до 4294967295.": "Seed 0 мен 4294967295 аралығындағы бүтін сан болуы керек.",
  "Некорректный идентификатор запуска.": "Іске қосу идентификаторы дұрыс емес.",
  "Для вопроса нужен сохранённый на сервере отчёт.": "Сұрақ қою үшін серверде сақталған есеп қажет.",
  "Введите вопрос длиной до 2000 символов.": "Ұзындығы 2000 таңбадан аспайтын сұрақ енгізіңіз.",
  "Выберите русский или казахский язык ответа.": "Жауап тілін таңдаңыз: орысша немесе қазақша.",
  "Сервер пока не поддерживает ответы на выбранном языке.": "Сервер таңдалған тілде жауап беруді әзірге қолдамайды.",
});

const MAX_REQUEST_BYTES = 16 * 1024;
const MAX_RESPONSE_BYTES = MAX_FILE_BYTES + 16 * 1024;
const encoder = new TextEncoder();
const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const string = (value, max, empty = false) => typeof value === "string" && value.length <= max && (empty || value.trim().length > 0);
const mode = (value) => value === "offline" || value === "openai";
const seed = (value) => Number.isInteger(value) && value >= 0 && value <= 4294967295;
const count = (value) => Number.isSafeInteger(value) && value >= 0 && value <= 1_000_000_000;
const id = (value) => string(value, 256) && value.trim() === value && !/[\s\u0000-\u001f\u007f]/u.test(value) && value !== "." && value !== "..";
const timestamp = (value) => string(value, 64) && /^\d{4}-\d{2}-\d{2}T.*(?:Z|\+00:00)$/.test(value) && Number.isFinite(Date.parse(value));
const serverError = (value) => object(value) && typeof value.code === "string" && /^[a-z][a-z0-9_]{0,79}$/.test(value.code) && string(value.message, 2000);

export class ApiError extends Error {
  constructor(code, message, status = 0, params = {}, serverMessage = false) {
    super(serverMessage ? message : t(message, params));
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.source = message;
    this.params = params;
    this.serverMessage = serverMessage;
  }
}

function assertResponse(condition, status = 200) {
  if (!condition) throw new ApiError("invalid_response", "Сервер вернул ответ неподдерживаемого формата. Обновите подключение и попробуйте ещё раз.", status);
}

function assertInput(condition, message) {
  if (!condition) throw new ApiError("invalid_input", message);
}

function checkHealth(value) {
  assertResponse(object(value) && value.api_version === "1.0" && value.status === "ok");
  assertResponse(typeof value.csrf_token === "string" && /^[\x21-\x7e]{1,512}$/.test(value.csrf_token));
  assertResponse(object(value.openai) && typeof value.openai.configured === "boolean" && typeof value.openai.enabled === "boolean" && string(value.openai.model, 200));
  assertResponse(object(value.capabilities) && typeof value.capabilities.run === "boolean" && typeof value.capabilities.chat === "boolean");
  if (value.capabilities.chat_languages !== undefined) {
    const languages = value.capabilities.chat_languages;
    assertResponse(Array.isArray(languages) && languages.length <= 16 && new Set(languages).size === languages.length && languages.every(language => typeof language === "string" && /^[a-z]{2}(?:-[A-Za-z0-9]{2,8})*$/.test(language) && language.length <= 32));
  }
  assertResponse(object(value.run) && ["idle", "running", "completed", "failed"].includes(value.run.state));
  assertResponse(value.run.state === "idle" ? value.run.run_id === null : id(value.run.run_id));
  return value;
}

function checkReport(value) {
  assertResponse(object(value) && id(value.report_id));
  try {
    validateReport(value.report);
  } catch {
    throw new ApiError("invalid_report", "Снимок сервера не прошёл проверку отчёта версии 1.0. Предыдущий отчёт можно открыть из файла.", 200);
  }
  return value;
}

function checkRun(value, requestedId) {
  assertResponse(object(value) && id(value.run_id) && value.run_id === requestedId);
  assertResponse(["running", "completed", "failed"].includes(value.state) && mode(value.mode) && seed(value.seed) && timestamp(value.started_at));
  if (value.state === "running") {
    assertResponse(value.stage === "evaluating" && value.finished_at === null && value.report_id === null && value.error === null);
  } else if (value.state === "completed") {
    assertResponse(value.stage === "ready" && timestamp(value.finished_at) && id(value.report_id) && value.error === null);
  } else {
    assertResponse(value.stage === "failed" && timestamp(value.finished_at) && value.report_id === null && serverError(value.error));
  }
  return value;
}

function checkChat(value, reportId) {
  assertResponse(object(value) && id(value.report_id) && value.report_id === reportId);
  assertResponse(string(value.answer, 20000) && mode(value.mode));
  if (value.language !== undefined) assertResponse(value.language === "ru" || value.language === "kk");
  assertResponse(Array.isArray(value.citations) && value.citations.length <= 100 && value.citations.every((citation) => object(citation) && string(citation.ref, 256) && string(citation.label, 500)));
  assertResponse(Array.isArray(value.warnings) && value.warnings.length <= 100 && value.warnings.every((warning) => string(warning, 2000)));
  assertResponse(object(value.usage) && count(value.usage.input_tokens) && count(value.usage.output_tokens));
  return value;
}

/** Same-origin only. The CSRF token is private to this instance and never persisted. */
export function createApiClient({ fetchImpl = globalThis.fetch, timeoutMs = 15000 } = {}) {
  assertInput(typeof fetchImpl === "function", "В этом браузере недоступно подключение к серверу.");
  assertInput(Number.isFinite(timeoutMs) && timeoutMs > 0 && timeoutMs <= 300000, "Некорректное время ожидания сервера.");
  let csrfToken = null;
  let healthInFlight = null;
  let chatLanguages = null;

  async function request(path, { method = "GET", body, expectedStatus = 200 } = {}) {
    const controller = new AbortController();
    let timer;
    const headers = { Accept: "application/json" };
    if (method === "POST") {
      headers["Content-Type"] = "application/json";
      headers["X-ARPU-Token"] = csrfToken;
    }
    const timeout = new Promise((_, reject) => {
      timer = setTimeout(() => {
        controller.abort();
        reject(new ApiError("timeout", "Сервер не ответил вовремя. Проверьте подключение перед повтором действия."));
      }, timeoutMs);
    });
    try {
      return await Promise.race([timeout, (async () => {
        let response;
        try {
          // Browsers set Origin themselves; do not imitate it or accept remote URLs.
          response = await fetchImpl(path, { method, headers, body, signal: controller.signal, credentials: "same-origin", cache: "no-store", redirect: "error" });
        } catch {
          throw new ApiError("network_error", "Локальный API недоступен. Запустите сервер Tariflow; импорт файла доступен без подключения.");
        }
        if (response.status === 403 && method === "POST") {
          throw new ApiError("csrf_expired", "Подключение к серверу изменилось.", 403);
        }
        const contentType = response.headers.get("content-type") || "";
        if (!/^application\/json(?:\s*;|$)/i.test(contentType)) {
          throw new ApiError("api_unavailable", "По этому адресу API недоступен. Запустите локальный сервер или откройте сохранённый report.json.", response.status);
        }
        const contentLength = response.headers.get("content-length");
        if (contentLength && Number(contentLength) > MAX_RESPONSE_BYTES) assertResponse(false, response.status);
        let raw;
        try { raw = await response.text(); } catch { throw new ApiError("network_error", "Не удалось получить полный ответ сервера. Проверьте подключение.", response.status); }
        assertResponse(encoder.encode(raw).byteLength <= MAX_RESPONSE_BYTES, response.status);
        let data;
        try { data = JSON.parse(raw); } catch { throw new ApiError("invalid_json", "Ответ сервера не удалось прочитать как JSON. Обновите подключение и попробуйте ещё раз.", response.status); }
        if (!response.ok) {
          if (object(data) && serverError(data.error)) throw new ApiError(data.error.code, data.error.message, response.status, {}, true);
          throw new ApiError("http_error", "Сервер не выполнил запрос (HTTP {status}). Попробуйте ещё раз.", response.status, {status:response.status});
        }
        assertResponse(response.status === expectedStatus, response.status);
        return data;
      })()]);
    } finally {
      clearTimeout(timer);
    }
  }

  async function health() {
    if (!healthInFlight) {
      healthInFlight = (async () => {
        try {
          const value = checkHealth(await request("/api/health"));
          csrfToken = value.csrf_token;
          chatLanguages = value.capabilities.chat_languages ?? null;
          return value;
        } catch (error) {
          csrfToken = null;
          chatLanguages = null;
          throw error;
        } finally {
          healthInFlight = null;
        }
      })();
    }
    return healthInFlight;
  }

  async function post(path, payload, expectedStatus = 200) {
    const body = JSON.stringify(payload);
    assertInput(encoder.encode(body).byteLength <= MAX_REQUEST_BYTES, "Запрос превышает допустимые 16 КиБ.");
    if (!csrfToken) await health();
    try {
      return await request(path, { method: "POST", body, expectedStatus });
    } catch (error) {
      if (error instanceof ApiError && error.status === 403) {
        csrfToken = null;
        let refreshed = false;
        try { await health(); refreshed = true; } catch { /* The original action remains unsubmitted. */ }
        throw new ApiError("csrf_refresh_required", refreshed
          ? "Подключение обновлено. Повторите действие вручную; запрос не был отправлен повторно."
          : "Доступ к серверу изменился. Обновите подключение и повторите действие вручную.", 403);
      }
      throw error;
    }
  }

  return Object.freeze({
    health,
    async report() { return checkReport(await request("/api/report")); },
    async startRun({ mode: requestedMode = "offline", seed: requestedSeed = 42 } = {}) {
      assertInput(mode(requestedMode), "Выберите автономный режим или OpenAI.");
      assertInput(seed(requestedSeed), "Seed должен быть целым числом от 0 до 4294967295.");
      const value = await post("/api/runs", { mode: requestedMode, seed: requestedSeed }, 202);
      assertResponse(object(value) && id(value.run_id) && value.state === "running", 202);
      return value;
    },
    async run(runId) {
      assertInput(id(runId), "Некорректный идентификатор запуска.");
      return checkRun(await request(`/api/runs/${encodeURIComponent(runId)}`), runId);
    },
    async chat({ report_id: reportId, message, language } = {}) {
      assertInput(id(reportId), "Для вопроса нужен сохранённый на сервере отчёт.");
      assertInput(string(message, 2000), "Введите вопрос длиной до 2000 символов.");
      assertInput(language === undefined || language === "ru" || language === "kk", "Выберите русский или казахский язык ответа.");
      if (!csrfToken) await health();
      const payload = { report_id: reportId, message };
      if (language !== undefined && chatLanguages?.includes(language)) payload.language = language;
      else if (language === "kk") throw new ApiError("language_unavailable", "Сервер пока не поддерживает ответы на выбранном языке.");
      return checkChat(await post("/api/chat", payload), reportId);
    },
  });
}
