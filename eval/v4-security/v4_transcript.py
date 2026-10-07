"""Read one run of protocol shape-baseline-v1 into a single, time-ordered event stream.

Layout read (the one eval/shape-baseline/run.sh writes; nothing else is assumed):
    <run>/raw/transcript/main.jsonl
    <run>/raw/transcript/subagents/agent-<id>.jsonl + agent-<id>.meta.json  (agentType, toolUseId)
    <run>/raw/local.json   {"fixture": <fixture dir>}         (required for a verdict, S3-3; the fixture falls back
                                                               to the main thread's cwd for diagnostics only)
    <run>/raw/run.jsonl    stream-json; only init/result used  (required for a verdict, V-1)
    <run>/meta.json        run.sh's record; main_model_requested used (required for a verdict, V-1)

Rules for reading (SP-1, 09-quinn-baseline-stage2.md section 11): one API call can be written as several
assistant records, one per tool_use block, and the last record of a call can be a mid-stream snapshot.
Tool calls are therefore collected from EVERY assistant record and de-duplicated by tool_use id; nothing
is taken from "the last record of a call". Usage and cost are not read here at all.

Attachment records (`type: attachment`) are kept: the host writes hook output (`hook_additional_context`,
`hook_success`), project CLAUDE.md / AGENTS.md (`instructions`), @-files (`file`), edited-file snippets,
listings and the system-prompt snapshot there, not as inline `<system-reminder>` text. Each becomes an
`attachment` event carrying all its strings; a `queued_command` typed by the human becomes `user_text`.

B1 (Sentinel W9 r4): no line is dropped silently. A non-empty line that does not parse into a JSON OBJECT (a
truncated record, `[]`, a bare string) is counted per file in `Run.unparsable`; the scorer makes any such run
INCOMPLETE. Wrong-shaped records the scorer would otherwise crash on (meta.json not an object, an init `plugins`
entry that is not an object) are evidence gaps too (F4).

Every event carries (ts, seq): ts is the host timestamp, seq the file order. The global order sorts by
(ts, thread rank, seq) so that records of one thread keep their file order when timestamps tie.
"""
import glob
import json
import os
import re

HEADER_RE = re.compile(r"router: shode-house@\S+ task:\S+ phase:\S+ iter:\d+")
# inline reminder blocks: any case, with attributes, and an unterminated block runs to the end of the text (B3-i;
# fail closed: the swallowed text is classified untrusted, never as the user's words)
SYSTEM_REMINDER_RE = re.compile(r"<system-reminder\b[^>]*>.*?(?:</system-reminder\s*>|\Z)", re.S | re.I)


def _rows(path, bad=None):
    """JSON objects of a JSONL file, in order. B1: every non-empty line that is not a JSON object is counted in
    `bad[path]` (when given), never dropped silently. A file that cannot be read gives []."""
    out, n_bad = [], 0
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    r = None
                if isinstance(r, dict):
                    out.append(r)
                else:
                    n_bad += 1
    except OSError:
        pass
    if bad is not None and n_bad:
        bad[path] = bad.get(path, 0) + n_bad
    return out


