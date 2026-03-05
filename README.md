# AI-Model-training-software-license-check
This was designed to assist with commercial production of software with AI. It helps protect you legally and ethically, and it saves audit review time! 

## License check script (`check_licenses.py`)

This script enforces the project’s licensing policy for:

- **Python dependencies** listed in `requirements.txt`
- **Third‑party code, tools, and datasets** documented in `THIRD-PARTY.md`

It classifies licenses into:

- **Permissive** (MIT, Apache‑2.0, BSD, 0BSD, BSL‑1.0, Blue Oak, UPL, etc.) – allowed, with attribution/notice as required  
- **Weak copyleft** (LGPL, MPL, EPL, CDDL, etc.) – allowed only in certain usage patterns (e.g., dynamic linking, external tools)  
- **Strong copyleft** (GPL, AGPL, some hardware/data licenses) – **not allowed** for code incorporation into this product  
- **Non‑commercial** (CC‑BY‑NC, Non‑Profit Open, etc.) – **not allowed** for a commercial product  
- **Non‑standard / unknown** – flagged for manual review

License categories are aligned with `docs/LICENSING.md` and OSI’s approved license list (`https://opensource.org/licenses`). The script does **not** fetch data from PyPI; it only uses local files.

---

## Basic usage

From the repo root:

```bash
python check_licenses.py
```

Typical outputs:

- **“License check passed”** – all detected licenses are permissive or otherwise allowed  
- **Warnings** – unknown or weak‑copyleft licenses that need review  
- **Errors** – strong copyleft or non‑commercial licenses used in a way that violates the policy (exit code `1`)

---

## Command‑line options

```bash
python check_licenses.py [options]
```

- **`--requirements PATH`**  
  Path to a requirements file (default: `requirements.txt`).

- **`--third-party PATH`**  
  Path to the third‑party manifest (default: `THIRD-PARTY.md`).

- **`--allow-weak-copyleft`**  
  Do **not** treat LGPL/MPL/EPL/CDDL as problematic (use when you only rely on them as external tools or in clearly safe linking patterns).

- **`--strict`**  
  Fail on *any* unknown or non‑permissive license, not just strong copyleft / non‑commercial.

- **`-q`, `--quiet`**  
  Only print warnings/errors and the final summary. Useful in CI.

### Examples

```bash
# Default: check requirements.txt + THIRD-PARTY.md
python check_licenses.py

# Quiet mode for CI
python check_licenses.py -q

# Strict mode (treat unknown / weak-copyleft as failures)
python check_licenses.py --strict

# Allow weak copyleft (e.g., Semgrep/LGPL as an external tool)
python check_licenses.py --allow-weak-copyleft
```

---

## Inputs and how they are interpreted

### `requirements.txt`

- Each entry is parsed into `(package, version_spec)`  
- A small `known_package_licenses` map inside `check_licenses.py` holds the expected license for core dependencies (FastAPI, Uvicorn, NumPy, etc.).  
- If a package is **not** in that map:
  - The script emits a **warning**: “Unknown license for package: X…”
  - It does **not** fail, unless you run with `--strict`.

**Recommended workflow when adding a new dependency:**

1. Add the package to `requirements.txt`.  
2. Look up its license (PyPI page or upstream repo).  
3. Add a row for it in `THIRD-PARTY.md` with name, source URL, and license.  
4. Add an entry to `known_package_licenses` in `check_licenses.py` so future runs classify it correctly.

### `THIRD-PARTY.md`

- The script heuristically parses Markdown tables to find rows with a **license** column.  
- Each license string is normalized (MIT vs. “The MIT License”, Apache‑2.0 vs. “Apache License Version 2.0”, etc.) and mapped into a risk category.  
- Behavior:
  - **Strong copyleft** → error for code incorporation (external‑tool use only is allowed but must be documented)  
  - **Non‑commercial** → error (not allowed for product use)  
  - **Weak copyleft** → warning by default (or error in `--strict` mode)  
  - **Permissive** → allowed; you still must satisfy attribution/notice obligations

---

## Exit codes and CI integration

- **`0`** – License check passed (no policy‑violating errors found).  
- **`1`** – One or more errors (e.g., strong copyleft or non‑commercial use, or unknown licenses in `--strict` mode).

For CI, you can add a job like:

```yaml
- name: Check licenses
  run: python check_licenses.py -q
```

Or in strict mode:

```yaml
- name: Check licenses (strict)
  run: python check_licenses.py --strict -q
```

---

## Where to look for policy details

- **`docs/LICENSING.md`** – Full licensing policy, risk categories, and examples  
- **`THIRD-PARTY.md`** – Canonical list of third‑party code, tools, and datasets and their licenses  
- **`README.md`** – Top‑level project overview; includes a short section pointing to this script

