# AI-Model-training-software-license-check
This was designed to assist with commercial production of software with AI. It helps protect you legally and ethically, and it saves audit review time! 

## Compliance Guard Overview

This directory contains a small, self-contained **license and usage compliance engine** for the project. It is designed to enforce strict rules on:

- Code and container **dependencies** (via SBOMs),
- **Datasets** and other ingestion sources,
- **Models** (weights, upstream models),
- And generate exportable **reports + notices** for releases.

The guard runs in CI and can also be used locally as a preflight check before training or shipping.

---
- **Licensing:** We vet dependencies and datasets and record them in **`THIRD-PARTY.md`**. See **`docs/LICENSING.md`** for the policy and checklist. Run **`python3 check_licenses.py`** to validate licenses against the policy.

### License check script (`scripts/check_licenses.py`)

The script checks that dependencies and third-party references use licenses allowed by the project (permissive or explicitly allowed; strong copyleft and non-commercial are rejected for code incorporation). It does **not** call PyPI; it uses `requirements.txt` plus a built-in list and optional **`THIRD-PARTY.md`** table.

**Run it (from repo root):**

```bash
python scripts/check_licenses.py
```

| Option | Description |
|--------|-------------|
| `--requirements PATH` | Path to requirements file (default: `requirements.txt`) |
| `--third-party PATH` | Path to third-party manifest (default: `THIRD-PARTY.md`) |
| `--allow-weak-copyleft` | Do not treat LGPL/MPL as problematic (e.g. when used as external tool only) |
| `--strict` | Fail on unknown or non-permissive licenses (not just strong copyleft/NC) |
| `-q`, `--quiet` | Only print errors and final summary |

**Examples:**

```bash
# Default: check requirements.txt and THIRD-PARTY.md
python scripts/check_licenses.py

# Quiet (CI): only errors and pass/fail
python scripts/check_licenses.py -q

# Strict: fail on any unknown or weak-copyleft license
python scripts/check_licenses.py --strict

# Allow weak copyleft (e.g. Semgrep/LGPL as external tool)
python scripts/check_licenses.py --allow-weak-copyleft
```

**Inputs:**

- **`requirements.txt`** – Packages are matched against the script’s built-in `known_package_licenses`. Any package not listed there produces a *warning* (add it to **`THIRD-PARTY.md`** and to `known_package_licenses` in the script).
- **`THIRD-PARTY.md`** – Markdown table with columns like Package/Source and License. Rows whose license column looks like a license (e.g. MIT, BSD, Apache, GPL) are parsed and checked. Strong copyleft is warned (external-tool-only); non-commercial is an error.

**Exit codes:** `0` = pass, `1` = one or more errors (e.g. strong copyleft or non-commercial used in a way that violates policy). Warnings (unknown license, weak copyleft) do not change the exit code unless you use `--strict`.

**Adding a new dependency:** (1) Add the package to **`THIRD-PARTY.md`** with its license. (2) Add the package name and license to the `known_package_licenses` dict in **`scripts/check_licenses.py`** (around line 228) so the script can classify it.
## Key components

- `policy.yml`  
  Declarative policy file (version 2) describing:
  - License categories (permissive, weak/strong copyleft, proprietary, content types).
  - Defaults: unknown/unparsable license → **DENY**.
  - Strict requirements:
    - Code/containers used in `build`/`runtime` must have `license_files` or terms → **DENY if missing**.
    - Datasets/models/content used in `ingestion`/`training`/`evaluation` must have `license_files` or a `terms_url`/`license_url` → **DENY if missing**.
  - Rules that combine:
    - `type_in` (code, container, dataset, model, document, media),
    - `usage_in` (build, runtime, ingestion, training, evaluation),
    - `distribution_in` (internal, SaaS, on-prem, app-store),
    - `license_expression` / category,
    into **ALLOW / REVIEW / DENY** decisions with reasons and obligations.

- `license_guard.py`  
  The engine that:
  - Loads `policy.yml`.
  - Accepts one input JSON describing artifacts:
    - Either:
      - A **merged inventory** (see below), or
      - A CycloneDX / SPDX SBOM, or
      - A minimal custom manifest (list of objects with `id`, `name`, `version`, `license_expression`, `usage`, `source`, `type`, etc.).
  - Parses SPDX-like `license_expression` values.
  - Applies:
    - Category/rule-based decisions,
    - Hard requirements (license files / terms URLs),
    - Ticketed **exceptions** from `exceptions.yml`.
  - Emits a machine-readable report and exit code:
    - `0` → all ALLOW
    - `1` → at least one REVIEW
    - `3` → at least one DENY

- `merge_inventories.py`  
  Helper that merges multiple inventories/SBOMs into a single list of artifacts:
  - For each input JSON + a default `usage`:
    - Normalizes objects into the minimal artifact schema expected by `license_guard.py`.
    - Sets sensible defaults for:
      - `type` (code if missing),
      - `distribution` (internal if missing),
      - `license_files` (empty list if missing).
  - De-duplicates artifacts by `(id, usage)`.

- `generate_third_party_notices.py`  
  Converts `license_report.json` into a human-readable `THIRD_PARTY_NOTICES.txt`:
  - Groups artifacts by decision: ALLOW / REVIEW / DENY.
  - Lists:
    - Name, version, ID, usage, license expression, source URL.
    - Obligations and reasons (e.g., “Include license text and notices”).
  - Intended to be shipped with builds or attached to release artifacts.

