import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  MISSING, CAMPAIGN_COLUMNS, parseReport, validateReport, number, money, ratio,
  findAllocation, campaignsToCsv, campaignMatches, channelLabel, translate,
  TARIFF_CATALOG, tariffInfo, tariffLabel, segmentInfo,
} from "./report.mjs";

const minimal = () => ({ schema_version: "1.0", engine: "test-offline", campaigns: [], pilots: [], resources: {} });
const validCampaign = () => ({ campaign_name: "compass_a", target_tariff: "tariff_8", channel: "push" });

test("minimal v1 report is valid and does not invent optional metrics", () => {
  const report = parseReport(JSON.stringify(minimal()));
  assert.equal(report.evaluation, undefined);
  assert.equal(report.planned_resources, undefined);
  assert.equal(number(report.resources.remaining_contacts), MISSING);
  assert.equal(money(report.evaluation?.net_arpu_gain), MISSING);
  assert.equal(ratio(null), MISSING);
  assert.notEqual(money(0), MISSING);
  assert.equal(number(0), "0");
  assert.equal(ratio(0), "0 %");
});

test("UTF-8 BOM is accepted but invalid JSON, versions, and shapes are rejected", () => {
  assert.deepEqual(parseReport(`\uFEFF${JSON.stringify(minimal())}`), minimal());
  assert.throws(() => parseReport("{broken"), /JSON/);
  assert.throws(() => parseReport("null"), /JSON-объектом/);
  assert.throws(() => parseReport("[]"), /JSON-объектом/);
  assert.throws(() => validateReport({ ...minimal(), schema_version: "2.0" }), /Версия/);
  for (const [field, value] of [["campaigns", {}], ["pilots", null], ["resources", []], ["engine", ""]]) {
    assert.throws(() => validateReport({ ...minimal(), [field]: value }), new RegExp(field));
  }
});

test("known metric types are strict; null and missing stay unknown", () => {
  for (const invalid of ["0", false, {}, Infinity, NaN]) {
    assert.throws(() => validateReport({ ...minimal(), resources: { remaining_budget: invalid } }), /resources.remaining_budget/);
    assert.throws(() => validateReport({ ...minimal(), evaluation: { net_arpu_gain: invalid } }), /evaluation.net_arpu_gain/);
  }
  assert.throws(() => parseReport('{"schema_version":"1.0","engine":"test","campaigns":[],"pilots":[],"resources":{"remaining_budget":1e999}}'), /конечное число/);
  assert.doesNotThrow(() => validateReport({ ...minimal(), resources: { remaining_budget: null, remaining_contacts: 0 } }));
  assert.throws(() => validateReport({ ...minimal(), allocation: [{ audience_size: "100" }] }), /allocation\[0\].audience_size/);
  assert.throws(() => validateReport({ ...minimal(), pilots: [{ observed_lift_ratio: "0.2" }] }), /observed_lift_ratio/);
});

test("campaign required strings and optional nested report fields are checked", () => {
  assert.doesNotThrow(() => validateReport({ ...minimal(), campaigns: [validCampaign()] }));
  assert.throws(() => validateReport({ ...minimal(), campaigns: [{ channel: "push" }] }), /target_tariff/);
  assert.throws(() => validateReport({ ...minimal(), campaigns: [{ ...validCampaign(), filter_arpu_segment: 5 }] }), /filter_arpu_segment/);
  assert.throws(() => validateReport({ ...minimal(), pilots: [{ filters: "segment" }] }), /filters/);
  assert.throws(() => validateReport({ ...minimal(), advisor: [{ summary: { html: true } }] }), /summary/);
  assert.throws(() => validateReport({ ...minimal(), warnings: [null] }), /warnings/);
  assert.throws(() => validateReport({ ...minimal(), warnings: Array(1001).fill("") }), /1 000/);
  assert.doesNotThrow(() => validateReport({ ...minimal(), pilots: [{ status: "failed", channel: "push" }], warnings: ["new_warning_code"] }));
});

