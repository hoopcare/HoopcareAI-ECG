# Contributing

Contributions should improve the reproducibility of the study without silently changing its scientific definitions.

## Make a change

1. Create a branch from `main`.
2. Make a focused change, including tests when behavior changes.
3. Open a pull request describing the purpose, validation performed and any effect on analysis outputs.
4. Wait for the repository checks to pass before merging.

Gaia (`@gbensouda`) and Yassine (`@ymoussali`) are the repository contacts. Repository management is described in the [maintainer guide](docs/GAIA_MAINTAINER_GUIDE.fr.md).

## Preserve the scientific contract

Changes to cohort selection, endpoints, time windows, lead reconstruction, preprocessing, calibration, thresholds, patient grouping or resampling must be explicit. Keep results produced by different definitions or code versions distinguishable. A formatting change must not change a number.

Do not claim that a successful code check validates diagnostic performance. State which datasets and model artifacts were actually available for a test, and distinguish a demonstration from a study result.

## Keep restricted material out of contributions

Do not attach patient records, ECGs, clinical reports, individual predictions, private model weights, credentials, or internal infrastructure details to commits, issues or pull requests. Use synthetic examples for bug reports. Do not copy code from another repository unless its redistribution rights are established and its licence is preserved.

Contributions must be your own work or work you have permission to contribute. They are submitted under this repository’s [licence](LICENSE), unless a compatible third-party licence is identified explicitly. No contributor transfers dataset or model rights merely by contributing code.
