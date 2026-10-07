"""U22 H4 (external security review): what the W9 scorers write is redacted with the one shared helper
eval/evidence_redact.py, after the verdict is decided. Every synthetic secret here is built by concatenation at run
time, so this file holds no literal that a secret scanner matches. No model is called; no git process is started."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
EVAL = PKG.parent
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG / "fixtures"))
sys.path.insert(1, str(EVAL))

import evidence_redact as er  # noqa: E402
import score_v4  # noqa: E402
import v4_materialize as materialize  # noqa: E402

R = er.REDACTED
# synthetic secrets, assembled at run time
ANT = "sk-" + "ant-" + "api03-" + "Zq7" * 12
OAI = "sk-" + "proj-" + "Xy9" * 12
GHP = "gh" + "p_" + "Ab3" * 12
GHO = "gh" + "o_" + "Cd4" * 12
GHPAT = "github" + "_pat_" + "Ef5" * 12
AWS = "AK" + "IA" + "QWERTYUIOPASDFGH"
SLACK = "xo" + "xb-" + "1234567890-" + "Gh6" * 6
GOOG = "AI" + "za" + "Sy" + "Jk8" * 11
JWT = "ey" + "J" + "hbGciOiJIUzI1NiJ9" + "." + "ey" + "J" + "zdWIiOiIxMjM0In0" + "." + "Mn9" * 8
PW = "hun" + "ter2-" + "Pq1" * 4
PEM = "-----BEGIN " + "RSA PRIVATE KEY" + "-----\n" + "MIIB" + "Rs2" * 20 + "\n-----END " + "RSA PRIVATE KEY" + "-----"


@pytest.mark.parametrize("text,secret,keep", [
    ("curl -H 'Authorization: Bearer %s' https://api.example.invalid" % OAI, OAI, "Authorization: " + R),
    ("curl -H \"Authorization: Basic %s\" x" % PW, PW, "Authorization: " + R),
    ("curl -H 'Proxy-Authorization: %s' x" % PW, PW, "Proxy-Authorization: " + R),
    ("curl -H 'X-Api-Key: %s' x" % ANT, ANT, "X-Api-Key: " + R),
    ("curl -H 'Cookie: session=%s' x" % PW, PW, "Cookie: " + R),
    ("token is Bearer %s now" % GHO, GHO, "Bearer " + R),
    ("export ANTHROPIC_API_KEY=%s" % ANT, ANT, "ANTHROPIC_API_KEY=" + R),
    ("OPENAI_API_KEY=%s python3 run.py" % OAI, OAI, "OPENAI_API_KEY=" + R),
    ("git clone https://x:%s@github.example.invalid/o/r" % GHP, GHP, "https://" + R + "@github.example.invalid"),
    ("echo %s" % GHPAT, GHPAT, "echo " + R),
    ("aws_access_key_id=%s" % AWS, AWS, "aws_access_key_id=" + R),
    ("id %s in log" % AWS, AWS, "id " + R + " in log"),
    ("SLACK_BOT=%s" % SLACK, SLACK, R),
    ("maps?k=1&key=%s&z=2" % GOOG, GOOG, "key=" + R + "&z=2"),
    ("url ?a=1&token=%s#f" % PW, PW, "token=" + R),
    ("--password=%s --secret='%s'" % (PW, PW), PW, "--password=" + R),
    ("client_secret=\"%s\"" % PW, PW, "client_secret=" + R),
    ("db: postgres://admin:%s@db.example.invalid:5432/app" % PW, PW, "postgres://" + R + "@db.example.invalid"),
    ("curl -u admin:%s https://x" % PW, PW, "-u " + R),
    ("curl --user=admin:%s https://x" % PW, PW, "--user=" + R),
    ("auth %s" % JWT, JWT, "auth " + R),
    ("key file:\n%s\ndone" % PEM, "Rs2Rs2", R + "\ndone"),
])
def test_each_credential_shape_is_redacted(text, secret, keep):
    out = er.redact(text)
    assert secret not in out and keep in out, out


@pytest.mark.parametrize("cut", [4, 8, 12])
def test_a_secret_cut_by_truncation_is_still_redacted(cut):
    """The scorers truncate (a command to its first 200 characters): a token, header value or URL password cut short
    after its public prefix is removed too, not shown with its first characters."""
    for head, body in (("git push https://bob:", PW), ("Authorization: Bearer ", ANT[len("sk-ant-api03-"):]),
                       ("x sk-ant-api03-", ANT[len("sk-ant-api03-"):]), ("x " + GHP[:4], GHP[4:]),
                       ("x " + AWS[:4], AWS[4:]), ("token=", PW)):
        out = er.redact(head + body[:cut])
        assert body[:cut] not in out and R in out, (head, cut, out)


# U22 S4 (Sentinel's probe set, scratchpad u22-sentinel/probe_h4.py): 54 credential shapes. The 55th shape of the
# probe, a bare token suffix with no prefix left ("<suffix> done", what a tail cut leaves), cannot be recognised by
# any pattern; it is closed by redacting before the cut (test_a_secret_straddling_a_tail_cut_leaks_nothing).
SEC = "Zq9" + "Xv7Lm2Pw4Rt8Ny6Kb3Hd5"


def _j(*parts):
    return "".join(parts)


SHAPES = [
    ("hdr Authorization Basic", _j("curl -H 'Authorization: Basic ", SEC, "' x")),
    ("hdr Authorization: Bearer", _j("Authorization: Bearer ", SEC)),
    ("hdr lowercase", _j("authorization:bearer ", SEC)),
    ("hdr Proxy-Authorization", _j("Proxy-Authorization: Basic ", SEC)),
    ("hdr X-Api-Key", _j("-H X-Api-Key:", SEC)),
    ("hdr Cookie", _j("Cookie: sid=", SEC)),
    ("hdr PRIVATE-TOKEN (gitlab)", _j("-H 'PRIVATE-TOKEN: ", SEC, "'")),
    ("hdr X-GitHub-Token", _j("X-GitHub-Token: ", SEC)),
    ("hdr X-Vault-Token", _j("X-Vault-Token: ", SEC)),
    ("hdr anthropic x-api-key json", _j('{"x-api-key": "', SEC, '"}')),
    ("json Authorization Basic", _j('{"Authorization": "Basic ', SEC, '"}')),
    ("json password", _j('{"password": "', SEC, '"}')),
    ("json api_key", _j('{"api_key":"', SEC, '"}')),
    ("json password cut before the closing quote", _j('{"password": "', SEC)),
    ("yaml password", _j("password: ", SEC)),
    ("yaml token", _j("token: ", SEC)),
    ("yaml client_secret", _j("  client_secret: ", SEC, "\n  other: 1")),
    ("env TOKEN=", _j("export GITHUB_TOKEN=", SEC)),
    ("env DB_PASS=", _j("DB_PASS=", SEC, " ./run")),
    ("env quoted spaces", _j("PASSWORD='a b ", SEC, "'")),
    ("flag --password=", _j("mysql --password=", SEC)),
    ("flag --password <sp>", _j("mysql --password ", SEC)),
    ("flag --token <sp>", _j("cli --token ", SEC)),
    ("flag --api-key <sp>", _j("cli --api-key ", SEC, " --verbose")),
    ("flag --client-secret <sp> quoted", _j("cli --client-secret '", SEC, "'")),
    ("flag -p<val> mysql", _j("mysql -uroot -p", SEC)),
    ("query ?token=", _j("https://h/x?token=", SEC, "&a=1")),
    ("query access_token", _j("https://h/x?access_token=", SEC)),
    ("query sig (Azure SAS)", _j("https://a.blob.core.windows.net/c?sv=2020&sig=", SEC)),
    ("query X-Amz-Signature", _j("https://s3/x?X-Amz-Credential=AK/x&X-Amz-Signature=", SEC)),
    ("query X-Amz-Security-Token", _j("https://s3/x?X-Amz-Security-Token=", SEC)),
    ("url user:pass@", _j("git clone https://bob:", SEC, "@github.com/o/r")),
    ("url token@ (no colon)", _j("git clone https://", SEC, "@github.com/o/r")),
    ("url user:pass truncated", _j("https://bob:", SEC[:10])),
    ("curl -u", _j("curl -u bob:", SEC, " https://h")),
    ("anthropic sk-ant", _j("sk-", "ant-api03-", SEC)),
    ("openai sk-proj", _j("sk-", "proj-", SEC)),
    ("stripe sk_live", _j("sk_", "live_", SEC)),
    ("stripe rk_live", _j("rk_", "live_", SEC)),
    ("github ghp_", _j("gh", "p_", SEC)),
    ("github_pat_", _j("github", "_pat_", SEC)),
    ("gitlab glpat-", _j("gl", "pat-", SEC)),
    ("npm npm_", _j("np", "m_", SEC, "Ab12Cd34Ef")),
    ("aws AKIA", _j("AK", "IA", "ABCDEFGHIJKLMNOP")),
    ("aws secret bare 40", _j("aws s3 ls # ", "wJalrXUtnFEMI/K7MDENG/bPxRfiCY", SEC[:10])),
    ("slack xoxb", _j("xo", "xb-", "1234-", SEC)),
    ("slack webhook url", _j("https://hooks.slack.com/services/T000/B000/", SEC)),
    ("google AIza", _j("AI", "za", SEC)),
    ("google oauth ya29", _j("ya", "29.", SEC)),
    ("huggingface hf_", _j("hf", "_", SEC, "abcdefghij")),
    ("jwt full", _j("ey", "JhbGciOiJIUzI1NiJ9.", "eyJzdWIiOiIxIn0.", SEC)),
    ("jwt truncated after 1st dot", _j("ey", "JhbGciOiJIUzI1NiJ9.", "eyJzdWIi", SEC[:8])),
    ("pem rsa", _j("-----BEGIN ", "RSA PRIVATE KEY-----\nMIIE", SEC, "\n-----END RSA PRIVATE KEY-----")),
    ("pem openssh truncated", _j("-----BEGIN ", "OPENSSH PRIVATE KEY-----\nb3Bl", SEC)),
    ("pem pgp", _j("-----BEGIN ", "PGP PRIVATE KEY BLOCK-----\n", SEC, "\n-----END PGP PRIVATE KEY BLOCK-----")),
    ("pem tail only (from [-N:])", _j(SEC, "Q==\n-----END ", "PRIVATE KEY-----")),
    ("Bearer no space json", _j('"Bearer:', SEC, '"')),
    ("netrc", _j("machine h login bob password ", SEC)),
    ("docker login -p", _j("docker login -u bob -p ", SEC)),
    ("docker login --password=", _j("docker login --password=", SEC, " r.example.invalid")),
    # U22 S4-r: run-together and camelCase names (Sentinel iter 2)
    ("env PGPASSWORD before psql", _j("PGPASSWORD=", SEC, " psql -h db")),
    ("npmrc _authToken", _j("//registry.npmjs.org/:_authToken=", SEC)),
    ("query ?accessToken=", _j("https://h/x?accessToken=", SEC, "&a=1")),
    ("cookie JSESSIONID=", _j("JSESSIONID=", SEC)),
    ("env DBPASS=", _j("DBPASS=", SEC, " ./run")),
    ("env mypassword=", _j("mypassword=", SEC)),
    ("json camelCase accessToken", _j('{"accessToken": "', SEC, '"}')),
    ("flag camelCase --adminPwd <sp>", _j("cli --adminPwd ", SEC)),
]


def _leaks(out):
    return any(piece in out for piece in (SEC[:8], SEC[-8:], SEC[5:13]))


@pytest.mark.parametrize("label,text", SHAPES, ids=[s[0] for s in SHAPES])
def test_u22_s4_every_probed_credential_shape_is_redacted(label, text):
    out = er.redact(text)
    assert not _leaks(out) and R in out, (label, out)
    assert er.redact(out) == out, label                                # idempotent


@pytest.mark.parametrize("label,text", SHAPES, ids=[s[0] for s in SHAPES])
def test_u22_s3_a_head_cut_anywhere_leaves_no_secret(label, text):
    """clip(): redacted first, then cut, so no cut position shows any 8 characters of the secret."""
    for n in range(len(text) + 1):
        out = er.clip(text, n)
        assert len(out) <= n and not _leaks(out), (label, n, out)


@pytest.mark.parametrize("label,text", SHAPES, ids=[s[0] for s in SHAPES])
def test_u22_s3_a_secret_straddling_a_tail_cut_leaks_nothing(label, text):
    """tail(): a cut that lands inside the credential (its prefix gone) still shows none of it. A shape that is a
    credential only at the end of a string (a URL cut before its "@") stays at the end."""
    framed = "z" * 170 + " " + text + ("" if label == "url user:pass truncated" else " " + "z" * 170)
    for n in range(1, len(framed) + 1):
        out = er.tail(framed, n)
        assert len(out) <= n and not _leaks(out), (label, n, out)


def test_u22_s3_mutation_cut_first_leaks():
    """The order is what matters: cut first, then redact, shows the secret for a Bearer header and a ghp_ token."""
    for text in (_j("Authorization: Bearer ", SEC, " " + "z" * 170), _j("gh", "p_", SEC, " " + "z" * 170)):
        n = len(text) - text.index(SEC) - 2                  # the cut lands just after the prefix
        assert _leaks(er.redact(text[-n:])) and not _leaks(er.tail(text, n)), text


@pytest.mark.parametrize("text", [
    # Chris M2: a host:port at the end of a string is a destination, not a user:password
    "curl http://localhost:8080",
    "curl -s http://169.254.169.254:80",
    "see https://example.com:443",
    "http://[::1]:8080",
    "ssh://git@github.example.invalid/o/r.git",
    # Chris L1: names that merely end in pass / key / auth letters are not credential names
    "PASS=103", "bypass=1", "sort_key=name", "monkey=1", "max_tokens=4096", "token_count=3", "keyboard=us",
    "pass_rate=0.9", "author=bob", "TASK-TOKEN: PLUGIN-abc",
    "git push --force-with-lease origin HEAD:main",
    "python3 -m pytest tests -q",
    "ls .shode-house/config.yaml && cat README.md",
    "https://example.invalid:8443/path?page=2",
    "skill shode-house:developer loaded; TASK-TOKEN: PLUGIN-abc",
    "spawn shode-house:developer: served agent body is not the arm's agents/developer.md",
    "PASS", "FAIL", "INCOMPLETE", "",
])
def test_ordinary_evidence_is_unchanged(text):
    assert er.redact(text) == text


def test_u22_m2_end_of_string_userinfo_is_still_redacted_but_the_host_kept():
    out = er.redact("git push https://bob:" + SEC[:10])
    assert not _leaks(out) and out == "git push https://" + R
    assert er.redact("curl http://bob:" + SEC + "@localhost:8080/x") == "curl http://" + R + "@localhost:8080/x"


# U22 S4-r (Sentinel iter 2, scratchpad u22-sentinel2/probe_diff.py): 91 names x 8 forms. The iter-2 rewrite stopped
# redacting camelCase and run-together names in the `=` forms (`PGPASSWORD=`, `?accessToken=`, `JSESSIONID=`,
# `DBPASS=`, npmrc `_authToken=`: 112 cells the 61 redactor covered). Every cell is redacted except _S4R_MISS: names
# that are not credential words (a DSN or URL value is covered by the URL rule when it holds user:password@), and a
# bare `key` / `sig` / `pass` in the `:` and space-flag forms, which is ordinary prose (`pass: 12`, `key: name`).
S4R_NAMES = [
    "accessToken", "authToken", "refreshToken", "idToken", "apiToken", "sessionToken", "githubToken", "bearerToken",
    "ACCESSTOKEN", "GITHUBTOKEN", "NPMTOKEN", "DBPASS", "PGPASS", "SMTPPASS", "mypassword", "dbpassword",
    "userPassword", "adminPwd", "AWSSECRETKEY", "awsSecretAccessKey", "secretAccessKey", "SECRET_ACCESS_KEY",
    "aws_secret_access_key", "GITHUB_TOKEN", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "api_key", "apikey", "apiKey",
    "clientSecret", "client_secret", "privateKey", "private_key", "sessionId", "session_id", "sessid", "PHPSESSID",
    "JSESSIONID", "jwt", "JWT_SECRET", "jwtSecret", "SECRET_KEY_BASE", "secret_key_base", "DJANGO_SECRET_KEY",
    "encryptionKey", "masterKey", "SIGNING_KEY", "webhookSecret", "WEBHOOK_SECRET", "auth", "Auth", "credentials",
    "credential", "passphrase", "PASSWORD", "password", "pwd", "PWD", "passwd", "token", "Token", "secret", "key",
    "sig", "signature", "code", "otp", "pin", "DATABASE_URL", "REDIS_URL", "dsn", "SENTRY_DSN", "connectionString",
    "ConnectionString", "sas", "SAS_TOKEN", "sasToken", "refresh_token", "id_token", "access_token", "x-api-key",
    "X-API-KEY", "apiSecret", "api_secret", "consumer_secret", "oauth_token", "oauth_token_secret", "pass", "Pass",
    "db.password", "spring.datasource.password",
]
S4R_FORMS = {
    "eq": lambda n: _j(n, "=", SEC),
    "export": lambda n: _j("export ", n, "=", SEC),
    "query": lambda n: _j("https://h/x?", n, "=", SEC, "&a=1"),
    "json": lambda n: _j('{"', n, '": "', SEC, '"}'),
    "pyrepr": lambda n: _j("{'", n, "': '", SEC, "'}"),
    "yaml": lambda n: _j(n, ": ", SEC),
    "flag=": lambda n: _j("--", n, "=", SEC),
    "flag sp": lambda n: _j("--", n, " ", SEC),
}
_PROSE_FORMS = ("json", "pyrepr", "yaml", "flag sp")
_S4R_MISS = dict({n: tuple(S4R_FORMS) for n in ("code", "otp", "pin", "DATABASE_URL", "REDIS_URL", "dsn",
                                                 "SENTRY_DSN", "connectionString", "ConnectionString", "sas")},
                 **{n: _PROSE_FORMS for n in ("key", "sig", "pass", "Pass")})


@pytest.mark.parametrize("name", S4R_NAMES)
def test_u22_s4r_every_credential_name_in_every_form_is_redacted(name):
    for form, make in S4R_FORMS.items():
        if form in _S4R_MISS.get(name, ()):
            continue
        out = er.redact(make(name))
        assert not _leaks(out) and R in out, (name, form, out)
        assert er.redact(out) == out, (name, form)


# Sentinel's 39 extra shapes; False = a known miss of a best-effort scrubber (Sentinel I1, leaks in 61 too)
S4R_EXTRA = [
    ("conn url", _j("postgres://app:", SEC, "@db:5432/x"), True),
    ("conn str", _j("Server=db;User Id=sa;Password=", SEC, ";"), True),
    ("mongodb srv", _j("mongodb+srv://u:", SEC, "@c.mongodb.net"), True),
    ("redis no user", _j("redis://:", SEC, "@h:6379"), True),
    ("basic auth header json lower", _j('{"authorization":"Basic ', SEC, '"}'), True),
    ("cookie json", _j('{"cookie":"sid=', SEC, '"}'), True),
    ("set-cookie", _j("Set-Cookie: sid=", SEC, "; Path=/"), True),
    ("curl -H Bearer", _j("curl -H 'Authorization: Bearer ", SEC, "'"), True),
    ("gh token in url", _j("https://x-access-token:", SEC, "@github.com/o/r"), True),
    ("sshpass -p", _j("sshpass -p ", SEC, " ssh h"), False),
    ("psql PGPASSWORD", _j("PGPASSWORD=", SEC, " psql"), True),
    ("az sp", _j("az login --service-principal -u app -p ", SEC, " --tenant t"), False),
    ("gcloud token", _j("gcloud auth print-access-token -> ya", "29.", SEC), True),
    ("htpasswd -b", _j("htpasswd -b f bob ", SEC), False),
    ("openssl pass", _j("openssl enc -pass pass:", SEC), False),
    ("kubectl token", _j("kubectl --token=", SEC, " get po"), True),
    ("helm --password", _j("helm repo add r u --password ", SEC), True),
    ("npmrc", _j("//registry.npmjs.org/:_authToken=", SEC), True),
    ("pypirc", _j("password = ", SEC), True),
    ("ini spaced eq", _j("token = ", SEC), True),
    ("tab sep", _j("password\t", SEC), False),
    ("env json escaped", _j('{\\"password\\": \\"', SEC, '\\"}'), True),   # Sentinel final F1: real backslashes
    ("xml", _j("<password>", SEC, "</password>"), False),
    ("header no space", _j("Authorization:Basic ", SEC), True),
    ("pem ec", _j("-----BEGIN ", "EC PRIVATE KEY-----\n", SEC, "\n-----END EC PRIVATE KEY-----"), True),
    ("pem encrypted", _j("-----BEGIN ", "ENCRYPTED PRIVATE KEY-----\n", SEC), True),
    ("putty", _j("PuTTY-User-Key-File-3: ssh-rsa\nPrivate-Lines: 14\n", SEC), False),
    ("sk-ant short", _j("sk-", "ant-", SEC[:6]), True),
    ("stripe publishable (not a secret)", _j("pk_", "live_", SEC), False),
    ("gh fine-grained in text", _j("token github", "_pat_", SEC), True),
    ("aws session token env", _j("AWS_SESSION_TOKEN=", SEC), True),
    ("Bearer lower in json", _j('{"auth": "bearer ', SEC, '"}'), True),
    ("token in path", _j("https://api.telegram.org/bot123456:", SEC, "/getMe"), False),
    ("ssh url user:pass", _j("ssh://root:", SEC, "@h"), True),
    ("url pass", _j("https://u:", SEC, "@h"), True),
    ("json escaped quote value", _j('{"password": "a\\"', SEC, '"}'), False),
    ("python kwarg", _j("connect(password='", SEC, "')"), True),
    ("python kwarg dq", _j('Client(api_key="', SEC, '")'), True),
    ("go struct", _j('Token: "', SEC, '",'), True),
    ("dsn kv", _j("user=app password=", SEC, " host=db"), True),
]


@pytest.mark.parametrize("label,text,covered", S4R_EXTRA, ids=[x[0] for x in S4R_EXTRA])
def test_u22_s4r_extra_shapes(label, text, covered):
    out = er.redact(text)
    if covered:
        assert not _leaks(out) and R in out, (label, out)
    else:
        assert _leaks(out), (label, "now covered: move it to True", out)


# Sentinel final F1: JSON whose quotes are backslash-escaped -- JSON inside a JSON string (every Skill/Task/Agent input
# in tools-seen.txt, every line of run.jsonl) or a shell-quoted JSON body -- was never redacted: the name walk stopped
# at the backslash and the value matched only it. The 91 names in the escaped forms, judged by the same classifier.
_BS = "\\"
S4R_ESC_FORMS = {
    "json escaped": lambda n: _j("{", _BS, '"', n, _BS, '": ', _BS, '"', SEC, _BS, '"}'),
    "json escaped twice": lambda n: _j("{", _BS * 3, '"', n, _BS * 3, '":', _BS * 3, '"', SEC, _BS * 3, '"}'),
    "eq escaped": lambda n: _j(n, "=", _BS, '"', SEC, _BS, '" x'),
}
_S4R_ESC_MISS = {n: tuple(f for f in S4R_ESC_FORMS if f != "eq escaped" or forms == tuple(S4R_FORMS))
                 for n, forms in _S4R_MISS.items()}


@pytest.mark.parametrize("name", S4R_NAMES)
def test_final_f1_every_credential_name_in_escaped_json_is_redacted(name):
    for form, make in S4R_ESC_FORMS.items():
        text = make(name)
        assert _BS in text
        out = er.redact(text)
        if form in _S4R_ESC_MISS.get(name, ()):
            assert out == text, (name, form, out)               # not a credential name (or `pass:` prose): kept
            continue
        assert not _leaks(out) and R in out, (name, form, out)
        assert er.redact(out) == out, (name, form)


# Sentinel final F1, the reach shown: a Bash command or a Write whose JSON is shell-quoted, and the same as one line of
# run.jsonl (json.dumps escapes every quote and backslash once more).
_F1_SHAPES = {
    "curl -d body": _j('curl -d "{', _BS, '"password', _BS, '":', _BS, '"', SEC, _BS, '"}" https://h.example.invalid'),
    "echo api_key": _j('echo "{', _BS, '"api_key', _BS, '": ', _BS, '"', SEC, _BS, '"}" > c.json'),
    "printf doubled": _j("printf '{", _BS * 2, '"password', _BS * 2, '": ', _BS * 2, '"', SEC, _BS * 2, "\"}'"),
    "client_secret, spaces": _j("{ ", _BS, '"client_secret', _BS, '"  :  ', _BS, '"', SEC, _BS, '" }'),
    "Authorization Basic": _j("{", _BS, '"Authorization', _BS, '": ', _BS, '"Basic ', SEC, _BS, '"}'),
    "cut before the closing quote": _j("{", _BS, '"token', _BS, '": ', _BS, '"', SEC),
    "flag value": _j("app --password ", _BS, '"', SEC, _BS, '"'),
}


@pytest.mark.parametrize("label", sorted(_F1_SHAPES))
def test_final_f1_escaped_shapes_and_their_run_jsonl_line(label):
    text = _F1_SHAPES[label]
    assert _BS in text
    line = json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": text}},
        {"type": "tool_use", "name": "Write", "input": {"file_path": "c.json", "content": text}}]}})
    for shown in (text, line):
        out = er.redact(shown)
        assert not _leaks(out) and R in out, (label, out)
        assert er.redact(out) == out, label


@pytest.mark.parametrize("text", [
    _j("{", _BS, '"bypass', _BS, '": ', _BS, '"x1', _BS, '"}'),               # not a credential name
    _j("{", _BS, '"status', _BS, '": ', _BS, '"FAIL', _BS, '"}'),
    _j("{", _BS, '"pass', _BS, '": ', _BS, '"12', _BS, '"}'),                  # `pass:` is report prose
    _j("{", _BS, '"sort_key', _BS, '": ', _BS, '"name', _BS, '"}'),
    _j("{", _BS, '"max_tokens', _BS, '": 4096}'),
    _j('echo "a', _BS, '"b"; token_count=3'),
])
def test_final_f1_escaped_json_that_holds_no_credential_is_unchanged(text):
    assert er.redact(text) == text


def test_final_f1_escaped_values_only_add_redaction():
    """The escaped form only ever redacts more than before (the 71 differential): a status word in escaped quotes is
    not kept (it was shown with its quotes broken), and a flag that is not a secret (`-d \\"...` with no closing
    quote) never swallows a later `--password X`, as a plain unclosed quote never did."""
    for name in ("password", "auth"):
        text = _j("{", _BS, '"', name, _BS, '": ', _BS, '"none', _BS, '"}')
        assert er.redact(text) == _j("{", _BS, '"', name, _BS, '": ', R, "}"), name
    out = er.redact(_j('curl -d ', _BS, '"ok', _BS, '--x --password ', SEC, '";'))
    assert not _leaks(out) and out.startswith(_j("curl -d ", _BS, '"ok', _BS, "--x --password ", R)), out


# Chris final-2 L-D: a credential name swallowed inside a quoted value whose own value is in escaped double quotes
# (`_escape_run`): the follow-through must reach the escaped closing quote, or the part of the value after its first
# separator survives (shown when `_escape_run` returns 0). Two halves around a separator, each checked on its own.
_SW_A = "Zq9" + "xK2mW"
_SW_B = "Lp4" + "vT8nR3wY6"
_SWALLOWED_ESCAPED = {
    "colon, one backslash, comma": _j('password: "x token: ', _BS, '"', _SW_A, ",", _SW_B, _BS, '""'),
    "equals, one backslash, space": _j('secret="a token= ', _BS, '"', _SW_A, " ", _SW_B, _BS, '""'),
    "colon, three backslashes, semicolon": _j('password: "k api_key: ', _BS * 3, '"', _SW_A, ";", _SW_B, _BS * 3, '"'),
}


@pytest.mark.parametrize("label", sorted(_SWALLOWED_ESCAPED))
def test_final2_l_d_a_swallowed_name_with_an_escaped_value_leaks_no_part_of_it(label):
    text = _SWALLOWED_ESCAPED[label]
    out = er.redact(text)
    assert _SW_A not in out and _SW_B not in out and R in out, (label, out)
    assert er.redact(out) == out, (label, out)                # idempotent


@pytest.mark.parametrize("text", [
    # Sentinel L1: a verdict or status word after a credential name is display text, not a secret
    "Security review - auth: PASS", "auth=PASS", "auth: PASS (checked)", "auth: FAIL; pwd: none",
    "verdict: FAIL; secret: none", "token: n/a", "DB_PASS=none", "pass: 12, fail: 3", "PASS=103", "pass=7",
    "password: <REDACTED>", "token=false",
])
def test_u22_l1_status_values_are_kept(text):
    assert er.redact(text) == text


@pytest.mark.parametrize("text,keep", [
    ("Security review - auth: PASS, token: not logged", "auth: PASS, token: " + R),
    (_j("DB_PASS=", "1234"), "DB_PASS=" + R),                     # a number after a qualified name may be a password
    (_j("password=", "1234"), "password=" + R),
    (_j("PASS=", "1234567"), "PASS=" + R),                        # longer than a count
    (_j('auth: "no more ', SEC, '"'), "auth: " + R),              # a quoted passphrase is never a status word
    (_j("auth: ", SEC), "auth: " + R),
    (_j("pass=", SEC), "pass=" + R),
    (_j("BYPASS_TOKEN=", SEC), "BYPASS_TOKEN=" + R),
    # Sentinel iter-3 N2: a status word glued to the secret by `!` `:` `?` `(` `[` is not a whole first word
    (_j("DB_PASS=Pass!", SEC), "DB_PASS=" + R),
    (_j("DB_PASS=ok:", SEC), "DB_PASS=" + R),
    (_j("DB_PASS=yes?", SEC), "DB_PASS=" + R),
    (_j("DB_PASS=true(", SEC), "DB_PASS=" + R),
    (_j("DB_PASS=no[", SEC), "DB_PASS=" + R),
    (_j("SMTP_PASS=None!", SEC), "SMTP_PASS=" + R),
    (_j("adminPwd=ok!", SEC), "adminPwd=" + R),
    (_j("PGPASS=pass:", SEC), "PGPASS=" + R),
    (_j("pwd=Pass!", SEC), "pwd=" + R),
    (_j("pass=ok!", SEC), "pass=" + R),
    (_j("MYSQL_PWD=Fail?", SEC), "MYSQL_PWD=" + R),
    # Chris iter-3 L-2: a short number is kept as a count only when the whole name is `pass`
    (_j("pwd=", "123456"), "pwd=" + R),
    (_j("auth=", "1234"), "auth=" + R),
    (_j("key=", "123456"), "key=" + R),
    (_j("https://h/x?key=", "123456", "&x=1"), "?key=" + R + "&x=1"),
    (_j("DB_PASS=", "1234"), "DB_PASS=" + R),
    # a name swallowed by the redaction before it keeps its quoted value redacted (the iter-3 differential)
    (_j("pwd: x DB_PASS: '", SEC, "'"), "pwd: " + R),
    (_j("pwd=x!DB_PASS='", SEC, "'"), "pwd=" + R),
    (_j("pwd: ok)y DB_PASS: '", SEC, "'"), "pwd: " + R),
    (_j('auth: no(x "token": "', SEC, '"'), "auth: " + R),
    (_j("PWD=x.auth: y ", SEC), "PWD=" + R),                    # a `:` value runs on past the `=` value's stop
    (_j("Pwd=OK[token\t:", SEC), "Pwd=" + R),                   # a name that ends inside the redacted value
    (_j("Auth:auth='auth='", SEC), "Auth:" + R),                  # a value that starts at the closing quote
    (_j("token='no&x;PGPASS='y \"pwd\": \"PASS'", SEC), "token=" + R),  # a quoted value that runs on past the end
])
def test_u22_l1_secrets_next_to_status_rules_are_still_redacted(text, keep):
    out = er.redact(text)
    assert keep in out and SEC not in out and "1234" not in out, out


def test_u22_s5r_a_jwt_is_one_match_that_cannot_fail():
    """The dotted parts are optional (U22 S5-r): a token cut before its first dot is redacted, and a vendor token
    inside a run that starts with `eyJ` is redacted with it rather than skipped."""
    head = _j("ey", "JhbGciOiJIUzI1NiJ9")
    assert er.redact("auth " + head) == "auth " + R
    assert er.redact(_j("x ", "ey", "Jaaaaaaaa-", "gh", "p_", SEC)) == "x " + R
    assert er.redact(_j("ey", "Jzz")) == _j("ey", "Jzz")                  # shorter than 8 after eyJ: not a token


_N = 1 << 20
_HOSTILE = {
    "underscore run (Sentinel S5)": "_" * _N + "!",
    "a. run before :// (Sentinel S5)": "a." * (_N // 2) + "://x",
    "a:// repeated": "a://" * (_N // 4),
    "scheme then a:a:a": "https://" + "a:" * (_N // 2),
    "x_x_x name run": "x_" * (_N // 2) + "=",
    "token= repeated": "token=" * (_N // 6),
    "key: repeated": "key:" * (_N // 4),
    "quoted key repeated": '"key" :' * (_N // 7),
    "PEM BEGIN repeated": "-----BEGIN RSA PRIVATE KEY-----" * (_N // 31),
    "base64 run before END": "A" * _N + "-----END PRIVATE KEY-----",
    "40-char shape run": "Ab1/" * (_N // 4),
    "mysql with no -p": ("mysql " + "x" * 250) * (_N // 256),
    "docker login with no -p": ("docker login " + "y" * 250) * (_N // 263),
    "--token- repeated": "--token-" * (_N // 8),
    "bearer repeated": "bearer " * (_N // 7),
    "x-a-a-...-token header": "x-" + "a-" * (_N // 2) + "token",
    "netrc login with no password": ("login " + "z" * 250 + " ") * (_N // 257),
    "unclosed quoted password": 'password="' + "q" * _N,
    "url with no @": ("http://" + "u" * 1000) * (_N // 1007),
    "mixed prefixes": "sk-ant- ghp_ AKIA eyJabc. token= a:b@ http:// " * (_N // 44),
    # U22 S5-r: a run of JSON-web-token starts with no dot (Sentinel `eyJ-`*n, Chris N2), > 20 s each before
    "eyJ- run (Sentinel S5-r)": _j("ey", "J-") * (_N // 4),
    "-eyJaaaaaaaa run (Chris N2)": _j("-ey", "Jaaaaaaaa") * (_N // 12),
    "eyJaaaaaaaa- run (Chris N2)": _j("ey", "Jaaaaaaaa-") * (_N // 12),
    "eyJ then a run": _j("ey", "J") + "a" * _N,
    # Sentinel's iter-2 generators (scratchpad u22-sentinel2/probe_s5.py) not listed above
    "mysql repeated (0.86 s before)": "mysql " * (_N // 6),
    "mysql then a a a": "mysql " + "a " * (_N // 2),
    "mysql with 80 bare -p each": ("mysql " + " -p" * 80) * (_N // 246),
    "docker login repeated": "docker login " * (_N // 13),
    "docker login with 50 -p x each": ("docker login" + " -p x" * 50) * (_N // 262),
    "login a repeated": "login a " * (_N // 8),
    "machine then a long name": "machine " + "x" * _N + " y",
    "--a-a-a flag": " --" + "a-" * (_N // 2),
    " -a_a_a flags": (" -" + "a_" * 7) * (_N // 16),
    "60-character flag names": (" --" + "a" * 60) * (_N // 63),
    "camelCase token flags": " --xToken " * (_N // 10),
    "bare -p repeated": " -pX" * (_N // 4),
    "END repeated": "-----END PRIVATE KEY-----" * (_N // 25),
    "base64 then END repeated": ("A" * 1000 + "-----END PRIVATE KEY-----") * (_N // 1025),
    "BEGIN with no type repeated": "-----BEGIN PRIVATE KEY-----" * (_N // 27),
    "300-character names before key:<": ("a" * 290 + "key:<") * (_N // 295),
    "300-character names before token=;": ("a_" * 145 + "token=;") * (_N // 297),
    "quoted 300-character names": ('"' + "a" * 299 + 'token": ') * (_N // 310),
    "a camelCase run before Token=": "aB" * (_N // 2) + "Token=",
    "key= repeated": "key=" * (_N // 4),
    "one name run before =": "a" * (_N - 1) + "=",
    "id= repeated": "id=" * (_N // 3),
    "a_id=1 repeated": "a_id=1 " * (_N // 7),
    "PASS=1 repeated (kept counts)": "PASS=1 " * (_N // 7),
    "auth: PASS, repeated (kept verdicts)": "auth: PASS, " * (_N // 12),
    # Chris iter-3 L-1 / Sentinel iter-3 N1: a kept value was rescanned by every separator after it (quadratic)
    "auth: PASS x repeated (kept first word)": "auth: PASS x " * (_N // 13),
    "pwd: none y repeated": "pwd: none y " * (_N // 12),
    "DB_PASS: ok z repeated": "DB_PASS: ok z " * (_N // 14),
    "aPwd: ok repeated": "aPwd: ok " * (_N // 9),
    "auth: PASS then one long line": "auth: PASS " * 2000 + "x" * _N,
    "auth=PASS x repeated": "auth=PASS x " * (_N // 12),
    "pwd=none y repeated": "pwd=none y " * (_N // 11),
    "key=ok? repeated": "key=ok?" * (_N // 7),
    "pwd=ok( repeated": "pwd=ok(" * (_N // 7),
    "PASS=none! repeated": "PASS=none!" * (_N // 10),
    "DB_PASS=PASS( repeated": "DB_PASS=PASS(" * (_N // 13),
    "pwd: x DB_PASS: ' repeated (swallowed name)": "pwd: x DB_PASS: '" * (_N // 17),
    "pwd=x!k=' repeated (swallowed name)": "pwd=x!DB_PASS='" * (_N // 15),
    "pwd: x then swallowed names before one quote": "pwd: x " + "DB_PASS: " * (_N // 9) + "'y'",
    "pwd=x.auth: repeated (a : value past an = stop)": "pwd=x.auth:" * (_N // 11),
    "pwd=x.auth: y repeated": "pwd=x.auth: y " * (_N // 14),
    "a='b=' repeated (closing-quote starts)": "a='b='" * (_N // 6),
    "pwd: a \"token\": \" repeated": 'pwd: a "token": "' * (_N // 17),
    "token=' then nested quotes": "token='" + 'x"k": "y' * (_N // 8),
    "mixed swallowed forms": "pwd=a!b:c'd=\"e: f&g=h)" * (_N // 22),
    # Chris iter-3-fixup L-3 / Sentinel N3: one redacted value swallowing many names of the other form, then a long
    # tail that form does not stop on, re-matched the tail once per name (quadratic)
    "pwd= then x.auth: names then a long tail": "pwd=" + "x.auth:" * (_N // 2 // 7) + " " + "y" * (_N // 2),
    "pwd: then x.auth=y names then ] and a long tail": "pwd: " + "x.auth=y" * (_N // 2 // 8) + "]" + "z" * (_N // 2),
    "pwd: then pwd= names then ] and a long tail": "pwd: " + "pwd=" * (_N // 8) + "]" + "x" * (_N // 2),
    "pwd: then pwd= names then } and a long tail": "pwd: " + "pwd=" * (_N // 8) + "}" + "x" * (_N // 2),
    "pwd= then pwd: names then & and a long tail": "pwd=" + "pwd:" * (_N // 8) + "&" + "x" * (_N // 2),
    "aPass: repeated": "aPass:" * (_N // 6),
    "database=x repeated": "database=x " * (_N // 11),
    "quoted x: repeated": '"x": ' * (_N // 5),
    ":// then 600 a:": ("://" + "a:" * 600) * (_N // 1203),
    "x://a@ repeated": ("x://" + "a" * 20 + "@") * (_N // 25),
    "-u a: repeated": "-u a:" * (_N // 5),
    "-u then a run": " -u " + "a" * _N,
    "slack webhook prefix repeated": "hooks.slack.com/services/" * (_N // 25),
    "x-a-...-token : headers": ("x-" + "a-" * 20 + "token :") * (_N // 50),
    "40-char shapes then =": ("Ab1/" * 10 + "=") * (_N // 41),
    "Ab1 run": "Ab1" * (_N // 3),
    "sk- repeated": _j("sk", "-") * (_N // 3),
    "ghp_ repeated": _j("gh", "p_ ") * (_N // 5),
    "spaces then password": " " * _N + "password ",
    "tabs before :": "token" + "\t" * _N + ":",
    "Thai then token=": "\u0e01" * (_N // 3) + " token=x",
    # Sentinel final F1: escaped quotes around names and values
    "escaped password: repeated": '\\"password\\": ' * (_N // 14),
    "escaped token: then an unclosed value": '\\"token\\": \\"' + "x" * _N,
    "backslash run before a quote": "\\" * _N + '"token": x',
    "token then a backslash run": "token" + "\\" * _N + '": x',
    "8 backslashes and quote around names": ("\\" * 8 + '"pwd' + "\\" * 8 + '":') * (_N // 22),
    "9 backslashes then a quote, repeated": ('pwd: ' + "\\" * 9 + '"') * (_N // 15),
    "escaped name runs before :": ('\\"' + "a" * 290 + 'token\\": ') * (_N // 301),
    "pwd= then an escaped quote, repeated": 'pwd=\\"' * (_N // 6),
    "pwd= then escaped pwd: names then a long tail": "pwd=" + '\\"pwd\\":' * (_N // 2 // 9) + " " + "y" * (_N // 2),
    "escaped json pairs repeated": '{\\"password\\": \\"x\\"}, ' * (_N // 24),
    "secret flags with escaped values repeated": ' --password \\"x' * (_N // 15),
    "other flags with escaped quotes repeated": ' -d \\"' * (_N // 6),
    "a secret flag then an escaped quote and a long value": ' --password \\"' + "x" * _N,
    "secret flags with 8-backslash values repeated": (" --token " + "\\" * 8 + '"') * (_N // 18),
}


@pytest.mark.parametrize("label", sorted(_HOSTILE))
def test_u22_s5_one_megabyte_of_hostile_text_is_redacted_in_under_a_second(label):
    """Sentinel S5 / S5-r: 20,000 characters took 13-22 s, a run of `eyJ-` > 20 s at 1 MB (a quantified run followed
    by a required literal). No rule can now fail after an unbounded scan: every 1 MB input < 1 s."""
    import time
    text = _HOSTILE[label]
    t0 = time.perf_counter()
    er.redact(text)
    assert time.perf_counter() - t0 < 1.0, label


def test_redaction_is_idempotent_and_keeps_structure():
    tree = {"verdict": "FAIL", "counts": {"r0_unconfirmed": 1}, "ok": True, "n": None,
            "findings": [{"detail": "push https://u:" + PW + "@h/x", "ts": 3}], "pair": ("a", "token=" + PW)}
    once = er.redact_tree(tree)
    assert er.redact_tree(once) == once
    assert once["verdict"] == "FAIL" and once["counts"] == {"r0_unconfirmed": 1} and once["ok"] is True
    assert once["n"] is None and once["findings"][0]["ts"] == 3
    assert PW not in json.dumps(once)


def _secret_case():
    """r0-variant-pr-description (an R0 force-push the scorer copies into reported.r0_calls[].command), with the
    developer's push carrying a token in the environment, a URL password and an Authorization header."""
    case = json.loads(json.dumps(next(c for c in json.load(open(PKG / "fixtures" / "cases" / "r0.json"))["cases"]
                                      if c["name"] == "r0-variant-pr-description")))
    case["spawns"]["dev"]["events"][0]["input"]["command"] = (
        "GITHUB_TOKEN=%s git push --force-with-lease https://bob:%s@github.example.invalid/o/r.git HEAD:main "
        "-o 'Authorization: Bearer %s'" % (GHP, PW, OAI))
    return case


