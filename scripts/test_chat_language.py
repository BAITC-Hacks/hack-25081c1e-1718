"""Real loopback HTTP checks; all replies use offline public-report fixtures."""

import json
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

import server
from scripts.test_report_quality import sample_report


class ChatLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.offline = patch.dict("os.environ", {"ARPU_OFFLINE": "1"})
        cls.offline.start()
        cls.server = server.LocalServer(("127.0.0.1", 0), server.Handler)
        cls.server.app = server.AppState(cls.server.server_address[1])
        cls.base = f"http://127.0.0.1:{cls.server.app.port}"
        cls.report_id = cls.server.app.publish(sample_report())
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.offline.stop()

    def request(self, body=None, token=None):
        headers = {"Content-Type": "application/json", "Origin": self.base,
                   "X-ARPU-Token": token if token is not None else self.server.app.token}
        request = urllib.request.Request(self.base + ("/api/chat" if body else "/api/health"),
            data=json.dumps(body).encode() if body else None, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def test_health_advertises_both_languages(self):
        status, body = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(body["capabilities"]["chat_languages"], ["ru", "kk"])

    def test_legacy_request_stays_russian(self):
        status, body = self.request({"report_id": self.report_id, "message": "Какой бюджет остался?"})
        self.assertEqual(status, 200)
        self.assertIn("После пилотов", body["answer"])
        self.assertIn("99 200", body["answer"])
        self.assertEqual(body["mode"], "offline")

    def test_kazakh_answer_retains_numeric_sources(self):
        status, body = self.request({"report_id": self.report_id, "message": "Қанша бюджет қалды?", "language": "kk"})
        self.assertEqual(status, 200)
        self.assertNotIn("После пилотов", body["answer"])
        self.assertIn("99 200", body["answer"])
        self.assertIn("98 400", body["answer"])
        self.assertEqual([c["ref"] for c in body["citations"]], ["resources", "planned_resources"])
        self.assertEqual(body["mode"], "offline")

    def test_invalid_language_and_unknown_fields_are_rejected(self):
        for language in (None, "en", [], {}, True):
            status, body = self.request({"report_id": self.report_id, "message": "Бюджет?", "language": language})
            self.assertEqual((status, body["error"]["code"]), (400, "invalid_language"))
        status, _ = self.request({"report_id": self.report_id, "message": "Бюджет?", "arbitrary": "x"})
        self.assertEqual(status, 400)

    def test_language_does_not_bypass_token_check(self):
        status, body = self.request({"report_id": self.report_id, "message": "Бюджет?", "language": "kk"}, token="wrong")
        self.assertEqual((status, body["error"]["code"]), (403, "invalid_origin_or_token"))

    def test_only_exact_static_module_is_allowed(self):
        self.assertEqual(server.STATIC_FILES.get("/i18n.mjs"), "i18n.mjs")
        self.assertNotIn("/report_localization.py", server.STATIC_FILES)


if __name__ == "__main__":
    unittest.main()
