# Instructions for coding assistants

This is a public research-code repository. Preserve the distinction between published code, restricted datasets and private trained-model artifacts.

- Read the analysis-specific README before changing a pipeline.
- Do not change cohort definitions, outcomes, time windows, lead handling, preprocessing, calibration, thresholds or resampling silently. Describe any scientific change explicitly.
- Never fabricate performance estimates, model outputs or missing metadata. A score-combination demonstration is not ECG inference.
- Keep patient records, waveforms, individual predictions, checkpoints, credentials and private infrastructure details out of files, logs, tests, issues and pull requests.
- Use synthetic fixtures for tests. Do not load arbitrary or untrusted checkpoints.
- Do not copy private code or third-party code without verified redistribution rights.
- Keep numerical precision and source provenance when editing analysis code. Do not substitute one score scale for another.
- Run relevant checks and review the complete diff before proposing a change. Explain any tests that could not run because an authorized artifact was unavailable.
- Follow the non-commercial research licence. Do not describe this repository as permissively licensed or OSI-approved open source.
- Do not publish, change access permissions, or upload artifacts without authorization for that action.
