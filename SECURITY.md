# Security and sensitive data

Never include patient information, ECG records, model checkpoints or credentials in a public issue or pull request.

For a suspected vulnerability or accidental disclosure, use GitHub’s **Report a vulnerability** option in this repository’s Security tab when available. If that option is unavailable, contact the maintainers through an established private channel. Do not describe the sensitive details in a public issue while arranging contact.

Include the affected code revision, the impact and a minimal synthetic reproduction. No patient example is required.

This repository does not operate an ECG upload service. Researchers who connect it to their own model environment are responsible for that environment’s access controls. Only load model artifacts obtained from a trusted, authorized source.