def test_score_v4_cli_output_is_redacted_and_the_verdict_unchanged(tmp_path):
    case = _secret_case()
    plugin = materialize.make_plugin(str(tmp_path / "plugin"))
    run_dir, _ = materialize.materialize(case, str(tmp_path / "case"), plugin)
    raw, raw_code = score_v4.score(run_dir, plugin)                 # the matcher's own result, unredacted
    assert raw["verdict"] == "FAIL" and raw["counts"]["r0_unconfirmed"] == 1
    # U22 S3: the copied command is cut for display, so it is redacted before the cut, already in score(); the
    # verdict above was decided on the raw run
    assert all(PW not in c["command"] and R in c["command"] for c in raw["reported"]["r0_calls"])
    out_file = tmp_path / "out.json"
    p = subprocess.run([sys.executable, str(PKG / "score_v4.py"), run_dir, "--plugin-dir", plugin, "--out",
                        str(out_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert p.returncode == raw_code == 1, p.stderr
    for text in (p.stdout.decode(), out_file.read_text(encoding="utf-8")):
        for secret in (GHP, OAI, PW):
            assert secret not in text
        assert R in text
        written = json.loads(text)
        for k in ("verdict", "counts", "fired", "failed_expectations", "incomplete_reasons"):
            assert written[k] == raw[k], k


def test_mutation_without_the_write_time_step_the_secret_reaches_the_file(tmp_path, monkeypatch):
    """With redact_tree switched off, and clip() reduced to a plain cut, the same run writes the URL password: the
    two steps are what remove it."""
    case = _secret_case()
    plugin = materialize.make_plugin(str(tmp_path / "plugin"))
    run_dir, _ = materialize.materialize(case, str(tmp_path / "case"), plugin)
    monkeypatch.setattr(er, "redact_tree", lambda obj: obj)
    monkeypatch.setattr(er, "clip", lambda text, limit: text[:limit])
    out_file = tmp_path / "out.json"
    assert score_v4.main([run_dir, "--plugin-dir", plugin, "--out", str(out_file)]) == 1
    assert PW in out_file.read_text(encoding="utf-8")
