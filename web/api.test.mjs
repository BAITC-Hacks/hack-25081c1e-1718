import test from "node:test";
import assert from "node:assert/strict";
import { ApiError, createApiClient } from "./api.mjs";
import { setLanguage } from "./i18n.mjs";

const health = (token = "session-token") => ({
  api_version: "1.0", status: "ok", csrf_token: token,
  openai: { configured: false, enabled: false, model: "gpt-4.1-mini-2025-04-14" },
  run: { run_id: null, state: "idle" }, capabilities: { run: true, chat: true },
});
const report = () => ({ schema_version: "1.0", engine: "test-fixture", campaigns: [], pilots: [], resources: {} });
const run = (changes = {}) => ({ run_id: "run-A:42", state: "running", stage: "evaluating", mode: "offline", seed: 42, started_at: "2026-09-23T10:00:00Z", finished_at: null, report_id: null, error: null, ...changes });
const chat = (changes = {}) => ({ report_id: "snapshot-A", answer: "Фактический результат доступен в отчёте.", mode: "offline", citations: [{ ref: "evaluation", label: "Итог" }], warnings: ["OpenAI не настроен."], usage: { input_tokens: 0, output_tokens: 0 }, ...changes });
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json; charset=utf-8" } });
const expectCode = (code, status) => (error) => error instanceof ApiError && error.code === code && (status === undefined || error.status === status);

function clientFor(replies, options = {}) {
  const calls = [];
  const client = createApiClient({
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      assert.ok(replies.length, `Unexpected fetch ${url}`);
      const reply = replies.shift();
      return typeof reply === "function" ? reply(url, init) : reply;
    }, ...options,
  });
  return { client, calls };
}

test("same-origin requests keep token in client and only submit the allowed run fields", async () => {
  const { client, calls } = clientFor([json(health()), json({ run_id: "run-A:42", state: "running" }, 202)]);
  assert.deepEqual(await client.startRun({ mode: "offline", seed: 42, key: "not-sent" }), { run_id: "run-A:42", state: "running" });
  assert.equal(calls[0].url, "/api/health");
  assert.equal(calls[1].url, "/api/runs");
  assert.equal(calls[1].init.headers["X-ARPU-Token"], "session-token");
  assert.equal(calls[1].init.headers["Content-Type"], "application/json");
  assert.deepEqual(JSON.parse(calls[1].init.body), { mode: "offline", seed: 42 });
  assert.equal(calls[1].init.credentials, "same-origin");
  assert.equal(calls[1].init.cache, "no-store");
  assert.equal(calls[1].init.redirect, "error");
  assert.equal(Object.keys(client).includes("csrfToken"), false);
});

test("403 refreshes health once and requires a manual retry, never a duplicate paid POST", async () => {
  const { client, calls } = clientFor([
    json(health("old-token")), json({ error: { code: "invalid_token", message: "Token expired" } }, 403),
    json(health("new-token")), json(chat()),
  ]);
  await client.health();
  await assert.rejects(client.chat({ report_id: "snapshot-A", message: "Почему?" }), expectCode("csrf_refresh_required", 403));
  assert.equal(calls.filter((call) => call.init.method === "POST").length, 1);
  assert.equal(calls.length, 3);
  await client.chat({ report_id: "snapshot-A", message: "Почему?" });
  assert.equal(calls[3].init.headers["X-ARPU-Token"], "new-token");
});

test("a failed refresh after 403 stays a clear non-retried authorization error", async () => {
  const { client, calls } = clientFor([json(health()), new Response("Forbidden", { status: 403 }), () => { throw new TypeError("offline"); }]);
  await assert.rejects(client.startRun(), expectCode("csrf_refresh_required", 403));
  assert.equal(calls.length, 3);
  assert.equal(calls.filter((call) => call.init.method === "POST").length, 1);
});

test("static HTML, invalid JSON, unknown API versions, invalid booleans and oversized responses fail explicitly", async () => {
  const cases = [
    [new Response("<html>404</html>", { status: 404, headers: { "Content-Type": "text/html" } }), "api_unavailable"],
    [new Response("{no", { headers: { "Content-Type": "application/json" } }), "invalid_json"],
    [json({ ...health(), api_version: "2.0" }), "invalid_response"],
    [json({ ...health(), openai: { ...health().openai, enabled: "false" } }), "invalid_response"],
    [json({ ...health(), csrf_token: "line\nbreak" }), "invalid_response"],
    [new Response("{}", { headers: { "Content-Type": "application/json", "Content-Length": "20000000" } }), "invalid_response"],
  ];
  for (const [response, code] of cases) {
    await assert.rejects(clientFor([response]).client.health(), expectCode(code));
  }
});

