"""Local study-score inference using separately authorized, trusted v4 artifacts."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

import numpy as np


HEADS = ("lvef_lte_50", "ph_rvsp40", "rv_dysfunction", "as_severe", "hcm")
REPOSITORY = Path(__file__).resolve().parents[1]
UNUSED_PACK = "__no_optional_regression_pack__.pt"


class InputError(ValueError):
    """A required input, artifact or calibration is unavailable or invalid."""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ecg", required=True, type=Path, help="Trusted local .npy signal in mV")
    parser.add_argument("--sampling-rate", required=True, type=float, help="Must be 500 Hz")
    parser.add_argument("--model-code", required=True, type=Path, help="Authorized nb18_inference_v4.py")
    parser.add_argument("--architecture-code", required=True, type=Path, help="Matching authorized resnet1d.py")
    parser.add_argument("--bundle", required=True, type=Path, help="Authorized v4 artifact directory")
    parser.add_argument("--leads", choices=("12lead", "limb3", "lead1"), default="12lead")
    parser.add_argument("--output", required=True, type=Path, help="New local JSON file outside this repository")
    return parser.parse_args(argv)


def load_signal(path, sampling_rate):
    if sampling_rate != 500 or path.suffix.lower() != ".npy":
        raise InputError("Use a .npy waveform acquired at 500 Hz; no resampling is performed.")
    try:
        signal = np.load(path, allow_pickle=False)
    except (OSError, ValueError):
        raise InputError("Cannot read the non-pickled .npy signal.") from None
    if signal.shape == (5000, 12):
        signal = signal.T
    if signal.shape != (12, 5000) or signal.dtype.kind not in "fiu" or not np.isfinite(signal).all():
        raise InputError("Expected 12 × 5000 finite, real samples in canonical lead order.")
    with np.errstate(over="ignore"):
        converted = signal.astype(np.float32)
    if not np.isfinite(converted).all():
        raise InputError("Samples exceed the supported numeric range.")
    return converted


def load_module(path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise InputError("Cannot load the explicitly selected model code.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def study_input(signal, leads):
    """Match chir_score.formats; the private scorer applies the final lead mask."""
    if leads == "lead1":
        return np.repeat(signal[:1], 12, axis=0)
    if leads == "limb3":
        first, second = signal[0], signal[1]
        return np.vstack((signal[:3], -(first + second) / 2,
                          first - second / 2, second - first / 2,
                          np.repeat(signal[1:2], 6, axis=0)))
    return signal


def calibrated_components(result, calibrators):
    components = {}
    for head in HEADS:
        raw = result.get("panel", {}).get(head, {}).get("raw")
        if not isinstance(raw, (int, float)) or not np.isfinite(raw) or not 0 <= raw <= 1:
            raise InputError("A required raw study output is unavailable or invalid.")
        table = calibrators.get(head, {})
        x = np.asarray(table.get("x", []), dtype=float)
        y = np.asarray(table.get("y", []), dtype=float)
        if (x.ndim != 1 or y.ndim != 1 or x.size == 0 or x.size != y.size
                or not np.isfinite(x).all() or not np.isfinite(y).all()
                or np.any(np.diff(x) <= 0) or np.any(np.diff(y) < 0)
                or np.any((x < 0) | (x > 1)) or np.any((y < 0) | (y > 1))):
            raise InputError("A required lead-specific isotonic calibrator is unavailable or invalid.")
        # Use original raw outputs, not the scorer's coherence-adjusted display probabilities.
        components[head] = float(np.clip(np.interp(raw, x, y), 0, 1))
    return components


def validate_paths(args):
    output = args.output.expanduser().resolve()
    if output == REPOSITORY or REPOSITORY in output.parents:
        raise InputError("Individual results must be saved outside the public repository.")
    if output.exists() or not output.parent.is_dir() or output.suffix.lower() != ".json":
        raise InputError("Choose a new .json file in an existing private local directory.")
    paths = (args.model_code, args.architecture_code, args.bundle / "nb18_panel_v4.pt")
    if not all(path.is_file() for path in paths):
        raise InputError("Provide the authorized v4 checkpoint and its matching scorer and architecture.")
    if (args.bundle / UNUSED_PACK).exists():
        raise InputError("The optional regression-pack exclusion path must not exist.")
    return output


def run(args):
    output = validate_paths(args)
    signal = load_signal(args.ecg, args.sampling_rate)
    inference = load_module(args.model_code, "authorized_ecg_inference")
    architecture = load_module(args.architecture_code, "authorized_ecg_architecture")
    scorer = inference.Scorer(str(args.bundle), panel="nb18_panel_v4.pt", pack=UNUSED_PACK, device="cpu")
    scorer.attach(lambda heads: architecture.ResNet1dLVEF(heads=heads))
    calibrators = (scorer.panel or {}).get("calibrators_isotonic_val_by_format", {}).get(args.leads)
    if not calibrators or any(head not in calibrators for head in HEADS):
        raise InputError("The bundle lacks matching internal diagnostic calibrators; no fallback is allowed.")
    result = scorer.predict(study_input(signal, args.leads), fs=500, leads=args.leads,
                            bandwidth="diagnostic", population="internal", strict=True, coherent=True)
    if result.get("problems"):
        raise InputError("The private scorer rejected waveform quality; no prediction was saved.")
    components = calibrated_components(result, calibrators)
    score = float(1 - np.prod([1 - components[head] for head in HEADS]))
    payload = {"research_use_only": True, "lead_configuration": args.leads,
               "sampling_rate_hz": 500, "calibration_set": "internal:" + args.leads,
               "components": components, "structural_heart_disease_score": score,
               "diagnostic_threshold_flag": score >= 0.453,
               "high_score_threshold_flag": score >= 0.635}
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload


def main(argv=None):
    try:
        run(parse_args(argv))
    except InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:
        print("Local inference failed (" + type(error).__name__
              + "); check the authorized artifact versions and local environment.", file=sys.stderr)
        return 2
    print("Research result saved locally. No waveform or result was uploaded by this wrapper.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
