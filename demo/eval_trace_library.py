"""
TraceLens Trace Library — classification evaluation harness.

Answers one question: for each curated Trace Library scenario, does the
investigation pipeline return the category the scenario was designed to
produce?

Expected categories come exclusively from demo/trace_library_eval.json —
the eval-only manifest written by demo/seed_trace_library.py. Nothing is
hard-coded here, deliberately: the whole point of that file's physical
separation from the public manifest is that ground truth lives in exactly
one place. Add a scenario there and it is evaluated here with no change to
this script.

Runs the REAL pipeline over the ALREADY-SEEDED evidence, through the same
HTTP endpoints the UI calls:

    POST /api/v1/incidents            (evidence_ids -> auto-link + correlate)
    POST /api/v1/incidents/{id}/investigate

so there is no second, divergent copy of the investigation flow to keep in
sync. That means it makes one live LLM call per scenario and costs real
money; it is a harness, not a test, and is not part of backend/tests/.

Test data: the only rows this creates are one incident per scenario (plus
its evidence links and the resulting investigation), each tagged with a
unique run id. All of them are deleted in a `finally` block. The seeded
traces/evidence/projects are read-only here and never touched — the
incident has to be created inside the scenario's own project, because
correlation scopes its window expansion by incident.project_id, and moving
it elsewhere would silently change the pipeline being measured.

Run (backend + Postgres up, from repo root):

    .venv/bin/python demo/eval_trace_library.py            # all scenarios
    .venv/bin/python demo/eval_trace_library.py 1 4 10     # by position

Requires the Trace Library to have been seeded (demo/seed_trace_library.py)
against the current Postgres volume — see demo/README.md.
"""

import json
import os
import subprocess
import sys
from uuid import UUID, uuid4

import requests

API = "http://localhost:8000/api/v1"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PUBLIC_MANIFEST_PATH = os.path.join(REPO_ROOT, "frontend/src/data/trace-library.json")
EVAL_MANIFEST_PATH = os.path.join(REPO_ROOT, "demo/trace_library_eval.json")


def load_scenarios(only: list[int]) -> list[dict]:
    """
    Joins the public manifest (evidence ids) to the eval manifest
    (expected categories) on scenario id. A scenario missing from either
    file is a seeding mismatch, so it fails loudly rather than being
    silently skipped and quietly inflating accuracy.
    """
    with open(PUBLIC_MANIFEST_PATH) as f:
        public = json.load(f)
    with open(EVAL_MANIFEST_PATH) as f:
        expected_by_id = {e["id"]: e for e in json.load(f)}

    scenarios = []
    for position, entry in enumerate(public, start=1):
        if only and position not in only:
            continue
        if entry["id"] not in expected_by_id:
            raise RuntimeError(
                f"Scenario '{entry['id']}' is in the public manifest but not in "
                f"{EVAL_MANIFEST_PATH}. Re-run demo/seed_trace_library.py."
            )
        scenarios.append({**entry, **expected_by_id[entry["id"]], "position": position})
    return scenarios


def investigate(scenario: dict, run_id: str) -> tuple[str, dict]:
    """
    Creates a throwaway incident from the scenario's seeded evidence and
    investigates it. Returns (incident_id, investigation) — the id comes
    back even on failure so cleanup can still remove the row.
    """
    create = requests.post(
        f"{API}/incidents",
        json={
            "project_name": scenario["project_name"],
            "title": f"[eval {run_id}] {scenario['incident_title']}",
            "description": f"Created by demo/eval_trace_library.py run {run_id}. Temporary.",
            "evidence_ids": [e["evidence_id"] for e in scenario["events"]],
        },
        timeout=60,
    )
    create.raise_for_status()
    incident_id = create.json()["id"]

    result = requests.post(f"{API}/incidents/{incident_id}/investigate", timeout=180)
    result.raise_for_status()
    return incident_id, result.json()


def cleanup(incident_ids: list[str]) -> None:
    """
    Deletes every row this run created, FK-safe order, via psql in the db
    container (there is no DELETE endpoint, and the host has no Postgres
    driver installed). Ids are parsed as UUIDs first, so nothing
    unvalidated reaches the SQL.
    """
    if not incident_ids:
        return

    ids = ", ".join(f"'{UUID(i)}'" for i in incident_ids)
    sql = (
        f"DELETE FROM remediations WHERE investigation_id IN "
        f"(SELECT id FROM investigations WHERE incident_id IN ({ids}));"
        f"DELETE FROM investigations WHERE incident_id IN ({ids});"
        f"DELETE FROM incident_evidence WHERE incident_id IN ({ids});"
        f"DELETE FROM incidents WHERE id IN ({ids});"
    )
    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "tracelens", "-d", "tracelens", "-q", "-c", sql],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(
            f"\nWARNING: cleanup failed, {len(incident_ids)} eval incident(s) may remain:\n"
            f"  {' '.join(incident_ids)}\n  {proc.stderr.strip()}",
            file=sys.stderr,
        )
    else:
        print(f"\nCleaned up {len(incident_ids)} temporary eval incident(s).")


def main() -> int:
    only = [int(a) for a in sys.argv[1:]]
    scenarios = load_scenarios(only)
    run_id = uuid4().hex[:8]

    created: list[str] = []
    rows: list[dict] = []

    print(f"Evaluating {len(scenarios)} scenario(s), run {run_id}. One live LLM call each.\n")

    try:
        for scenario in scenarios:
            incident_id = None
            try:
                incident_id, investigation = investigate(scenario, run_id)
                actual = investigation["category"]
            except requests.HTTPError as exc:
                actual = f"ERROR {exc.response.status_code}"
            except requests.RequestException as exc:
                actual = f"ERROR {type(exc).__name__}"
            finally:
                if incident_id:
                    created.append(incident_id)

            rows.append(
                {
                    "id": scenario["id"],
                    # None in the eval manifest means "healthy control": no
                    # failure to classify, so there is no correct category
                    # to score against, and this harness does not invent one.
                    "expected": scenario["expected_category"],
                    "actual": actual,
                }
            )
            print(f"  {scenario['position']:>2}. {scenario['id']:<32} -> {actual}", flush=True)

        scored = [r for r in rows if r["expected"] is not None]
        control = [r for r in rows if r["expected"] is None]

        width = max((len(r["id"]) for r in rows), default=8)
        print(f"\n{'scenario'.ljust(width)} | {'expected':<16} | {'actual':<16} | result")
        print(f"{'-' * width}-+-{'-' * 16}-+-{'-' * 16}-+-------")
        for row in scored:
            verdict = "PASS" if row["actual"] == row["expected"] else "FAIL"
            print(f"{row['id'].ljust(width)} | {row['expected']:<16} | {row['actual']:<16} | {verdict}")

        passed = sum(1 for r in scored if r["actual"] == r["expected"])
        pct = (passed / len(scored) * 100) if scored else 0.0
        print(f"\nAccuracy: {passed}/{len(scored)} ({pct:.1f}%) — healthy control excluded.")

        for row in control:
            print(
                f"\nHealthy control: {row['id']}\n"
                f"  returned '{row['actual']}'. Not scored — trace_library_eval.json defines no\n"
                f"  expected category for it, so there is no PASS/FAIL to assert. It exists to\n"
                f"  show what the pipeline says about a trace with no failure in it."
            )

        return 0 if passed == len(scored) else 1

    finally:
        cleanup(created)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"\nFAILED: {exc}", file=sys.stderr)
        sys.exit(2)