test("typed server errors retain status and stable code without exposing malformed payloads", async () => {
  const { client } = clientFor([json({ error: { code: "no_report", message: "Отчёт ещё не создан." } }, 404)]);
  await assert.rejects(client.report(), (error) => expectCode("no_report", 404)(error) && error.message === "Отчёт ещё не создан.");
  const bad = clientFor([json({ error: { code: { raw: "provider" }, message: "raw-secret" } }, 500)]);
  await assert.rejects(bad.client.report(), (error) => expectCode("http_error", 500)(error) && !error.message.includes("raw-secret"));
});

test("report snapshots require an ID and a valid report; optional provenance survives", async () => {
  const payload = { report_id: "snapshot-A", report: { ...report(), provenance: { git_sha: "example" } } };
  assert.deepEqual(await clientFor([json(payload)]).client.report(), payload);
  await assert.rejects(clientFor([json({ report_id: "snapshot-A", report: { ...report(), schema_version: "9" } })]).client.report(), expectCode("invalid_report"));
  await assert.rejects(clientFor([json({ report_id: null, report: report() })]).client.report(), expectCode("invalid_response"));
});

test("opaque run IDs are encoded and each status must belong to the requested run", async () => {
  const opaqueId = "run:A/seed?42#local";
  const { client, calls } = clientFor([json(run({ run_id: opaqueId }))]);
  await client.run(opaqueId);
  assert.equal(calls[0].url, `/api/runs/${encodeURIComponent(opaqueId)}`);
  await assert.rejects(clientFor([json(run({ run_id: "another" }))]).client.run("run-A:42"), expectCode("invalid_response"));
});

test("run statuses distinguish fresh success, failure and an unfinished calculation", async () => {
  const complete = run({ state: "completed", stage: "ready", finished_at: "2026-09-23T10:01:00.123Z", report_id: "snapshot-A" });
  const failed = run({ state: "failed", stage: "failed", finished_at: "2026-09-23T10:01:00Z", error: { code: "run_failed", message: "Расчёт завершился ошибкой." } });
  for (const payload of [run(), complete, failed, run({started_at:"2026-09-23T10:00:00+00:00"})]) assert.deepEqual(await clientFor([json(payload)]).client.run(payload.run_id), payload);
  for (const payload of [run({ report_id: "old-report" }), { ...complete, report_id: null }, { ...failed, report_id: "old-report" }, run({ started_at: "yesterday" }), run({ seed: -1 })]) {
    await assert.rejects(clientFor([json(payload)]).client.run(payload.run_id), expectCode("invalid_response"));
  }
});

test("chat verifies snapshot identity, preserves safe text and retains unknown evidence references for rendering", async () => {
  const payload = chat({ answer: "<img src=x onerror=alert(1)>", citations: [{ ref: "future.section", label: "<script>text</script>" }] });
  const { client } = clientFor([json(health()), json(payload)]);
  assert.deepEqual(await client.chat({ report_id: "snapshot-A", message: "Вопрос" }), payload);
  const wrong = clientFor([json(health()), json(chat({ report_id: "snapshot-B" }))]);
  await assert.rejects(wrong.client.chat({ report_id: "snapshot-A", message: "Вопрос" }), expectCode("invalid_response"));
});

test("chat validates actual mode, answer, citation/warning bounds and measured usage", async () => {
  for (const changes of [
    { answer: "" }, { answer: "a".repeat(20001) }, { mode: "pretend-openai" },
    { citations: [{ ref: "evaluation", label: 3 }] }, { citations: Array(101).fill({ ref: "evaluation", label: "Итог" }) },
    { warnings: [4] }, { usage: { input_tokens: -1, output_tokens: 0 } },
  ]) {
    const { client } = clientFor([json(health()), json(chat(changes))]);
    await assert.rejects(client.chat({ report_id: "snapshot-A", message: "Вопрос" }), expectCode("invalid_response"));
  }
});

test("invalid input never reaches the API, including path segments and excessive messages", async () => {
  const { client, calls } = clientFor([]);
  for (const invalid of ["", "..", "bad id", "line\nbreak", "a".repeat(257), null]) await assert.rejects(client.run(invalid), expectCode("invalid_input"));
  for (const invalid of [-1, 4294967296, 1.2, "42", NaN]) await assert.rejects(client.startRun({ seed: invalid }), expectCode("invalid_input"));
  await assert.rejects(client.startRun({ mode: "mock" }), expectCode("invalid_input"));
  for (const message of ["", "   ", "a".repeat(2001), 1]) await assert.rejects(client.chat({ report_id: "snapshot-A", message }), expectCode("invalid_input"));
  await assert.rejects(client.chat({ report_id: "", message: "Вопрос" }), expectCode("invalid_input"));
  assert.equal(calls.length, 0);
});

