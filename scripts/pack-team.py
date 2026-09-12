#!/usr/bin/env python3
"""Build a full-team test candidate; maintainer-only, never a runtime dependency.

Does not publish, install, edit source, or certify host compatibility. Existing
artifacts are never overwritten. Stable publication requires separate qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUCKETS = ("workflow", "ops", "ui", "style", "discipline")


def payload(root=ROOT):
    root = root.resolve()
    manifest = json.loads((root / ".claude-plugin/plugin.json").read_text())
    if manifest["name"] != "shode-house":
        raise ValueError("unexpected plugin identity")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", manifest["version"]):
        raise ValueError("invalid version")
    entries = {}
    roots = [root / "agents", root / "references", root / "output-styles"]
    roots += [root / "skills" / bucket for bucket in BUCKETS]
    for folder in roots:
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError(f"invalid source directory: {folder}")
        for path in sorted(folder.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"symlink not allowed in candidate: {path}")
            if not path.is_file() or "__pycache__" in path.parts or path.name == ".DS_Store":
                continue
            if not path.resolve().is_relative_to(root):
                raise ValueError("source escapes repository")
            entries[path.relative_to(root).as_posix()] = path.read_bytes()
    for name in ("commands/ask.md", "LICENSE"):
        path = root / name
        if path.is_symlink():
            raise ValueError(f"symlink not allowed: {name}")
        entries[name] = path.read_bytes()
    roles = [p for p in entries if p.startswith("agents/") and p.endswith(".md")]
    skills = [p for p in entries if p.endswith("/SKILL.md")]
    if len(roles) != 19 or len(skills) < 24:
        raise ValueError("candidate must preserve 19 roles, original 23 skills and ask")
    # Preserve authored relative layout under one knowledge root. Native discovery
    # requires flat skills/<name>/SKILL.md, unlike Claude's historical buckets.
    # Wrappers dispatch to full source instructions, never persona summaries.
    source_entries = entries
    entries = {"knowledge/" + name: body for name, body in source_entries.items()}
    for name in [*roles, *skills]:
        text = source_entries[name].decode("utf-8")
        parts = text.split("---", 2)
        if len(parts) != 3 or parts[0]:
            raise ValueError(f"missing frontmatter: {name}")
        if name in roles:
            target = name
            relative = "../knowledge/" + name
        else:
            target = "skills/" + Path(name).parent.name + "/SKILL.md"
            relative = "../../knowledge/" + name
        if target in entries:
            raise ValueError(f"duplicate discovery path: {target}")
        wrapper = ("---" + parts[1] + "---\n\n"
                   f"Read [{Path(name).parent.name if name in skills else Path(name).stem}]({relative}) "
                   "in full before carrying out the task, including its declared prerequisite skills.\n"
                   "This is a discovery adapter, not a replacement for the role or skill knowledge.\n"
                   "Resolve source-root paths beginning agents/, skills/, references/ or output-styles/ "
                   "under this plugin's knowledge/ directory, not the user's project.\n"
                   "Use actual host tools and preserve host/project/user authority.\n")
        entries[target] = wrapper.encode()
    entries["commands/ask.md"] = (
        '---\ndescription: "Work with Oliver and the full Shode House team."\n---\n\n'
        'User request: $ARGUMENTS\n\n'
        'Read `${CLAUDE_PLUGIN_ROOT}/skills/ask/SKILL.md` and its full referenced source. '
        'Oliver is the main session; delegate specialist work, never spawn Oliver.\n'
    ).encode()
    entries["LICENSE"] = source_entries["LICENSE"]
    # No hooks directory, root runner scripts or auto-start MCP is copied. The
    # knowledge/reference tree remains intact, including optional project examples.
    manifest = {key: manifest[key] for key in
                ("name", "version", "author", "homepage", "repository", "license")}
    description = "Shode House: full expert team, scoped delivery, independent verification and resumable work."
    manifest.update(description=description,
                    skills="./skills/",
                    commands=["./commands/ask.md"])
    entries[".claude-plugin/plugin.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    codex = {key: manifest[key] for key in
             ("name", "version", "description", "author", "homepage", "repository", "license")}
    codex.update(skills="./skills/", interface={
        "displayName": "Shode House",
        "shortDescription": "Oliver and the full software-house expert team",
        "longDescription": description,
        "developerName": "shode666",
        "category": "Developer Tools",
        "capabilities": ["Interactive", "Write"],
        "websiteURL": manifest["homepage"],
        "defaultPrompt": ["Work with Oliver and the team on this project."],
    })
    entries[".codex-plugin/plugin.json"] = (json.dumps(codex, indent=2) + "\n").encode()
    return manifest["version"], entries


def build(destination, root=ROOT):
    version, entries = payload(root)
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / f"shode-house-v{version}-team-candidate.plugin"
    # Exclusive creation fails safely rather than overwriting an earlier candidate.
    with output.open("xb") as stream:
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in sorted(entries.items()):
                item = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                item.compress_type = zipfile.ZIP_DEFLATED
                item.external_attr = 0o100644 << 16
                archive.writestr(item, content)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(entries):
            raise ValueError("archive integrity check failed")
    return {"path": str(output), "entries": len(entries),
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "qualification": "NOT VERIFIED: host discovery, execution and release acceptance"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    destination = args.out or Path(tempfile.mkdtemp(prefix="shode-team-candidate-"))
    print(json.dumps(build(destination.resolve()), indent=2))
