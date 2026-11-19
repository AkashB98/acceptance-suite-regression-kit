"""CLI: demo / run / compare. JSON report + markdown diff only."""
from __future__ import annotations

import argparse
import json
import sys

from compare import compare_reports, render_markdown_diff
from runner import run_version
from suite import generate_suite, load_suite

EXIT_OK, EXIT_ERROR = 0, 2


def _write_json(obj, path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _load_report(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def demo_text() -> str:
    suite = generate_suite()
    v1 = run_version(suite, "v1")
    v2 = run_version(suite, "v2")
    v1b = run_version(suite, "v1b")
    diff_v2 = compare_reports(v1, v2)
    diff_v1b = compare_reports(v1, v1b)
    drift_suite = generate_suite(suite_version="1.1.0")
    drift = compare_reports(v1, run_version(drift_suite, "v1"))
    zero = next(c for c in v2["criteria"] if c["id"] == "zero_tolerance")
    failed = zero["details"]["failed_cases"]
    lines = [
        "== acceptance-suite-regression-kit demo ==",
        f"suite_version={suite['suite_version']} cases={v1['total_cases']}",
        f"v1: average_success={v1['average_success']} verdict={v1['verdict']}",
        f"v2: average_success={v2['average_success']} verdict={v2['verdict']}",
        f"v2 improved on average ({v2['average_success']} > {v1['average_success']}) "
        f"but is REJECTED: zero-tolerance failure "
        + ", ".join(f"{f['id']} ({f['slice']}/{f['failure_class']})" for f in failed),
        f"compare v1->v2: flips={[f['criterion'] for f in diff_v2['flips']]}",
        f"compare v1->v1b: flips={len(diff_v1b['flips'])} (no-flip control)",
        f"compare mismatched suite_version: status={drift['status']} "
        f"reason='{drift['reason']}'",
        "Demo OK: improved average does not override a zero-tolerance veto.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo")
    p_run = sub.add_parser("run")
    p_run.add_argument("--version", required=True)
    p_run.add_argument("--suite", default=None)
    p_run.add_argument("--out", default=None)
    p_cmp = sub.add_parser("compare")
    p_cmp.add_argument("--from-report", required=True)
    p_cmp.add_argument("--to-report", required=True)
    p_cmp.add_argument("--out", default=None)
    p_cmp.add_argument("--markdown", default=None)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "demo":
            sys.stdout.write(demo_text())
            return EXIT_OK
        if args.cmd == "run":
            suite = load_suite(args.suite) if args.suite else generate_suite()
            report = run_version(suite, args.version)
            if args.out:
                _write_json(report, args.out)
            else:
                sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
            return EXIT_OK
        if args.cmd == "compare":
            diff = compare_reports(_load_report(args.from_report),
                                   _load_report(args.to_report))
            if args.out:
                _write_json(diff, args.out)
            if args.markdown:
                with open(args.markdown, "w", encoding="utf-8") as fh:
                    fh.write(render_markdown_diff(diff))
            if not args.out and not args.markdown:
                sys.stdout.write(json.dumps(diff, indent=2, sort_keys=True) + "\n")
            return EXIT_OK
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
