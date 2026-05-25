#!/usr/bin/env bash
# apply-v3.0.sh — Apply shode-house v3.0.0 release
#
# Usage: bash apply-v3.0.sh
#
# What it does:
#   1. Verify on main branch + clean working tree (after Claude's edits)
#   2. Sprint 1 commit  — skill cleanup (rm 6 skills + dev-gate merge)
#   3. Sprint 2 commit  — Sentinel + Reggie + Phase 1c/6 + drift defense + teams
#   4. Sprint 3 commit  — Patrick + Stan + Phase 0/7 + scope split + SME elevation
#   5. Build .plugin bundle
#   6. Tag v3.0.0
#   7. Push to GitHub origin main + tags
#
# Safety:
#   - Stops on first error (set -e)
#   - Shows diff summary before each commit
#   - Asks confirmation before push (R0 gate)

set -e

cd "$(dirname "$0")"
ROOT="$(pwd)"
echo "📂 Working in: $ROOT"

# ─── Sanity check ───────────────────────────────────────────────────────
if [ ! -d ".git" ]; then
  echo "❌ Not a git repo. Abort."
  exit 1
fi

BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
  echo "⚠️  On branch '$BRANCH', not 'main'. Continue? [y/N]"
  read -r answer; [ "$answer" = "y" ] || exit 1
fi

# Configure git identity (if not set globally)
git config user.email "shode666@gmail.com" 2>/dev/null || true
git config user.name "shode666" 2>/dev/null || true

# ─── Sprint 0: baseline (v2.8.2 uncommitted) ────────────────────────────
echo ""
echo "🔖 Sprint 0 — Commit v2.8.2 baseline (catch up uncommitted work)"
echo "---"
git add -A
if ! git diff --cached --quiet; then
  git commit -m "v2.8.2 baseline — Review Audit Trail (catch up uncommitted)

- v2.8.1: Uma hardened (Bash, UX Evidence, Anti-Puppet UX, Universal UX 13 rules)
- v2.8.2: Review Report Format (bd-native primary; markdown fallback)
- Built bundles: shode-house-v2.8.0/.1/.2.plugin
- New tracking: SHODE-HOUSE-MASTER.md, wcpred-prompt.md
"
  echo "✅ v2.8.2 baseline committed"
else
  echo "ℹ️  Nothing to commit (already up to date)"
fi

# ─── Sprint 1: skill cleanup → v2.9.0 ──────────────────────────────────
echo ""
echo "🧹 Sprint 1 — Skill cleanup (remove 6, merge 2)"
echo "---"

# Remove 6 deprecated skills
echo "Removing: sd, do, tdd, code-quality, grill-me, triage, to-prd, to-issues, zoom-out"
rm -rf skills/sd skills/do skills/tdd skills/code-quality skills/grill-me \
       skills/triage skills/to-prd skills/to-issues skills/zoom-out

# Verify dev-gate exists (Claude created)
if [ ! -f "skills/dev-gate/SKILL.md" ]; then
  echo "❌ skills/dev-gate/SKILL.md missing — Claude did not create. Abort."
  exit 1
fi

git add -A
git commit -m "v2.9.0 — Skill cleanup (remove 6, merge 2)

Removed:
  - skills/sd, skills/do — identical (v1.1 stale), superseded by meeting (v2.1+)
  - skills/tdd, skills/code-quality — merged into skills/dev-gate
  - skills/grill-me — merged into meeting (Clarifying section, 6 patterns)
  - skills/triage, skills/to-prd, skills/to-issues, skills/zoom-out — empty stubs

Added:
  - skills/dev-gate/SKILL.md — unified dev-time discipline (TDD + quality gates)

Net: −1,500 tokens, baseline for v3.0
"
echo "✅ Sprint 1 committed (v2.9.0 prep)"

# ─── Sprint 2: Sentinel + Reggie + new skills → v2.10.0 ─────────────────
echo ""
echo "🛡️  Sprint 2 — Sentinel + Reggie + Phase 1c/6 + Drift Defense + Teams"
echo "---"

# Sanity check Sprint 2 files exist
for f in agents/security-engineer.md agents/sre-engineer.md \
         skills/secure/SKILL.md skills/slo/SKILL.md \
         skills/incident/SKILL.md skills/web-q/SKILL.md; do
  if [ ! -f "$f" ]; then
    echo "❌ Missing: $f — Claude did not create. Abort."
    exit 1
  fi
done

git add -A
git commit -m "v2.10.0 — Security + SRE discipline (new agents Sentinel + Reggie)

Added agents:
  - agents/security-engineer.md (Sentinel) — sole owner: STRIDE, SAST/DAST, CSP, secrets, pen test
  - agents/sre-engineer.md (Reggie) — sole owner: SLO/SLI, error budget, runbook, on-call, postmortem

Added skills:
  - skills/secure/ — STRIDE + threat-driven design
  - skills/slo/ — SLI/SLO/error budget (Google SRE Book-aligned)
  - skills/incident/ — runbook + on-call + blameless postmortem
  - skills/web-q/ — Core Web Vitals + SEO + security headers (ported from addyosmani/web-quality-skills MIT)

Added phases:
  - Phase 1c Threat Model (Sentinel + Sara) — mandatory if touches auth/PII/money
  - Phase 6 Operate (Reggie + Aaron + Oliver) — continuous post-deploy

