#!/usr/bin/env python3
"""Catalog -> Evidence gate (shode-house v3.11).

Palette ที่ออกจาก search.py = **ข้อเสนอ (proposal)** ไม่ใช่หลักฐาน.
สคริปต์นี้เปลี่ยนมันเป็นหลักฐาน (หรือ reject). Uma ต้องรันผ่านก่อนเขียน tokens.json.

Usage:
  python3 check_contrast.py --pair "#1E3A8A,#FFFFFF" [--pair ...] [--large|--nontext]
  python3 check_contrast.py --design-system-json ds.json   # จาก: search.py ... --design-system --json

Exit 0 = ผ่านทุกคู่ · 1 = มี FAIL (block hand-off) · 2 = ไม่มีอะไรให้ตรวจ
Threshold (WCAG 2.1/2.2 AA): text 4.5:1 · large text (>=24px หรือ >=18.66px bold) 3:1 · non-text UI 3:1
"""
import argparse, json, sys

def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def luminance(hex_color):
    h = hex_color.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(ch * 2 for ch in h)
    if len(h) != 6:
        raise ValueError(f"bad hex: {hex_color}")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)

def ratio(fg, bg):
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)

# HARD = ตกแล้ว block (WCAG AA บังคับแน่นอน)
DS_PAIRS = [
    ("On Primary", "Primary", "text"),
    ("On Secondary", "Secondary", "text"),
    ("On Accent", "Accent", "text"),
    ("On Destructive", "Destructive", "text"),
    ("Foreground", "Background", "text"),
    ("Card Foreground", "Card", "text"),
    ("Muted Foreground", "Muted", "text"),
    # focus indicator = non-text ที่ "สื่อความหมาย" เสมอ -> 1.4.11 บังคับ 3:1
    ("Ring", "Background", "nontext"),
]
# WARN = ขึ้นกับการใช้งาน ตัดสินอัตโนมัติไม่ได้ -> รายงาน ไม่ block
#   WCAG 1.4.11 บังคับ 3:1 เฉพาะ non-text ที่ "สื่อความหมาย" (UI component boundary ที่จำเป็นต่อการระบุ
#   control, graphical object ที่สื่อข้อมูล). เส้นคั่น/ขอบการ์ดที่เป็น "ตกแต่งล้วน" ไม่เข้าข่าย
#   -> Uma ต้องตัดสินเองต่อ component ว่าขอบนั้น meaningful หรือ decorative
DS_WARN_PAIRS = [
    ("Border", "Background", "nontext"),
    ("Border", "Card", "nontext"),
]
THRESHOLD = {"text": 4.5, "large": 3.0, "nontext": 3.0}

def check(fg, bg, role, label="", warn_only=False):
    r = ratio(fg, bg)
    need = THRESHOLD[role]
    ok = r >= need
    if warn_only:
        tag = "ok  " if ok else "WARN"
    else:
        tag = "PASS" if ok else "FAIL"
    print(f"  {tag}  {r:5.2f}:1  (need {need}:1, {role})  {fg} on {bg}  {label}")
    return True if warn_only else ok

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pair", action="append", default=[], help='"#fg,#bg"')
    p.add_argument("--large", action="store_true")
    p.add_argument("--nontext", action="store_true")
    p.add_argument("--design-system-json")
    p.add_argument("--border-decorative", metavar="REASON",
                   help="ack ว่าขอบที่ต่ำกว่า 3:1 เป็นของตกแต่งล้วน (ไม่ใช่ boundary ของ control) "
                        "พร้อมเหตุผลที่จะไปแปะใน bd -- ไม่ใส่ = block")
    a = p.parse_args()

    role = "large" if a.large else ("nontext" if a.nontext else "text")
    allok, checked = True, 0
    print("WCAG 2.1/2.2 AA contrast gate")

    for pair in a.pair:
        fg, bg = [x.strip() for x in pair.split(",")]
        allok &= check(fg, bg, role); checked += 1

    if a.design_system_json:
        with open(a.design_system_json, encoding="utf-8") as f:
            data = json.load(f)
        block = data.get("design_system", data)
        colors = block.get("colors", {})
        if not colors:
            print("  no 'colors' block in JSON", file=sys.stderr); sys.exit(2)
        norm = {k.strip().lower().replace(" ", "_"): v for k, v in colors.items()
                if isinstance(v, str) and v.strip().startswith("#")}
        key = lambda k: norm.get(k.lower().replace(" ", "_"))
        for fgk, bgk, r in DS_PAIRS:
            fg, bg = key(fgk), key(bgk)
            if fg and bg:
                allok &= check(fg, bg, r, f"[{fgk} / {bgk}]"); checked += 1
        warned = []
        for fgk, bgk, r in DS_WARN_PAIRS:
            fg, bg = key(fgk), key(bgk)
            if fg and bg and ratio(fg, bg) < THRESHOLD[r]:
                warned.append((fg, bg, r, f"[{fgk} / {bgk}]"))
        if warned:
            print("\n  ขอบต่ำกว่า 3:1 — WCAG 1.4.11 บังคับ 3:1 เฉพาะ non-text ที่ 'สื่อความหมาย':")
            for fg, bg, r, lbl in warned:
                check(fg, bg, r, lbl, warn_only=True); checked += 1
            if a.border_decorative:
                print(f"  ACK (ตกแต่งล้วน): {a.border_decorative}")
                print("  -> paste บรรทัด ACK นี้ลง bd เป็นหลักฐานการตัดสิน")
            else:
                allok = False
                print("  🔴 ต้องตัดสินก่อน ผ่านเองไม่ได้ — ขอบนี้จำเป็นต่อการระบุ control ไหม?")
                print("     จำเป็น (input/select/checkbox boundary, selected state) -> แก้สีให้ถึง 3:1 แล้วรันใหม่")
                print("     ตกแต่งล้วน (เส้นคั่น section, ขอบการ์ดที่มี elevation อยู่แล้ว) ->")
                print("       รันซ้ำด้วย --border-decorative \"<เหตุผล>\" แล้ว paste ACK ลง bd")

    if not checked:
        print("nothing checked", file=sys.stderr); sys.exit(2)
    print(f"\n{'ALL PASS' if allok else 'BLOCKED'} -- {checked} pair(s) checked")
    sys.exit(0 if allok else 1)

if __name__ == "__main__":
    main()
