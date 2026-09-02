# design-intel — UI/UX lookup layer (Uma)

Vendored subset ของ [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (MIT © Next Level Builder) + `check_contrast.py` ของ shode-house

## ทำไมถึงมี

Uma Phase 1b สั่งให้ผลิต design token (primitive → semantic → component) แต่เดิม **ไม่มีแหล่งว่าค่าอะไร** → Uma เสกสี/ฟอนต์/สเกลจากหัว model ทุกครั้ง = ผลลัพธ์แปรผันตาม model และ reproduce ไม่ได้
pack นี้ทำให้ส่วนนั้นเป็น **retrieval** แทน **recall** — และ **ข้อมูลไม่เข้า context** เข้าเฉพาะผลลัพธ์ของ query (preload cost = 0 tok)

## กฎเหล็ก — catalog ≠ evidence (🔴)

`data-provenance.json` ของ upstream ระบุเองว่าหลายรายการเป็น `derived` / `sla: needs-review` / `confidence < 1.0`

| ชั้น | สถานะ | ใช้ทำอะไรได้ |
|---|---|---|
| ผลจาก `search.py` (palette, pairing, pattern, style) | **ข้อเสนอ (proposal)** | ตั้งต้น design direction, ลดการเดา |
| WCAG / axe / Lighthouse / Playwright output | **หลักฐาน (evidence)** | cite ใน bd, sign-off gate |

- ขัดกันเมื่อไหร่ **มาตรฐานชนะ catalog เสมอ**
- ห้าม cite ตัวเลขจาก CSV เป็น evidence ระดับเดียวกับ axe/Lighthouse (ผิด UX Evidence Protocol)
- 0 result → retry 1 ครั้งด้วย query แคบลง → ถ้ายังว่าง **บอกตรง ๆ ว่าใช้ built-in default ไม่ใช่ match จากฐานข้อมูล** · ห้าม present 0-result เหมือนมีข้อมูล · **ห้าม persist output ที่ยังไม่ verify**

> พิสูจน์แล้วว่ากฎนี้จำเป็น: palette ที่ catalog คืนมาสำหรับ "hotel booking dashboard" มี `Border #BFDBFE` บน `Background #F8FAFC` = **1.36:1**
>
> **สองชั้นของ gate (v3.12)** — WCAG 1.4.11 บังคับ 3:1 เฉพาะ non-text ที่ *สื่อความหมาย*:
> - **text + `Ring` (focus indicator)** = hard block เสมอ แก้สีสถานเดียว
> - **`Border`** = block จนกว่าจะ **ตัดสินแล้วบันทึก** — ขอบของ input/select/checkbox/selected state ต้องถึง 3:1; เส้นคั่น section หรือขอบการ์ดที่มี elevation แล้ว ผ่านได้ด้วย `--border-decorative "<เหตุผล>"` แล้ว paste บรรทัด `ACK` ลง bd
> (เวอร์ชันแรกทำ Border เป็น hard block → block ทุก palette ในแคตตาล็อก = Uma ทำงานไม่ได้เลย)

## ใช้ยังไง

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-.}/references/design-intel"

# 1) design system ทั้ง product (ใช้ตอนเริ่ม project/หน้าใหม่)
python3 "$ROOT/scripts/search.py" "<product> <industry> <keywords>" --design-system \
        --variance <1-10> --motion <1-10> --density <1-10> -p "<Project>" --json > /tmp/ds.json

# 2) 🔴 gate: catalog -> evidence (ต้องผ่านก่อนเขียน tokens.json)
python3 "$ROOT/scripts/check_contrast.py" --design-system-json /tmp/ds.json
#    ขอบต่ำกว่า 3:1 และเป็นของตกแต่งล้วน -> ตัดสินแล้วบันทึก:
python3 "$ROOT/scripts/check_contrast.py" --design-system-json /tmp/ds.json \
        --border-decorative "เส้นคั่น section เท่านั้น; input ใช้ token.border.strong"  # -> paste ACK ลง bd

# 3) query เฉพาะจุด
python3 "$ROOT/scripts/search.py" "focus not obscured" --domain ux -n 3
python3 "$ROOT/scripts/search.py" "chip badge overflow nowrap" --stack html-tailwind
```

**Domain**: `ux` `style` `color` `typography` `google-fonts` `product` `landing` `icons` `gsap` `chart` `react` `web`
**Stack ที่เก็บไว้**: react · nextjs · vue · nuxtjs · nuxt-ui · svelte · astro · html-tailwind · shadcn · flutter · react-native · swiftui · jetpack-compose · laravel · angular

**Design dials** (เฉพาะกับ `--design-system`) — ใช้แทนคำถามเปิด "อยากได้แนวไหน" ในการ clarify:
`--variance` 1 มินิมอล ↔ 10 bold/asymmetric · `--motion` 1 subtle ↔ 10 choreography (แนบ GSAP snippet) · `--density` 1 โปร่ง ↔ 10 dashboard (override spacing scale)

## Reference (on-demand — 🔴 ห้าม preload)

- `references/quick-reference.md` (~6k tok) — 119 UX guideline เต็ม พร้อม rationale
- `references/pro-rules.md` — pre-delivery checklist ของ native/mobile app UI

## สิ่งที่ตัดออกจาก upstream

`google-fonts.csv` เหลือ 250 แถวแรก · stack เหลือ 15 ตัวที่ทีมใช้ · ตัด `phosphor-icons-upstream.json` + `google-font-licenses.json` (805K+423K — เป็น input ของ refresh tooling ไม่ใช่ของ search) · ตัด `validate_data.py` + `scripts/tests/` (maintainer tooling)
→ 2.5MB เหลือ **1.2MB**. refresh ข้อมูล = ดึง upstream ใหม่แล้ว re-apply การตัดชุดนี้