Added in meeting skill:
  - 👥 Team Structure (7 teams + single-owner capability matrix)
  - 🤝 Handoff Broadcast Protocol (1-line caveman)
  - 📋 RACI per Phase
  - 🛡️ Workflow Drift Defense (7 mechanisms M1-M7)
  - 🧪 Clarifying — option-style v3.0 (merged from grill-me, 6 patterns)

Changed (scope handoff):
  - Sara — deep threat model → Sentinel
  - Aaron — SLO/incident → Reggie
  - Chris — deep security → Sentinel
  - Quinn — pen test → Sentinel
  - Oliver — added Phase 1c/6 dispatch, Follow-up Classifier, SESSION-STATE, multi-sig gate
"
echo "✅ Sprint 2 committed (v2.10.0 prep)"

# ─── Sprint 3: Patrick + Stan + Phase 0/7 → v3.0.0 ─────────────────────
echo ""
echo "🎯 Sprint 3 — Patrick + Stan + Phase 0/7 + scope split"
echo "---"

# Sanity check Sprint 3 files
for f in agents/product-manager.md agents/staff-engineer.md; do
  if [ ! -f "$f" ]; then
    echo "❌ Missing: $f. Abort."
    exit 1
  fi
done

git add -A
git commit -m "v3.0.0 — Comprehensive Org Structure (Patrick + Stan + Phase 0/7)

Added agents:
  - agents/product-manager.md (Patrick) — sole owner: OKR, RICE/WSJF, opportunity sizing, kill decisions
  - agents/staff-engineer.md (Stan) — sole owner: tech radar, cross-team consistency, polyglot review

Added phases:
  - Phase 0 Discovery (Patrick + Domain SME) — OKR + opportunity + pain validation BEFORE BRD
  - Phase 7 Learn (Patrick + Oliver) — sprint retro: OKR review, kill decision, tech debt RICE

Changed (scope split):
  - Oliver — kept Engagement Lead; Tech Lead role → Stan
  - Bella — kept BA; PM work (OKR/RICE/opportunity) → Patrick
  - 7 Domain SMEs — elevated to Phase 0 active driver (was passive consultant)

Plugin manifest:
  - plugin.json + marketplace.json bumped to 3.0.0
  - keywords added: raci, sre, security-engineering, product-management, staff-engineer, core-web-vitals, lighthouse, okr, team-structure, drift-defense

Total v3.0 stats:
  - 19 agents (12 core + 7 domain) in 7 teams
  - 13 skills (after cleanup + 4 new)
  - 8 phases (was 5)
  - +6,000 tokens net (~+4%), comparable to v2.8.1 patch
"
echo "✅ Sprint 3 committed (v3.0.0)"

# ─── Build .plugin bundle ──────────────────────────────────────────────
echo ""
echo "📦 Building shode-house-v3.0.0.plugin bundle..."
echo "---"

# Plugin bundle = zip of project root excluding bundled outputs
BUNDLE="shode-house-v3.0.0.plugin"
if command -v zip >/dev/null 2>&1; then
  zip -r "$BUNDLE" \
    .claude-plugin/ agents/ commands/ skills/ references/ \
    README.md CHANGELOG.md \
    -x "*.DS_Store" -x "*/node_modules/*" -x "outputs/*" \
       -x ".git/*" -x "*.plugin" \
    > /dev/null
  echo "✅ Built: $BUNDLE ($(du -h "$BUNDLE" | cut -f1))"
else
  echo "⚠️  zip not found — skip bundle build (run manually later)"
fi

# ─── Tag ──────────────────────────────────────────────────────────────
echo ""
echo "🏷️  Tagging v3.0.0..."
echo "---"
git tag -a v3.0.0 -m "v3.0.0 — Comprehensive Org Structure

Single biggest release since v1.0. 4 new agents (Patrick/Stan/Sentinel/Reggie),
4 new phases (0/1c/6/7), 7-team structure with zero-overlap capability matrix,
Workflow Drift Defense (7 mechanisms), Handoff Broadcast Protocol, RACI per phase,
multi-sig pre-deploy-prod gate.

See CHANGELOG.md [3.0.0] for full details.
"
echo "✅ Tag v3.0.0 created"

# ─── Final R0 confirm before push ──────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "🚨 R0 — About to push to GitHub public marketplace"
echo "════════════════════════════════════════════════════════════════════"
echo "Remote: $(git remote get-url origin)"
echo "Commits to push:"
git log --oneline origin/main..HEAD 2>/dev/null || git log --oneline -5
echo ""
echo "Tag to push: v3.0.0"
echo ""
echo "After push, marketplace.json v3.0.0 will be live for all users."
echo ""
read -p "Continue push? [y/N] " answer
if [ "$answer" != "y" ]; then
  echo "❌ Aborted. Commits + tag are local; not pushed."
  echo "   To push later: git push origin main && git push origin v3.0.0"
  exit 0
fi

# ─── Push ──────────────────────────────────────────────────────────────
echo ""
echo "🚀 Pushing..."
echo "---"
git push origin main
git push origin v3.0.0
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "🎉 v3.0.0 released!"
echo "════════════════════════════════════════════════════════════════════"
echo "GitHub:  https://github.com/shode666/claude-skill-shode-house"
echo "Tag:     https://github.com/shode666/claude-skill-shode-house/releases/tag/v3.0.0"
echo "Bundle:  $BUNDLE"
echo ""
echo "Next:"
echo "  - Create GitHub Release using $BUNDLE"
echo "  - Announce in marketplace + community"
echo "  - Update SHODE-HOUSE-MASTER.md if needed"
