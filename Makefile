# shode-house dev-loop. Tools: bash, jq, zip (pack/stats/skills) + python3 (เฉพาะ design-intel smoke ใน gate #17)
# gh = publish only
# Usage: make validate | make pack | make stats | make skills
# NOTE: ใช้ TAB เป็น recipe prefix (v3.12) — `.RECIPEPREFIX` ต้องการ GNU Make >= 3.82
#       แต่ macOS ยังมาพร้อม 3.81 -> `make pack` เดิมพังบนเครื่อง maintainer ("missing separator")
.PHONY: help validate pack build stats skills clean

VERSION := $(shell jq -r .version .claude-plugin/plugin.json)
PLUGIN  := shode-house-v$(VERSION).plugin

help:
	@echo "shode-house dev-loop:"
	@echo "  make validate   run the same invariant + lint gate as CI (bash + jq)"
	@echo "  make pack       build $(PLUGIN) artifact (zip)"
	@echo "  make stats      skill/agent/command counts"
	@echo "  make skills     list shipped skills by bucket"
	@echo "  make clean      remove the built .plugin artifact"

# validate = รัน gate ชุดเดียวกับ CI ในเครื่อง (v3.12 — เดิม .pre-commit-config อ้าง target นี้ทั้งที่ไม่มีอยู่)
# แหล่งความจริงเดียวคือ .github/workflows/ci.yml -> ดึง inline script ออกมารัน ไม่ copy logic ซ้ำ
validate:
	@g=$$(mktemp -t shode-gate.XXXXXX) && \
	 awk '/^        run: \|/{f=1;next} f&&/^      - name:/{exit} f{sub(/^          /,"");print}' \
	   .github/workflows/ci.yml > "$$g" && \
	 test -s "$$g" || { echo "make validate: extract gate script failed (ci.yml layout changed)"; rm -f "$$g"; exit 1; }; \
	 bash "$$g"; rc=$$?; rm -f "$$g"; exit $$rc

# zip เขียน temp archive ไว้ใน cwd เมื่อถูกขัดจังหวะ -> ให้มันไปอยู่ใน temp dir ของตัวเองแทน
# แล้วย้ายเข้ามาเมื่อสำเร็จ (v3.12: เดิม `make clean` ใช้ glob `zi*` ซึ่งลบไฟล์ผู้ใช้ที่ขึ้นต้น zi ได้ เช่น zig/zip-config)
pack build:
	@rm -f $(PLUGIN)
	@d=$$(mktemp -d -t shode-pack.XXXXXX) && \
	 (cd . && zip -rq "$$d/$(PLUGIN)" \
	  .claude-plugin agents commands \
	  skills/workflow skills/ops skills/ui skills/style skills/discipline \
	  output-styles \
	  references docs \
	  README.md CHANGELOG.md CLAUDE.md .pre-commit-config.yaml \
	  -x '*.DS_Store' -x '*__pycache__*' -x '*/.git/*' -x '*.fuse_hidden*') && \
	 mv "$$d/$(PLUGIN)" ./ ; rc=$$?; rm -rf "$$d"; exit $$rc
	@echo "built $(PLUGIN) ($$(du -k $(PLUGIN) | cut -f1)K, $$(unzip -l $(PLUGIN) | tail -1 | awk '{print $$2}') files)"

stats:
	@printf 'agents:   %s\n' "$$(ls agents/*.md | wc -l | tr -d ' ')"
	@printf 'skills:   %s (shipped buckets)\n' "$$(find skills/workflow skills/ops skills/ui skills/style skills/discipline -name SKILL.md | wc -l | tr -d ' ')"
	@printf 'commands: %s\n' "$$(ls commands/*.md | wc -l | tr -d ' ')"

skills:
	@for b in workflow ops ui style discipline; do echo "[$$b]"; for d in skills/$$b/*/; do echo "  - $$(basename $$d)"; done; done

# zip ทิ้ง temp archive (ziXXXXXX) ไว้เมื่อถูกขัดจังหวะ — .gitignore ซ่อนมันไว้จนไม่มีใครเห็น
# ลบเฉพาะ artifact ที่ target นี้สร้างเองเท่านั้น — ห้ามใช้ glob กว้าง (v3.12: `zi[A-Za-z0-9]*` เดิม
# ลบไฟล์ผู้ใช้ที่ขึ้นต้นด้วย zi ได้ทั้งหมด; ตอนนี้ temp archive ไปอยู่ใน mktemp -d แล้วจึงไม่ต้องกวาด cwd)
clean:
	@rm -f shode-house-v*.plugin shode-house-v*.plugin.tmp
	@echo "cleaned"
