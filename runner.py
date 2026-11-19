"""Run a scripted agent version against a suite.

Criteria are evaluated per run, pass/fail each -- NEVER one weighted
score:
  1. per-slice success floor (>= floor for every slice)
  2. zero-tolerance: zero failures in any zero-tolerance class
  3. latency ceiling: p95 latency <= threshold (one simple criterion)

Overall verdict is ACCEPTED only if every criterion passes; any
failure -- including a zero-tolerance failure on an otherwise
improved average -- yields REJECTED.
"""
from __future__ import annotations

import math
import random

from profiles import get_profile
from suite import case_set_hash, validate_suite


def p95(values):
    if not values:
        return 0
    ordered = sorted(values)
    idx = math.ceil(0.95 * len(ordered)) - 1
    return ordered[max(0, idx)]


def _latency_ms(seed: int, ordinal: int) -> int:
    rng = random.Random(seed * 10000 + ordinal)
    return rng.randint(400, 1200)


def run_version(suite: dict, version: str) -> dict:
    issues = validate_suite(suite)
    if issues:
        raise ValueError(f"invalid suite: {issues}")
    profile = get_profile(version)
    crit = suite["criteria"]
    floor = crit["slice_success_floor"]
    zero_classes = set(crit["zero_tolerance_classes"])
    threshold = crit["latency_p95_threshold_ms"]

    results = []
    for ordinal, case in enumerate(suite["cases"]):
        failed = case["id"] in profile["fail_ids"]
        results.append({
            "id": case["id"],
            "slice": case["slice"],
            "failure_class": case["failure_class"],
            "expected_outcome": case["expected_outcome"],
            "outcome": "fail" if failed else "pass",
            "latency_ms": _latency_ms(profile["seed"], ordinal),
        })

    per_slice = {}
    for slice_name in sorted({c["slice"] for c in suite["cases"]}):
        rows = [r for r in results if r["slice"] == slice_name]
        passed = sum(1 for r in rows if r["outcome"] == "pass")
        per_slice[slice_name] = {
            "total": len(rows),
            "passed": passed,
            "success_rate": round(passed / len(rows), 6) if rows else 0.0,
        }

    total = len(results)
    passed_total = sum(1 for r in results if r["outcome"] == "pass")
    average = round(passed_total / total, 6) if total else 0.0

    floor_failures = {s: v["success_rate"] for s, v in per_slice.items()
                      if v["success_rate"] < floor}
    zero_failures = [r for r in results
                     if r["outcome"] == "fail" and r["failure_class"] in zero_classes]
    latency_p95 = p95([r["latency_ms"] for r in results])

    criteria = [
        {
            "id": "per_slice_success_floor",
            "passed": not floor_failures,
            "details": {"floor": floor, "per_slice": per_slice,
                        "failing_slices": floor_failures},
        },
        {
            "id": "zero_tolerance",
            "passed": not zero_failures,
            "details": {
                "zero_tolerance_classes": sorted(zero_classes),
                "failure_count": len(zero_failures),
                "failed_cases": [
                    {"id": r["id"], "slice": r["slice"],
                     "failure_class": r["failure_class"]}
                    for r in zero_failures
                ],
            },
        },
        {
            "id": "latency_p95",
            "passed": latency_p95 <= threshold,
            "details": {"p95_ms": latency_p95, "threshold_ms": threshold},
        },
    ]
    verdict = "ACCEPTED" if all(c["passed"] for c in criteria) else "REJECTED"
    return {
        "suite_version": suite["suite_version"],
        "suite_hash": case_set_hash(suite),
        "agent_version": version,
        "total_cases": total,
        "passed_cases": passed_total,
        "average_success": average,
        "per_slice": per_slice,
        "criteria": criteria,
        "verdict": verdict,
        "cases": results,
    }


def criterion(report: dict, criterion_id: str) -> dict:
    for c in report["criteria"]:
        if c["id"] == criterion_id:
            return c
    raise KeyError(criterion_id)
