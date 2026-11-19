# Model access and ECG testing

Researchers who already have the authorized bundle can use [the local ECG test entrypoint](LOCAL_ECG_TEST.md). Its synthetic tests verify input handling and score calculation, not network accuracy.

## What this release can test

The public analysis code supports inspection of the study’s computational steps. The browser demonstration illustrates score combination using supplied component scores. It is not a trained ECG model and does not read a waveform or photograph.

## What is required for actual ECG inference

Actual inference requires the authorized trained checkpoint, its matching architecture and inference implementation, and the matching preprocessing and calibration configuration. These artifacts are not distributed with this repository.

Researchers with separately authorized access should use the inference environment corresponding to the study revision. Follow the provider’s exact signal units, lead order, sampling rate, preprocessing and output definitions. Do not substitute raw scores for calibrated scores, or substitute a different model version, without documenting and validating that change.

The weights were derived from a model-development environment subject to separate release conditions. Permission to export a model from that environment is distinct from permission to redistribute it publicly. The repository’s code licence grants neither permission.

## A future public ECG demonstration

A genuine public demonstration would require a confirmed model version, redistribution or hosted-inference authorization, validated input handling and a clear intended-use statement. Until those requirements are met, this repository makes no promise of publicly available raw-ECG inference.

Do not upload clinical data or private checkpoints to GitHub while requesting access. Contact the maintainers through an established private channel for research collaboration or licensing questions.
