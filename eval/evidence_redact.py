#!/usr/bin/env python3
"""The one redaction step for evidence an eval scorer WRITES (UD U22 H4, external security review).

The W9 scorers copy raw strings out of a run into their results: a Bash command, a hand-back tail, a path, a URL.
A credential in one of them (an Authorization or Bearer header, a vendor API key, a `password=` parameter, a
`scheme://user:pass@host` URL) would be copied into a result file that is meant to be read and shared. Every scorer
output passes through `redact_tree` right before it is written, and every place a scorer shortens run text for
display goes through `clip` / `tail`, which redact the WHOLE string first and cut second (a cut first can remove the
prefix a rule keys on, `Bearer ` or `ghp_`, and leave the rest of the secret showing). So:

- the matcher input is never touched: rules and verdicts are computed on the raw run first, and only text that is
  shown is redacted (a verdict, a count or an exit code is never a string this step changes);
- the raw run files themselves (run.jsonl, stream.jsonl, the transcripts) are the evidence the scorers read and hash,
  and stay byte-exact; this step covers what a scorer writes about them.

Replaced with `<REDACTED>` (the name of a header, parameter or flag is kept, its value is not):
  - private key blocks: PEM `-----BEGIN ... PRIVATE KEY-----` and PGP `PRIVATE KEY BLOCK`, also one cut short, and
    the key text before an `-----END ... PRIVATE KEY-----` whose BEGIN was cut off
  - header values: Authorization, Proxy-Authorization, X-Api-Key, Api-Key, X-Auth-Token, Private-Token, X-<any>-Token
    / -Key / -Secret / -Signature, Cookie, Set-Cookie
  - `Bearer <token>`
  - `scheme://user:password@` and `scheme://<token>@` (a user part of 16 characters or more) URLs; at the end of a
    string (a truncation cut before the "@") `scheme://user:password` too, but never `scheme://host:port`
  - `curl -u user:password` / `--user user:password`; `mysql ... -p<password>`; `docker|podman|helm ... login ... -p X`
  - `<name>=<value>` and `<name>: <value>` (also JSON / YAML `"<name>": "<value>"`, and JSON whose quotes are
    backslash-escaped, `{\\"<name>\\": \\"<value>\\"}` as inside a JSON string or a shell-quoted `curl -d` body, up to 8
    backslashes) where the name is a credential name (U22 S4-r):
      - a long credential word after ANY prefix, joined with a separator, in camelCase or run together: token,
        secret, password, passwd, passphrase, credential(s), cookie, session id / sessid, jwt, authorization,
        signature, api key, access/secret/private/client/... key, client secret, secret key base (`PGPASSWORD`,
        `accessToken`, `_authToken`, `JSESSIONID`, `mypassword`, `awsSecretAccessKey`);
      - a short, ambiguous word (pass, pwd, auth) only on a boundary: after `_` `.` `-` (`DB_PASS`), on a camelCase
        step (`adminPwd`), in an all-capitals name (`PGPASS`, `SMTPPASS`) or as the whole name; never inside a word
        (`bypass`, `compass`, `author`). A bare `pass` counts only in the `=` form (`pass:` is test-report prose);
        a bare `key` or `sig` (the Azure SAS signature) only as the whole name in the `=` form (`sort_key=`,
        `monkey=` are not names). `max_tokens=`, `token_count=` and `TASK-TOKEN:` are not credential names;
      - a value that is plainly not a secret is kept (Sentinel L1): a verdict / status word (PASS, FAIL, none, true,
        ...) as the whole value; after a short, ambiguous name also when the whole first whitespace-separated word
        of an unquoted value is one (`auth: PASS (x)`, but not `DB_PASS=Pass!x`); and a number of up to 6 digits
        only when the whole name is `pass` (`PASS=103`, a count; `pwd=123456` and `key=1234` are redacted).
  - space-separated flags: `--password X`, `--token X`, `--accessToken X`, `--api-key X`, ... and netrc `password X`
  - vendor tokens: Anthropic and OpenAI `sk-...`, Stripe `sk_live_` / `rk_live_` / `whsec_`, GitHub `gh[pousr]_...`
    and `github_pat_...`, GitLab `glpat-...`, npm `npm_...`, Hugging Face `hf_...`, AWS `AKIA...` / `ASIA...` and a
    bare 40-character AWS secret shape, Slack `xox[abposr]-...` and webhook URLs, Discord webhook URLs, Google
    `AIza...` and `ya29.`, JSON web tokens `eyJ...` (also one cut before its first dot)
Minimum lengths are low on purpose: a token cut short must still be removed, not shown with its first characters.

Linear time (U22 S5, S5-r): every regex starts at a fixed literal or at the first character of a run (a lookbehind
refuses a start inside the run). A quantifier that can FAIL after it has scanned is bounded by a small constant
(at most 1024 characters, and one scan per literal start); an unbounded quantifier appears only where the match can
no longer fail (the JSON web token's dotted parts are optional, so a run of `eyJ-eyJ-...` is one match, not one
failed scan per start). The command-line rules (mysql `-p`, registry login `-p`) pair each flag with the closest
command word before it in one forward pass, and `name=value` / `name: value` walk back over at most one name run per
separator; whether a value is kept is decided on its first 80 characters, and only a value that is redacted is
scanned in full (and then skipped), so a kept value is never rescanned by the separators after it. A 1 MB hostile
string is redacted in well under a second (test_evidence_redact.py pins every hostile shape the security reviews
produced).

This is a best-effort scrubber over known shapes only, not a guarantee. Known misses: a credential in an unknown
shape; a bare suffix of a token with no prefix left (the reason for `tail`); a URL password of 1-5 digits at the very
end of a string, which reads as a port; a value split across lines; a credential passed as a plain command argument
(`sshpass -p X`); a quote escaped with more than 8 backslashes. The frozen eval/shape-baseline/scrub.py is not used
or changed (eval/shape-baseline/FREEZE.sha256).
"""
import re

