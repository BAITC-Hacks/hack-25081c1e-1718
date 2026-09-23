"""Unit checks for the pure Russian/Kazakh report localization layer."""

import copy
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from report_localization import SUPPORTED_LANGUAGES, localize_response, query_for_facts
from report_assistant import _offline_answer, _scope_context, _project


class ReportLocalizationTests(unittest.TestCase):
    def test_supported_languages_and_russian_identity(self):
        self.assertEqual(SUPPORTED_LANGUAGES, ("ru", "kk"))
        response = {"answer": "Кампания 1: 12 345.", "citations": [{"ref": "pilots.16", "label": "Пилоты"}],
                    "warnings": ["invalid_message"]}
        result = localize_response(response, "ru")
        self.assertEqual(result, response)
        self.assertIsNot(result, response)
        result["citations"][0]["label"] = "changed"
        self.assertEqual(response["citations"][0]["label"], "Пилоты")

    def test_kazakh_query_keeps_original_and_maps_campaign_ordinals(self):
        result = query_for_facts("Бірінші және екінші науқанның болжамы қандай?", "kk")
        self.assertEqual(result["original_message"], "Бірінші және екінші науқанның болжамы қандай?")
        self.assertEqual(result["message"], result["original_message"])
        self.assertIn("первая", result["routing_message"])
        self.assertIn("вторая", result["routing_message"])
        self.assertIn("кампания", result["routing_message"])
        self.assertEqual(result["intent"], "forecast")

    def test_kazakh_query_maps_all_major_intents(self):
        examples = {
            "Қанша гипотеза зерттелді?": "research",
            "Бюджет пен ресурстар қанша қалды?": "resources",
            "Қай арналар таңдалды?": "channels",
            "Пилоттар қанша болды?": "pilots",
            "Тәуекел мен белгісіздік қандай?": "risk",
            "Нәтиже қандай?": "result",
        }
        for message, intent in examples.items():
            self.assertEqual(query_for_facts(message, "kk")["intent"], intent, message)

    def test_kazakh_campaign_routing_scopes_both_numbers(self):
        report = {"allocation": [
            {"candidate_id": "c1", "channel": "sms", "audience_size": 10, "communication_cost": 40,
             "conservative_net": 100, "target_tariff": "tariff_1", "pilot_refs": ["pilots.0"]},
            {"candidate_id": "c2", "channel": "sms", "audience_size": 20, "communication_cost": 80,
             "conservative_net": 200, "target_tariff": "tariff_2", "pilot_refs": ["pilots.1"]}],
            "pilots": [], "evaluation": {"net_arpu_gain": 300}}
        context, refs = _project(report)
        query = query_for_facts("Бірінші және екінші науқанның болжамы қандай?", "kk")
        scoped, _ = _scope_context(context, refs, query["routing_message"])
        self.assertEqual(scoped["scope"]["numbers"], [1, 2])

        for text in ("1-науқан қалай таңдалды?", "2-ші науқан неге таңдалмаған?", "Белгісіздік қандай?"):
            routing = query_for_facts(text, "kk")["routing_message"]
            self.assertIn("кампания", routing.lower()) if "науқан" in text else None

    def test_all_canonical_answer_branches_translate_numeric_values_and_refs(self):
        answers = [
            "Кампания 1: охват 1 234, расходы 560 у. е., осторожный прогноз прироста 7 890 у. е. Номера пилотов: 17, 18.",
            "Создано гипотез: 299; исследовано собственными пилотами: 8. Вариантов с каналом исследовано: 10; выбрано: 3.",
            "Прогноз прироста выручки за вычетом расходов на коммуникации для финальных кампаний: 1 234 ден. ед.; осторожная оценка: 900 ден. ед.",
            "После пилотов осталось: бюджет — 71 200, контакты — 11 400, пилоты — 0.",
            "Для выбранных каналов в плане указаны: кампания 1, SMS: пилотов 2, осторожная оценка прироста 500 у. е.",
            "Кампаний в плане: 3. Кампания 1: тариф №8, охват 543.",
            "В отчёте есть 20 записей пилотов, из них завершённых: 20.",
            "Риск оценивается по наблюдаемым пилотам и разбросу результатов; причинный эффект по одному историческому числу не подтверждается.",
            "Прирост выручки за вычетом расходов на коммуникации в этом синтетическом прогоне: 685 150 ден. ед.",
            "В доступном отчёте нет фактов, чтобы надёжно ответить на этот вопрос.",
        ]
        for answer in answers:
            response = {"answer": answer, "citations": [{"ref": "pilots.16", "label": "Пилоты"}],
                        "warnings": ["OpenAI недоступен: использован offline-ответ по отчёту"]}
            result = localize_response(response, "kk")
            self.assertIn("pilots.16", result["citations"][0]["ref"])
            self.assertIn("17", result["answer"], answer) if "17" in answer else None
            self.assertNotIn("OpenAI недоступен", result["warnings"][0])
            self.assertNotEqual(result["answer"], answer)

    def test_real_offline_answers_keep_all_numbers_and_refs(self):
        report = {
            "allocation": [{"candidate_id": "c1", "channel": "digital_ads", "audience_size": 543,
                            "communication_cost": 11946, "conservative_net": 382847, "estimated_net": 461250,
                            "target_tariff": "tariff_8", "repeats": 2, "pilot_refs": ["pilots.16", "pilots.17"]}],
            "pilots": [{"candidate_id": "c1", "channel": "digital_ads", "status": "completed",
                        "n_customers": 200, "observed_lift_ratio": 0.2},
                       {"candidate_id": "c1", "channel": "digital_ads", "status": "completed",
                        "n_customers": 200, "observed_lift_ratio": 0.21}],
            "resources": {"remaining_budget": 71200, "remaining_contacts": 11400, "pilots_left": 0},
            "planned_resources": {"remaining_budget": 53402, "remaining_contacts": 9394},
            "selection_diagnostics": {"generated_candidates": 299, "tested_candidates": 8,
                                      "tested_variants": 10, "confirmed_variants": 6, "selected_variants": 1,
                                      "reason_counts": {"insufficient_pilots": 4, "nonpositive_estimate": 2}},
            "forecast_summary": {"scope": "final_campaigns_only", "estimated_net": 461250,
                                 "conservative_net": 382847, "communication_cost": 11946},
            "evaluation": {"net_arpu_gain": 685150, "n_pilots": 20, "n_campaigns_including_pilots": 21},
        }
        queries = ["Кампания 1", "Сколько гипотез исследовано?", "Какой прогноз?", "Какие ресурсы?",
                   "Какие каналы?", "Сколько пилотов?", "Какой риск?", "Какой результат?", "Что известно?"]
        for query in queries:
            russian = _offline_answer(report, query, ["OpenAI недоступен: использован offline-ответ по отчёту"])
            kazakh = localize_response(russian, "kk")
            self.assertEqual(re.findall(r"\d+(?:[ ,.]*\d+)*", russian["answer"]),
                             re.findall(r"\d+(?:[ ,.]*\d+)*", kazakh["answer"]), query)
            self.assertEqual([row["ref"] for row in russian["citations"]],
                             [row["ref"] for row in kazakh["citations"]], query)
            self.assertNotIn("у. е.", kazakh["answer"])
            self.assertNotIn("п. п.", kazakh["answer"])
            self.assertNotIn("Кампания", kazakh["answer"])
            self.assertNotIn("Пилоты", kazakh["answer"])

    def test_kazakh_grammar_regressions_keep_values(self):
        response = {"answer": "Вариантов с каналом исследовано: 10; с двумя завершёнными пилотами: 6. "
                              "Наблюдаемый прирост от 18.4% до 23.4%. Эвристический запас неопределённости — "
                              "3.6 п. п.; Метод: шаблонный порог.", "citations": [], "warnings": []}
        answer = localize_response(response, "kk")["answer"]
        self.assertIn("Арнасы бар", answer)
        self.assertIn("екі аяқталған сынағы бар", answer)
        self.assertIn("бақыланған өсім: 18.4%–23.4%", answer)
        self.assertIn("3.6 пайыздық тармақ.", answer)
        self.assertNotIn("ақша бірл..", answer)

    def test_metadata_translation_without_touching_model_answer(self):
        response = {"answer": "Model answer: keep this exact sentence 42.",
                    "citations": [{"ref": "selection_diagnostics", "label": "Исследование"},
                                  {"ref": "forecast_summary", "label": "Прогноз плана"}],
                    "warnings": ["invalid_message"]}
        original = copy.deepcopy(response)
        result = localize_response(response, "kk", translate_answer=False)
        self.assertEqual(result["answer"], original["answer"])
        self.assertEqual([row["ref"] for row in result["citations"]],
                         ["selection_diagnostics", "forecast_summary"])
        self.assertEqual([row["label"] for row in result["citations"]], ["Зерттеу", "Жоспар болжамы"])
        self.assertEqual(result["warnings"], ["Есеп бойынша сұрақты нақтылаңыз."])
        self.assertEqual(response, original)

    def test_invalid_language_is_rejected(self):
        with self.assertRaises(ValueError):
            query_for_facts("test", "en")
        with self.assertRaises(ValueError):
            localize_response({}, "en")


if __name__ == "__main__":
    unittest.main()
