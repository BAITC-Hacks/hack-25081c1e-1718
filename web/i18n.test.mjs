import test from "node:test";
import assert from "node:assert/strict";
import {
  getLanguage, getLocale, localizedError, onLanguageChange,
  registerMessages, setLanguage, t,
} from "./i18n.mjs";
import {
  MISSING, FILTER_LABELS, TARIFF_CATALOG, campaignMatches, campaignsToCsv,
  channelLabel, displayText, money, number, parseReport, ratio,
  segmentInfo, tariffInfo, tariffLabel, translate, validateReport,
} from "./report.mjs";

test.beforeEach(() => setLanguage("ru"));
test.afterEach(() => setLanguage("ru"));

const minimal = () => ({schema_version:"1.0", engine:"test-offline", campaigns:[], pilots:[], resources:{}});
const captureError = (callback) => {
  try { callback(); } catch (error) { return error; }
  assert.fail("Expected validation to throw");
};

test("errors resolve the current language when read, including nested report reasons", () => {
  registerMessages({"Тестовая ошибка: {reason}": "Тексеру қатесі: {reason}"});
  const error = localizedError("Тестовая ошибка: {reason}", {reason:() => t("нет данных")});
  const reportError = captureError(() => validateReport({...minimal(), resources:{remaining_budget:"123"}}));
  const jsonError = captureError(() => parseReport("{broken"));
  assert.ok(error instanceof Error);
  const russian = [error.message, reportError.message, jsonError.message];
  assert.match(reportError.message, /resources\.remaining_budget.*конечное число/);

  setLanguage("kk");
  assert.equal(error.message, "Тексеру қатесі: дерек жоқ");
  assert.match(reportError.message, /resources\.remaining_budget.*шекті сан/);
  assert.match(jsonError.message, /JSON файлын/);
  assert.notEqual(jsonError.message, russian[2]);

  setLanguage("ru");
  assert.deepEqual([error.message, reportError.message, jsonError.message], russian);
});

test("unknown labels and raw report text remain exact in either language", () => {
  const raw = '  <b>raw tariff_999 MID {unbound}</b>  ';
  const report = {...minimal(), warnings:[raw], advisor:[{summary:raw}], campaigns:[{
    campaign_name:raw, target_tariff:"tariff_999", channel:"custom-channel", rationale:raw,
  }]};
  const original = structuredClone(report);
  for (const language of ["kk", "ru"]) {
    setLanguage(language);
    assert.equal(t(raw), raw);
    assert.equal(t(null), null);
    assert.equal(displayText(raw), raw);
    assert.equal(translate(raw), raw);
    assert.equal(channelLabel(raw), raw);
    assert.equal(validateReport(report), report);
    assert.deepEqual(parseReport(JSON.stringify(report)), original);
    for (const code of [raw, "constructor", "__proto__"]) {
      assert.ok(tariffInfo(code).name.endsWith(code));
      assert.equal(tariffInfo(code).price, MISSING);
      assert.ok(segmentInfo("filter_arpu_segment", code).label.endsWith(code));
    }
    assert.deepEqual(report, original);
  }
});

test("campaign CSV remains byte-identical with raw codes through RU-KK-RU", () => {
  const campaigns = [{
    campaign_name:'Кампания "A", тест', filter_current_tariff:"tariff_4;tariff_8",
    filter_arpu_segment:"MID", filter_data_segment:"LITE", filter_call_segment:"LOW",
    target_tariff:"tariff_12", channel:"push", rationale:"Unexported source text",
  }];
  const original = structuredClone(campaigns);
  const expected = '\uFEFF"campaign_name","filter_current_tariff","filter_arpu_segment","filter_data_segment","filter_call_segment","target_tariff","channel"\r\n'
    + '"Кампания ""A"", тест","tariff_4;tariff_8","MID","LITE","LOW","tariff_12","push"\r\n';
  for (const language of ["ru", "kk", "ru"]) {
    setLanguage(language);
    assert.deepEqual(Buffer.from(campaignsToCsv(campaigns), "utf8"), Buffer.from(expected, "utf8"));
    assert.deepEqual(campaigns, original);
  }
});