REDACTED = "<REDACTED>"

# A long credential word: it may end a name after ANY prefix (`client_secret`, `X-Vault-Token`, `PGPASSWORD`,
# `accessToken`, `JSESSIONID`). The longest spelling is 14 characters, so only a name's last 24 are searched.
_LONG = (r"(?:token|secret|password|passwd|passphrase|credentials?|cookie|sess(?:ion)?[_-]?id|jwt|"
         r"authorization|signature|api[_-]?key|secret[_-]?key[_-]?base|"
         r"(?:access|secret|private|client|signing|master|encryption|account|app|license)[_-]?key|"
         r"client[_-]?secret)")
_LONG_TAIL = re.compile(r"(?i)" + _LONG + r"\Z")
_LONG_SPAN = 24
_LONG_ENDS = ("token", "secret", "password", "passwd", "passphrase", "credential", "credentials", "cookie", "id",
              "jwt", "authorization", "signature", "key", "base")      # a cheap test before _LONG_TAIL
# The short, ambiguous words: a credential only on a boundary (see `_name_kind`).
_SHORT = ("pass", "pwd", "auth")
_NAME_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-")
_NAME_MAX = 300                                       # a longer name run is judged on its last 300 characters
_QVALUE = r"\"[^\"\n]*\"?|'[^'\n]*'?"                  # a quoted value, also one cut before its closing quote
# Sentinel final F1: a double quote may be backslash-escaped (JSON inside a JSON string, a shell-quoted JSON body:
# `{\"password\": \"x\"}`), up to _ESC backslashes. After a credential name or a secret flag the value then runs to
# the next quote, as a quoted value does (its closing escape is part of it). A status word in escaped quotes is not
# kept: such a value is redacted, never shown with its quotes broken.
_ESC = 8
_QVALUE_ESC = r"\\{0,8}\"[^\"\n]*\"?|'[^'\n]*'?"
_HEADERS = (r"(?:proxy-)?authorization|x-api-key|api-key|x-auth-token|private-token|set-cookie|cookie|"
            r"x-[a-z0-9-]{1,40}-(?:token|key|secret|signature)")
