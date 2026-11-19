"""Compare two run reports: per-criterion flips with evidence.

Suite versioning guard: each report records suite_version and a
hash of the case set. If either differs, compare REFUSES to diff --
that is suite drift, not agent drift.
"""
from __future__ import annotations


def _diff_cases(a: dict, b: dict):
    by_id_a = {c["id"]: c for c in a["cases"]}
    return [c for c in b["cases"]
            if c["id"] in by_id_a and by_id_a[c["id"]]["outcome"] != c["outcome"]]


def _evidence(criterion_id: str, a: dict, b: dict, diffs: list):
    if criterion_id == "zero_tolerance":
        classes = set(a["criteria"][1]["details"]["zero_tolerance_classes"])
        rows = [c for c in diffs if c["failure_class"] in classes]
    elif criterion_id == "per_slice_success_floor":
        rows = diffs
    elif criterion_id == "latency_p95":
        rows = sorted(diffs, key=lambda c: -c["latency_ms"])
    else:
        rows = diffs
    by_id_a = {c["id"]: c for c in a["cases"]}
    return [{"id": c["id"], "slice": c["slice"],
             "failure_class": c["failure_class"],
             "from_outcome": by_id_a[c["id"]]["outcome"],
             "to_outcome": c["outcome"]} for c in rows]


def compare_reports(a: dict, b: dict) -> dict:
    if a["suite_version"] != b["suite_version"] or a["suite_hash"] != b["suite_hash"]:
        return {
            "status": "REFUSED",
            "reason": "suite drift, not agent drift",
            "from_version": a["agent_version"],
            "to_version": b["agent_version"],
            "suite_version_from": a["suite_version"],
            "suite_version_to": b["suite_version"],
            "suite_hash_from": a["suite_hash"],
            "suite_hash_to": b["suite_hash"],
            "flips": [],
        }
    diffs = _diff_cases(a, b)
    crit_a = {c["id"]: c for c in a["criteria"]}
    crit_b = {c["id"]: c for c in b["criteria"]}
    flips = []
    for cid in crit_a:
        if crit_a[cid]["passed"] != crit_b[cid]["passed"]:
            flips.append({
                "criterion": cid,
                "from": "pass" if crit_a[cid]["passed"] else "fail",
                "to": "pass" if crit_b[cid]["passed"] else "fail",
                "evidence": _evidence(cid, a, b, diffs),
            })
    return {
        "status": "COMPARED",
        "reason": "",
        "from_version": a["agent_version"],
        "to_version": b["agent_version"],
        "suite_version": a["suite_version"],
        "suite_hash": a["suite_hash"],
        "average_success_from": a["average_success"],
        "average_success_to": b["average_success"],
        "verdict_from": a["verdict"],
        "verdict_to": b["verdict"],
        "flips": flips,
    }


def render_markdown_diff(diff: dict) -> str:
    lines = ["# Acceptance diff summary", ""]
    if diff["status"] == "REFUSED":
        lines += [f"**REFUSED:** {diff['reason']}.",
                  f"- suite_version: {diff['suite_version_from']} -> {diff['suite_version_to']}",
                  f"- suite_hash: {diff['suite_hash_from']} -> {diff['suite_hash_to']}", ""]
        return "\n".join(lines)
    lines += [
        f"- Agent: {diff['from_version']} -> {diff['to_version']}",
        f"- Suite: {diff['suite_version']} ({diff['suite_hash']})",
        f"- Average success: {diff['average_success_from']} -> {diff['average_success_to']}",
        f"- Verdict: {diff['verdict_from']} -> {diff['verdict_to']}",
        f"- Criterion flips: {len(diff['flips'])}",
        "",
    ]
    for flip in diff["flips"]:
        lines.append(f"## {flip['criterion']}: {flip['from']} -> {flip['to']}")
        for ev in flip["evidence"]:
            lines.append(f"- {ev['id']} ({ev['slice']}, {ev['failure_class']}): "
                         f"{ev['from_outcome']} -> {ev['to_outcome']}")
        lines.append("")
    return "\n".join(lines)