def text_of(content):
    """Plain text of a message/tool_result content (str, list of blocks, or None)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts = []
    for c in content:
        if isinstance(c, dict):
            if c.get("type") == "text":
                parts.append(c.get("text", ""))
            elif c.get("type") == "tool_result":
                parts.append(text_of(c.get("content")))
        elif isinstance(c, str):
            parts.append(c)
    return "\n".join(parts)


class Thread:
    """One conversation: the main session or one spawn."""

    def __init__(self, tid, agent_type=None, tool_use_id=None):
        self.id = tid
        self.agent_type = agent_type          # e.g. "shode-house:developer"; None for main
        self.tool_use_id = tool_use_id        # the Agent/Task call in main that started it
        self.events = []                      # dicts, see Run.load
        self.delegation = None                # first user message of a spawn
        self.handback = ""                    # main-thread tool_result of the starting Agent call
        self.handback_error = False
        self.served_tools = None              # from the prompt_snapshot attachment, if recorded
        self.cwd = None
        self.records = 0                      # parsable JSON records in the thread's file (V-1 / H-2)
        self.assistant_records = 0
        self.system_prompt = None             # first prompt_snapshot `systemPrompt` (frozen score.py thread(), S3-1)
        self.file = None                      # the transcript path this thread was read from

    @property
    def is_main(self):
        return self.agent_type is None

    @property
    def bare(self):
        t = self.agent_type or ""
        return t.split(":", 1)[1] if t.startswith("shode-house:") else t

    @property
    def in_arm(self):
        return (self.agent_type or "").startswith("shode-house:")

    @property
    def has_header(self):
        first = (self.delegation or "").lstrip("\n").split("\n", 1)[0].strip()
        return bool(HEADER_RE.fullmatch(first))

    def uses(self, *names):
        return [e for e in self.events if e["kind"] == "tool_use" and (not names or e["name"] in names)]


class Run:
    def __init__(self, run_dir):
        self.dir = run_dir
        self.main = None
        self.spawns = []
        self.fixture = None
        self.result = None
        self.init = None
        self.meta = None                      # <run>/meta.json written by the frozen run.sh (None: missing)
        self.notes = []
        # V-1 / H-2: evidence the host should have written but did not (a spawn transcript without its .meta.json,
        # a .meta.json without its transcript, an Agent/Task call in main with no spawn thread). The scorer turns
        # any of these into INCOMPLETE: rules over the spawns would otherwise pass vacuously.
        self.evidence_gaps = []
        self.unparsable = {}                  # B1: path -> number of non-empty lines that are not a JSON object
        self.local_ok = False                 # S3-3: raw/local.json read and names a fixture

    @property
    def threads(self):
        return [self.main] + self.spawns

    def ordered(self):
        """Every event of every thread in host time order."""
        rank = {t.id: i for i, t in enumerate(self.threads)}
        evs = [e for t in self.threads for e in t.events]
        return sorted(evs, key=lambda e: (e["ts"] or "", rank[e["thread"]], e["seq"]))

    def rel(self, path):
        """Fixture-relative path of an absolute or relative path; None when outside the fixture."""
        if path is None:
            return None
        path = str(path)
        root = self.fixture or (self.main.cwd if self.main else None)
        if not os.path.isabs(path):
            norm = os.path.normpath(path)
            return None if norm == ".." or norm.startswith("../") else norm
        if not root:
            return None
        root = os.path.normpath(root)
        norm = os.path.normpath(path)
        if norm == root:
            return "."
        return os.path.relpath(norm, root) if norm.startswith(root + os.sep) else None


def _load_thread(path, thread, seq0=0, bad=None):
    seen = set()
    results = {}
    seq = seq0
    first_user = True
    thread.file = path
    for r in _rows(path, bad):
        seq += 1
        thread.records += 1
        ts = r.get("timestamp")
        typ = r.get("type")
        if typ == "assistant":
            thread.assistant_records += 1
        if thread.cwd is None and r.get("cwd"):
            thread.cwd = r.get("cwd")
        if not isinstance(r.get("message") or {}, dict):
            if bad is not None:                         # B1/F4: a record of the wrong shape is not evidence either
                bad[path] = bad.get(path, 0) + 1
            continue
        if typ == "attachment":
            a = r.get("attachment") or {}
            if not isinstance(a, dict):
                continue
            if a.get("type") == "prompt_snapshot":       # the frozen reader's system prompt (score.py thread())
                thread.system_prompt = thread.system_prompt or a.get("systemPrompt")
            if a.get("type") == "prompt_snapshot" and a.get("tools") and thread.served_tools is None:
                thread.served_tools = [t.get("name") if isinstance(t, dict) else t for t in a["tools"]]
            if is_human_prompt(a) and thread.is_main:
                # a prompt the user typed while the session was busy (host queue): the user's own words
                thread.events.append({"kind": "user_text", "thread": thread.id, "ts": ts, "seq": seq,
                                      "text": text_of(a.get("prompt")), "via": "queued_command"})
                continue
            text = attachment_text(a)
            if text.strip():
                # hook output, project CLAUDE.md / AGENTS.md (`instructions`), @-files, edited-file snippets,
                # task notifications, listings, the system-prompt snapshot ...: host-recorded text that is not
                # the user's words (router decision R71); classified untrusted for provenance
                thread.events.append({"kind": "attachment", "thread": thread.id, "ts": ts, "seq": seq,
                                      "atype": str(a.get("type")), "text": text})
            continue
        msg = r.get("message") or {}
        content = msg.get("content")
        if typ == "user":
            if isinstance(content, list) and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        ev = {"kind": "tool_result", "thread": thread.id, "ts": ts, "seq": seq,
                              "tool_use_id": c.get("tool_use_id"), "error": bool(c.get("is_error")),
                              "text": text_of(c.get("content"))}
                        results[c.get("tool_use_id")] = ev
                        thread.events.append(ev)
                continue
            text = text_of(content)
            meta = bool(r.get("isMeta"))
            if first_user and not thread.is_main and not meta:
                thread.delegation = text
                first_user = False
                thread.events.append({"kind": "delegation", "thread": thread.id, "ts": ts, "seq": seq, "text": text})
                continue
            if not meta:
                first_user = False
            thread.events.append({"kind": "user_meta" if meta else "user_text", "thread": thread.id, "ts": ts,
                                  "seq": seq, "text": text})
        elif typ == "assistant":
            for c in content or []:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_use":
                    if c.get("id") in seen:
                        continue
                    seen.add(c.get("id"))
                    thread.events.append({"kind": "tool_use", "thread": thread.id, "ts": ts, "seq": seq,
                                          "id": c.get("id"), "name": c.get("name"), "input": c.get("input") or {}})
                elif c.get("type") == "text" and (c.get("text") or "").strip():
                    thread.events.append({"kind": "text", "thread": thread.id, "ts": ts, "seq": seq,
                                          "text": c.get("text")})
    for e in thread.events:
        if e["kind"] == "tool_use":
            res = results.get(e["id"])
            e["result"] = res["text"] if res else None
            e["result_error"] = res["error"] if res else None
            e["result_ts"] = res["ts"] if res else None
    return seq


def load(run_dir):
    run = Run(run_dir)
    tdir = os.path.join(run_dir, "raw", "transcript")
    try:
        local = json.load(open(os.path.join(run_dir, "raw", "local.json"), encoding="utf-8"))
        if isinstance(local, dict) and isinstance(local.get("fixture"), str) and local["fixture"]:
            run.fixture = local["fixture"]
            run.local_ok = True
    except (OSError, ValueError):
        pass
    stream = _rows(os.path.join(run_dir, "raw", "run.jsonl"), run.unparsable)
    run.init = next((e for e in stream if e.get("type") == "system" and e.get("subtype") == "init"), None)
    if run.init is not None:                            # F4: an init the frozen rule cannot read is an evidence gap
        plugins = run.init.get("plugins")
        if plugins is not None and not (isinstance(plugins, list) and all(isinstance(p, dict) for p in plugins)):
            run.evidence_gaps.append("run.jsonl init `plugins` is not a list of objects")
            run.init = dict(run.init, plugins=[p for p in plugins if isinstance(p, dict)]
                            if isinstance(plugins, list) else [])
    res = [e for e in stream if e.get("type") == "result" and not e.get("parent_tool_use_id")]
    run.result = res[-1] if res else None

    try:
        run.meta = json.load(open(os.path.join(run_dir, "meta.json"), encoding="utf-8"))
        if not isinstance(run.meta, dict):              # F4: `[1]` is not a meta record
            run.meta = None
    except (OSError, ValueError):
        run.meta = None

    run.main = Thread("main")
    seq = _load_thread(os.path.join(tdir, "main.jsonl"), run.main, bad=run.unparsable)
    calls = {e["id"]: e for e in run.main.uses("Agent", "Task")}
    sdir = os.path.join(tdir, "subagents")
    for jp in sorted(glob.glob(os.path.join(sdir, "*.jsonl"))):
        if not os.path.isfile(jp[: -len(".jsonl")] + ".meta.json"):
            run.evidence_gaps.append("spawn transcript without .meta.json: " + os.path.basename(jp))
    for mp in sorted(glob.glob(os.path.join(sdir, "*.meta.json"))):
        try:
            meta = json.load(open(mp, encoding="utf-8"))
            if not isinstance(meta, dict):
                raise ValueError
        except (OSError, ValueError):
            run.notes.append("unreadable meta: " + os.path.basename(mp))
            run.evidence_gaps.append("unreadable spawn meta: " + os.path.basename(mp))
            continue
        th = Thread(os.path.basename(mp)[: -len(".meta.json")], meta.get("agentType") or "?", meta.get("toolUseId"))
        if not os.path.isfile(mp[: -len(".meta.json")] + ".jsonl"):
            run.evidence_gaps.append("spawn .meta.json without its transcript: " + os.path.basename(mp))
        seq = _load_thread(mp[: -len(".meta.json")] + ".jsonl", th, seq, bad=run.unparsable)
        call = calls.get(th.tool_use_id)
        if call is not None:
            th.handback = call.get("result") or ""
            th.handback_error = bool(call.get("result_error"))
            if th.delegation is None:
                th.delegation = (call.get("input") or {}).get("prompt") or ""
        else:
            run.notes.append("spawn %s has no Agent call in main" % th.id)
        if not th.handback:
            texts = [e["text"] for e in th.events if e["kind"] == "text"]
            th.handback = texts[-1] if texts else ""
        run.spawns.append(th)
    loaded = {th.tool_use_id for th in run.spawns}
    for cid in sorted(c for c in calls if c not in loaded):
        run.evidence_gaps.append("%s call %s in main has no spawn transcript" % (calls[cid]["name"], cid))
    if run.fixture is None and run.main.cwd:
        run.fixture = run.main.cwd
    return run


def is_human_prompt(a):
    """A `queued_command` attachment that the host marks as typed by the human (origin.kind == "human",
    commandMode "prompt"). Task notifications and every other queued command are not the user's words."""
    return (a.get("type") == "queued_command" and (a.get("origin") or {}).get("kind") == "human"
            and a.get("commandMode") in (None, "prompt"))


ATTACHMENT_SKIP_KEYS = frozenset({"type"})


def attachment_text(a):
    """Every string an attachment record carries (any type, known or not), in record order: `content`,
    `snippet`, `files[].content`, `file.content`, `stdout`, `prompt`, ... Keys are not text; `type` is skipped."""
    out = []

    def walk(v):
        if isinstance(v, str):
            if v.strip():
                out.append(v)
        elif isinstance(v, dict):
            for k, x in v.items():
                if k not in ATTACHMENT_SKIP_KEYS:
                    walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(a)
    return "\n".join(out)


def user_authored(text):
    """User text with injected reminders removed (host-injected blocks are not the user's words)."""
    return SYSTEM_REMINDER_RE.sub("", text or "").strip()