_PEM_HEAD = r"-----BEGIN [A-Z0-9 ]{0,40}PRIVATE KEY(?: BLOCK)?-----"
_PEM_END = re.compile(r"-----END [A-Z0-9 ]{0,40}PRIVATE KEY(?: BLOCK)?-----")
_B64 = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\r\n\t ")
_PORT = re.compile(r"[0-9]{1,5}")
# A value that is a verdict or a status word, not a secret (Sentinel L1: `auth: PASS`, `token: none`).
_STATUS = frozenset(("pass", "passed", "fail", "failed", "ok", "none", "null", "nil", "true", "false", "yes", "no",
                     "n/a", "unset", "empty", "missing", "incomplete", "skipped", "unknown", "required", "optional",
                     "enabled", "disabled", "redacted", "<redacted>"))
_KEEP_PEEK = 80        # a keep decision needs at most 8 spaces, a quote and a 10-character word: 80 is ample


_SCHEME = re.compile(r"(?i)(?<![A-Za-z0-9+.-])[a-z][a-z0-9+.-]{0,31}\Z")


def _url_userinfo(m):
    """<scheme>://<userinfo>(@|end), matched from the "://" (the scheme, at most 32 characters, is checked here):
    redact a user:password, a long token-only user part, or (at the end of a string, a cut before the "@") a
    user:password, but never host:port."""
    if not _SCHEME.search(m.string, max(0, m.start() - 32), m.start()):
        return m.group(0)                                # not a URL scheme
    info, at = m.group(1), m.group(2)
    if at:                                               # followed by "@": a real userinfo
        if ":" in info or len(info) >= 16:
            return "://" + REDACTED + at
        return m.group(0)                                # ssh://git@host: a plain user name
    head, sep, last = info.rpartition(":")
    if not sep or info.startswith("[") or _PORT.fullmatch(last):
        return m.group(0)                                # host, host:port, an IPv6 literal
    return "://" + REDACTED


def _pem_tails(text):
    """The base64 text before an `-----END ... PRIVATE KEY-----` whose BEGIN was cut off (a tail slice). Walks back
    from each END over base64 characters only, never past the previous END: linear."""
    out, last = [], 0
    for m in _PEM_END.finditer(text):
        i = m.start()
        while i > last and text[i - 1] in _B64:
            i -= 1
        out.append(text[last:i] + REDACTED)
        last = m.end()
    if not out:
        return text
    return "".join(out) + text[last:]


def _command_flag(words, flags):
    """-> a rule that redacts the value (group "v") of a flag match whose closest command word before it lies within
    256 characters on the same command (no newline, `|`, `;` or `&` between them): `mysql -uroot -pX`,
    `docker login -u bob -p X`. Flags and words are each found once, in order (two pointers): linear."""
    def rule(text):
        ends = [w.end() for w in words.finditer(text)]
        if not ends:
            return text
        out, last, k = [], 0, -1
        for m in flags.finditer(text):
            while k + 1 < len(ends) and ends[k + 1] <= m.start():
                k += 1
            if k < 0 or m.start("v") < last:
                continue
            w = ends[k]
            if m.start() - w > 256 or any(c in text[w:m.start()] for c in "\n|;&"):
                continue
            out.append(text[last:m.start("v")] + REDACTED)
            last = m.end("v")
        if not out:
            return text
        return "".join(out) + text[last:]
    return rule


# mysql-style attached password: mysql -uroot -pSECRET (a bare `-p` there prompts, so only the attached form)
_MYSQL = _command_flag(re.compile(r"(?i)\b(?:mysql|mysqldump|mysqladmin|mariadb|mariadb-dump)\b"),
                       re.compile(r"\s-p(?P<v>(?=[^\s<])\S+)"))
# registry logins: docker|podman|nerdctl|buildah|helm [registry] login ... -p X / --password X
_LOGIN = _command_flag(re.compile(r"(?i)\b(?:docker|podman|nerdctl|buildah|helm)\s{1,8}(?:registry\s{1,8})?login\b"),
                       re.compile(r"\s(?:-p|(?i:--password))(?:\s{1,8}|=)(?P<v>(?=[^\s<-])\S+)"))


_KIND_MEMO = {}


