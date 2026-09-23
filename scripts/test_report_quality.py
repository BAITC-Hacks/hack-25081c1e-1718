"""Report arithmetic, scope and qualitative OpenAI commentary regression checks."""

import copy
import json
import unittest
import urllib.error
from unittest.mock import patch

import report_assistant as assistant
from scripts.export_report import forecast_summary, validate_selection_diagnostics


def sample_report():
    filters = {"filter_current_tariff": "tariff_1", "filter_arpu_segment": "MID"}
    pilots = [{"candidate_id": "c_a", "channel": "sms", "target_tariff": "tariff_2", "filters": filters,
               "status": "completed", "n_customers": 100, "cost": 400, "observed_lift_ratio": ratio}
              for ratio in (.08, .12)]
    report = {"candidate_count": 5, "evaluation": {"net_arpu_gain": 1400, "status": "PASS"},
              "resources": {"remaining_budget": 99200, "remaining_contacts": 14800, "pilots_left": 18},
              "planned_resources": {"remaining_budget": 98400, "remaining_contacts": 14600},
              "campaigns": [{"campaign_name": "compass_c_a", "channel": "sms", "target_tariff": "tariff_2", **filters}],
              "allocation": [{"candidate_id": "c_a", "channel": "sms", "audience_size": 200,
                              "communication_cost": 800, "estimated_net": 1200, "conservative_net": 900,
                              "posterior_mean": .1, "uncertainty": .04, "repeats": 2, "sample_std": .028,
                              "empirical_se": .02, "template_uncertainty": .04, "uncertainty_method": "max_template_empirical"}],
              "pilots": pilots,
              "selection_diagnostics": {"generated_candidates": 5, "tested_candidates": 1, "tested_variants": 1,
                  "confirmed_variants": 1, "selected_variants": 1, "unexplored_candidates": 4,
                  "reason_counts": {"selected": 1}, "variants": [{"candidate_id": "c_a", "channel": "sms",
                      "repeats": 2, "conservative_net": 900, "selected": True, "reason": "selected",
                      "pilot_refs": ["pilots.0", "pilots.1"]}]}}
    report["forecast_summary"] = forecast_summary(report)
    return report


class ProviderResponse:
    def __init__(self, answer, refs):
        self.payload = {"status": "completed", "usage": {"input_tokens": 123, "output_tokens": 14},
                        "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(
                            {"answer": answer, "refs": refs}, ensure_ascii=False)}]}]}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read(self, *_):
        return json.dumps(self.payload).encode()


