# Test an ECG locally with authorized model artifacts

This entrypoint runs genuine inference **only when you already have lawful access to the private trained model and matching code**. The repository contains neither those artifacts nor a substitute model. The browser score demonstration is a separate calculator and does not interpret ECGs.

## Prerequisites

- An authorized, trusted `nb18_panel_v4.pt` checkpoint, its matching `nb18_inference_v4.py` scorer and `resnet1d.py` architecture exposing `ResNet1dLVEF`. Verify their identities against the provider's study-version manifest before running them.
- The private model's compatible Python, NumPy and PyTorch environment. This wrapper adds no dependency beyond NumPy and the Python standard library. It does not install packages, download weights or connect to an inference service.
- Internal diagnostic isotonic calibrators for all five study components and the selected lead configuration, stored in the checkpoint. Missing calibrators cause failure; there is no substitution with another population or lead format.
- A lawful local ECG file and a private output directory outside this repository. Do not put patient waveforms or individual predictions in Git, issues, pull requests or the public browser demonstration.

The specified Python files execute locally, and the private scorer may deserialize its checkpoint using Python object loading. Supply only independently trusted, authorized files. This interface is not a service for accepting checkpoint uploads.

## Input contract

Save a numeric NumPy `.npy` array containing a complete diagnostic ECG: **12 leads × 5,000 samples, sampled at 500 Hz, in millivolts**. The canonical lead order is `I, II, III, aVR, aVL, aVF, V1, V2, V3, V4, V5, V6`. A `5,000 × 12` array is also accepted and transposed. Object arrays, non-finite samples and other dimensions are rejected. Sampling rate, lead identities and physical units must come from the source acquisition; the array alone cannot verify them.

This wrapper does not digitize images, resample waveforms, infer lead identities or reconstruct missing chest leads. It does not accept native monitor recordings. All three configurations start from the same complete diagnostic recording. The reduced configurations follow the study's `chir_score.py` input masking convention, followed by the private scorer's own preprocessing and lead mask. Waveform quality rejection produces no score and must not be interpreted as a negative finding.

## Run

Set each variable to your own authorized local path. Keep input, model and output directories outside the checkout.

```sh
python examples/run_authorized_ecg.py \
  --ecg "$ECG_NPY" \
  --sampling-rate 500 \
  --model-code "$SCORER_PY" \
  --architecture-code "$ARCHITECTURE_PY" \
  --bundle "$MODEL_DIRECTORY" \
  --leads 12lead \
  --output "$PRIVATE_RESULTS_DIRECTORY/ecg-research-result.json"
```

Use `--leads limb3` for leads I–III or `--leads lead1` for lead I, and choose a new output filename each time. Existing output files are never overwritten. The output is created with owner-only file permissions where supported. The wrapper uses CPU inference, `population="internal"`, `bandwidth="diagnostic"`, strict quality checks and coherent head handling; the optional regression pack is disabled.

## Returned study score

The JSON contains five calibrated study components, the combined structural heart disease score, lead configuration and two fixed-threshold flags. It contains no waveform or patient identifier. Terminal output contains neither prediction values nor source paths.

| Component key | Meaning |
| --- | --- |
| `lvef_lte_50` | LVEF ≤50% |
| `ph_rvsp40` | Estimated right ventricular systolic pressure ≥40 mmHg |
| `rv_dysfunction` | Right ventricular systolic dysfunction |
| `as_severe` | Severe aortic stenosis |
| `hcm` | LV hypertrophy proxy; training used septal thickness ≥15 mm or a qualifying HCM diagnosis code |

For every component, the wrapper applies the checkpoint's configuration-specific **internal diagnostic isotonic calibrator to the original raw output**. This matches `analysis/mimic_iv_surgical/scripts/chir_score.py`. It deliberately does not use coherence-adjusted display probabilities from the scorer. It combines the resulting values as `S = 1 − product(1 − p_k)`.

The study composite reference uses measured septal thickness for the hypertrophy component; the `hcm` prediction target is broader and must not be labelled adjudicated hypertrophic cardiomyopathy. Estimated RVSP is not catheter-confirmed pulmonary hypertension.

- `diagnostic_threshold_flag`: `S ≥0.453`, the study's fixed diagnostic threshold.
- `high_score_threshold_flag`: `S ≥0.635`, the threshold identifying the highest 5% in the original surgical cohort. It need not flag 5% in another population.

`S` is a research score, not a measured ejection fraction or a demonstrated calibrated probability of the composite in every population. The output provides no clinical referral recommendation. This entrypoint does not reproduce the full cohort analysis or paired all-configuration quality exclusions.

## Verification scope

The automated tests use synthetic arrays and a stub model to check input handling, explicit artifact loading, calibration scale, score calculation, refusal behaviour and local output protection. **They do not validate the private network or clinical accuracy.** A study-reproduction claim requires the authorized artifact manifest and reference-case verification in the corresponding private environment.
