def main() -> None:
    ...
    data = json.loads(report_path.read_text(encoding="utf-8"))
    findings = data.get("findings") or []

    grouped: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        grouped[_safe(f.get("decision"))].append(f)
...
    def emit_section(title: str, items: list[dict]) -> None:
        lines.append("=" * len(title))
        lines.append(title)
        lines.append("=" * len(title))
        lines.append("")
        if not items:
            lines.append("None")
            lines.append("")
            return
        for f in sorted(items, key=lambda x: (_safe(x.get("name")), _safe(x.get("version")))):
            lines.append(f"- Artifact: {_safe(f.get('name'))} {_safe(f.get('version'))}".rstrip())
            lines.append(f"  ID: {_safe(f.get('artifact_id'))}")
            lines.append(f"  Usage: {_safe(f.get('usage'))}")
            lines.append(f"  License: {_safe(f.get('license_expression'))}")
            src = _safe(f.get("source"))
            if src:
                lines.append(f"  Source: {src}")
...
            obligations = f.get("obligations") or []
            if obligations:
                lines.append("  Obligations:")
                for o in obligations:
                    lines.append(f"    - {_safe(o)}")
...
    emit_section("ALLOWED COMPONENTS", grouped.get("ALLOW", []))
    emit_section("REVIEW REQUIRED", grouped.get("REVIEW", []))
    emit_section("DENIED COMPONENTS", grouped.get("DENY", []))

    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
