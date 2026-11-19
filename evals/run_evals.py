"""Golden evals for acceptance-suite-regression-kit.

SYNTHETIC DATA ONLY. Deterministic: eval_report.json must be
byte-identical across runs. No timestamps or temp paths in the report.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli import main as cli_main  # noqa: E402
from compare import compare_reports  # noqa: E402
from runner import criterion, run_version  # noqa: E402
from suite import case_set_hash, generate_suite, load_suite, suite_to_json  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = []


def check(name, passed, detail=""):
    RESULTS.append({"name": name, "passed": bool(passed), "detail": detail})
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    return passed


def main():
    print("== golden evals: acceptance-suite-regression-kit ==")
    suite = generate_suite()
    v1, v2, v1b = (run_version(suite, v) for v in ("v1", "v2", "v1b"))

    md5 = hashlib.md5(suite_to_json(suite).encode()).hexdigest()
    check("E1 generator determinism (suite md5 pinned)",
          suite_to_json(generate_suite()) == suite_to_json(suite)
          and md5 == "ca30b688cfec590e8db029f767d3b4d4", f"md5={md5}")

    check("E2 suite hash pinned",
          case_set_hash(suite) == "bcbfcf6a65e545cbd232973cb43f4d69975ff121562a318179fe857a4ea512c2",
          f"hash={case_set_hash(suite)}")

    check("E3 headline averages pinned (v1 0.933333, v2 0.966667, v2 > v1)",
          v1["average_success"] == 0.933333 and v2["average_success"] == 0.966667
          and v2["average_success"] > v1["average_success"])

    check("E4 verdicts pinned (v1 ACCEPTED, v2 REJECTED)",
          v1["verdict"] == "ACCEPTED" and v2["verdict"] == "REJECTED")

    z = criterion(v2, "zero_tolerance")
    check("E5 v2 rejection pinned to zero-tolerance billing/pii_leak BIL-010",
          not z["passed"] and z["details"]["failure_count"] == 1
          and z["details"]["failed_cases"] == [
              {"id": "BIL-010", "slice": "billing", "failure_class": "pii_leak"}])

    check("E6 v2 rejection is NOT a floor or latency failure",
          criterion(v2, "per_slice_success_floor")["passed"]
          and criterion(v2, "latency_p95")["passed"])

    check("E7 latency p95 pinned (v1 1133, v2 1173, threshold 2000)",
          criterion(v1, "latency_p95")["details"] == {"p95_ms": 1133, "threshold_ms": 2000}
          and criterion(v2, "latency_p95")["details"] == {"p95_ms": 1173, "threshold_ms": 2000})

    d = compare_reports(v1, v2)
    check("E8 v1->v2 diff pinned (exactly one flip: zero_tolerance pass->fail, evidence BIL-010)",
          len(d["flips"]) == 1 and d["flips"][0]["criterion"] == "zero_tolerance"
          and (d["flips"][0]["from"], d["flips"][0]["to"]) == ("pass", "fail")
          and [e["id"] for e in d["flips"][0]["evidence"]] == ["BIL-010"])

    check("E9 no-flip control pinned (v1 vs v1b = zero flips)",
          compare_reports(v1, v1b)["flips"] == [])

    drift = compare_reports(v1, run_version(generate_suite("1.1.0"), "v1"))
    check("E10 suite drift refusal pinned (mismatched suite_version)",
          drift["status"] == "REFUSED" and drift["reason"] == "suite drift, not agent drift")

    s2 = generate_suite(); s2["cases"] = s2["cases"][:-1] + [dict(s2["cases"][-1], id="ONB-099")]
    drift2 = compare_reports(v1, run_version(s2, "v1"))
    check("E11 suite drift refusal pinned (mismatched case-set hash, same version)",
          drift2["status"] == "REFUSED")

    fixture = load_suite(os.path.join(ROOT, "fixtures", "suite.json"))
    check("E12 fixture pinned (loaded fixture equals generated suite)",
          fixture == suite and run_version(fixture, "v2") == v2)

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli_main(["demo"])
    check("E13 CLI demo exit 0 and deterministic",
          code == 0 and "REJECTED" in buf.getvalue())

    passed = sum(1 for r in RESULTS if r["passed"])
    total_n = len(RESULTS)
    doc = {"passed": passed, "total": total_n, "all_passed": passed == total_n, "evals": RESULTS}
    with open(os.path.join(HERE, "eval_report.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, sort_keys=True) + "\n")
    print(f"\n{passed}/{total_n} evals passed -> evals/eval_report.json")
    return 0 if passed == total_n else 1


if __name__ == "__main__":
    sys.exit(main())