def _name_kind(name, colon):
    """-> "long" / "short" / "bare" / "count" when `name` (a whole name run) names a credential, else None. Long
    words count after any prefix; a short word (pass, pwd, auth) only on a boundary: `_` `.` `-` before it, a
    camelCase step (`adminPwd`), an all-capitals name (`PGPASS`) or the whole name ("bare"; "count" when the whole
    name is `pass`, the only name whose short number is kept)."""
    key = (name, colon)
    if key not in _KIND_MEMO:
        if len(_KIND_MEMO) > 4096:
            _KIND_MEMO.clear()
        _KIND_MEMO[key] = _classify(name, colon)
    return _KIND_MEMO[key]


def _classify(name, colon):
    core = name.lstrip("-")
    if not core:
        return None
    low = core.lower()
    if colon and low == "task-token":
        return None                                      # the eval's own TASK-TOKEN marker is not a credential
    if low.endswith(_LONG_ENDS) and _LONG_TAIL.search(core[-_LONG_SPAN:]):
        return "long"
    if not colon and low in ("key", "sig"):
        return "bare"                                    # ?key=..., Azure SAS ?sig=...
    for word in _SHORT:
        if not low.endswith(word):
            continue
        if len(core) == len(word):
            if word == "pass":
                return None if colon else ("count" if name.lower() == "pass" else "bare")
            return "bare"
        before, first = core[-len(word) - 1], core[-len(word)]
        if before in "_.-" or (first.isupper() and (before.islower() or before.isdigit())) or core == core.upper():
            return "short"
        return None
    return None


def _escape_run(text, i):
    """-> the number of backslashes (at most _ESC) from text[i] on that come right before a double quote, else 0."""
    j = i
    while j < len(text) and j - i < _ESC and text[j] == "\\":
        j += 1
    return j - i if j > i and text[j:j + 1] == '"' else 0


def _keep_value(kind, value):
    """True when the value is plainly not a secret: a verdict / status word as the whole value; after a short name
    also as the whole first whitespace-separated word of an unquoted value (`Pass!x` is not `pass`); and a number of
    up to 6 digits when the whole name is `pass` (`PASS=103` is a count)."""
    v = value.strip(" \t")
    quoted = v[:1] in "\"'"
    if quoted:
        v = v[1:-1] if len(v) > 1 and v[-1] == v[0] else v[1:]
    low = v.lower()
    if low in _STATUS:
        return True
    if kind == "long":
        return False
    if not quoted and (low.split(None, 1) or [""])[0] in _STATUS:
        return True                                      # auth: PASS (checked) -- never a quoted passphrase
    return kind == "count" and v.isdigit() and len(v) <= 6


# A space-separated flag: `-`/`--`, a name of at most 64 characters (greedy, so a longer run fails after 64 steps
# at one start), whitespace, then a value that does not look like the next flag. The name is judged by _name_kind.
_FLAG = re.compile(r"(?<!\S)(--?)([A-Za-z0-9_.-]{1,64})(\s{1,8})(?=[^\s<-])(" + _QVALUE + r"|[^\s\"']+)")


# A secret flag whose value opens with an escaped quote (`--password \"x\"`). _FLAG redacts only its backslashes
# (`--password <REDACTED>"x\"`) and every later rule sees the rest as before; this last rule then extends that
# redaction to the closing quote. Only the flag and its spaces are matched, so a flag that is not a secret (`-d \"...`
# with no closing quote) consumes nothing; a secret flag's value is skipped (one pass: linear).
_FLAG_ESC_START = re.compile(r"(?<!\S)--?([A-Za-z0-9_.-]{1,64})\s{1,8}(?=(?:<REDACTED>|\\{1,8})\")")
_ESC_VALUE = re.compile(r"(?:<REDACTED>|\\{1,8})\"[^\"\n]*\"?")


def _flag_escaped(text):
    out, last = [], 0
    for m in _FLAG_ESC_START.finditer(text):
        if m.start() < last or _name_kind(m.group(1), True) is None:
            continue
        out.append(text[last:m.end()] + REDACTED)
        last = _ESC_VALUE.match(text, m.end()).end()
    if not out:
        return text
    return "".join(out) + text[last:]


