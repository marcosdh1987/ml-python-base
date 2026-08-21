# Security Policy

## Reporting a vulnerability

**Do not open a public issue for a security problem.**

Report it privately through GitHub's [Security Advisories][advisories] on this
repository (Security → Report a vulnerability). If you cannot use that channel,
contact the maintainers listed in [.github/CODEOWNERS](.github/CODEOWNERS).

Please include what you can:

- what the problem is and where in the repository it lives;
- how to reproduce it;
- what an attacker could achieve with it.

We aim to acknowledge a report within five working days and to agree a disclosure
timeline with you before anything is made public.

[advisories]: https://github.com/marcosdh1987/ml-python-base/security/advisories/new

## Scope

This repository is a **project template**. It ships no running service, no
credentials, and no production data. The realistic risk surface is:

- **The quality gates.** `make check` runs ruff, bandit, mypy, and pytest. A change
  that weakens or bypasses a gate is a security-relevant change.
- **CI workflows.** Both workflows are read-only and declare
  `permissions: contents: read`. A workflow that widens permissions, adds a secret,
  or executes untrusted input is in scope.
- **The skills-projection engine** (`src/ml_python_base/skills_sync`), which writes
  files and creates symlinks inside the repository. Path traversal or writes outside
  the repository root are in scope.
- **Vendored agent skills** under `.github/skills-external/`. These are third-party
  instructions executed by AI agents. Content that induces an agent to exfiltrate
  data or run destructive commands is in scope — see [NOTICE](NOTICE) for provenance.

Out of scope: vulnerabilities in upstream dependencies (report those upstream; open
a normal issue here so we can bump the pin), and anything requiring an attacker to
already control the developer's machine.

## Secrets

No secrets belong in this repository. `.env` and `gateway/config.yaml` are
gitignored; only their `.example` counterparts are committed, and those must contain
placeholders only.

If you believe a credential was committed, **treat it as compromised and rotate it
first**, then report it privately. Do not open a pull request that deletes it — that
draws attention to the value while leaving it in the git history.
