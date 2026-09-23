import test from "node:test";
import assert from "node:assert/strict";
import {
  MISSING, CAMPAIGN_COLUMNS, parseReport, validateReport, number, money, ratio,
  findAllocation, campaignsToCsv, campaignMatches, channelLabel, translate,
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
  assert.equal(channelLabel("push"), "Push");
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
});