def _flag_value(m):
    """--password X, --accessToken X, --db-pwd X (a bare `--pass`, `--key` or `--sig` is not a secret flag)."""
    kind = _name_kind(m.group(2), True)
    if kind is None or _keep_value(kind, m.group(4)):
        return m.group(0)
    return m.group(1) + m.group(2) + m.group(3) + REDACTED


# A separator a credential name can end before: the C regex engine finds these, so a text full of `:` or `=` after
# ordinary words costs one scan, not one Python step per separator.
_SEP = re.compile(r"(?i)(?:token|secret|password|passwd|passphrase|pwd|credentials?|cookie|sess(?:ion)?[_-]?id|jwt|"
                  r"auth|authorization|signature|key|key[_-]?base|pass|sig)(?:[\"']|\\{1,8}\")?[ \t]{0,8}([=:])")
_VALUE_EQ = re.compile(r"[ \t]{0,8}(?=[^\s&<>;,)])(?:" + _QVALUE_ESC + r"|[^\s&\"'<>;,)]+)")
_VALUE_COLON = re.compile(r"[ \t]{0,8}(?=[^\s<,;}\]])(?:" + _QVALUE_ESC + r"|[^\r\n\"',;}<>\]]+)")


# Per kind of value (unquoted after `=`, unquoted after `:`, double- or single-quoted): the characters that end it
# and the rest of it from a given point (the classes of the two patterns above and of _QVALUE).
_ENDS = {"=": (re.compile(r"[\s&\"'<>;,)]"), re.compile(r"[^\s&\"'<>;,)]*")),
         ":": (re.compile(r"[\r\n\"',;}<>\]]"), re.compile(r"[^\r\n\"',;}<>\]]*")),
         '"': (re.compile(r'["\n]'), re.compile(r'[^"\n]*"?')),
         "'": (re.compile(r"['\n]"), re.compile(r"[^'\n]*'?"))}


def _name_before(text, i, floor):
    """-> the `_name_kind` of the name that ends before the separator at i (spaces and, for `"name":`, a quote
    between them), walking back over at most one name run and never past `floor`."""
    e = i
    while e > floor and i - e < 8 and text[e - 1] in " \t":
        e -= 1                                           # spaces between the name and the separator
    quote = ""
    if text[i] == ":" and e > floor and text[e - 1] in "\"'":
        quote, e = text[e - 1], e - 1                    # "name": value
        b = e
        while quote == '"' and e > floor and b - e < _ESC and text[e - 1] == "\\":
            e -= 1                                       # \"name\": value (escaped JSON, Sentinel final F1)
    s = e
    while s > floor and e - s < _NAME_MAX and text[s - 1] in _NAME_CHARS:
        s -= 1
    if s == e or (quote and (s == floor or text[s - 1] != quote)):
        return None                                      # no name; a quoted name must open with the same quote
    return _name_kind(text[s:e], text[i] == ":")


def _last_stop(stop, text, a, b):
    end = -1
    for m in stop.finditer(text, a, b):
        end = m.start()
    return end


