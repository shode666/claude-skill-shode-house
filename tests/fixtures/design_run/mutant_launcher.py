"""Run design_run.main() with one check switched off, in a real `python3 -I` process.

Used only by mutation tests that need a separate process (for example to SIGKILL the runner).
Usage: python3 -I mutant_launcher.py <path to design_run.py> <mutation> --order <p> --sha256 <h>
"""
import importlib.util
import os
import sys


def main():
    runner_path, mutation, rest = sys.argv[1], sys.argv[2], sys.argv[3:]
    spec = importlib.util.spec_from_file_location("design_run_mutant", runner_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if mutation == "stage-bypass":
        # children write straight into outputs/<task>/design-run/<stem>/ instead of the private dir
        mod._stage_dir = lambda private, run_dir, run_id: run_dir
    elif mutation == "no-signal-handlers":
        # SIGTERM/SIGHUP keep their default action: the runner dies without its `finally` blocks
        mod._install_signal_handlers = lambda ctx: {}
    else:
        raise SystemExit("unknown mutation " + mutation)
    os.environ.setdefault("PATH", "/usr/bin:/bin")
    sys.exit(mod.main(rest))


if __name__ == "__main__":
    main()