test("numbers, money, ratios and missing values follow the current locale without changing values", () => {
  for (const [language, missing, unit] of [["kk", "дерек жоқ", "ақша бірл."], ["ru", "нет данных", "ден. ед."]]) {
    setLanguage(language);
    // Some browser runtimes lack kk-KZ; getLocale may deliberately use ru-RU there.
    const locale = getLocale();
    assert.equal(MISSING, missing);
    for (const value of [4678.6, -1234.5, 0]) {
      const formatted = new Intl.NumberFormat(locale, {maximumFractionDigits:1}).format(value);
      assert.equal(number(value, 1), formatted);
      assert.equal(money(value, 1), `${formatted} ${unit}`);
    }
    for (const value of [0.125, -0.03125, 0]) {
      assert.equal(ratio(value), new Intl.NumberFormat(locale, {
        style:"percent", maximumFractionDigits:2, signDisplay:"exceptZero",
      }).format(value));
    }
    for (const value of [undefined, null, NaN, Infinity, "0"]) {
      assert.equal(number(value), missing);
      assert.equal(money(value), missing);
      assert.equal(ratio(value), missing);
    }
    assert.notEqual(money(0), missing);
    assert.equal(displayText("  "), missing);
  }
});

test("known tariffs and segments localize and return to RU with original package facts", () => {
  const codes = ["tariff_1", "tariff_4", "tariff_8", "tariff_12"];
  const segments = [["filter_arpu_segment", "MID"], ["filter_data_segment", "LITE"], ["filter_call_segment", "LOW"]];
  const catalog = structuredClone(TARIFF_CATALOG);
  const presentation = () => ({
    tariffs:codes.map(code => tariffInfo(code)), segments:segments.map(([key, value]) => segmentInfo(key, value)),
    alternatives:tariffLabel("tariff_4;tariff_8"), filter:FILTER_LABELS.filter_call_segment,
  });
  const russian = presentation();
  setLanguage("kk");
  assert.equal(tariffInfo("tariff_4").name, "№4 тариф");
  assert.equal(tariffInfo("tariff_8").name, "№8 тариф");
  assert.equal(tariffInfo("tariff_4").package, "4 ГБ · 40 мин");
  assert.equal(tariffInfo("tariff_8").package, "8 ГБ · 80 мин");
  assert.equal(tariffInfo("tariff_4").price, `${money(4678.6, 1)}/ай`);
  assert.equal(tariffInfo("tariff_8").price, `${money(5934.6, 1)}/ай`);
  assert.equal(tariffInfo("tariff_1").price, "Абоненттік төлемсіз");
  assert.match(tariffInfo("tariff_12").description, /300 минут.*ортақ пакет/);
  assert.doesNotMatch(tariffInfo("tariff_12").package, /600/);
  assert.match(tariffLabel("tariff_4;tariff_8"), /№4 тариф.*немесе.*№8 тариф/);
  assert.match(segmentInfo("filter_arpu_segment", "MID").label, /орташа/);
  assert.match(segmentInfo("filter_data_segment", "LITE").description, /2 000 МБ/);
  assert.equal(segmentInfo("filter_call_segment", "LOW").label, "Сирек қоңырау шалады");
  assert.equal(FILTER_LABELS.filter_call_segment, "Қоңыраулар");
  assert.deepEqual(TARIFF_CATALOG, catalog);
  setLanguage("ru");
  assert.deepEqual(presentation(), russian);
});

test("campaign search accepts both languages and raw codes after a language change", () => {
  const campaign = {
    campaign_name:"compass_a", filter_current_tariff:"tariff_4;tariff_8",
    filter_arpu_segment:"MID", filter_data_segment:"LITE", filter_call_segment:"LOW",
    target_tariff:"tariff_12", channel:"push",
  };
  for (const language of ["ru", "kk", "ru"]) {
    setLanguage(language);
    for (const query of ["Сирек қоңырау", "Редко звонят", "орташа", "средний доход", "tariff_8", "8 ГБ"]) {
      assert.equal(campaignMatches(campaign, query, "push"), true, `${language}: ${query}`);
    }
    assert.equal(campaignMatches(campaign, "Редко звонят", "sms"), false);
    assert.equal(campaignMatches(campaign, "absent-segment", ""), false);
  }
});

test("language listeners only run for valid changes and can be removed", () => {
  const changes = [];
  const unsubscribe = onLanguageChange(language => changes.push(language));
  try {
    assert.equal(setLanguage("ru"), false);
    assert.equal(setLanguage("en"), false);
    assert.equal(getLanguage(), "ru");
    assert.equal(setLanguage("kk"), true);
    assert.equal(setLanguage("kk"), false);
    assert.deepEqual(changes, ["kk"]);
    unsubscribe();
    assert.equal(setLanguage("ru"), true);
    assert.deepEqual(changes, ["kk"]);
  } finally { unsubscribe(); }
});
