# shode-house dev-loop — NO Python. Tools: bash, jq, zip, gh (publish only).
# Usage: make pack | make stats | make skills   (invariant + lint gate runs in CI)
.RECIPEPREFIX = >
.PHONY: help pack build stats skills clean

VERSION := $(shell jq -r .version .claude-plugin/plugin.json)
PLUGIN  := shode-house-v$(VERSION).plugin

help:
> @echo "shode-house dev-loop (no Python):"
> @echo "  make pack       build $(PLUGIN) artifact (zip)"
> @echo "  make stats      skill/agent/command counts"
> @echo "  make skills     list shipped skills by bucket"
> @echo "  (invariant + lint gate runs in CI: .github/workflows/ci.yml)"

# pack = no-Python equivalent of the old build_plugin.py (same include/exclude set)
pack build:
> @rm -f $(PLUGIN)
> @zip -rq $(PLUGIN) \
>   .claude-plugin agents commands \
>   skills/workflow skills/ops skills/ui skills/style skills/discipline \
>   output-styles \
>   references docs \
>   README.md CHANGELOG.md CLAUDE.md .pre-commit-config.yaml \
>   -x '*.DS_Store' -x '*__pycache__*' -x '*/.git/*' -x '*.fuse_hidden*'
> @echo "built $(PLUGIN) ($$(du -k $(PLUGIN) | cut -f1)K, $$(unzip -l $(PLUGIN) | tail -1 | awk '{print $$2}') files)"

stats:
> @printf 'agents:   %s\n' "$$(ls agents/*.md | wc -l | tr -d ' ')"
> @printf 'skills:   %s (shipped buckets)\n' "$$(find skills/workflow skills/ops skills/ui skills/style skills/discipline -name SKILL.md | wc -l | tr -d ' ')"
> @printf 'commands: %s\n' "$$(ls commands/*.md | wc -l | tr -d ' ')"

skills:
> @for b in workflow ops ui style discipline; do echo "[$$b]"; for d in skills/$$b/*/; do echo "  - $$(basename $$d)"; done; done

clean:
> @rm -f shode-house-v*.plugin.tmp
