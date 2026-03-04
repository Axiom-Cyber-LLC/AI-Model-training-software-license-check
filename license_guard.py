@dataclass
class Policy:
    categories: Dict[str, Set[str]]
    defaults_unknown: Decision
    defaults_unparsable: Decision
    rules: List[Dict[str, Any]]
    overrides: Dict[str, Any]
    requirements: Dict[str, Any]
...
def evaluate(
    policy: Policy,
    artifacts: List[Dict[str, Any]],
    *,
    distribution_mode: str = "internal",
    exceptions: List[ExceptionRule] | None = None,
) -> Tuple[List[Finding], int]:
    findings: List[Finding] = []
    exit_code = 0
    exceptions = exceptions or []

    for a in artifacts:
        artifact_id = str(a.get("id") or a.get("name") or "unknown")
        name = str(a.get("name") or artifact_id)
        version = str(a.get("version") or "")
        usage = str(a.get("usage") or "build")
        expr = str(a.get("license_expression") or "NOASSERTION")
        source = a.get("source")
        artifact_type = str(a.get("type") or "code")

        decision, reasons, obligations = policy.decide_expression(
            expr,
            usage,
            distribution_mode=distribution_mode,
            artifact_type=artifact_type,
        )

        # Enforce strict metadata requirements (license_files / terms_url, etc.)
        decision, reasons = policy.enforce_requirements(
            artifact=a,
            decision=decision,
            reasons=reasons,
            distribution_mode=distribution_mode,
        )

        # Apply exceptions (ticketed)
        decision, reasons, obligations = apply_exception(
            exceptions=exceptions,
            artifact_id=artifact_id,
            usage=usage,
            distribution_mode=distribution_mode,
            decision=decision,
            reasons=reasons,
            obligations=obligations,
        )

        if decision == "DENY":
            exit_code = max(exit_code, 3)
        elif decision == "REVIEW":
            exit_code = max(exit_code, 1)

        findings.append(Finding(
            artifact_id=artifact_id,
            name=name,
            version=version,
            usage=usage,
            license_expression=expr,
            decision=decision,
            reasons=reasons,
            obligations=obligations,
            source=source,
        ))

    return findings, exit_code
...
def main(argv: List[str]) -> int:
    if len(argv) < 3:
        print("Usage: license_guard.py <policy.yml> <input.json> [output.json] [--distribution-mode MODE] [--exceptions PATH]", file=sys.stderr)
        return 2
...
    policy = Policy.load(policy_path)
    artifacts = load_artifacts(input_path)

    exceptions = load_exceptions(exceptions_path)
    findings, code = evaluate(
        policy,
        artifacts,
        distribution_mode=distribution_mode,
        exceptions=exceptions,
    )

    report = {
        "summary": {
            "allow": sum(1 for f in findings if f.decision == "ALLOW"),
            "review": sum(1 for f in findings if f.decision == "REVIEW"),
            "deny": sum(1 for f in findings if f.decision == "DENY"),
        },
        "findings": [f.__dict__ for f in findings],
    }

    out = json.dumps(report, indent=2)
    if out_path:
        out_path.write_text(out, encoding="utf-8")
    else:
        print(out)

    return code
