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


def archives(root=ROOT):
    config, data = payload(root)
    portable = {f"ask/{name}": value for name, value in data.items()}
    claude = {f"skills/ask/{name}": value for name, value in data.items()}
    manifest = {key: config[key] for key in ("name", "version", "description")}
    claude[".claude-plugin/plugin.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    return config, {"portable.zip": portable, "claude.plugin": claude}


def build(destination, root=ROOT):
    config, bundles = archives(root)
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
    args = parser.parse_args()
    if args.check:
        config, data = payload()
        print(f"PASS {config['version']}: one ask entrypoint, {len(data)} instruction files")
    else:
        destination = args.out or Path(tempfile.mkdtemp(prefix="shode-release-"))
        print(json.dumps(build(destination.resolve()), indent=2))
