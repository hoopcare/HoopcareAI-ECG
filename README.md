# HoopcareAI-ECG

Research code supporting the study **Development and validation of an AI-ECG structural heart disease score with evaluation before noncardiac surgery**.

This repository is the public home for the study’s analysis code and reproducibility documentation. It is separate from the Hoopcare clinical application and private model-development repositories. The manuscript is in preparation; no publication DOI is available yet.

## What is available

| Component | Status |
|---|---|
| MIMIC-IV surgical analysis | Eight analysis scripts and their execution documentation in [`analysis/mimic_iv_surgical`](analysis/mimic_iv_surgical/) |
| Component-score explorer | An offline illustration of the published code’s score combination; see [`demo/index.html`](demo/index.html) |
| Authorized local ECG test | A [local entrypoint](docs/LOCAL_ECG_TEST.md) for researchers who already have the matching authorized model bundle |
| Patient records, ECG signals and individual predictions | Not distributed |
| Trained model weights and the private inference bundle | Not distributed; authorized access is required separately |
| Complete reproduction of all manuscript analyses | Not yet supported by this release |

The analysis scripts require authorized datasets and, for inference, the corresponding authorized model environment. Cloning this repository alone does not enable predictions from a raw ECG.

## Try the score explorer

Open the [browser explorer](https://hoopcare.github.io/HoopcareAI-ECG/demo/) or [`demo/index.html`](demo/index.html) locally. It illustrates how supplied calibrated component scores combine. It does **not** interpret an ECG, estimate a patient’s postoperative event probability, or replace the trained network. The example inputs are synthetic; no patient record is needed. Input values stay in your browser.

For genuine ECG inference, read [Model access](docs/MODEL_ACCESS.md) and [Test an ECG locally](docs/LOCAL_ECG_TEST.md). The local entrypoint requires separately authorized artifacts and fails if they are unavailable; it never substitutes a toy model. There is no public upload service in this repository.

## Reproduce an analysis

1. Obtain the required dataset access independently: [Data access](docs/DATA_ACCESS.md).
2. Read the [reproducibility status](docs/REPRODUCIBILITY.md) and the analysis-specific README in [`analysis/mimic_iv_surgical`](analysis/mimic_iv_surgical/).
3. Configure local input and output paths. Keep all data, model artifacts and generated patient-level outputs outside the repository.
4. Run the documented analysis in the appropriate authorized environment, retaining the code revision and configuration with the results.

The public repository contains code, not a transfer of any dataset access rights. An authorization to export a trained model is also not, by itself, authorization to redistribute it publicly.

## Contribute and maintain

- [Contributing](CONTRIBUTING.md): changes, review and research reproducibility.
- [Guide de maintenance pour Gaia](docs/GAIA_MAINTAINER_GUIDE.fr.md): branches, pull requests and releases.
- [Security](SECURITY.md): private reporting of sensitive issues.
- [CITATION.cff](CITATION.cff): software citation metadata. Please cite the exact release or commit used.

## Licence

The original code is available for **non-commercial research** under the [Hoopcare Non-Commercial Research License 1.0](LICENSE). Commercial use requires a separate written agreement. This is a source-available research release, not an OSI-approved open-source release. Dataset licences, third-party code licences, model rights and trademarks remain separate.

This licence does not grant permission for clinical deployment or clinical decision-making.
