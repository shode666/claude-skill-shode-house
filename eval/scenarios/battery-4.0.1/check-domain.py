#!/usr/bin/env python3
"""Offline check for the 7 domain probes of the 4.0.1 battery (P15, P23, P24, P42..P45). In 4.0.0 each probe named its own expert
agent; in 4.0.1 every domain is a `plan` spawn, so the type alone cannot tell them apart. This reads the main-session spawns of a
stream-json trace and checks what the router passed: the `plan` spawn's delegation names the expected `references/domain/<d>.md`
(and no other domain's), and the requested model follows the pinned tier (battery-4.0.1.json `domain_tier`: opus for fintech, sap,
trading, insurance; erp, booking, ecommerce at the type default, `opus` only when the delegation records a high-stakes reason).
It reads the dispatch request, never a model output, and it is report-only for the runner (domain-check.txt).

  python3 check-domain.py <probe id> <trace.jsonl>            exit 0 PASS, 1 FAIL, 2 UNSCORABLE (not a domain probe, unreadable trace)"""
import importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
spec = importlib.util.spec_from_file_location("trc", os.path.join(ROOT, "scripts", "team-run-check.py"))
trc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trc)
REF = re.compile(r"references/domain/([a-z]+)\.md")
NEGATION = re.compile(r"(?i)\b(?:not|no|non|never|without|neither|nor)\b|n't\b")


def high_stakes_recorded(text):
    """True when `high-stakes` appears at least once outside a negation: the words before it in the same clause (back to the last
    punctuation) hold no not/no/non/never/without/neither/nor/n't ("not high-stakes", "no high-stakes reason" do not record one)."""
    for m in re.finditer(r"(?i)high-stakes", text):
        clause = re.split(r"[.;:,!?\n]", text[:m.start()])[-1]
        if not NEGATION.search(clause):
            return True
    return False


def plan_spawns(events):
    out = []
    for e in events:
        if e.get("type") != "assistant" or e.get("parent_tool_use_id"):
            continue
        for c in trc.blocks(e):
            if c.get("type") == "tool_use" and c.get("name") in ("Task", "Agent"):
                inp = c.get("input") or {}
                if str(inp.get("subagent_type") or "").split(":")[-1] == "plan":
                    text = " ".join(str(inp.get(k) or "") for k in ("description", "prompt"))
                    out.append((text, str(inp.get("model") or "")))
    return out


def check(ident, events, battery):
    scen = next((s for s in battery["scenarios"] if s["id"] == ident), None)
    domain = (scen or {}).get("domain_4_0_1")
    if not domain:
        raise ValueError(f"{ident} is not a domain probe of the battery")
    tier = battery["domain_tier"]
    spawns = plan_spawns(events)
    why = []
    if not spawns:
        return False, ["no plan spawn"]
    named = [set(REF.findall(t)) for t, _ in spawns]
    if not any(domain in n for n in named):
        why.append(f"no plan spawn names references/domain/{domain}.md (named: {sorted(set().union(*named))})")
    if any(n - {domain} for n in named):
        why.append(f"a plan spawn names another domain reference: {sorted(set().union(*named) - {domain})}")
    for (text, model), n in zip(spawns, named):
        if domain not in n:
            continue
        opus = "opus" in model.lower()
        if domain in tier["opus"] and not opus:
            why.append(f"{domain} is an opus domain but the plan spawn requested model {model or '(type default)'}")
        if domain in tier["default"] and opus and not high_stakes_recorded(text):
            why.append(f"{domain} runs at the type default; opus was requested without a recorded high-stakes reason")
    return not why, why


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    try:
        battery = json.load(open(os.path.join(HERE, "battery-4.0.1.json"), encoding="utf-8"))
        events = trc.load(argv[1])
        ok, why = check(argv[0], events, battery)
    except (OSError, ValueError) as exc:
        print(f"UNSCORABLE: {exc}")
        return 2
    print(("PASS " if ok else "FAIL ") + argv[0] + (": " + "; ".join(why) if why else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
