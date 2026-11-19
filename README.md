# acceptance-suite-regression-kit

**A customer acceptance suite as a versioned contract — per-criterion pass/fail verdicts, a zero-tolerance veto that rejects an agent whose average *improved*, and a compare mode that refuses to diff runs from different suite versions ("suite drift, not agent drift").**

When a customer POC ends, the question is not "what was the average score?" — it is "did the agent meet the acceptance criteria we agreed?" This kit models that agreement directly: a **suite** is a versioned JSON definition (`suite_version` plus cases grouped by **slice** — one segment of the workload), where each case declares its slice, its **failure class** (the kind of failure a miss on that case counts as), and its expected outcome. A run is judged on separate criteria, pass/fail each, never collapsed into one weighted score:

1. **Per-slice success floor** — every slice must reach ≥ 0.90 success.
2. **Zero-tolerance** — zero failures in the zero-tolerance class (`pii_leak` in the seeded suite).
3. **Latency ceiling** — p95 latency must be at or under the threshold (the kit's single latency criterion).

The verdict is **ACCEPTED** only if every criterion passes. The build was motivated by an Anthropic Applied AI Commercial job description (2026-11-19) calling for "evaluation suites that become the customer's acceptance criteria"; it is an original implementation, not a reproduction of any company's process.

> **Synthetic data only.** The suite, the cases, and all three "agent versions" are fabricated. The agent versions are scripted, deterministic seeded outcome profiles — stand-ins, not real agents, with no LLM and no network anywhere in the kit.

Stdlib-only Python — deliberately. An acceptance artifact a customer signs off on should be readable line by line, re-runnable offline, and byte-identical on every run.

## The headline: a better average that gets rejected

| Version | Average success | Slice floors | Zero-tolerance | Latency p95 | Verdict |
|---|---|---|---|---|---|
| v1 (baseline) | 0.933333 (56/60) | pass | pass (0 failures) | 1133 ms ≤ 2000 ms | **ACCEPTED** |
| v2 | **0.966667 (58/60)** | pass | **fail — 1 failure** | 1173 ms ≤ 2000 ms | **REJECTED** |
| v1b (control) | 0.933333 (56/60) | pass | pass | 1133 ms ≤ 2000 ms | **ACCEPTED** |

v2 fails only two cases where v1 fails four — and one of v2's failures is case `BIL-010`, a `pii_leak` case in the **billing** slice. That single zero-tolerance failure rejects v2 even though its average improved and every slice still clears its floor. A headline average would have shipped it; per-criterion acceptance does not.

**Compare mode** diffs two run reports into per-criterion **flips** (pass→fail, fail→pass) with per-case evidence: v1 → v2 flips exactly one criterion, `zero_tolerance`, with `BIL-010` as the evidence. The control profile **v1b** is identical in behaviour to v1, and v1 → v1b diffs to zero flips, as a no-change comparison must. Each run report records the `suite_version` and a SHA-256 hash of the case set; if either differs between the two reports, compare **refuses** and reports "suite drift, not agent drift" — a changed yardstick is not a regression.

## How this differs from agent-eval-dashboard

A sibling shipped repo, **agent-eval-dashboard**, already shows a headline-score trend across runs. This kit is deliberately different: it has no headline score at all. It reports per-criterion pass/fail flips between two runs, a zero-tolerance veto that can override an improved average, and a suite-drift refusal when the two runs were not measured against the same suite. A trend line answers "is the number going up?"; this kit answers "would the customer accept this version, and what exactly changed?"

## Quickstart

```bash
python3 demo.py                                   # end-to-end demo, exit 0
python3 cli.py demo                               # same demo via the CLI
python3 cli.py run --version v1 --out v1.json     # run a version, JSON report
python3 cli.py run --version v2 --out v2.json
python3 cli.py compare --from-report v1.json --to-report v2.json --markdown diff.md
python3 -m unittest discover -s tests             # 26 tests
python3 evals/run_evals.py                        # 13 golden evals
```

Output is a JSON run report plus a markdown diff summary only — no dashboard, no HTML, no server.

## How it works

**The suite.** `suite.py` generates and validates the seeded suite: 3 slices (support / billing / onboarding) × 20 cases, 12 of them `pii_leak` probes (every 5th case per slice), the rest cycling ordinary failure classes (`task_error`, `tone_error`, `refusal_error`). `case_set_hash` hashes only the canonical case set, so a version bump and a case change are detected independently.

**The profiles.** `profiles.py` defines the scripted versions as explicit fail sets plus a latency seed: v1 fails four ordinary cases; v2 fails two cases, one of them the billing `pii_leak` probe `BIL-010`; v1b reuses v1's fail set and seed exactly, which is what makes it a true no-flip control (identical outcomes *and* latencies).

**The runner.** `runner.py` evaluates the three criteria independently and folds them into ACCEPTED / REJECTED (rejected if any criterion fails). Per-case latency is recorded on every result row, generated from the profile seed so runs are deterministic.

**Compare.** `compare.py` checks `suite_version` and the case-set hash before diffing anything, then emits flips only for criteria whose pass/fail actually changed, each with the differing cases that evidence it, and renders the markdown summary.

## Architecture

| Module | Job |
|---|---|
| `suite.py` | Suite generation, validation, canonical case-set hash, JSON load/write |
| `profiles.py` | The three scripted agent versions (fail sets + latency seeds) |
| `runner.py` | Run a version against a suite: per-slice rates, the three criteria, ACCEPTED/REJECTED, p95 |
| `compare.py` | Suite-drift refusal, per-criterion flips with per-case evidence, markdown diff summary |
| `generator.py` | Re-exports the suite generator for fixture generation |
| `cli.py` | `demo` / `run` / `compare` (exit 0 on success, 2 on IO/usage error) |
| `demo.py` | End-to-end demo with asserts: headline rejection, no-flip control, drift refusal |
| `fixtures/` | The seeded suite (`suite.json`, suite_version 1.0.0, 60 cases) |

## Evals

`python3 evals/run_evals.py` → **13/13 golden evals**, report committed at `evals/eval_report.json`:

- **E1–E2** generator determinism — suite JSON md5 and case-set hash pinned
- **E3–E4** headline pinned — v1 average 0.933333 ACCEPTED; v2 average 0.966667 REJECTED
- **E5–E6** rejection cause pinned — zero-tolerance `billing` / `pii_leak` case `BIL-010`, and *not* a floor or latency failure
- **E7** latency p95 pinned (v1 1133 ms, v2 1173 ms, threshold 2000 ms)
- **E8–E9** diffs pinned — v1→v2 exactly one flip (`zero_tolerance` pass→fail, evidence `BIL-010`); v1→v1b zero flips
- **E10–E11** suite-drift refusal pinned — mismatched `suite_version`, and mismatched case-set hash at the same version
- **E12** bundled fixture pinned — loading `fixtures/suite.json` reproduces the generated suite and its v2 run exactly
- **E13** CLI demo exits 0 and is deterministic

Unit tests: `python3 -m unittest discover -s tests` → **26 hermetic tests**, including a no-network enforcement test (sockets stubbed), hand-computed p95, drift refusal by version and by hash, and CLI run/compare round-trips.

## How this would be used in a customer POC

The customer and the deployment team agree the suite and its criteria up front — slices that mirror their real workload, the floor per slice, and the one failure class neither side will tolerate at any average. That signed-off suite is versioned and frozen for the POC. Every candidate agent version is run against it; a version ships only on ACCEPTED, and a regression review is a compare diff: which criteria flipped, and which cases prove it. If the customer wants to change the yardstick mid-POC, the suite version bumps — and old runs stop being comparable, on purpose, instead of quietly diffing against a moved target.

## Scope and honest limits

- **Scripted policies are deterministic stand-ins, not real agents.** Fail sets are curated so the golden scenario is exact and reviewable; a real integration would replace `profiles.py` with an adapter that runs an actual agent and records the same per-case outcome and latency fields. Nothing here measures a real model's quality.
- **Outcomes are binary.** A case passes or fails against its expected outcome; there is no partial credit, rubric scoring, or judge model — acceptance criteria in a POC are usually binary at the case level, but richer scoring would need a different case model.
- **Latency gets one simple criterion.** p95 against one threshold, recorded from the profile seed — synthetic latencies in a plausible range, not measured timings, and no budget or cost logic of any kind.
- **The floor and threshold are the seeded suite's values.** 0.90 per slice and 2000 ms are plausible POC numbers chosen for the demo, not recommendations; a real engagement negotiates them per customer.
- **Drift refusal is all-or-nothing.** Any case-set change refuses the whole diff rather than diffing the intersection — conservative by design, since a partial diff can hide exactly the case that changed.

## Why this project

It takes the least visible part of forward-deployed AI work — turning "the customer will know it works when…" into a versioned, testable acceptance contract — and builds the discipline around it: judge per criterion, never by one blended score; let a zero-tolerance failure veto an improved average; and refuse to call a changed suite an agent regression. That is the difference between an eval that produces a number and an acceptance suite a customer can sign.
