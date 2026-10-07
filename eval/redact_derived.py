#!/usr/bin/env python3
"""Post-run redaction of DERIVED evidence for eval/run-core.sh (UD U23, OD-2 option A+).

The frozen writers (eval/run-lib.sh `run_one` / `tools_seen`, scripts/team-run-check.py) copy raw run text into the
files a person reads and pastes. They are frozen (eval/FREEZE.sha256), so the redaction runs after them, here, with
the one redaction step the eval scorers share (eval/evidence_redact.py). What is redacted and what is not:

  derived (redacted in place): tools-seen.txt, score.txt, score.json, meta.json -- every file run_one computes FROM
      the run (meta.json carries first_skill / first_agent / route / model_id copied out of the trace)
  raw (never touched, local only): run.jsonl (the scorer's input; its sha256 is recorded before and checked after),
      run.files (also a scorer input), run.diff, run.stderr, prompt.txt, fixture.*, probe-settings.json

Every replacement is atomic: the redacted copy is written to a temporary file in the same directory (mode 0600),
flushed and fsync'd, then renamed over the original (os.replace = rename(2), the same operation as `mv -f` within
one file system); a failure removes the temporary file and leaves the original as it was. A file whose redaction
changes nothing is not rewritten. JSON files are parsed and only string VALUES are redacted (`redact_tree`), so a
status, verdict, count or exit code is never changed; a JSON file that does not parse is redacted as text. In
tools-seen.txt the JSON of each first-input line is parsed too, and a value the frozen writer cut at 300 characters
(it appends "...") is redacted as if the cut were the end of the string (`redact_tools_seen`).

Commands (exit 0 = done; any other exit = redaction failed, the caller must stop -- fail-closed):
  redact_derived.py selftest            the helper and eval/evidence_redact.py load and redact a known shape
  redact_derived.py seal <run-dir>      redact the derived files of one run and write <run-dir>/redaction.json
  redact_derived.py file <path>         redact one text file in place (the runner's buffered console output)
  redact_derived.py text                stdin -> stdout (a SUMMARY.tsv row, a console line)
A failure message names the file and the error type only, never file content.
"""
import hashlib, json, os, re, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evidence_redact import REDACTED, redact, redact_tree   # noqa: E402  (an import error = exit 1 = fail-closed)

DERIVED = ("tools-seen.txt", "score.txt", "score.json", "meta.json")
RAW = "run.jsonl"
JSON_INDENT = {"score.json": 2, "meta.json": 1}   # the indent the frozen writers use


class RedactionError(Exception):
    pass


