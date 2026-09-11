#!/usr/bin/env python3
"""Maintainer-only packaging. No scripts are included in runtime distributions."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message="invalid release payload"):
    if not condition:
        raise ValueError(message)


def payload(root=ROOT):
    config = json.loads((root / "release/3.16.json").read_text())
    source = root / config["source"]
    require(source.resolve().is_relative_to(root.resolve()), "source escapes repository")
    require(re.fullmatch(r"\d+\.\d+\.\d+(?:-rc\.\d+)?", config["version"]))
    require(config["name"] == "shode-house")
    require(config.get("release_host") == "codex", "3.16 release scope is Codex only")
    files = config["files"]
    require(len(files) == len(set(files)), "duplicate source files")
    actual = {p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file()}
    require(actual == set(files), "unexpected or missing source file")
    data = {}
    for name in files:
        path = source / name
        require(not path.is_symlink() and path.resolve().is_relative_to(source.resolve()))
        require(not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts)
        require(name.endswith(".md"), "runtime must be instruction-only")
        content = path.read_bytes()
        text = content.decode("utf-8")
        require(text.endswith("\n") and not re.search(r"[ \t]+$", text, re.M))
        for link in re.findall(r"\]\(([^)]+)\)", text):
            target = (path.parent / link).resolve()
            require(target.is_relative_to(source.resolve()) and target.is_file(), f"bad link: {link}")
        data[name] = content
    require(data["SKILL.md"].startswith(b"---\nname: ask\ndescription: "))
    require(len(list(source.rglob("SKILL.md"))) == 1, "multiple entrypoints")
    return config, data


def archives(root=ROOT, include_experimental=False):
    config, data = payload(root)
    portable = {f"ask/{name}": value for name, value in data.items()}
    hosts = root / "release/hosts"
    expected = {"codex/openai.yaml", "claude/plugin.json"}
    require({p.relative_to(hosts).as_posix() for p in hosts.rglob("*") if p.is_file()} == expected,
            "unexpected or missing host configuration")
    for name in expected:
        path = hosts / name
        require(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()),
                "host configuration escapes repository")
    metadata = (hosts / "codex/openai.yaml").read_bytes()
    # Intentionally accept only this small UI-only YAML subset. No extra dependency,
    # execution settings, implicit-invocation override or host tool declarations.
    match = re.fullmatch(
        r'interface:\n  display_name: ("[^\n]+")\n'
        r'  short_description: ("[^\n]+")\n'
        r'  default_prompt: ("[^\n]+")\n', metadata.decode("utf-8"))
    require(match is not None, "invalid Codex UI-only metadata")
    display, description, prompt = (json.loads(value) for value in match.groups())
    require(display and 25 <= len(description) <= 64 and "$ask" in prompt,
            "invalid Codex skill interface")
    portable["ask/agents/openai.yaml"] = metadata
    manifest = json.loads((hosts / "claude/plugin.json").read_text())
    require(manifest == {"name": config["name"]}, "invalid Claude manifest template")
    # Version and description have a single authority, not copied host values.
    manifest.update({key: config[key] for key in ("version", "description")})
    if not include_experimental:
        return config, {"portable.zip": portable}
    claude = {f"skills/ask/{name}": value for name, value in data.items()}
    claude[".claude-plugin/plugin.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    return config, {"portable.zip": portable, "claude.plugin": claude}


def build(destination, root=ROOT, include_experimental=False):
    config, bundles = archives(root, include_experimental)
    destination.mkdir(parents=True, exist_ok=True)
    results = []
    for suffix, entries in bundles.items():
        output = destination / f"shode-house-v{config['version']}-{suffix}"
        # Never overwrite a previous artifact; validation must not destroy user files.
        with output.open("xb") as stream:
            with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, content in sorted(entries.items()):
                    info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, content)
        with zipfile.ZipFile(output) as archive:
            require(archive.testzip() is None, "corrupt archive")
            require(set(archive.namelist()) == set(entries), "archive entries mismatch")
        results.append({"path": str(output), "entries": len(entries),
                        "sha256": hashlib.sha256(output.read_bytes()).hexdigest()})
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out", type=Path, help="new output directory; existing artifacts are not overwritten")
    parser.add_argument("--include-experimental", action="store_true",
                        help="also build the unverified Claude-format archive; not stable support")
    args = parser.parse_args()
    if args.check:
        config, bundles = archives(include_experimental=True)
        print(f"PASS {config['version']}: one ask entrypoint, 6 instruction files, both host configs")
    else:
        destination = args.out or Path(tempfile.mkdtemp(prefix="shode-release-"))
        print(json.dumps(build(destination.resolve(), include_experimental=args.include_experimental), indent=2))
