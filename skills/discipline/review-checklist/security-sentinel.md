---
name: security-sentinel
description: Reference (lazy-load) ของ `review-checklist` — security depth axis ของ Sentinel (SAST/SCA/secret scan/CSP/abuse case/pen test). โหลดเมื่อ diff แตะ auth/money/PII หรือเมื่อ secure skill ถูก trigger
---

```lazy-load-contract
LOAD: skills/discipline/review-checklist/security-sentinel.md
WHEN: diff_touches in {auth,money,PII,crypto,secrets} OR secure_skill_triggered=true
OWNER: security-engineer
REQUIRED-BEFORE: phase_3b_verdict
```

# Security depth axis (Sentinel)

รันเมื่อ diff แตะ auth / money / PII / crypto / secret หรือเมื่อ `secure` skill ถูก trigger — **parallel กับ Chris + Quinn ไม่ใช่หลังจาก**

| ขั้น | เครื่องมือตัวอย่าง | ขอบเขต |
|---|---|---|
| SAST | Semgrep / CodeQL | full repo (ไม่ใช่แค่ diff — taint อาจมาจากที่อื่น) |
| SCA | Trivy / Grype / `npm audit` | dependency + container image |
| Secret scan | gitleaks / truffleHog | commit history + working tree |
| Policy review | CSP / Trusted Types / SRI | frontend ที่ render user content |
| Abuse case | threat model จาก `secure` skill | ทุก abuse case ที่ระบุไว้ต้องมี verdict |
| Pen test | OWASP ASVS | เฉพาะ PCI / HIPAA / regulated scope |

**Verdict rule**: finding จาก scanner ที่ยังไม่ triage = 🔴 Critical จนกว่าจะพิสูจน์ว่า false positive พร้อม paste เหตุผล
ห้าม claim "security ผ่าน" โดยไม่ paste output ของ scanner ที่รันเอง