def _name_values(text):
    """`name=value` and `name: value` / `"name": "value"` whose name is a credential name (`_name_kind`, judged on
    the WHOLE name run, so `bypass`, `sort_key` and `monkey` are not names of a secret). Driven by the separators,
    not by every position: each separator walks back over at most one name run and forward over at most one value,
    and a redacted value is skipped, so the work is linear in the length of the text.

    A redacted value can swallow another credential name (`pwd=x!DB_PASS='y'`, `PWD=x.auth: y z`, `a='b='y`). Its
    value is redacted with it: a value that starts where the redaction stopped (or at its closing quote) is matched
    as usual, and the redaction runs on to the end of an unquoted value of the other form that the stop does not
    end. In each round the stops of the redacted stretch and the tail after it are scanned once per form (`last` is
    fixed within a round and moves past that tail), however many names the stretch swallowed, so this stays
    linear."""
    seps = [m.start(1) for m in _SEP.finditer(text)]
    out, last, k = [], 0, 0
    while k < len(seps):
        i = seps[k]
        k += 1
        inside = i < last
        if inside:
            j = i + 1
            while j < last and j - i <= 8 and text[j] in " \t":
                j += 1
            if j < last - 1 or (j == last - 1 and text[j] not in "\"'"):
                continue                                 # its value lies inside a value already redacted
        kind = _name_before(text, i, 0)                  # a name may end inside a redacted value: `x=a:b token\t:`
        if kind is None:
            continue
        colon = text[i] == ":"
        pat = _VALUE_COLON if colon else _VALUE_EQ
        peek = pat.match(text, i + 1, i + 1 + _KEEP_PEEK)    # keep or not, decided on a bounded prefix
        if not peek or _keep_value(kind, peek.group(0)):
            continue                                     # kept: `last` stays, but only _KEEP_PEEK was scanned
        v = pat.match(text, i + 1)
        lead = len(v.group(0)) - len(v.group(0).lstrip(" \t"))
        out.append(text[last:max(last, i + 1 + lead)] + REDACTED)
        seg, last, q = i + 1 + lead, v.end(), k
        while q < len(seps) and seps[q] < last:          # a swallowed name whose own value runs past `last`
            stops, tails = {}, {}                        # per form, once per round: `last` is fixed in it
            end = last
            while q < len(seps) and seps[q] < last:
                i2 = seps[q]
                q += 1
                j = i2 + 1
                while j < last and j - i2 <= 8 and text[j] in " \t":
                    j += 1
                if j >= last:
                    continue                             # starts at `last` or later: the main loop matches it
                esc = _escape_run(text, j)               # \"value\": the double-quoted form
                form, a = (text[j + esc], j + esc + 1) if text[j + esc] in "\"'" else (text[i2], j)
                if form not in stops:
                    stops[form] = _last_stop(_ENDS[form][0], text, seg, last)
                if stops[form] >= a or _name_before(text, i2, 0) is None:
                    continue                             # its value ends inside the redaction, or no name
                if form not in tails:
                    tails[form] = _ENDS[form][1].match(text, last).end()
                end = max(end, tails[form])
            if end == last:
                break
            seg, last = last, end
    if not out:
        return text
    return "".join(out) + text[last:]