test("quality diagnostics remain optional but known fields reject malformed values", () => {
  const report = {
    ...minimal(),
    selection_diagnostics: {
      generated_candidates: 5, tested_candidates: 1, tested_variants: 1,
      confirmed_variants: 1, selected_variants: 1, unexplored_candidates: 4,
      reason_counts: {selected: 1},
      variants: [{candidate_id: "c_a", channel: "sms", repeats: 2, conservative_net: -10,
        selected: true, reason: "selected", pilot_refs: ["pilots.0", "pilots.1"]}],
      strategy_config: {exploration_policy: "baseline", uncertainty_mode: "template"},
    },
    forecast_summary: {scope: "final_campaigns_only", estimated_net: 100, conservative_net: 80,
      communication_cost: 20, campaign_count: 1, comparison_to_evaluation: "not_comparable"},
    allocation: [{candidate_id: "c_a", template_uncertainty: .04, sample_std: null,
      empirical_se: .02, uncertainty_method: "template_floor", pilot_refs: null}],
  };
  assert.doesNotThrow(() => validateReport(report));
  assert.doesNotThrow(() => validateReport({...report, future_optional_field: {unknown: true}}));
  assert.throws(() => validateReport({...report, selection_diagnostics: {...report.selection_diagnostics, tested_variants: "1"}}), /tested_variants/);
  assert.throws(() => validateReport({...report, selection_diagnostics: {...report.selection_diagnostics, generated_candidates: -1.5}}), /generated_candidates/);
  assert.throws(() => validateReport({...report, selection_diagnostics: {...report.selection_diagnostics, reason_counts: {selected: -3}}}), /reason_counts.selected/);
  assert.throws(() => validateReport({...report, selection_diagnostics: {...report.selection_diagnostics, reason_counts: {selected: "1"}}}), /reason_counts.selected/);
  assert.throws(() => validateReport({...report, selection_diagnostics: {...report.selection_diagnostics,
    variants: [{...report.selection_diagnostics.variants[0], pilot_refs: [0]}]}}), /pilot_refs/);
  assert.throws(() => validateReport({...report, selection_diagnostics: {...report.selection_diagnostics,
    variants: [{...report.selection_diagnostics.variants[0], repeats: -2}]}}), /repeats/);
  assert.throws(() => validateReport({...report, forecast_summary: {...report.forecast_summary, estimated_net: Infinity}}), /estimated_net/);
  assert.throws(() => validateReport({...report, forecast_summary: {...report.forecast_summary, campaign_count: -4.5}}), /campaign_count/);
  assert.throws(() => validateReport({...report, allocation: [{sample_std: "0.1"}]}), /sample_std/);
  assert.throws(() => validateReport({...report, selection_diagnostics: {...report.selection_diagnostics,
    variants: Array(21).fill(report.selection_diagnostics.variants[0])}}), /selection_diagnostics.variants/);
  assert.throws(() => validateReport({...report, selection_diagnostics: {...report.selection_diagnostics,
    variants: [{...report.selection_diagnostics.variants[0], pilot_refs: Array(21).fill("pilots.0")}]}}), /pilot_refs/);
});

test("allocation only joins unambiguous matching identities and channels", () => {
  const campaign = validCampaign();
  const allocation = { candidate_id: "a", channel: "push", communication_cost: 0 };
  assert.equal(findAllocation(campaign, [allocation]), allocation);
  assert.equal(findAllocation(campaign, [{ ...allocation, channel: "sms" }]), null);
  assert.equal(findAllocation(campaign, [{ ...allocation, candidate_id: "b" }]), null);
  assert.equal(findAllocation(campaign, [allocation, { ...allocation }]), null);
  assert.equal(findAllocation(campaign, [{ communication_cost: 123 }]), null);
  assert.equal(findAllocation({ ...campaign, candidate_id: "different" }, [allocation]), null);
  assert.equal(findAllocation({ campaign_name: "same", candidate_id: "a", channel: "push" }, [
    { campaign_name: "same", candidate_id: "b", channel: "push", estimated_net: 999 },
  ]), null);
  const named = { campaign_name: "legacy-campaign", channel: "push" };
  assert.equal(findAllocation(named, [named]), named);
  assert.equal(findAllocation(named, [{ ...named, candidate_id: "unknown" }]), null);
});

test("channel and status labels treat prototype-shaped strings as ordinary data", () => {
  for (const name of ["constructor", "__proto__", "toString"]) {
    assert.equal(channelLabel(name), name);
    assert.equal(translate(name), name);
  }
  assert.equal(channelLabel("push"), "Push-уведомление");
  assert.equal(channelLabel("digital_ads"), "Цифровая реклама");
  assert.equal(channelLabel(null), MISSING);
  assert.equal(translate("offline_mode"), "Автономный режим");
});