test("timeout covers fetch and body reading and aborts the request without auto retry", async () => {
  let signal;
  const pendingFetch = createApiClient({ timeoutMs: 5, fetchImpl: async (_url, init) => { signal = init.signal; return new Promise(() => {}); } });
  await assert.rejects(pendingFetch.health(), expectCode("timeout", 0));
  assert.equal(signal.aborted, true);
  const pendingBody = createApiClient({ timeoutMs: 5, fetchImpl: async () => ({ status: 200, ok: true, headers: new Headers({ "content-type": "application/json" }), text: () => new Promise(() => {}) }) });
  await assert.rejects(pendingBody.health(), expectCode("timeout", 0));
});

test("network failure becomes a safe ApiError and concurrent health checks share a request", async () => {
  const failed = createApiClient({ fetchImpl: async () => { throw new Error("secret internal URL"); } });
  await assert.rejects(failed.health(), (error) => expectCode("network_error", 0)(error) && !error.message.includes("secret"));
  const { client, calls } = clientFor([json(health())]);
  const values = await Promise.all([client.health(), client.health()]);
  assert.deepEqual(values[0], values[1]);
  assert.equal(calls.length, 1);
});

test("chat language is sent only after the server advertises it; legacy RU keeps its exact payload", async () => {
  const legacy = clientFor([json(health()), json(chat())]);
  await legacy.client.chat({report_id:"snapshot-A", message:"Вопрос", language:"ru"});
  assert.deepEqual(JSON.parse(legacy.calls[1].init.body), {report_id:"snapshot-A", message:"Вопрос"});
  const bilingualHealth = {...health(), capabilities:{run:true, chat:true, chat_languages:["ru","kk"]}};
  const bilingual = clientFor([json(bilingualHealth), json(chat({answer:"Есеп бойынша жауап.", language:"kk"}))]);
  const response = await bilingual.client.chat({report_id:"snapshot-A", message:"Сұрақ", language:"kk"});
  assert.equal(response.language,"kk");
  assert.equal(response.answer,"Есеп бойынша жауап.");
  assert.deepEqual(JSON.parse(bilingual.calls[1].init.body), {report_id:"snapshot-A", message:"Сұрақ", language:"kk"});
  const unsupported = clientFor([json(health())]);
  await assert.rejects(unsupported.client.chat({report_id:"snapshot-A",message:"Сұрақ",language:"kk"}),expectCode("language_unavailable"));
  assert.equal(unsupported.calls.filter(call=>call.init.method==="POST").length,0);
});

test("language schema permits legacy/future capabilities but rejects malformed capabilities and answer language", async () => {
  for (const languages of ["ru,kk", ["ru",42], ["ru","ru"], ["invalid language"], Array(17).fill("ru")]) {
    const {client} = clientFor([json({...health(),capabilities:{run:true,chat:true,chat_languages:languages}})]);
    await assert.rejects(client.health(),expectCode("invalid_response"));
  }
  const future = clientFor([json({...health(),capabilities:{run:true,chat:true,chat_languages:["ru","kk","en"]}})]);
  assert.deepEqual((await future.client.health()).capabilities.chat_languages,["ru","kk","en"]);
  const malformed = clientFor([json(health()),json(chat({language:"pretend-kazakh"}))]);
  await assert.rejects(malformed.client.chat({report_id:"snapshot-A",message:"Вопрос"}),expectCode("invalid_response"));
  const badInput = clientFor([]);
  await assert.rejects(badInput.client.chat({report_id:"snapshot-A",message:"Вопрос",language:"en"}),expectCode("invalid_input"));
  assert.equal(badInput.calls.length,0);
});

test("local API errors follow KK/RU while raw server messages remain unmodified", async () => {
  try {
    setLanguage("kk");
    const badInput = clientFor([]);
    await assert.rejects(badInput.client.run(""), error => error instanceof ApiError && error.message === "Іске қосу идентификаторы дұрыс емес." && error.source === "Некорректный идентификатор запуска.");
    const failure = clientFor([json({error:{code:"no_report",message:"Оригинальное сообщение сервера."}},404)]);
    await assert.rejects(failure.client.report(), error => error.message === "Оригинальное сообщение сервера." && error.serverMessage === true);
  } finally {setLanguage("ru");}
  const badInput = clientFor([]);
  await assert.rejects(badInput.client.run(""), error => error.message === "Некорректный идентификатор запуска.");
});
