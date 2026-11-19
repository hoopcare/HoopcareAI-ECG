"""Compatibility loader for the study's separately authorized model artifacts.

Only the shared loader is distributed here. The unrelated standalone monitor
rotation experiment and its unpublished reference results are excluded.
"""

import importlib.util
import os

from study_config import external_dir, external_file, required_dir, workspace_dir


MOD = external_dir("HOOPCARE_MODEL_DIR")
BASE = required_dir("HOOPCARE_DATA_ROOT") / "mimic-iv-ecg/v1.0"
ARCHITECTURE = external_file("HOOPCARE_ARCHITECTURE_FILE")
if not (MOD / "nb18_panel_v4.pt").is_file():
    raise ValueError("The authorized study checkpoint is required before scoring.")
if not (MOD / "nb18_inference_v4.py").is_file():
    raise ValueError("The matching authorized study scorer is required before scoring.")
if ARCHITECTURE.suffix.lower() != ".py":
    raise ValueError("HOOPCARE_ARCHITECTURE_FILE must be the authorized Python architecture.")


def _load_authorized(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load the explicitly supplied study model code.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = _load_authorized(MOD / "nb18_inference_v4.py", "authorized_study_scorer")
architecture = _load_authorized(ARCHITECTURE, "authorized_study_architecture")
if not callable(getattr(architecture, "ResNet1dLVEF", None)):
    raise ValueError("The study architecture must expose the matching ResNet1dLVEF class.")
os.chdir(workspace_dir())
SC = m.Scorer(str(MOD), device="cpu")
SC.attach(lambda heads: architecture.ResNet1dLVEF(heads=tuple(heads)))
ORD = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]

# A = pd.read_csv -- compatibility boundary used by the surgical scoring scripts.
# The original standalone monitor-rotation analysis is not included in this release.
