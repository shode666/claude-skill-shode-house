#!/usr/bin/env python3
"""Offline stand-in for the `claude` CLI, used ONLY to prove the eval runner wiring
(eval/run-e01.sh, eval/run-probes.sh) without calling a model. It emits a minimal stream-json
trace in the shape scripts/team-run-check.py parses. It proves nothing about what a real
`claude -p` trace looks like (Skill tool_use shape stays UNVERIFIED until a live run).
Behaviour: prompt containing "typo" -> fix src/validators.py in cwd + targeted test + success;
anything else -> one Skill load (env FAKE_SKILL, default diagnose) then error_max_turns.
FAKE_MODE=noresult -> trace without a result event (UNSCORABLE path)."""
import json, os, sys

args = sys.argv[1:]
if "--version" in args:
    print("0.0.0-stub (fake claude)"); sys.exit(0)
if "--help" in args:
    print("Usage: claude [options]\n  --settings <file-or-json>\n  --max-budget-usd <amount>\n  --max-turns <n>"); sys.exit(0)
for required in ("-p", "--plugin-dir", "--model", "--max-turns", "--output-format", "--verbose"):
    if required not in args:
        sys.exit(f"fake claude: missing {required}")
prompt, n = args[args.index("-p") + 1], 0


def emit(event):
    print(json.dumps(event, ensure_ascii=False), flush=True)


def use(name, inp):
    global n
    n += 1
    emit({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"toolu_{n}", "name": name, "input": inp}]}})
    emit({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"toolu_{n}", "content": "ok"}]}})


emit({"type": "system", "subtype": "init", "model": "stub-" + args[args.index("--model") + 1],
      "plugins": [{"name": "shode-house", "path": args[args.index("--plugin-dir") + 1]}]})
if "typo" in prompt:
    path = os.path.join(os.getcwd(), "src", "validators.py")
    use("Grep", {"pattern": "emial"})
    text = open(path, encoding="utf-8").read()
    open(path, "w", encoding="utf-8").write(text.replace("vaild emial", "valid email"))
    use("Edit", {"file_path": path})
    use("Bash", {"command": "python3 -m unittest tests.test_validators"})
    final = {"type": "result", "subtype": "success", "is_error": False, "result": "Fixed the typo; targeted test passes."}
else:
    use("Skill", {"skill": "shode-house:" + os.environ.get("FAKE_SKILL", "diagnose")})
    final = {"type": "result", "subtype": "error_max_turns", "is_error": True, "result": ""}
final.update({"total_cost_usd": 0.0, "modelUsage": {"stub": {"outputTokens": 1}}})
if os.environ.get("FAKE_MODE") != "noresult":
    emit(final)
