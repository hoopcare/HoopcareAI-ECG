# MIMIC-IV surgical cohort analysis

Analysis code for external evaluation of the fixed HoopcareAI-ECG structural heart disease score in adults undergoing noncardiac surgery in MIMIC-IV. The analysis protocol was registered before the scores were linked to this surgical cohort. The protocol identifier is withheld here while the registration is under embargo.

This package adapts Gaia's eight source scripts, plus a path-configuration helper. The source snapshot is the verified clean commit `e6720f740c9bf1b8a0d1a2467b48554d30e41287`. Seven scripts retain their scientific logic and numerical settings, with paths made configurable and the embargoed protocol identifier redacted. In `rotation_memes_patients.py`, only the shared loader is retained: the architecture must be supplied separately, and the unrelated standalone monitor-rotation experiment and its unpublished reference values are excluded. [provenance.json](provenance.json) records the source and released file hashes.

## What this release can reproduce

The scripts build the surgical cohort, derive covariates and RCRI variants, assemble model scores, and run the registered analyses **when the required authorized data, model environment and diagnostic reference files are available**. This release is not a self-contained reproduction package for all manuscript results.

Not distributed:

- Patient records, ECG signals, individual predictions or analysis outputs.
- Trained weights, calibration artifacts, model architecture or private inference modules.
- HCUP classification files or PhysioNet datasets.
- Diagnostic-reference artifacts from the preceding validation pipeline, including `results/paires_principales.csv`. The eight scripts do not create this file; obtain it in the same authorized analysis environment before running the surgical analyses.

The scorer must be the study's corresponding authorized version. Do not substitute another model or calibrator and present the resulting analysis as a reproduction.

## Authorized data and directory layout

Obtain MIMIC-IV v3.1, MIMIC-IV-ECG v1.0 and MIMIC-IV-Echo v1.0.1 through PhysioNet under the applicable access agreement. `HOOPCARE_DATA_ROOT` must contain the original extracted directory structure:

```text
mimic-iv/v3.1/hosp/
mimic-iv-ecg/v1.0/
```

Preserve the MIMIC-IV-Echo extraction layout under the same dataset root. The cohort script locates `structured-measurement.csv.gz` at the same directory depths as the original analysis.

The diagnostic reference helper also needs `HOOPCARE_ECHO_FILE`: the local structured-measurement CSV used by the original diagnostic pipeline, with columns `subject_id`, `measurement_id`, `measurement_datetime`, `test_type`, `measurement` and `result`. This setting replaces the original staged CSV path. Data staging or conversion is not included; do not silently substitute a different reference extraction.

Place the following authorized AHRQ HCUP tools in `HOOPCARE_HCUP_DIR`:

- Procedure Classes Refined for ICD-10-PCS: `PClassR_v2027-1.csv`.
- Procedure Classes for ICD-9-CM: `pc2015.csv`.
- CCSR for ICD-10-PCS procedures: `PRCCSR_v2027-1.csv`.
- CCS for ICD-9-CM procedures: `prref2015.csv`.

The original cohort script contains fallback definitions for missing classification files. Those fallbacks are preserved in the source; **they do not reproduce the registered analysis using the complete classification files**. Check that all required classifications were loaded before interpreting a run.

## Configure local paths

Run from the repository root. Replace each example path with an existing directory in your authorized environment. The workspace must be outside the Git repository because it holds patient-level intermediate files.

```bash
export HOOPCARE_ANALYSIS_SCRIPTS="$PWD/analysis/mimic_iv_surgical/scripts"
export HOOPCARE_WORKSPACE="/path/to/local-analysis-workspace"
export HOOPCARE_DATA_ROOT="/path/to/authorized-datasets"
export HOOPCARE_HCUP_DIR="/path/to/hcup-tools"
export HOOPCARE_ECHO_FILE="/path/to/authorized-echo/structured_measurement.csv"
export HOOPCARE_MODEL_DIR="/path/to/authorized-model-bundle"
export HOOPCARE_ARCHITECTURE_FILE="/path/to/authorized-model-code/resnet1d.py"
mkdir -p "$HOOPCARE_WORKSPACE/results/mimic_complet"
```