def sha256(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except FileNotFoundError:
        return None


def atomic_write(path, data):
    """Write bytes to `path` via a same-directory temporary file + fsync + rename; never a half-written file."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".redact-", suffix=".tmp", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    try:   # make the rename itself durable; a directory that cannot be opened for fsync is not an error
        dfd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dfd)
    except OSError:
        pass
    finally:
        os.close(dfd)


def redact_text(raw):
    return redact(raw.decode("utf-8", "surrogateescape")).encode("utf-8", "surrogateescape")


# tools-seen.txt (frozen eval/run-lib.sh `tools_seen`): `# first Skill|Task|Agent tool_use input: <json.dumps(...)>`.
# The writer cuts every input value longer than 300 characters to its first 300 plus CUT before any redaction, so a
# credential can end at the cut (`https://user:pw` with the "@" cut off), where a rule that needs the end of the
# string would no longer see it (Sentinel final F2); and every quote of JSON inside a value is escaped (F1).
TOOLS_SEEN_INPUT = re.compile(r"(# first (?:Skill|Task|Agent) tool_use input: )(.+)")
CUT = "..."


def redact_cut(value):
    """A string that ends in the cut marker is redacted as if the marker were the end of the string (strip it, redact,
    put it back), so the marker stays visible; then once more as a whole, which also covers a value cut to nothing
    (`"pw": ...`). Any other value: `redact_tree`."""
    if isinstance(value, str) and value.endswith(CUT):
        return redact(redact(value[:-len(CUT)]) + CUT)
    return redact_tree(value)


def redact_tools_seen(text):
    """tools-seen.txt: each first-input line is parsed, its values redacted (cut-aware at the top level, where the
    writer cuts) and dumped again as the writer dumps it; every other line, or one that does not parse, as text."""
    out = []
    for line in text.split("\n"):
        m = TOOLS_SEEN_INPUT.fullmatch(line)
        if m:
            try:
                obj = json.loads(m.group(2))
            except ValueError:
                obj = line
            else:
                clean = {k: redact_cut(v) for k, v in obj.items()} if isinstance(obj, dict) else redact_tree(obj)
                line = line if clean == obj else m.group(1) + json.dumps(clean, ensure_ascii=False)
        out.append(redact(line))
    return "\n".join(out)


def redacted_bytes(name, raw):
    """-> the redacted content of a derived file, or None when nothing changes."""
    if name == "tools-seen.txt":
        clean = redact_tools_seen(raw.decode("utf-8", "surrogateescape")).encode("utf-8", "surrogateescape")
        return None if clean == raw else clean
    if name in JSON_INDENT:
        try:
            obj = json.loads(raw.decode("utf-8"))
        except ValueError:
            obj = None
        else:
            clean = redact_tree(obj)
            if clean == obj:
                return None
            return (json.dumps(clean, indent=JSON_INDENT[name], ensure_ascii=False) + "\n").encode("utf-8")
    clean = redact_text(raw)
    return None if clean == raw else clean


def redact_file(path, name=None):
    """-> "redacted" or "unchanged"; a missing file is "absent". Unreadable / unwritable = an OSError (fail)."""
    if not os.path.lexists(path):
        return "absent"
    if os.path.islink(path) or not os.path.isfile(path):
        raise RedactionError(f"not a regular file: {path}")
    with open(path, "rb") as f:
        raw = f.read()
    clean = redacted_bytes(name or os.path.basename(path), raw)
    if clean is None:
        return "unchanged"
    atomic_write(path, clean)
    return "redacted"


def seal(run_dir):
    """Redact the derived files of one run dir; record and verify the raw trace hash; write redaction.json last."""
    if not os.path.lexists(run_dir):
        return {"run_dir": run_dir, "state": "absent"}       # refused before start: nothing was written
    if os.path.islink(run_dir) or not os.path.isdir(run_dir):
        raise RedactionError(f"not a directory: {run_dir}")
    raw_path = os.path.join(run_dir, RAW)
    before = sha256(raw_path)
    files = {name: redact_file(os.path.join(run_dir, name), name) for name in DERIVED}
    after = sha256(raw_path)
    if before != after:
        raise RedactionError(f"{raw_path} changed during redaction (sha256 {before} -> {after})")
    record = {"run_jsonl_sha256": before, "derived": files, "raw_untouched": [RAW, "run.files", "run.diff", "run.stderr"],
              "redactor_sha256": sha256(os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence_redact.py"))}
    atomic_write(os.path.join(run_dir, "redaction.json"), (json.dumps(record, indent=1) + "\n").encode("utf-8"))
    return record


def selftest():
    probe = "Authorization: Bearer " + "ghp_" + "0123456789abcdefghij"
    if REDACTED not in redact(probe) or "ghp_" in redact(probe):
        raise RedactionError("evidence_redact did not redact a known credential shape")


def main(argv):
    if len(argv) == 1 and argv[0] == "selftest":
        selftest()
    elif len(argv) == 2 and argv[0] == "seal":
        selftest()
        seal(argv[1])
    elif len(argv) == 2 and argv[0] == "file":
        selftest()
        redact_file(argv[1], "")
    elif len(argv) == 1 and argv[0] == "text":
        selftest()
        sys.stdout.buffer.write(redact_text(sys.stdin.buffer.read()))
        sys.stdout.buffer.flush()
    else:
        print("usage: redact_derived.py selftest | seal <run-dir> | file <path> | text", file=sys.stderr)
        return 64
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:   # name the failure, never echo content
        where = getattr(exc, "filename", None) or (str(exc) if isinstance(exc, RedactionError) else "")
        print(f"!! redaction failed: {type(exc).__name__}{': ' + str(where) if where else ''}", file=sys.stderr)
        sys.exit(1)