class ReportQualityTests(unittest.TestCase):
    def setUp(self):
        self.report = sample_report()

    def test_forecast_scope_and_missing_are_explicit(self):
        result = forecast_summary(self.report)
        self.assertEqual(result["estimated_net"], 1200)
        self.assertEqual(result["scope"], "final_campaigns_only")
        self.assertEqual(result["comparison_to_evaluation"], "not_comparable")
        del self.report["allocation"][0]["estimated_net"]
        self.assertIsNone(forecast_summary(self.report))

    def test_diagnostic_counts_and_source_refs_are_checked(self):
        self.assertTrue(validate_selection_diagnostics(self.report)["valid"])
        broken = copy.deepcopy(self.report)
        broken["selection_diagnostics"]["tested_candidates"] = 2
        self.assertFalse(validate_selection_diagnostics(broken)["valid"])
        broken = copy.deepcopy(self.report)
        broken["selection_diagnostics"]["variants"][0]["pilot_refs"] = ["pilots.19"]
        self.assertFalse(validate_selection_diagnostics(broken)["valid"])

    def test_old_report_omits_diagnostics(self):
        del self.report["selection_diagnostics"]
        self.assertFalse(validate_selection_diagnostics(self.report)["checked"])
        reply = assistant.answer_question(self.report, "Сколько гипотез исследовано?", offline=True)
        self.assertIn("нет диагностики", reply["answer"])
        self.assertEqual(reply["citations"], [])

    def test_legacy_names_pilot_records_and_unprefixed_filters(self):
        self.report["campaigns"][0]["campaign_name"] = "campaign-c_a"
        self.report["pilot_records"] = self.report.pop("pilots")
        for row in self.report["pilot_records"]:
            row["filters"] = {key.removeprefix("filter_"): value for key, value in row["filters"].items()}
        self.report["resources"]["planned_resources_after_final"] = self.report.pop("planned_resources")
        context, refs = assistant._project(self.report)
        self.assertEqual(context["allocation"][0]["pilot_refs"], ["pilots.0", "pilots.1"])
        self.assertEqual(context["allocation"][0]["uncertainty_percentage_points"], 4)
        self.assertEqual(context["planned_resources"]["remaining_budget"], 98400)
        reply = assistant.answer_question(self.report, "Первая кампания", offline=True)
        self.assertIn("Номера пилотов: 1–2", reply["answer"])
        self.assertIn("тариф №2", reply["answer"])

    def test_ambiguous_legacy_identity_does_not_borrow_evidence(self):
        duplicate = dict(self.report["campaigns"][0], campaign_name="campaign-c_a")
        self.report["campaigns"].append(duplicate)
        context, _ = assistant._project(self.report)
        self.assertNotIn("pilot_refs", context["allocation"][0])
        reply = assistant.answer_question(self.report, "Первая кампания", offline=True)
        self.assertIn("Нет однозначного источника", reply["answer"])

    def test_conflicting_legacy_filters_do_not_match(self):
        self.report["pilots"][0]["filters"] = {"filter_current_tariff": "tariff_1", "current_tariff": "tariff_3"}
        context, _ = assistant._project(self.report)
        self.assertEqual(context["allocation"][0]["pilot_refs"], ["pilots.1"])

    def test_campaign_context_excludes_all_global_totals(self):
        context, refs = assistant._project(self.report)
        for question in ("первая кампания", "1-я кампания", "кампания №1"):
            scoped, allowed = assistant._scope_context(context, refs, question)
            self.assertNotIn("evaluation", scoped)
            self.assertNotIn("forecast_summary", scoped)
            self.assertNotIn("selection_diagnostics", scoped)
            self.assertEqual(set(allowed), {"allocation.0", "pilots.0", "pilots.1"})

    def test_unknown_range_is_compact(self):
        reply = assistant.answer_question(self.report, "Сравни кампании 1–999", offline=True)
        self.assertIn("2–999", reply["answer"])
        self.assertLess(len(reply["answer"]), 2000)

    def test_forecast_is_not_reported_as_prediction_error(self):
        reply = assistant.answer_question(self.report, "Каков прогноз и ошибка прогноза?", offline=True)
        self.assertIn("1 200", reply["answer"])
        self.assertIn("не является ошибкой", reply["answer"])
        self.assertEqual(reply["citations"][0]["ref"], "forecast_summary")

    def test_evidence_projection_uses_explicit_percentage_points(self):
        context, _ = assistant._project(self.report)
        value = context["allocation"][0]
        self.assertEqual(value["uncertainty_percentage_points"], 4)
        self.assertEqual(value["empirical_se_percentage_points"], 2)
        self.assertNotIn("uncertainty", value)

    def test_counts_distinguish_hypotheses_from_channels(self):
        reply = assistant.answer_question(self.report, "Сколько гипотез исследовано?", offline=True)
        self.assertIn("Создано гипотез: 5", reply["answer"])
        self.assertIn("Вариантов с каналом", reply["answer"])
        self.assertEqual(reply["citations"][0]["ref"], "selection_diagnostics")

    def test_specific_pilot_and_risk_intents_precede_generic_plan(self):
        risk = assistant.answer_question(self.report, "Какие риски у этого плана?", offline=True)
        self.assertIn("Риск оценивается", risk["answer"])
        pilots = assistant.answer_question(self.report, "На каких пилотах основан финальный план?", offline=True)
        self.assertIn("2 записей пилотов", pilots["answer"])
        self.assertNotIn("Кампаний в плане", pilots["answer"])
        scoped = assistant.answer_question(self.report, "Какие риски у кампании 1?", offline=True)
        self.assertIn("Кампания 1", scoped["answer"])
        self.assertIn("Номера пилотов: 1–2", scoped["answer"])

    def call_provider(self, answer, refs, question="Какой бюджет остался?"):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "local-fixture", "ARPU_OFFLINE": "0"}), \
                patch("urllib.request.urlopen", return_value=ProviderResponse(answer, refs)) as provider:
            reply = assistant.answer_question(self.report, question)
            body = json.loads(provider.call_args.args[0].data)
        return reply, body

    def test_canonical_numbers_and_real_provider_mode(self):
        reply, body = self.call_provider("Ресурсов хватает для сохранения резерва.", ["resources"])
        self.assertEqual(reply["mode"], "openai")
        self.assertIn("99 200", reply["answer"])
        self.assertIn("98 400", reply["answer"])
        self.assertIn("Ресурсов хватает", reply["answer"])
        self.assertEqual(reply["usage"]["input_tokens"], 123)
        facts = json.loads(body["input"][1]["content"][0]["text"])
        self.assertIn("99 200", facts["verified_numeric_summary"])

    def test_unverified_numbers_and_bad_refs_fall_back_with_usage(self):
        for text, refs in (("Осталось 999999 рублей.", ["resources"]), ("Достаточно.", ["pilots.19"])):
            reply, _ = self.call_provider(text, refs)
            self.assertEqual(reply["mode"], "offline")
            self.assertEqual(reply["usage"]["input_tokens"], 123)
            self.assertIn("проверку", reply["warnings"][0])
            self.assertNotIn("999999", reply["answer"])

    def test_provider_errors_never_retry_or_replace_verified_facts(self):
        failures = (TimeoutError(), urllib.error.URLError("fixture"),
                    urllib.error.HTTPError("https://api.openai.com/v1/responses", 401, "fixture", {}, None))
        for failure in failures:
            with patch.dict("os.environ", {"OPENAI_API_KEY": "local-fixture", "ARPU_OFFLINE": "0"}), \
                    patch("urllib.request.urlopen", side_effect=failure) as provider:
                reply = assistant.answer_question(self.report, "Какой бюджет остался?")
            self.assertEqual(provider.call_count, 1)
            self.assertEqual(reply["mode"], "offline")
            self.assertIn("99 200", reply["answer"])
            self.assertTrue(reply["warnings"])

    def test_refusal_and_incomplete_response_keep_usage_and_fall_back(self):
        for kind in ("refusal", "incomplete"):
            response = ProviderResponse("Комментарий", ["resources"])
            if kind == "incomplete":
                response.payload["status"] = "incomplete"
            else:
                response.payload["output"][0]["content"] = [{"type": "refusal", "refusal": "fixture"}]
            with patch.dict("os.environ", {"OPENAI_API_KEY": "local-fixture", "ARPU_OFFLINE": "0"}), \
                    patch("urllib.request.urlopen", return_value=response):
                reply = assistant.answer_question(self.report, "Какой бюджет остался?")
            self.assertEqual(reply["mode"], "offline")
            self.assertEqual(reply["usage"]["input_tokens"], 123)
            self.assertIn("99 200", reply["answer"])

    def test_unit_and_number_guards(self):
        self.assertTrue(assistant._invalid_uncertainty_units("Неопределённость 4,3%"))
        self.assertFalse(assistant._invalid_uncertainty_units("Неопределённость 4,3 п. п., эффект 18%"))
        self.assertTrue(assistant._invalid_pilot_numbers("Пилоты 16 и 17", ["pilots.16", "pilots.17"]))
        self.assertFalse(assistant._invalid_pilot_numbers("Пилоты 17 и 18", ["pilots.16", "pilots.17"]))


    def test_kazakh_unit_and_number_guards(self):
        self.assertTrue(assistant._invalid_uncertainty_units("Белгісіздік 4%"))
        self.assertFalse(assistant._invalid_uncertainty_units("Белгісіздік 4 пайыздық тармақ"))
        self.assertTrue(assistant._invalid_pilot_numbers("Пилоттар 0 және 1", ["pilots.0"]))
        self.assertFalse(assistant._invalid_pilot_numbers("Пилоттар 1 және 2", ["pilots.0", "pilots.1"]))

    def test_kazakh_provider_uses_original_question_and_same_sources(self):
        question = "Бірінші науқанның болжамы қандай?"
        comment = "Пилоттық сынақтар болашақ нәтижеге кепілдік бермейді."
        with patch.dict("os.environ", {"OPENAI_API_KEY": "local-fixture", "ARPU_OFFLINE": "0"}), \
                patch("urllib.request.urlopen", return_value=ProviderResponse(comment, ["allocation.0"])) as provider:
            reply = assistant.answer_question(self.report, question, language="kk")
            body = json.loads(provider.call_args.args[0].data)
        self.assertEqual(reply["mode"], "openai")
        self.assertIn(comment, reply["answer"])
        self.assertIn("Науқан 1", reply["answer"])
        facts = json.loads(body["input"][1]["content"][0]["text"])
        self.assertEqual(facts["question"], question)
        self.assertNotIn("evaluation", facts["report"])
        self.assertNotIn("selection_diagnostics", facts["report"])
        self.assertIn("Науқан 1", facts["verified_numeric_summary"])
        self.assertIn("қазақ тілінде", body["input"][0]["content"][0]["text"])
        self.assertEqual({row["ref"] for row in reply["citations"]}, {"allocation.0", "pilots.0", "pilots.1"})

    def test_kazakh_provider_failure_keeps_localized_facts_and_usage(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "local-fixture", "ARPU_OFFLINE": "0"}), \
                patch("urllib.request.urlopen", return_value=ProviderResponse("Бюджет 999999", ["resources"])):
            reply = assistant.answer_question(self.report, "Бюджет қанша қалды?", language="kk")
        self.assertEqual(reply["mode"], "offline")
        self.assertIn("99 200", reply["answer"])
        self.assertNotIn("999999", reply["answer"])
        self.assertEqual(reply["usage"]["input_tokens"], 123)
        self.assertIn("тексеруден өтпеді", reply["warnings"][0])


if __name__ == "__main__":
    unittest.main()
