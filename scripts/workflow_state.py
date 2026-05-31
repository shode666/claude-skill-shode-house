#!/usr/bin/env python3
"""shode-house Dynamic Workflow State (Medium — v3.4 candidate).

Externalizes PEV loop state out of agent context to mitigate context rot,
enable resume/replay, and enforce gate criteria deterministically.

Replaces ``outputs/SESSION-STATE.md`` (per shode-house-drift M6) with
structured ``outputs/<bd-id>/state.json``. Cross-platform Python stdlib.

Commands::

    python3 scripts/workflow_state.py init <bd-id> --name "feature" --mode hybrid
    python3 scripts/workflow_state.py status <bd-id>
    python3 scripts/workflow_state.py validate <bd-id>
    python3 scripts/workflow_state.py phases <bd-id>
    python3 scripts/workflow_state.py advance <bd-id> --to <phase> --owner <agent>
    python3 scripts/workflow_state.py findings <bd-id> --critical N --high N

Agents collaborate by reading/writing state.json through this script.
ห้าม agent edit state.json directly — go through script API (idempotent + validated).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "1.0"

VALID_PHASES = [
    "pick",
    "phase_0_discovery",
    "phase_1a_foundation",
    "phase_1b_expand",
    "phase_1c_threat_model",
    "phase_2_implement",
    "phase_3a_ui_check",
    "phase_3b_code_review",
    "phase_4_triage",
    "phase_5_deploy",
    "phase_6_operate",
    "closed",
]

VALID_STATUSES = ["pending", "in_progress", "conditional_pass", "passed", "failed", "skipped"]
VALID_MODES = ["afk", "hybrid", "interactive"]
VALID_OWNERS = {
    "oliver", "patrick", "stan", "bella", "sara", "uma", "dave", "chris", "quinn",
    "sentinel", "aaron", "reggie", "felix", "iris", "sam", "tara", "elena", "brooke", "emma",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_path(bd_id: str) -> Path:
    return Path("outputs") / bd_id / "state.json"


def load_state(bd_id: str) -> dict:
    path = state_path(bd_id)
    if not path.exists():
        raise FileNotFoundError(f"state not found: {path} (run `init {bd_id}` first)")
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(bd_id: str, state: dict) -> None:
    path = state_path(bd_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now_utc()
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def init_state(bd_id: str, name: str, mode: str, domain: list[str]) -> dict:
    if mode not in VALID_MODES:
        raise ValueError(f"invalid mode: {mode} (expected {VALID_MODES})")
    state = {
        "schema_version": SCHEMA_VERSION,
        "bd_id": bd_id,
        "engagement": {
            "name": name,
            "mode": mode,
            "started_at": now_utc(),
            "domain": domain,
        },
        "current_phase": "pick",
        "iter": 0,
        "phases": {p: {"status": "pending", "owners": [], "artifacts": [], "gate": {}} for p in VALID_PHASES},
        "handoff_log": [],
        "findings": {"critical": 0, "high": 0, "medium": 0, "low": 0, "suggestion": 0},
        "open_questions": [],
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    state["phases"]["pick"]["status"] = "in_progress"
    return state


def validate_schema(state: dict) -> list[str]:
    errors: list[str] = []
    required = ["schema_version", "bd_id", "engagement", "current_phase", "iter", "phases"]
    for f in required:
        if f not in state:
            errors.append(f"missing field: {f}")
    if state.get("current_phase") not in VALID_PHASES:
        errors.append(f"invalid current_phase: {state.get('current_phase')}")
    mode = state.get("engagement", {}).get("mode")
    if mode and mode not in VALID_MODES:
        errors.append(f"invalid mode: {mode}")
    for phase, data in state.get("phases", {}).items():
        if phase not in VALID_PHASES:
            errors.append(f"invalid phase key: {phase}")
        if data.get("status") and data["status"] not in VALID_STATUSES:
            errors.append(f"{phase}: invalid status {data['status']}")
        for owner in data.get("owners", []):
            if owner not in VALID_OWNERS:
                errors.append(f"{phase}: unknown owner '{owner}'")
    iter_val = state.get("iter", 0)
    if not isinstance(iter_val, int) or iter_val < 0:
        errors.append(f"iter must be non-negative int (got {iter_val})")
    if iter_val > 3:
        errors.append(f"iter {iter_val} > 3 — escalate user per workflow rule")
    return errors


def gate_check(state: dict, phase: str) -> list[str]:
    """Check if a phase is ready to advance (gate criteria met)."""
    errors: list[str] = []
    p = state["phases"].get(phase, {})
    status = p.get("status")
    if status not in ("passed", "conditional_pass"):
        errors.append(f"{phase}: status={status} (need passed or conditional_pass to advance)")
    if not p.get("artifacts"):
        errors.append(f"{phase}: no artifacts recorded (need ≥ 1 deliverable path)")
    if not p.get("owners"):
        errors.append(f"{phase}: no owners recorded")
    return errors


def cmd_init(args: argparse.Namespace) -> int:
    state = init_state(args.bd_id, args.name or "unnamed", args.mode, args.domain or [])
    save_state(args.bd_id, state)
    print(f"✓ initialized state: {state_path(args.bd_id)}")
    print(f"  bd: {args.bd_id}  mode: {args.mode}  current_phase: pick")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = load_state(args.bd_id)
    cur = state["current_phase"]
    cur_data = state["phases"].get(cur, {})
    print(f"bd: {state['bd_id']}  engagement: {state['engagement']['name']}")
    print(f"mode: {state['engagement']['mode']}  iter: {state['iter']}")
    print(f"current_phase: {cur}  status: {cur_data.get('status')}")
    if cur_data.get("owners"):
        print(f"  owners: {', '.join(cur_data['owners'])}")
    if cur_data.get("artifacts"):
        print(f"  artifacts: {len(cur_data['artifacts'])} file(s)")
    f = state.get("findings", {})
    if any(f.get(k, 0) for k in ("critical", "high", "medium", "low")):
        print(f"findings: 🔴{f.get('critical',0)} 🟠{f.get('high',0)} 🟡{f.get('medium',0)} 🔵{f.get('low',0)}")
    if state.get("open_questions"):
        unanswered = [q for q in state["open_questions"] if not q.get("answered_at")]
        if unanswered:
            print(f"⚠ open questions: {len(unanswered)} unanswered")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        state = load_state(args.bd_id)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"✗ load error: {exc}")
        return 1
    errors = validate_schema(state)
    if errors:
        print(f"✗ schema validation failed ({len(errors)} errors):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"✓ state schema valid (bd: {state['bd_id']})")
    return 0


def cmd_phases(args: argparse.Namespace) -> int:
    state = load_state(args.bd_id)
    print(f"bd: {state['bd_id']}  iter: {state['iter']}")
    for phase in VALID_PHASES:
        data = state["phases"].get(phase, {})
        status = data.get("status", "pending")
        marker = {
            "pending": "  ⚪",
            "in_progress": "  🔵",
            "conditional_pass": "  🟡",
            "passed": "  ✅",
            "failed": "  ❌",
            "skipped": "  ⏭",
        }.get(status, "  ?")
        n_art = len(data.get("artifacts", []))
        owners = ",".join(data.get("owners", [])) or "-"
        print(f"{marker} {phase:30s} {status:18s} owners:{owners:20s} artifacts:{n_art}")
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    state = load_state(args.bd_id)
    target = args.to
    if target not in VALID_PHASES:
        print(f"✗ invalid phase: {target}")
        return 1
    # gate check: previous phase must be passed
    cur = state["current_phase"]
    if cur != target:
        gate_errors = gate_check(state, cur)
        if gate_errors:
            print(f"✗ cannot advance from {cur} to {target} — gate not met:")
            for e in gate_errors:
                print(f"  - {e}")
            return 1
    state["current_phase"] = target
    if state["phases"][target]["status"] == "pending":
        state["phases"][target]["status"] = "in_progress"
        state["phases"][target]["started_at"] = now_utc()
    if args.owner:
        if args.owner not in VALID_OWNERS:
            print(f"✗ unknown owner: {args.owner}")
            return 1
        if args.owner not in state["phases"][target]["owners"]:
            state["phases"][target]["owners"].append(args.owner)
    save_state(args.bd_id, state)
    print(f"✓ advanced to {target}  iter:{state['iter']}  status:{state['phases'][target]['status']}")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    """Record artifact + status + owner update for a phase."""
    state = load_state(args.bd_id)
    phase = args.phase
    if phase not in VALID_PHASES:
        print(f"✗ invalid phase: {phase}")
        return 1
    p = state["phases"][phase]
    if args.artifact:
        if args.artifact not in p["artifacts"]:
            p["artifacts"].append(args.artifact)
    if args.owner:
        if args.owner not in VALID_OWNERS:
            print(f"✗ unknown owner: {args.owner}")
            return 1
        if args.owner not in p["owners"]:
            p["owners"].append(args.owner)
    if args.status:
        if args.status not in VALID_STATUSES:
            print(f"✗ invalid status: {args.status}")
            return 1
        p["status"] = args.status
        if args.status in ("passed", "conditional_pass", "failed"):
            p["completed_at"] = now_utc()
    save_state(args.bd_id, state)
    owners_str = ",".join(p["owners"]) or "-"
    print(f"✓ recorded {phase}: status={p['status']}, owners={owners_str}, artifacts={len(p['artifacts'])}")
    return 0


def cmd_findings(args: argparse.Namespace) -> int:
    state = load_state(args.bd_id)
    if args.critical is not None:
        state["findings"]["critical"] = args.critical
    if args.high is not None:
        state["findings"]["high"] = args.high
    if args.medium is not None:
        state["findings"]["medium"] = args.medium
    if args.low is not None:
        state["findings"]["low"] = args.low
    save_state(args.bd_id, state)
    f = state["findings"]
    print(f"✓ findings: 🔴{f['critical']} 🟠{f['high']} 🟡{f['medium']} 🔵{f['low']}")
    return 0


def cmd_iter_inc(args: argparse.Namespace) -> int:
    state = load_state(args.bd_id)
    state["iter"] += 1
    save_state(args.bd_id, state)
    if state["iter"] > 3:
        print(f"⚠ iter={state['iter']} > 3 — escalate user per workflow rule")
        return 2
    print(f"✓ iter advanced to {state['iter']}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="shode-house workflow state (v3.4 candidate)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize new bd state")
    p_init.add_argument("bd_id")
    p_init.add_argument("--name", help="Engagement name")
    p_init.add_argument("--mode", default="hybrid", help="afk|hybrid|interactive (default hybrid)")
    p_init.add_argument("--domain", action="append", help="Domain trigger (repeatable)")

    p_status = sub.add_parser("status", help="Show current status")
    p_status.add_argument("bd_id")

    p_validate = sub.add_parser("validate", help="Validate schema")
    p_validate.add_argument("bd_id")

    p_phases = sub.add_parser("phases", help="List all phases status")
    p_phases.add_argument("bd_id")

    p_advance = sub.add_parser("advance", help="Advance to next phase (gate-checked)")
    p_advance.add_argument("bd_id")
    p_advance.add_argument("--to", required=True, help="Target phase")
    p_advance.add_argument("--owner", help="Phase owner (agent name)")

    p_record = sub.add_parser("record", help="Record artifact + status + owner for a phase")
    p_record.add_argument("bd_id")
    p_record.add_argument("--phase", required=True)
    p_record.add_argument("--artifact", help="Artifact path")
    p_record.add_argument("--status", help="phase status update")
    p_record.add_argument("--owner", help="Phase owner (agent name)")

    p_findings = sub.add_parser("findings", help="Update findings counts")
    p_findings.add_argument("bd_id")
    p_findings.add_argument("--critical", type=int)
    p_findings.add_argument("--high", type=int)
    p_findings.add_argument("--medium", type=int)
    p_findings.add_argument("--low", type=int)

    p_iter = sub.add_parser("iter-inc", help="Increment iter (with > 3 escalation)")
    p_iter.add_argument("bd_id")

    args = p.parse_args()

    handlers = {
        "init": cmd_init,
        "status": cmd_status,
        "validate": cmd_validate,
        "phases": cmd_phases,
        "advance": cmd_advance,
        "record": cmd_record,
        "findings": cmd_findings,
        "iter-inc": cmd_iter_inc,
    }
    try:
        return handlers[args.cmd](args)
    except FileNotFoundError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