_RULES = (
    # a PEM / PGP private key block, also one cut short (the match cannot fail after BEGIN: it ends at END or \Z)
    (re.compile(_PEM_HEAD + r"[\s\S]*?(?:-----END [A-Z0-9 ]{0,40}PRIVATE KEY(?: BLOCK)?-----|\Z)"), REDACTED),
    # ... and a key whose BEGIN was cut off
    (None, _pem_tails),
    # header values (to the end of the line or a closing quote): Authorization: Basic x, PRIVATE-TOKEN: x
    (re.compile(r"(?i)(?<![A-Za-z0-9_-])(" + _HEADERS + r")(\s{0,8}:\s{0,8})(?=[^\s<])[^\r\n\"']+"),
     r"\1\2" + REDACTED),
    # scheme://userinfo@host (and the end-of-string cut, never host:port); found from the literal "://", bounded
    (re.compile(r"://([^/\s@\"'<>?#]{1,1024})(@|\Z)"), _url_userinfo),
    # curl -u user:password / --user user:password / --user=user:password
    (re.compile(r"(?<!\S)(-u|--user)(\s{1,8}|=)[\"']?[^\s:\"'<]{1,256}:[^\s\"']{0,1024}"), r"\1\2" + REDACTED),
    # mysql -uroot -pSECRET
    (None, _MYSQL),
    # docker|podman|nerdctl|buildah|helm [registry] login ... -p X / --password X
    (None, _LOGIN),
    # space-separated secret flags: --password X, --token X, --accessToken X, --api-key X, --db-pwd X
    (_FLAG, _flag_value),
    # netrc: machine h login bob password X
    (re.compile(r"(?i)(?<![\w-])((?:machine|login|account)\s{1,8}\S{1,256}\s{1,8}password\s{1,8})(?=[^\s<])\S+"),
     r"\1" + REDACTED),
    # name=value parameters, environment assignments, --flag=value, YAML name: value and JSON "name": "value"
    (None, _name_values),
    # Bearer <token>, also "Bearer:<token>"
    (re.compile(r"(?i)\b(bearer)(\s{1,8}|:\s{0,8})(?=[A-Za-z0-9._~+/=-])[A-Za-z0-9._~+/=-]+"), r"\1\2" + REDACTED),
    # webhook URLs whose path is the secret
    (re.compile(r"(?i)(hooks\.slack\.com/)(?:services|workflows|triggers)/[A-Za-z0-9/_-]+"), r"\1" + REDACTED),
    (re.compile(r"(?i)(discord(?:app)?\.com/api/webhooks/)[0-9]{1,30}/[A-Za-z0-9_-]+"), r"\1" + REDACTED),
    # vendor token shapes, one pass: Anthropic sk-ant-... and OpenAI sk-...; Stripe secret / restricted key and
    # webhook secret; GitHub; GitLab; npm; Hugging Face; AWS access key id; Slack; Google API key and OAuth token;
    # JSON web token (its dotted parts optional, so the match cannot fail once `eyJ` + 8 has matched: U22 S5-r)
    (re.compile(r"\b(?:sk-[A-Za-z0-9_-]{4,}|(?:sk|rk)_(?:live|test)_[A-Za-z0-9]+|whsec_[A-Za-z0-9]{4,}|"
                r"(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]+|gl(?:pat|dt|ptt|rt|soat|cbt)-[A-Za-z0-9_-]+|"
                r"npm_[A-Za-z0-9]{4,}|hf_[A-Za-z0-9]{4,}|(?:AKIA|ASIA)[0-9A-Z]{4,}|xox[abposr]-[A-Za-z0-9-]{4,}|"
                r"AIza[0-9A-Za-z_-]{4,}|ya29\.[0-9A-Za-z_-]{4,}|"
                r"eyJ[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]*){0,2})"), REDACTED),
    # a bare 40-character AWS secret access key shape: base64 alphabet, upper, lower and a digit, exactly 40 long
    (re.compile(r"(?<![A-Za-z0-9/+=])(?=[A-Za-z0-9/+]{0,39}[A-Z])(?=[A-Za-z0-9/+]{0,39}[a-z])"
                r"(?=[A-Za-z0-9/+]{0,39}[0-9])[A-Za-z0-9/+]{40}(?![A-Za-z0-9/+=])"), REDACTED),
    # a secret flag whose value opens with an escaped quote: --password \"X\" (Sentinel final F1), last
    (None, _flag_escaped),
)


# Per rule, the lower-case substrings it cannot match without (empty = always run). A rule whose needles are all
# absent is skipped; a replacement only ever inserts <REDACTED>, so it never creates a needle a later rule would miss.
_NEEDLES = (("private key",), ("-----end",), (":",), ("://",), ("-u", "--user"), ("-p",), ("-p", "--password"),
            ("-",), ("password",), ("=", ":"), ("bearer",), ("hooks.slack.com",), ("discord",), (), (), ('\\"',))
assert len(_NEEDLES) == len(_RULES)


def redact(text):
    """-> `text` with every credential shape above replaced by <REDACTED>. A non-string is returned unchanged."""
    if not isinstance(text, str):
        return text
    low = text.lower()
    for (pattern, repl), needles in zip(_RULES, _NEEDLES):
        if needles and not any(n in low for n in needles):
            continue
        text = repl(text) if pattern is None else pattern.sub(repl, text)
    return text


def clip(text, limit):
    """The first `limit` characters of `text` for display, redacted BEFORE the cut (a non-string: unchanged)."""
    return redact(text)[:limit] if isinstance(text, str) else text


def tail(text, limit):
    """The last `limit` characters of `text` for display, redacted BEFORE the cut: a cut first can drop the prefix a
    rule keys on (`Bearer `, `ghp_`, `password=`) and leave the rest of the secret showing (U22 S3)."""
    return redact(text)[-limit:] if isinstance(text, str) else text


def redact_tree(obj):
    """-> a copy of a JSON-shaped value (dict / list / tuple / str / number / bool / None) with every string VALUE
    redacted. Keys are the scorer's own field names and stay as they are; numbers and booleans are never changed."""
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, dict):
        return {k: redact_tree(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact_tree(v) for v in obj]
    return obj
