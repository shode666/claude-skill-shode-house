"""Explicit source-policy migrations for lexical conservation, not semantic proof.

Every exception matches one exact old fragment and requires all replacement anchors.
Changing this manifest requires review; it never authorizes deleting unrelated rules.
"""
import json
from pathlib import Path


def load(root):
    root = Path(root).resolve()
    result = {}
    for item in json.loads((root / ".rule-migrations.json").read_text())["migrations"]:
        key = (item["source"], item["old_fragment"])
        if key in result or not item.get("reason") or not item.get("requires"):
            raise ValueError("invalid or duplicate rule migration")
        if not all(isinstance(anchor, str) and anchor.strip() for anchor in item["requires"]):
            raise ValueError("empty replacement anchor")
        target = (root / item["replacement"]).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError("missing or escaped rule migration target")
        text = " ".join(target.read_text().split())
        if not all(" ".join(anchor.split()) in text for anchor in item["requires"]):
            raise ValueError("replacement invariant missing: " + item["old_fragment"])
        result[key] = item
    return result
