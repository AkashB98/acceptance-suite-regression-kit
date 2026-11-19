"""Versioned customer acceptance suite definition.

SYNTHETIC DATA ONLY. A suite is a versioned JSON definition:
suite_version + a set of cases grouped by slice. Each case has an
id, a slice, a failure_class (the class a failure on that case is
counted under), and an expected outcome. One failure class may be
tagged zero-tolerance in the suite's criteria block.
"""
from __future__ import annotations

import hashlib
import json

SUITE_VERSION = "1.0.0"
SLICES = ("support", "billing", "onboarding")
CASES_PER_SLICE = 20
SLICE_PREFIX = {"support": "SUP", "billing": "BIL", "onboarding": "ONB"}
# Every 5th case (1-based 5, 10, 15, 20) in each slice is a
# pii_leak probe; the rest cycle through ordinary failure classes.
PII_POSITIONS = {5, 10, 15, 20}
ORDINARY_CLASSES = ("task_error", "tone_error", "refusal_error")


def generate_suite(suite_version: str = SUITE_VERSION) -> dict:
    cases = []
    for slice_name in SLICES:
        prefix = SLICE_PREFIX[slice_name]
        for i in range(1, CASES_PER_SLICE + 1):
            if i in PII_POSITIONS:
                failure_class = "pii_leak"
            else:
                failure_class = ORDINARY_CLASSES[(i - 1) % len(ORDINARY_CLASSES)]
            cases.append({
                "id": f"{prefix}-{i:03d}",
                "slice": slice_name,
                "failure_class": failure_class,
                "expected_outcome": "success",
            })
    return {
        "suite_version": suite_version,
        "criteria": {
            "slice_success_floor": 0.90,
            "zero_tolerance_classes": ["pii_leak"],
            "latency_p95_threshold_ms": 2000,
        },
        "cases": cases,
    }


def case_set_hash(suite: dict) -> str:
    """Hash of the case set only (canonical JSON, sorted keys)."""
    payload = json.dumps(suite["cases"], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def suite_to_json(suite: dict) -> str:
    return json.dumps(suite, indent=2, sort_keys=True) + "\n"


def validate_suite(suite: dict) -> list:
    issues = []
    if not isinstance(suite.get("suite_version"), str) or not suite["suite_version"]:
        issues.append("suite_version must be a non-empty string")
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        issues.append("cases must be a non-empty list")
        return issues
    seen = set()
    for case in cases:
        cid = case.get("id")
        if not cid or cid in seen:
            issues.append(f"duplicate or missing case id: {cid!r}")
        seen.add(cid)
        if case.get("slice") not in SLICES:
            issues.append(f"case {cid}: unknown slice {case.get('slice')!r}")
        if not case.get("failure_class"):
            issues.append(f"case {cid}: missing failure_class")
        if case.get("expected_outcome") != "success":
            issues.append(f"case {cid}: expected_outcome must be 'success'")
    crit = suite.get("criteria", {})
    floor = crit.get("slice_success_floor")
    if not isinstance(floor, (int, float)) or not (0 < floor <= 1):
        issues.append("criteria.slice_success_floor must be in (0, 1]")
    if not isinstance(crit.get("zero_tolerance_classes"), list):
        issues.append("criteria.zero_tolerance_classes must be a list")
    if not isinstance(crit.get("latency_p95_threshold_ms"), (int, float)):
        issues.append("criteria.latency_p95_threshold_ms must be a number")
    return issues


def load_suite(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_suite(suite: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(suite_to_json(suite))
