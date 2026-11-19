"""End-to-end demo with asserts. Deterministic; exits 0."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import demo_text  # noqa: E402
from compare import compare_reports  # noqa: E402
from runner import run_version  # noqa: E402
from suite import generate_suite  # noqa: E402


def main() -> None:
    suite = generate_suite()
    v1, v2, v1b = (run_version(suite, v) for v in ("v1", "v2", "v1b"))
    assert v2["average_success"] > v1["average_success"]
    assert v1["verdict"] == "ACCEPTED" and v2["verdict"] == "REJECTED"
    assert compare_reports(v1, v1b)["flips"] == []
    drift = compare_reports(v1, run_version(generate_suite("1.1.0"), "v1"))
    assert drift["status"] == "REFUSED"
    sys.stdout.write(demo_text())


if __name__ == "__main__":
    main()