Paths are read explicitly from environment variables; no credentials or private service endpoints are needed by the publication package. The scripts remain partly documented in French.

`HOOPCARE_MODEL_DIR` must contain the authorized `nb18_inference_v4.py` scorer, `nb18_panel_v4.pt` and the corresponding study artifacts. `HOOPCARE_ARCHITECTURE_FILE` must expose the matching `ResNet1dLVEF` class from the authorized study export, accepting `heads=tuple(heads)`. The original embedded architecture is not distributed here. Supply the corresponding architecture and artifact manifest; a merely shape-compatible substitute is not an equivalent reproduction. Both model locations must remain outside this repository. These explicitly selected Python files execute locally and the scorer may deserialize Python checkpoint objects; use only trusted, authorized artifacts.

The package's [environment-reference.txt](environment-reference.txt) records six package versions read from the original analysis environment. It is a provenance record, not a complete lockfile. PyTorch's `+cpu` build is platform-specific; preserve the authorized environment or obtain the matching CPU distribution from the official PyTorch installation instructions. The private scorer may require additional dependencies.

## Execution sequence

| Step | Script | Local output |
|---|---|---|
| 1. Cohort | `chir_codes.py` | `chir_cohorte_v1_*.csv`, `chir_index_v1_*.csv` |
| 2. Covariates and RCRI | `chir_rcri.py <cohort file> <classes>` | `chir_covariables_*.csv` |
| 3. Twelve-lead scores for MIMIC-IV ECGs | `score_mimic_complet.py` | `results/mimic_complet/` |
| 4. Reduced-lead scores and composite | `chir_score.py results/chir_index_v1_c34.csv` | `chir_scores_c34.csv` |
| 5. Registered analyses | `chir_analyse.py` | `chir_resultats_c34.txt` |

```bash
python "$HOOPCARE_ANALYSIS_SCRIPTS/chir_codes.py"
python "$HOOPCARE_ANALYSIS_SCRIPTS/chir_rcri.py" results/chir_cohorte_v1_c34.csv 3,4
python "$HOOPCARE_ANALYSIS_SCRIPTS/chir_rcri.py" results/chir_cohorte_v1_c4.csv 4
python "$HOOPCARE_ANALYSIS_SCRIPTS/chir_rcri.py" results/chir_cohorte_v1_c34_ecg90.csv 3,4
python "$HOOPCARE_ANALYSIS_SCRIPTS/score_mimic_complet.py"
python "$HOOPCARE_ANALYSIS_SCRIPTS/chir_score.py" results/chir_index_v1_c34.csv
python "$HOOPCARE_ANALYSIS_SCRIPTS/chir_analyse.py"
```

The scoring and analysis scripts change to the configured workspace where required. Supporting scripts are resolved from this package, rather than from an unrelated `scripts` directory in the workspace.

Supporting modules:

- `rotation_memes_patients.py`: compatibility loader reused by the scoring scripts. The original standalone monitor-rotation experiment is excluded from this release; it is not a runnable monitor-analysis entrypoint.
- `score_3formats.py`: reduced-lead handling reused by `chir_score.py`; it is not a substitute for the private model bundle.
- `joindre_echo.py`: diagnostic reference definitions reused by the surgical bridging-cohort analysis; it also relies on preceding diagnostic-validation artifacts.

## Validation and limitations

Public tests cover the new path configuration and the separate synthetic score explorer. Syntax checks do not execute the clinical analyses. No patient-level dataset or authorized model bundle was used to rerun the full pipeline as part of preparing this public package. Preserve the original environment manifest with each authorized run and compare outputs before treating a different environment as equivalent.

Code is licensed for non-commercial research under the repository's [LICENSE](../../LICENSE). Dataset access, model access and clinical use are separate rights.