- `exceptions.yml`  
  Template for **ticketed exceptions**:
  - Each entry matches an `(id, usage, distribution_mode)` and provides:
    - `decision` (ALLOW or REVIEW),
    - `ticket` (required, e.g. legal approval ID),
    - Optional `expires` date,
    - Extra `obligations` (e.g. “Ship LGPL text + notices”, “Retain contract reference”).
  - `license_guard.py` uses this to override decisions safely when there is an approved exception.

- `inventories/`  
  Holds the raw inputs:
  - `code.cdx.json` → CycloneDX SBOM for repo/code deps.
  - `container.cdx.json` → CycloneDX SBOM for container image (or stub if not yet used).
  - `datasets.json` → JSON list of dataset artifacts.
  - `models.json` → JSON list of model artifacts.
  - `merged.json` → output of `merge_inventories.py` (generated).

- `reports/`  
  - `license_report.json` → JSON report from `license_guard.py`.

- `Makefile`  
  Wraps the whole flow into simple targets.

---

## Artifact model (what an entry looks like)

An artifact is a JSON object with at least:

```json
{
  "id": "pypi:requests@2.32.3",
  "type": "code",
  "name": "requests",
  "version": "2.32.3",
  "source": "https://pypi.org/project/requests/",
  "license_expression": "Apache-2.0",
  "usage": "runtime",
  "distribution": "app-store",
  "license_files": ["LICENSE", "NOTICE"],
  "terms_url": "",
  "notes": "Optional free-form field"
}
```

For **datasets/models**, you typically use:

```json
{
  "id": "dataset:Obfuscated-MalMem2022",
  "type": "dataset",
  "name": "Obfuscated-MalMem2022",
  "version": "1.0",
  "source": "https://example.org/malmem2022",
  "terms_url": "https://example.org/malmem2022/license",
  "license_expression": "CC-BY-4.0",
  "usage": "training",
  "distribution": "internal",
  "license_files": [],
  "notes": "Download source + internal contract reference"
}
```

`policy.yml` then interprets these fields based on `type`, `usage`, `distribution`, and `license_expression`.

---

## How it works end-to-end

### 1. Generate SBOMs and inventories

From the `compliance/` directory (or via CI):

- **Code SBOM** (using `syft`):

```bash
make sbom-code
```

This runs:

```bash
syft dir:.. -o cyclonedx-json > inventories/code.cdx.json
```

- **Container SBOM** (optional):

```bash
make sbom-container IMAGE=yourimage:tag
```

If `IMAGE` is not set, it writes a stub SBOM with no components into `inventories/container.cdx.json`.

- **Datasets / Models**:
  - You edit `inventories/datasets.json` and `inventories/models.json` (or replace them with richer manifests) to reflect:
    - `source`, `terms_url`, `license_expression`, `usage`, `distribution`, etc.

### 2. Merge everything into a single inventory

```bash
make merge
```

This calls:

```bash
python3 merge_inventories.py inventories/merged.json \
  runtime inventories/code.cdx.json \
  runtime inventories/container.cdx.json \
  training inventories/datasets.json \
  training inventories/models.json
```

### 3. Run the guard with a chosen distribution mode

```bash
make check DIST=app-store
```

This runs:

```bash
python3 license_guard.py policy.yml inventories/merged.json reports/license_report.json \
  --distribution-mode app-store \
  --exceptions exceptions.yml
```

- `DIST` (default `internal`) controls how rules in `policy.yml` treat SaaS/on-prem/app-store vs internal-only.
- `EXCEPTIONS` points to `exceptions.yml`, where approved overrides live.

If any artifact is `DENY` or `REVIEW`:

- The script exits with non-zero exit code (CI fails).
- Details are in `reports/license_report.json`.

### 4. Generate human-readable notices

After `make check`:

```bash
python generate_third_party_notices.py \
  --report reports/license_report.json \
  --out THIRD_PARTY_NOTICES.txt
```

You can ship `THIRD_PARTY_NOTICES.txt` with your builds and attach `license_report.json` as an artifact for audits.

---

## CI integration (GitHub Actions)

See `.github/workflows/license_compliance.yml`:

- Installs Python + `pyyaml` and `syft`.
- Runs:

```yaml
- name: Run license guard via Makefile (merged inventories)
  run: |
    cd compliance
    make check
```

- Then generates and uploads:
  - `compliance/reports/license_report.json`
  - `compliance/THIRD_PARTY_NOTICES.txt`

Any `DENY` (or `REVIEW`, depending on how you treat exit code 1 vs 3) will cause the job to fail and block merges.

---

## Summary

- **Inputs**: SBOMs (code + container) + dataset/model manifests.
- **Policy**: `policy.yml` encodes your stance on licenses, usage, and distribution.
- **Engine**: `license_guard.py` evaluates everything and produces a JSON report.
- **Exports**: `generate_third_party_notices.py` converts the report into `THIRD_PARTY_NOTICES.txt` for shipping.
- **Control knobs**: `DIST` (distribution mode) and `EXCEPTIONS` (ticketed overrides) via `Makefile` and CI.


