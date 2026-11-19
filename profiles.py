"""Scripted agent versions: deterministic seeded outcome profiles.

These are deterministic stand-ins, not real agents. Each profile
names the case ids it fails (a curated, seeded simulation) and a
seed that drives its per-case latency. No LLM, no network.

- v1: baseline. Fails 4 ordinary cases, no pii_leak case.
- v2: higher average success than v1 (fails only 2 cases), but one
  failure is BIL-010, a pii_leak case in the billing slice -- the
  zero-tolerance failure that must reject it.
- v1b: a clean control identical in behaviour to v1 (same fail set,
  same seed, hence same latencies), for the no-flip control.
"""
from __future__ import annotations

_V1_FAILS = frozenset({"SUP-003", "BIL-007", "ONB-004", "ONB-012"})

PROFILES = {
    "v1": {"seed": 101, "fail_ids": _V1_FAILS},
    "v2": {"seed": 202, "fail_ids": frozenset({"BIL-010", "ONB-003"})},
    "v1b": {"seed": 101, "fail_ids": _V1_FAILS},
}

VERSIONS = tuple(PROFILES.keys())


def get_profile(version: str) -> dict:
    if version not in PROFILES:
        raise ValueError(f"unknown agent version: {version!r} (known: {sorted(PROFILES)})")
    return PROFILES[version]
