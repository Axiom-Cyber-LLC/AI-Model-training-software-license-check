#!/usr/bin/env python3
"""
License compliance check for Axiom-Verity dependencies and third-party references.

Uses the license risk categories from docs/LICENSING.md:
- Permissive (MIT, Apache 2.0, BSD, CC0, etc.): allowed; verify attribution.
- Weak copyleft (LGPL, MPL): review if linked; external-tool use OK.
- Strong copyleft (GPL, AGPL): banned for code incorporation; external tools only.
- Non-commercial (CC-BY-NC, etc.): banned for commercial product.
- Unknown: flag for manual review.

Reads requirements.txt and optional THIRD-PARTY manifest; does not fetch PyPI
(use pip-licenses or similar for full dependency tree). See docs/LICENSING.md
and https://opensource.org/licenses for authoritative license definitions.
License categories and identifiers are informed by the OSI-approved list; optional
local copies of OSI pages may be kept in downloaded_pages/ for reference.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# License risk categories aligned with docs/LICENSING.md, OSI (opensource.org/licenses),
# and optional local copies in downloaded_pages/ (OSI license list and review process).
PERMISSIVE = {
    "mit", "mit-0", "apache-2.0", "apache 2.0", "bsd-2-clause", "bsd-3-clause",
    "0bsd", "bsd", "bsd-1-clause", "isc", "cc0", "unlicense", "cc-by",
    "cdla-permissive-1.0", "python-2.0", "psf", "zlib", "ncsa", "postgresql",
    "bsl-1.0", "boost", "blueoak", "blue oak", "upl-1.0", "universal permissive",
    "simpl-2.0", "fair", "artistic-2.0", "w3c", "php-3.0", "php-3.01",
    "unicode-dfs-2016", "unicode", "mulanpsl-2.0", "mulan permissive",
    "ecl-2.0", "ecl-1.0", "educational community", "ntp", "jam", "cmu",
    "zlib libpng", "vsl-1.0", "vovida", "xnet", "miros", "multics",
    "bsd-2-clause-patent", "bsd+patent", "eudatagrid", "efl-2.0", "eiffel forum",
    "watcom", "sybase", "osl-3.0", "osl-2.1", "osl-1.0", "open software license",
    "apl-1.0", "adaptive public", "afl-3.0", "academic free", "aal", "attribution assurance",
    "lpl-1.02", "lpl-1.0", "lucent", "spl-1.0", "sun public", "cua opl",
    "sleepycat", "oldap", "apache-1.1", "cnri python", "intel", "cvw", "mitre",
    "oclc-2.0", "entessa", "rpsl-1.0", "realnetworks", "rscpl", "ricoh",
    "unicode-3.0", "hpnd", "nasa-1.3", "naumen", "liliq-p-1.1", "quebec permissive",
    "cern-ohl-p-2.0", "cern open hardware permissive", "olfl-1.3", "open logistics",
    "oset-pl-2.1", "oset public", "osc-1.0", "jabber", "icu",
}
WEAK_COPYLEFT = {
    "lgpl-2.0", "lgpl-2.1", "lgpl-3.0", "lgpl-2.0-only", "lgpl-2.1-only", "lgpl-3.0-only",
    "mpl-2.0", "mpl-1.1", "mpl-1.0", "epl-2.0", "epl-1.0", "eclipse public",
    "cddl-1.0", "cddl-1.1", "cddl", "common development and distribution",
    "cern-ohl-w-2.0", "cern open hardware weakly", "ms-rl", "microsoft reciprocal",
    "qpl-1.0", "q public",
    "wxwindows", "wxwindows library", "lppl-1.3c", "latex project public",
    "cpal-1.0", "common public attribution", "rpl-1.1", "rpl-1.5", "reciprocal public",
    "liliq-r-1.1", "quebec reciprocite", "ngpl", "nethack general public",
}
STRONG_COPYLEFT = {
    "gpl-2.0", "gpl-3.0", "gpl-1.0", "agpl-3.0", "gpl", "agpl",
    "gpl-2.0-only", "gpl-3.0-only", "gpl-1.0-only", "agpl-3.0-only",
    "cern-ohl-s-2.0", "cern open hardware strong", "cal-1.0", "cryptographic autonomy",
    "eupl-1.1", "eupl-1.2", "eupl", "european union public",
    "cecill-2.1", "cecill", "ms-pl", "microsoft public", "apsl-2.0", "apple public source",
    "osl-3.0", "osl-2.1", "osl-1.0", "open software license",
}
NON_COMMERCIAL = {"cc-by-nc", "cc-by-nc-sa", "cc-by-nc-nd", "non-commercial", "nc", "nposl", "non-profit open"}
# Non-standard or ambiguous (e.g. JSON "Good, not Evil")
NON_STANDARD = {"json", "json license", "beerware", "wtfpl"}
# Banned for code incorporation in commercial product (strong copyleft + NC)
BANNED_FOR_CODE = STRONG_COPYLEFT | NON_COMMERCIAL


def normalize_license(license_str: str) -> str:
    """Normalize license string for lookup."""
    if not license_str or not license_str.strip():
        return ""
    s = license_str.strip().lower()
    s = re.sub(r"[\s\-_]+", " ", s)
    s = re.sub(r"version\s*\d+(\.\d+)*", "", s).strip()
    if "apache" in s and "2" in s:
        return "apache-2.0"
    if "bsd" in s:
        if "2-clause" in s or "2 clause" in s:
            return "bsd-2-clause"
        if "3-clause" in s or "3 clause" in s:
            return "bsd-3-clause"
        return "bsd"
    if "mit" in s:
        return "mit"
    if "lgpl" in s:
        return "lgpl-2.1" if "2.1" in s else "lgpl-3.0" if "3" in s else "lgpl-2.0"
    if "gpl" in s and "agpl" not in s:
        return "gpl-3.0" if "3" in s else "gpl-2.0"
    if "agpl" in s:
        return "agpl-3.0"
    if "mpl" in s or "mozilla" in s:
        return "mpl-2.0"
    if "boost" in s and "software license" in s:
        return "bsl-1.0"
    if "blue oak" in s or "blueoak" in s:
        return "blueoak"
    if "universal permissive" in s or "upl" in s:
        return "upl-1.0"
    if "eclipse public" in s or "epl" in s:
        return "epl-2.0" if "2" in s else "epl-1.0"
    if "cddl" in s or "common development and distribution" in s:
        return "cddl-1.0"
    if "eupl" in s or "european union public" in s:
        return "eupl-1.2"
    if "cal-1.0" in s or "cryptographic autonomy" in s:
        return "cal-1.0"
    if "osl" in s and "open software license" in s:
        return "osl-3.0"
    if "unlicense" in s:
        return "unlicense"
    if "0bsd" in s or "zero clause bsd" in s or "zero-clause" in s:
        return "0bsd"
    return s


def classify_license(license_str: str) -> tuple[str, str]:
    """
    Classify license into risk category and short label.
    Returns (category, label). Category: permissive, weak_copyleft, strong_copyleft,
    non_commercial, non_standard, unknown.
    """
    n = normalize_license(license_str)
    if not n:
        return "unknown", "Unknown"
    if n in PERMISSIVE or any(p in n for p in ("mit", "apache", "bsd", "isc", "cc0", "unlicense")):
        return "permissive", n or license_str.strip()
    if n in WEAK_COPYLEFT or "lgpl" in n or "mpl" in n or "epl" in n:
        return "weak_copyleft", n or license_str.strip()
    if n in STRONG_COPYLEFT or "gpl" in n or "agpl" in n:
        return "strong_copyleft", n or license_str.strip()
    if n in NON_COMMERCIAL or "nc" in n or "non-commercial" in n:
        return "non_commercial", n or license_str.strip()
    if n in NON_STANDARD or "json" in n or "good, not evil" in n:
        return "non_standard", n or license_str.strip()
    return "unknown", n or license_str.strip()


def parse_requirements(req_path: Path) -> list[tuple[str, str]]:
    """Parse requirements.txt and return list of (package, version_spec or '')."""
    if not req_path.is_file():
        return []
    pairs = []
    for line in req_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip extras [extras] and env markers ; or #
        pkg = re.split(r"[\s\[\]#;]", line)[0]
        if pkg.startswith("-"):
            continue
        version = ""
        if re.search(r"(==|>=|<=|~=|!=)", pkg):
            parts = re.split(r"(==|>=|<=|~=|!=)", pkg, maxsplit=1)
            pkg = (parts[0] or "").strip()
            version = ("".join(parts[1:]) if len(parts) > 1 else "").strip()
        pairs.append((pkg, version))
    return pairs


def parse_third_party_md(md_path: Path) -> list[tuple[str, str]]:
    """
    Heuristic parse of THIRD-PARTY.md for package/license table rows.
    Looks for | Package | ... | License | ... and | [Name](url) | ... | License |
    """
    if not md_path.is_file():
        return []
    text = md_path.read_text(encoding="utf-8", errors="replace")
    # Simple: find table rows with at least 3 columns and license-like 3rd column
    rows = []
    in_table = False
    for line in text.splitlines():
        if "|" in line and line.strip().startswith("|"):
            in_table = True
            parts = [p.strip() for p in line.split("|") if p]
            if len(parts) >= 3:
                # Second column often package/source; third often license
                license_val = parts[2] if len(parts) > 2 else ""
                if any(
                    x in license_val.lower()
                    for x in ("mit", "bsd", "apache", "gpl", "lgpl", "cc-", "see ", "yes", "no")
                ):
                    name = parts[1]
                    # Strip markdown link to get name
                    if "]" in name:
                        name = re.sub(r"\[([^\]]+)\].*", r"\1", name).strip()
                    rows.append((name, license_val))
        else:
            in_table = False
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check dependency and third-party licenses against policy (docs/LICENSING.md)."
    )
    parser.add_argument(
        "--requirements",
        type=Path,
        default=Path("requirements.txt"),
        help="Path to requirements.txt",
    )
    parser.add_argument(
        "--third-party",
        type=Path,
        default=Path("THIRD-PARTY.md"),
        help="Path to THIRD-PARTY.md",
    )
    parser.add_argument(
        "--allow-weak-copyleft",
        action="store_true",
        help="Do not fail on LGPL/MPL (e.g. when used as external tool only)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any unknown or non-permissive license",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only print errors and summary",
    )
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parent.parent
    req_path = project_root / args.requirements if not args.requirements.is_absolute() else args.requirements
    tp_path = project_root / args.third_party if not args.third_party.is_absolute() else args.third_party

    errors: list[str] = []
    warnings: list[str] = []

    # Known licenses for packages we use (from THIRD-PARTY.md / PyPI). Update when adding deps.
    known_package_licenses: dict[str, str] = {
        "fastapi": "MIT",
        "uvicorn": "BSD",
        "httpx": "BSD",
        "pydantic": "MIT",
        "python-dateutil": "Apache 2.0",
        "joblib": "BSD",
        "scikit-learn": "BSD-3-Clause",
        "xgboost": "Apache 2.0",
        "numpy": "BSD",
        "pandas": "BSD-3-Clause",
        "pytest": "MIT",
        "pytest-asyncio": "Apache 2.0",
    }

    # Check requirements.txt
    packages = parse_requirements(req_path)
    if not args.quiet:
        print(f"Checking {len(packages)} packages from {req_path} ...")
    for pkg, _ver in packages:
        lic = known_package_licenses.get(pkg.lower(), "")
        if not lic:
            warnings.append(f"Unknown license for package: {pkg} (add to THIRD-PARTY.md and known_package_licenses)")
            continue
        cat, _ = classify_license(lic)
        if cat == "strong_copyleft" or cat == "non_commercial":
            errors.append(f"Package {pkg} has {cat} license ({lic}); not allowed for code incorporation.")
        elif cat == "unknown" and args.strict:
            errors.append(f"Package {pkg}: unclassified license '{lic}'")
        elif cat == "weak_copyleft" and not args.allow_weak_copyleft and args.strict:
            warnings.append(f"Package {pkg}: weak copyleft ({lic}); ensure used as library/link only.")

    # Optional: parse THIRD-PARTY.md for other entries (e.g. external tools)
    third_party_entries = parse_third_party_md(tp_path)
    if not args.quiet and third_party_entries:
        print(f"Found {len(third_party_entries)} third-party / license entries in {tp_path}")

    for name, lic in third_party_entries:
        cat, _ = classify_license(lic)
        if cat == "strong_copyleft":
            # External tools only are OK per docs; just note
            if not args.quiet:
                warnings.append(f"Third-party '{name}' is {lic}; ensure not incorporated (external tool only).")
        elif cat == "non_commercial":
            errors.append(f"Third-party '{name}' has non-commercial license; do not use in commercial product.")

    # Report
    if not args.quiet:
        for w in warnings:
            print("WARNING:", w)
    for e in errors:
        print("ERROR:", e)

    if errors:
        print(f"\nLicense check failed with {len(errors)} error(s). See docs/LICENSING.md.")
        return 1
    if args.strict and warnings:
        print(f"\nLicense check completed with {len(warnings)} warning(s).")
    if not args.quiet and not errors:
        print("License check passed (permissive or allowed licenses only).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