test("CSV quotes commas, quotes and line breaks, neutralizes formulas, and excludes unknown columns", () => {
  const csv = campaignsToCsv([{
    campaign_name: '=HYPERLINK("https://invalid.example")',
    filter_current_tariff: "tariff_1,tariff_2",
    filter_arpu_segment: "MID\nHIGH",
    filter_data_segment: 'LITE"HEAVY',
    filter_call_segment: " \t@formula",
    target_tariff: "tariff_8", channel: "push", private_field: "SHOULD_NOT_EXPORT",
  }]);
  assert.ok(csv.startsWith("\uFEFF"));
  assert.equal(csv.slice(1).split("\r\n")[0], CAMPAIGN_COLUMNS.map((key) => `"${key}"`).join(","));
  assert.ok(csv.includes('"\'=HYPERLINK(""https://invalid.example"")"'));
  assert.ok(csv.includes('"tariff_1,tariff_2"'));
  assert.ok(csv.includes('"MID\nHIGH"'));
  assert.ok(csv.includes('"LITE""HEAVY"'));
  assert.ok(csv.includes('"\' \t@formula"'));
  assert.ok(!csv.includes("private_field"));
  assert.ok(!csv.includes("SHOULD_NOT_EXPORT"));
  for (const formula of ["+SUM(A1)", "-1+1", "\tformula", "\rformula", "\nformula", "\u0000=1"]) {
    assert.ok(campaignsToCsv([{ ...validCampaign(), campaign_name: formula }]).includes(`"'${formula}"`));
  }
});

test("campaign search uses displayed campaign fields and exact channel", () => {
  const campaign = { ...validCampaign(), filter_current_tariff: "tariff_4", filter_arpu_segment: "MID" };
  assert.equal(campaignMatches(campaign, " TARIFF_4 ", "push"), true);
  assert.equal(campaignMatches(campaign, "MID", "sms"), false);
  assert.equal(campaignMatches(campaign, "unknown", ""), false);
  assert.equal(campaignMatches(campaign, "8 ГБ", ""), true);
  assert.equal(campaignMatches(campaign, "средний доход", ""), true);
});

test("display tariff catalog stays equal to the public source, including fractional monthly prices", () => {
  const rows = readFileSync(new URL("../tariff_dictionary.csv", import.meta.url), "utf8").trim().split(/\r?\n/).slice(1);
  assert.equal(Object.keys(TARIFF_CATALOG).length, rows.length);
  for (const line of rows) {
    // The five fixed numeric/code columns precede the free-form CSV description.
    const [mb, minutes, sharedMinutes, price, code] = line.split(",").slice(0, 5);
    assert.deepEqual(TARIFF_CATALOG[code], {mb:+mb, minutes:+minutes, sharedMinutes:+sharedMinutes, price:+price});
  }
  assert.match(tariffInfo("tariff_4").price, /4\s678,6/);
});

test("tariff presentation preserves distinct identities, shared minutes, alternatives and unknowns", () => {
  assert.notEqual(tariffInfo("tariff_5").name, tariffInfo("tariff_8").name);
  assert.equal(tariffInfo("tariff_5").package, tariffInfo("tariff_8").package);
  assert.match(tariffInfo("tariff_12").description, /300 минут на других операторов и городские номера \(общий пакет\)/);
  assert.doesNotMatch(tariffInfo("tariff_12").package, /600/);
  assert.match(tariffInfo("tariff_1").price, /Без абонентской платы/);
  assert.match(tariffInfo("tariff_1").description, /не включён/);
  assert.match(tariffLabel("tariff_4; tariff_8"), /Тариф №4.* или Тариф №8/);
  assert.equal(tariffLabel(undefined), "Любой текущий тариф");
  for (const code of ["tariff_99", "constructor", "__proto__"]) assert.equal(tariffInfo(code).price, MISSING);
  assert.match(segmentInfo("filter_data_segment", "LITE").description, /2 000 МБ/);
  assert.match(segmentInfo("filter_call_segment", "MEDIUM").description, /100 до 400 минут/);
  assert.match(segmentInfo("filter_arpu_segment", "MEDIUM").label, /Неизвестный/);
  assert.match(segmentInfo("constructor", "HIGH").label, /Неизвестный/);
});
