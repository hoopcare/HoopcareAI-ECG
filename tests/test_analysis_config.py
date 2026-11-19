"""Synthetic tests for public-package path configuration; no clinical data."""

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "analysis" / "mimic_iv_surgical" / "scripts" / "study_config.py"
SPEC = importlib.util.spec_from_file_location("study_config", MODULE_PATH)
config = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(config)


class AnalysisConfigTests(unittest.TestCase):
    def test_missing_or_empty_configuration_fails(self):
        for value in (None, "", "   "):
            with self.subTest(value=value), patch.dict(os.environ, {}, clear=True):
                if value is not None:
                    os.environ["HOOPCARE_DATA_ROOT"] = value
                with self.assertRaisesRegex(ValueError, "HOOPCARE_DATA_ROOT"):
                    config.required_dir("HOOPCARE_DATA_ROOT")

    def test_nonexistent_path_and_file_are_not_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            file_path = root / "placeholder.txt"
            file_path.write_text("synthetic")
            for candidate in (root / "missing", file_path):
                with self.subTest(candidate=candidate), patch.dict(
                    os.environ, {"HOOPCARE_DATA_ROOT": str(candidate)}
                ):
                    with self.assertRaisesRegex(ValueError, "existing directory"):
                        config.required_dir("HOOPCARE_DATA_ROOT")

    def test_existing_directory_is_resolved(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ, {"HOOPCARE_DATA_ROOT": temporary}
        ):
            self.assertEqual(config.required_dir("HOOPCARE_DATA_ROOT"), Path(temporary).resolve())

    def test_workspace_cannot_live_inside_repository(self):
        with patch.dict(os.environ, {"HOOPCARE_WORKSPACE": str(ROOT)}):
            with self.assertRaisesRegex(ValueError, "outside"):
                config.workspace_dir()

    def test_symlink_cannot_hide_repository_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            alias = Path(temporary) / "alias"
            alias.symlink_to(ROOT, target_is_directory=True)
            with patch.dict(os.environ, {"HOOPCARE_WORKSPACE": str(alias)}):
                with self.assertRaisesRegex(ValueError, "outside"):
                    config.workspace_dir()

    def test_external_workspace_is_accepted_without_writing(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ, {"HOOPCARE_WORKSPACE": temporary}
        ):
            self.assertEqual(config.workspace_dir(), Path(temporary).resolve())
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_script_path_does_not_depend_on_current_directory(self):
        self.assertEqual(Path(config.script_path("study_config.py")), MODULE_PATH)

    def test_script_path_rejects_traversal_absolute_or_non_python_names(self):
        for candidate in ("../README.md", "/tmp/script.py", "folder/script.py", "model.pt", ""):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                config.script_path(candidate)

    def test_script_path_rejects_missing_file(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            config.script_path("not_a_script.py")

    def test_required_file_checks_missing_values_and_non_files(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            config.required_file("HOOPCARE_ARCHITECTURE_FILE")
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {"HOOPCARE_ARCHITECTURE_FILE": temporary}):
                with self.assertRaisesRegex(ValueError, "existing file"):
                    config.required_file("HOOPCARE_ARCHITECTURE_FILE")
            candidate = Path(temporary) / "architecture.py"
            candidate.write_text("# Synthetic fixture only\n")
            with patch.dict(os.environ, {"HOOPCARE_ARCHITECTURE_FILE": str(candidate)}):
                self.assertEqual(config.required_file("HOOPCARE_ARCHITECTURE_FILE"), candidate.resolve())

    def test_private_file_must_remain_outside_repository(self):
        with patch.dict(os.environ, {"HOOPCARE_ARCHITECTURE_FILE": str(MODULE_PATH)}):
            with self.assertRaisesRegex(ValueError, "outside"):
                config.external_file("HOOPCARE_ARCHITECTURE_FILE")

    def test_private_directory_must_remain_outside_repository(self):
        with patch.dict(os.environ, {"HOOPCARE_MODEL_DIR": str(ROOT)}):
            with self.assertRaisesRegex(ValueError, "outside"):
                config.external_dir("HOOPCARE_MODEL_DIR")

    def test_loader_uses_explicit_private_architecture_and_private_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model, data, workspace = (root / name for name in ("model", "data", "workspace"))
            for path in (model, data, workspace):
                path.mkdir()
            architecture = root / "architecture.py"
            architecture.write_text("class ResNet1dLVEF:\n def __init__(self, heads): self.heads = heads\n")
            (model / "nb18_inference_v4.py").write_text(
                "class Scorer:\n def __init__(self, folder, device): self.device = device\n"
                " def attach(self, factory): self.attached = factory(['synthetic'])\n"
            )
            (model / "nb18_panel_v4.pt").write_bytes(b"synthetic fixture; never deserialized")
            environment = {
                "HOOPCARE_MODEL_DIR": str(model), "HOOPCARE_DATA_ROOT": str(data),
                "HOOPCARE_WORKSPACE": str(workspace), "HOOPCARE_ARCHITECTURE_FILE": str(architecture),
            }
            source = (MODULE_PATH.parent / "rotation_memes_patients.py").read_text().split("A = pd.read_csv")[0]
            prior = Path.cwd()
            try:
                with patch.dict(os.environ, environment), patch.dict(sys.modules, {"study_config": config}):
                    namespace = {}
                    exec(compile(source, "synthetic-loader-check", "exec"), namespace)
                    self.assertEqual(Path.cwd(), workspace.resolve())
                    self.assertEqual(namespace["SC"].attached.heads, ("synthetic",))
                    self.assertEqual(namespace["SC"].device, "cpu")
                    (model / "nb18_panel_v4.pt").unlink()
                    with self.assertRaisesRegex(ValueError, "checkpoint"):
                        exec(compile(source, "synthetic-loader-check", "exec"), {})
            finally:
                os.chdir(prior)


if __name__ == "__main__":
    unittest.main()
