"""Focused safety and reproducibility tests for the submission packager."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_submission", ROOT / "scripts" / "package_submission.py")
PACKAGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGER)


class PackageSubmissionTests(unittest.TestCase):
    def test_document_links_are_recursive_and_personal_files_are_excluded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "docs" / "agents").mkdir(parents=True)
            (root / "README.md").write_text("[one](docs/one.md)", encoding="utf-8")
            (root / "docs" / "one.md").write_text("[two](two.json) [personal](agents/LOG.md)", encoding="utf-8")
            (root / "docs" / "two.json").write_text("{}", encoding="utf-8")
            (root / "docs" / "agents" / "LOG.md").write_text("private", encoding="utf-8")
            self.assertEqual([p.as_posix() for p in PACKAGER.collect_documentation(root)],
                             ["README.md", "docs/one.md", "docs/two.json"])

    def test_invalid_local_link_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "README.md").write_text("[missing](docs/missing.md)", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                PACKAGER.collect_documentation(root)

    def test_symlinked_document_is_rejected_when_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "docs").mkdir()
            outside = root.parent / (root.name + "-outside.md")
            outside.write_text("outside", encoding="utf-8")
            try:
                (root / "docs" / "linked.md").symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are unavailable")
            (root / "README.md").write_text("[linked](docs/linked.md)", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                PACKAGER.collect_documentation(root)

    def test_output_symlink_is_rejected_before_external_write(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, content in {
                "agent.py": "class Agent:\n    pass\n",
                "candidate_model.py": "def build_candidates(*args):\n    return []\n",
                "llm_advisor.py": "class Advisor:\n    pass\n",
                "submission.csv": "campaign_name,filter_arpu_segment,filter_data_segment,filter_call_segment,filter_current_tariff,target_tariff,channel\nA,,,,,tariff_1,sms\n",
                "requirements.txt": "pandas==3.0.1\n",
                "README.md": "submission docs",
            }.items():
                (root / name).write_text(content, encoding="utf-8")
            outside = root.parent / (root.name + "-external")
            outside.mkdir()
            sentinel = outside / "sentinel.txt"
            sentinel.write_text("untouched", encoding="utf-8")
            try:
                (root / "output").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlinks are unavailable")
            with patch.object(PACKAGER, "ROOT", root), patch.object(PACKAGER, "SUBMISSION_DIR", root / "output" / "submission"):
                with self.assertRaises(RuntimeError):
                    PACKAGER.build()
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "untouched")

    def test_secret_is_rejected_before_writing_package(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            synthetic_token = "s" + "k-" + ("1" * 24)
            (root / "README.md").write_text("token " + synthetic_token, encoding="utf-8")
            marker = root / "output.marker"
            marker.write_text("untouched", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                PACKAGER._validate_secret_free((Path("README.md"),), root)
            self.assertEqual(marker.read_text(encoding="utf-8"), "untouched")

    def test_build_archive_has_exact_allowlist_hashes_and_ignores_stale_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, content in {
                "agent.py": "class Agent:\n    pass\n",
                "candidate_model.py": "def build_candidates(*args):\n    return []\n",
                "llm_advisor.py": "class Advisor:\n    pass\n",
                "submission.csv": "campaign_name,filter_arpu_segment,filter_data_segment,filter_call_segment,filter_current_tariff,target_tariff,channel\nA,,,,,tariff_1,sms\n",
                "requirements.txt": "pandas==3.0.1\n",
                "README.md": "[guide](docs/guide.md)",
            }.items():
                (root / name).write_text(content, encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "guide.md").write_text("Guide", encoding="utf-8")
            output = root / "output" / "submission"
            output.mkdir(parents=True)
            (output / "stale.txt").write_text("must not enter archive", encoding="utf-8")
            with patch.object(PACKAGER, "ROOT", root), patch.object(PACKAGER, "SUBMISSION_DIR", output):
                manifest, archive = PACKAGER.build()
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
                self.assertEqual(names, manifest["files"])
                self.assertNotIn("stale.txt", names)
                self.assertEqual(names[-1], "manifest.json")
                archive_manifest = json.loads(bundle.read("manifest.json"))
                self.assertEqual(archive_manifest["files"], names)
                for name, expected in manifest["artifact_sha256"].items():
                    self.assertEqual(hashlib.sha256(bundle.read(name)).hexdigest(), expected)
            self.assertIn("original participant kit", (output / "SUBMISSION.md").read_text(encoding="utf-8"))
            before = (output / "agent.py").read_bytes()
            (root / "README.md").write_text("token " + "s" + "k-" + ("2" * 24), encoding="utf-8")
            with patch.object(PACKAGER, "ROOT", root), patch.object(PACKAGER, "SUBMISSION_DIR", output):
                with self.assertRaises(RuntimeError):
                    PACKAGER.build()
            self.assertEqual((output / "agent.py").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
