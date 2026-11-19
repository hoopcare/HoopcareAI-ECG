# Reproducibility status

This is an initial release of research analysis code. It is not a self-contained reproduction package for every result in the manuscript.

## Included

The MIMIC-IV surgical analysis code is provided in [`analysis/mimic_iv_surgical`](../analysis/mimic_iv_surgical/). Its README describes the execution sequence and prerequisites. Repository checks can verify supported code behavior with synthetic inputs; they do not reproduce clinical performance without the authorized data and model environment.

## Not included

- Patient-level datasets, ECG waveforms, clinical reports and predictions.
- Trained model weights and the private inference bundle.
- A complete publicly runnable environment for every internal and external validation cohort.
- Unpublished analysis outputs or a final manuscript DOI.

## Record each research run

Keep the source-code commit, dataset version, cohort-selection configuration, model revision, calibration and thresholds, input/output schema and execution environment with each run. Record any exclusions and whether comparisons use the same patients and recordings.

When adapting a path or environment setting, keep the scientific definitions unchanged. If an endpoint, cutoff, matching interval or processing step changes, record it as a new analysis variant rather than replacing an earlier result silently.

## Release policy

A tagged release identifies a specific code state. Its release notes should state what is newly available, which checks were run, what remains dependent on restricted artifacts and whether a change affects scientific results. A passing automated check is not a claim of clinical validation.
