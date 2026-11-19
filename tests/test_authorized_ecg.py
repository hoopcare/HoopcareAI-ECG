"""Synthetic plumbing tests; these do not test the private trained network."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "examples" / "run_authorized_ecg.py"
SPEC = importlib.util.spec_from_file_location("authorized_ecg", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class LocalInferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.signal = self.root / "synthetic.npy"
        np.save(self.signal, np.full((12, 5000), 0.1))
        self.bundle = self.root / "authorized-bundle"
        self.bundle.mkdir()
        (self.bundle / "nb18_panel_v4.pt").write_text("synthetic placeholder")
        self.model = self.root / "synthetic_scorer.py"
        self.architecture = self.root / "synthetic_architecture.py"
        self.architecture.write_text("class ResNet1dLVEF:\n    def __init__(self, heads): pass\n")
        self.model.write_text(
            "class Scorer:\n"
            "    def __init__(self, folder, **kwargs):\n"
            "        self.panel = {'calibrators_isotonic_val_by_format': "
            + repr({lead: {head: {"x": [0, 1], "y": [0, 1]} for head in runner.HEADS}
                    for lead in ("12lead", "limb3", "lead1")}) + "}\n"
            "    def attach(self, builder): builder(tuple(self.panel['calibrators_isotonic_val_by_format']['12lead']))\n"
            "    def predict(self, signal, **kwargs):\n"
            "        assert signal.shape == (12, 5000)\n"
            "        assert kwargs['strict'] and kwargs['coherent']\n"
            "        assert kwargs['population'] == 'internal'\n"
            "        assert kwargs['bandwidth'] == 'diagnostic'\n"
            "        assert kwargs['fs'] == 500\n"
            "        return {'problems': [], 'calibration_set': 'internal:' + kwargs['leads'], 'panel': "
            + repr({head: {"raw": 0.1, "calibrated": 0.99} for head in runner.HEADS}) + "}\n"
        )
        self.output = self.root / "private-result.json"
        self.arguments = ["--ecg", str(self.signal), "--sampling-rate", "500",
                          "--model-code", str(self.model), "--architecture-code", str(self.architecture),
                          "--bundle", str(self.bundle), "--output", str(self.output)]

    def tearDown(self):
        self.temp.cleanup()

    def test_local_cli_uses_explicit_artifacts_and_writes_study_result(self):
        result = subprocess.run([sys.executable, str(SCRIPT), *self.arguments],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(self.output.read_text())
        self.assertAlmostEqual(data["structural_heart_disease_score"], 1 - 0.9**5)
        self.assertFalse(data["diagnostic_threshold_flag"])
        self.assertFalse(data["high_score_threshold_flag"])
        self.assertEqual(set(data["components"]), set(runner.HEADS))
        self.assertNotIn(str(self.signal), result.stdout + result.stderr)

    def test_transposed_input_and_each_reduced_configuration(self):
        np.save(self.signal, np.full((5000, 12), 0.1))
        for leads in ("limb3", "lead1"):
            args = runner.parse_args(self.arguments + ["--leads", leads])
            data = runner.run(args)
            self.assertEqual(data["calibration_set"], "internal:" + leads)
            self.output.unlink()

    def test_bad_signal_shapes_and_nonfinite_values(self):
        for values in (np.zeros((3, 5000)), np.zeros((12, 4999)),
                       np.full((12, 5000), np.nan), np.full((12, 5000), np.inf),
                       np.full((12, 5000), 1 + 2j), np.full((12, 5000), 1e300)):
            np.save(self.signal, values)
            with self.assertRaises(runner.InputError):
                runner.run(runner.parse_args(self.arguments))
            self.assertFalse(self.output.exists())

    def test_pickle_and_npz_inputs_rejected(self):
        np.save(self.signal, np.array([{"do_not_unpickle": True}], dtype=object))
        with self.assertRaises(runner.InputError):
            runner.run(runner.parse_args(self.arguments))
        archive = self.root / "archive.npz"
        np.savez(archive, ecg=np.zeros((12, 5000)))
        with self.assertRaises(runner.InputError):
            runner.load_signal(archive, 500)

    def test_wrong_sampling_rate_fails_before_importing_model(self):
        args = runner.parse_args(self.arguments + ["--sampling-rate", "250"])
        with patch.object(runner, "load_module") as loader:
            with self.assertRaises(runner.InputError):
                runner.run(args)
            loader.assert_not_called()

    def test_missing_checkpoint_does_not_import_private_code(self):
        (self.bundle / "nb18_panel_v4.pt").unlink()
        with patch.object(runner, "load_module") as loader:
            with self.assertRaises(runner.InputError):
                runner.run(runner.parse_args(self.arguments))
            loader.assert_not_called()

    def test_missing_model_code_and_existing_output_rejected(self):
        self.model.unlink()
        with self.assertRaises(runner.InputError):
            runner.run(runner.parse_args(self.arguments))
        self.output.write_text("keep existing")
        with self.assertRaises(runner.InputError):
            runner.run(runner.parse_args(self.arguments))
        self.assertEqual(self.output.read_text(), "keep existing")

    def test_repository_output_and_symlink_to_repository_rejected(self):
        for path in (SCRIPT.parent / "result.json", self.root / "linked" / "result.json"):
            if path.parent.name == "linked":
                path.parent.symlink_to(SCRIPT.parent, target_is_directory=True)
            args = runner.parse_args(self.arguments + ["--output", str(path)])
            with self.assertRaises(runner.InputError):
                runner.run(args)

    def test_no_calibration_fallback(self):
        self.model.write_text(self.model.read_text().replace("'lead1':", "'unavailable':"))
        with self.assertRaises(runner.InputError):
            runner.run(runner.parse_args(self.arguments + ["--leads", "lead1"]))

    def test_quality_rejection_never_becomes_negative_prediction(self):
        self.model.write_text(self.model.read_text().replace("'problems': []", "'problems': ['flat lead']"))
        with self.assertRaisesRegex(runner.InputError, "quality"):
            runner.run(runner.parse_args(self.arguments))
        self.assertFalse(self.output.exists())

    def test_invalid_or_missing_raw_component_rejected(self):
        original = self.model.read_text()
        for replacement in ("None", "-0.1", "1.1", "float('nan')"):
            self.model.write_text(original.replace("'raw': 0.1", "'raw': " + replacement))
            with self.assertRaises(runner.InputError):
                runner.run(runner.parse_args(self.arguments))
            self.assertFalse(self.output.exists())

    def test_error_message_does_not_echo_artifact_contents(self):
        self.model.write_text("raise RuntimeError('private-debug-content')\n")
        with patch("sys.stderr") as stderr:
            code = runner.main(self.arguments)
        self.assertEqual(code, 2)
        self.assertNotIn("private-debug-content", str(stderr.write.call_args_list))

    def test_malformed_calibrator_is_rejected(self):
        original = self.model.read_text()
        self.model.write_text(original.replace("'x': [0, 1]", "'x': [1, 0]"))
        with self.assertRaisesRegex(runner.InputError, "calibrator"):
            runner.run(runner.parse_args(self.arguments))
        self.assertFalse(self.output.exists())

    def test_reduced_input_follows_study_masking_without_mutating_original(self):
        signal = np.repeat(np.arange(12, dtype=np.float32)[:, None], 5000, axis=1)
        original = signal.copy()
        three = runner.study_input(signal, "limb3")
        np.testing.assert_array_equal(three[:3], original[:3])
        np.testing.assert_array_equal(three[6:], np.repeat(original[1:2], 6, axis=0))
        np.testing.assert_array_equal(runner.study_input(signal, "lead1"),
                                      np.repeat(original[:1], 12, axis=0))
        np.testing.assert_array_equal(signal, original)

    def test_optional_pack_is_never_loaded(self):
        (self.bundle / runner.UNUSED_PACK).write_text("unexpected")
        with self.assertRaises(runner.InputError):
            runner.run(runner.parse_args(self.arguments))


if __name__ == "__main__":
    unittest.main()
