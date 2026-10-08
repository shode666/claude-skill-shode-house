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
  redact_derived.py lockdown <out-dir>  before any run: every dir 0700, every file 0600, or refuse (see `lockdown`)
A failure message names the file and the error type only, never file content.
"""
import hashlib, json, os, re, stat, sys, tempfile

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


# lockdown <out-dir>: an out-dir begun before umask 077 (or written by hand) can hold 0644/0755 entries, raw run.jsonl
# included. Before any run, every directory goes to 0700 and every regular file to 0600. Pass 1 only looks: one entry
# that is a symlink, a FIFO/socket/device, a hard-linked file, another user's, or unreadable refuses the batch with
# nothing changed. Pass 2 tightens. Both walk by descriptor: each name is opened relative to its parent's descriptor
# with O_NOFOLLOW (a link is never followed, so a swapped-in link fails instead of redirecting the chmod), the opened
# object is fstat'ed and must be the same (st_dev, st_ino) pass 1 saw, and the mode is set with fchmod on that
# descriptor, never by path. Contents are never written; every redaction.json must be a regular file and what `seal`
# writes (an object whose run_jsonl_sha256 is a 64-char lowercase hex sha256 beside a regular-file run.jsonl, null with
# none: `_recorded_sha`); a recorded sha256 whose run.jsonl is gone or is not a regular file (a directory, a link, a
# FIFO) refuses the batch, and a run.jsonl beside one must still hash to it (pass 1, and before and after its fchmod in
# pass 2). A tree (or a redaction.json) nested past Python's recursion limit is refused, never a traceback. A refusal
# in pass 1 changes nothing; one in pass 2 (the tree changed between passes, or a chmod failed) leaves the entries
# already tightened as they are now, owner-only, and loosens nothing. Messages are static: no path, no content.
LOCKDOWN_DIR, LOCKDOWN_FILE = 0o700, 0o600
NESTED_TOO_DEEPLY = "the out-dir or a redaction.json in it is nested too deeply"
_NOFOLLOW = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)


class LockdownRefused(Exception):
    """A static reason; the caller prints it and stops (exit 4) -- never a path or file content."""


def _open_at(name, dir_fd, want_dir):
    flags = _NOFOLLOW | (getattr(os, "O_DIRECTORY", 0) if want_dir else 0)
    try:
        return os.open(name, flags, dir_fd=dir_fd)
    except OSError:
        raise LockdownRefused("an entry could not be opened without following a link (symlink, swapped entry or "
                              "no owner access)") from None


def _check_entry(st):
    """Pass-1 rule for one lstat result: a directory, or a regular file with one link, owned by this user."""
    if not (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)):
        raise LockdownRefused("an entry is a symlink or not a regular file or directory")
    if stat.S_ISREG(st.st_mode) and st.st_nlink != 1:
        raise LockdownRefused("a file has more than one hard link (tightening it would change a file outside the out-dir)")
    if st.st_uid != os.geteuid():
        raise LockdownRefused("an entry is not owned by the user running the batch")


def _sha256_fd(fd):
    h = hashlib.sha256()
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(fd, 1 << 20)
        if not chunk:
            return h.hexdigest()
        h.update(chunk)


SHA256_HEX = re.compile(r"[0-9a-f]{64}")   # what `seal` records: hashlib's hexdigest, or null with no run.jsonl


def _recorded_sha(dir_fd, names):
    """-> the run_jsonl_sha256 this directory's run.jsonl must hash to, or None when there is nothing to check.

    Every redaction.json is checked, with or without a run.jsonl beside it. It must be a regular file (lstat'ed before
    it is opened: a FIFO, directory or link of that name is never read) and what `seal` writes: a JSON object whose
    "run_jsonl_sha256" is a 64-char lowercase hex sha256 when a regular-file run.jsonl is there, and null when none is
    (a run sealed before it wrote one). A sha256 recorded with no regular-file run.jsonl (deleted, or replaced by a
    directory, link or special file) is raw evidence missing. Anything else refuses the batch: a recorded sha256 is
    never silently skipped. `_walk` hashes the run.jsonl against the one returned, and refuses it as raw evidence
    missing if it is no longer a regular file when the walk reaches it."""
    if "redaction.json" not in names:
        return None
    if not stat.S_ISREG(os.stat("redaction.json", dir_fd=dir_fd, follow_symlinks=False).st_mode):
        raise LockdownRefused("a redaction.json is a symlink or not a regular file")
    fd = _open_at("redaction.json", dir_fd, False)
    try:
        chunks = []
        while True:
            chunk = os.read(fd, 1 << 16)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(fd)
    try:
        record = json.loads(b"".join(chunks).decode("utf-8"))
    except ValueError:
        record = None
    if not isinstance(record, dict) or "run_jsonl_sha256" not in record:
        raise LockdownRefused("a redaction.json does not parse")
    want = record["run_jsonl_sha256"]
    if RAW not in names or not stat.S_ISREG(os.stat(RAW, dir_fd=dir_fd, follow_symlinks=False).st_mode):
        if want is not None:
            raise LockdownRefused("a run.jsonl recorded in its redaction.json is missing (raw evidence missing)")
        return None
    if not (isinstance(want, str) and SHA256_HEX.fullmatch(want)):
        raise LockdownRefused("a redaction.json has no valid run_jsonl_sha256 for the run.jsonl beside it")
    return want


def _walk(dir_fd, seen, tighten):
    """Pass 1 (tighten=False): record (dev, ino) of every entry, refuse any odd one. Pass 2: fchmod each entry, which
    must still be the object pass 1 recorded."""
    names = sorted(os.listdir(dir_fd))
    want_sha = _recorded_sha(dir_fd, names)
    for name in names:
        st = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        if name == RAW and want_sha is not None and not stat.S_ISREG(st.st_mode):   # replaced since _recorded_sha
            raise LockdownRefused("a run.jsonl recorded in its redaction.json is missing (raw evidence missing)")
        _check_entry(st)
        is_dir = stat.S_ISDIR(st.st_mode)
        if not tighten:
            seen[(st.st_dev, st.st_ino)] = is_dir
        elif seen.get((st.st_dev, st.st_ino)) is not is_dir:
            raise LockdownRefused("the out-dir changed during the permission check")
        fd = _open_at(name, dir_fd, is_dir)
        try:
            fst = os.fstat(fd)
            if (fst.st_dev, fst.st_ino) != (st.st_dev, st.st_ino):
                raise LockdownRefused("the out-dir changed during the permission check")
            _check_entry(fst)
            if is_dir:
                if tighten:
                    os.fchmod(fd, LOCKDOWN_DIR)
                _walk(fd, seen, tighten)
            else:
                check = name == RAW and want_sha is not None
                if check and _sha256_fd(fd) != want_sha:   # pass 1 too: refused before anything changes
                    raise LockdownRefused("a run.jsonl does not match the sha256 in its redaction.json")
                if tighten:
                    os.fchmod(fd, LOCKDOWN_FILE)
                    if check and _sha256_fd(fd) != want_sha:
                        raise LockdownRefused("a run.jsonl changed during the permission check")
        finally:
            os.close(fd)


def lockdown(out_dir):
    """Make every entry under `out_dir` owner-only (dirs 0700, files 0600), or refuse (LockdownRefused): with nothing
    changed when pass 1 refuses; when pass 2 refuses, the out-dir and the entries it already tightened stay owner-only,
    the rest keep their modes, nothing is loosened and no content is written."""
    root = _open_at(os.path.abspath(out_dir), None, True)
    try:
        st = os.fstat(root)
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid():
            raise LockdownRefused("the out-dir is not a directory owned by the user running the batch")
        seen = {}
        try:
            _walk(root, seen, tighten=False)
        except OSError:
            raise LockdownRefused("the out-dir could not be read in full") from None
        except RecursionError:   # a deep tree, or a deeply nested redaction.json: refused, never a traceback
            raise LockdownRefused(NESTED_TOO_DEEPLY) from None
        try:
            os.fchmod(root, LOCKDOWN_DIR)
            _walk(root, seen, tighten=True)
        except OSError:
            raise LockdownRefused("an entry could not be made owner-only") from None
        except RecursionError:
            raise LockdownRefused(NESTED_TOO_DEEPLY) from None
    finally:
        os.close(root)


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
    elif len(argv) == 2 and argv[0] == "lockdown":
        lockdown(argv[1])
    else:
        print("usage: redact_derived.py selftest | seal <run-dir> | file <path> | text | lockdown <out-dir>", file=sys.stderr)
        return 64
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except LockdownRefused as exc:   # a static reason: no path, no content
        print(f"!! out-dir refused: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:   # name the failure, never echo content
        where = getattr(exc, "filename", None) or (str(exc) if isinstance(exc, RedactionError) else "")
        print(f"!! redaction failed: {type(exc).__name__}{': ' + str(where) if where else ''}", file=sys.stderr)
        sys.exit(1)
