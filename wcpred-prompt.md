# World Cup Prediction 2026 — เว็บเล่นทายผลกับเพื่อน

## บริบท
เว็บทายผลบอลโลก เล่นกับเพื่อนกลุ่ม 10-50 คน ใช้แต้มเสมือน (credit) **ไม่ใช่เงินจริง**
โหมด casual fun — **ห้าม over-engineer ห้ามทำ feature ที่ enterprise/banking ใส่มา**

## หลักคิด
- KISS เป็นหลัก เล่นกับเพื่อน
- ตัดทิ้ง: email noti, web push, OpenTelemetry, Prometheus, SSRF allowlist, anti-cheat IP sweep, suspicious activity, achievement system, PWA, password auth, rate limit หนักๆ
- เน้น: realtime ความสนุก, theme manga ดูเท่ห์, feature เล่นได้จริง

## Tech Stack
- Next.js 15 App Router + TypeScript + Tailwind v4 + shadcn/ui
- Prisma + PostgreSQL 16
- Redis (cache + Socket.io adapter)
- NextAuth v5 + Google OAuth **เท่านั้น** (ไม่มี password)
- Socket.io custom server (`src/server.ts`)
- MinIO (รูป player + team logo)
- Docker Compose (postgres + redis + minio + app)
- Port **8666** (ไม่ใช้ 6666 — browser block IRC port)

## Theme — Manga
Blue Lock x Captain Tsubasa hybrid
- Dark theme + accent สีธงชาติทีม
- Player portrait = manga style (admin upload จาก ChatGPT/DALL-E เอง, ระบบ**ไม่**ต้อง auto-gen)
- Team logo, Team Flag = (admin upload จาก ChatGPT/DALL-E เอง, ระบบ**ไม่**ต้อง auto-gen)
- `<TrophyIcon>` amber `#854F0B` = honor
- `<CoinIcon>` blue `#185FA5` = credit
- ทุกตัวเลข balance/transaction ต้องมี icon คู่

## Word convention (สำคัญมาก — ห้ามคำพนัน)
ใช้:
- ส่งคำทาย / ลงแต้ม / คำทาย
- ทายสกอร์ตรง (exact score)
- ทายเฉือน (Asian handicap)
- ทายเกมประตู (over/under)

ห้าม: "เดิมพัน", "wager", "bet", "betting", "สูง/ต่ำ", "ต่อ/รอง"

## User & Auth
- Google OAuth เท่านั้น
- **First user ที่ login → auto SYSTEM_ADMIN + 2000 credit + isApproved=true** (เช็คจาก user count = 0 ใน DB)
- User ใหม่ default `isApproved=false` → redirect `/pending`
- SYSTEM_ADMIN promote ADMIN ได้, ADMIN approve user + adjust ledger ได้
- มี `displayName` (override Google name) 2-20 chars, unique per league
- เลือก favorite team 1-3 ทีม → badge ต่อท้ายชื่อทุกที่ (leaderboard/chat/shout/wager/profile)

## Credit + Honor — Double-entry ledger
- `Transaction` table = credit ledger, INSERT only
- `HonorTransaction` table = honor ledger, INSERT only
- **ไม่มี** mutable column `user.credit` / `user.honor`
- Balance = `SUM(amount WHERE userId=?)`
- ทุก wager/payout/refund = INSERT row, ใช้ `src/lib/credit-ledger.ts` + `src/lib/honor-ledger.ts`

## Match Data
- Provider: **football-data.org** (มี API key พร้อม)
- Bootstrap on boot:
  - มี key → sync 104 matches WC2026 จาก API
  - ไม่มี key → load `prisma/fixtures/wc2026.json` (72 matches fallback)
- Cron: sync live score ทุก 1 นาที + kickoff reminder 30 นาทีก่อนแข่ง
- Asset auto-download: ดึง team logo จาก API → save MinIO `teams/{code}.png`

## Features (เรียงตาม priority)

### Phase 1 — Core
1. **Auth + Approval gate** (Google OAuth, first-user-admin)
2. **Match list + detail page** (manga style card)
3. **Prediction form 3 types**:
   - ทายสกอร์ตรง — กรอกสกอร์, payout x5-x35 (Poisson model)
   - ทายเฉือน — step 0.25/0.5/0.75/1.0/1.5
   - ทายเกมประตู — เส้น 1.5/2.5/3.5
   - UI: tab + score stepper + slider unified (credit ↔ honor)
4. **Stage-based wager cap** — backend validate:
   - Group: 500 / R16-QF: 1000 / SF: 2000 / Final: ∞
5. **Credit + Honor ledger** (double-entry, INSERT only)
6. **Settlement** — เมื่อแมตช์จบ คิด payout + INSERT transaction
   - ชนะ → คืน credit (wager amount) + ได้ honor
   - แพ้ → ไม่คืน

### Phase 2 — Realtime + Social
7. **Socket.io events**:
   - `score:update` — broadcast match room
   - `leaderboard:update` — global rerank
   - `chat:message` / `chat:join` / `chat:leave` — chat ห้องแมตช์
   - `shout:cast` — overlay scroll R→L 8s
   - `prediction:settled` — toast user เมื่อ wager จบ
8. **Leaderboard** (global + filter by competition) — rerank realtime
9. **Match chat** — chat panel ในหน้าแมตช์, approved user เท่านั้น
10. **Shout overlay** — lower-third scroll R→L 8s, max 60 ตัวอักษร
    - Basic 10 credit (สีขาว)
    - VIP 50 honor (gold + sound)
    - Bad word filter + admin ban

### Phase 3 — Honor mechanics
11. **Mix-wager** — เพิ่ม payout +0.4× (cost honor)
12. **Purge ×2** (100 honor) / **Purge ×3** (250 honor) — multiplier payout
13. **Sabotage เพื่อน** (80 honor) — ลด payout target ในนัดนั้น
14. **Comeback insurance** (500 honor) — ยกเลิก 1 wager เสีย/tournament

### Phase 4 — Catch-up (anti-quit รอบ knockout)
15. Rubber-band honor: rank ครึ่งล่าง ได้ honor **×1.8**
16. Underdog bonus: ทาย team odds สูง ถูก → payout **+×1.5**
17. Tier leaderboard: top-half / bottom-half แยก รางวัล tier

### Phase 5 — Profile + Admin
18. **Profile** — แก้ displayName, เลือก favorite teams (1-3)
19. **/players/[slug]** — manga portrait + career stats
20. **/teams/[code]** — squad + upcoming matches + form
21. **/me/stats** — สถิติส่วนตัว (charts recharts)
22. **/admin/users** — approve user + promote ADMIN + adjust ledger
23. **/admin/assets** — **upload ภาพ manga manual** (สำคัญ — theme หลักของเว็บ):
    - หน้า list player + team พร้อม preview รูปปัจจุบัน (หรือ dummy ถ้ายังไม่มี)
    - Drag-drop หรือ file picker (รับ jpg/png ≤ 5MB)
    - Upload → save MinIO ตาม convention `players/{playerId}.jpg` / `teams/{teamCode}.png`
    - Override รูปเดิมได้ (ไม่ต้อง versioning)
    - Update DB column `imageUrl` หลัง upload สำเร็จ
    - Crop/resize ไม่ต้อง — admin เตรียมมาจาก ChatGPT/DALL-E ขนาดถูกต้องแล้ว (3:4 portrait)
    - แสดง prompt template ในหน้านี้ด้วย (copy ไป paste ChatGPT ได้เลย):
      ```
      manga anime portrait of [PLAYER NAME] as Blue Lock sports manga protagonist,
      wearing [COUNTRY] [home/away] [JERSEY COLOR] jersey number [N],
      intense expressive brown eyes with sharp eyebrows,
      spiky [HAIR COLOR] hair, dynamic 3/4 angle, bold black ink outlines,
      cel-shaded coloring, dramatic action lines + paint splash bg in [FLAG COLORS],
      shounen sports manga aesthetic, 3:4 portrait
      ```
24. **/admin/competitions** — config season, sync match จาก API manual trigger

## DB Schema
- `Competition` → `Season` → `Stage` → `Match`
- `Team` (many-to-many `TeamCompetition`)
- `User` → `Prediction`, `Transaction`, `HonorTransaction`
- `Sabotage`, `ComebackInsurance`, `Player`, `ChatMessage`, `Shout`
- `AdminLog` (audit ง่ายๆ ไม่ต้อง security-grade)

## Asset fallback
- Player ไม่มีรูป → fallback `/assets/players/__dummy.jpg` (manga silhouette เสื้อเทา หมายเลข "?")
- Team logo ไม่มี → flag emoji + bg สีธงชาติ
- Convention path: `players/{playerId}.jpg`, `teams/{teamCode}.png`

## File structure
```
src/
├── app/
│   ├── (public)/       # public pages
│   ├── (protected)/    # ต้อง isApproved
│   ├── admin/          # ต้อง ADMIN
│   └── api/
├── lib/
│   ├── auth.ts         # NextAuth (Node)
│   ├── auth.config.ts  # NextAuth (Edge-safe)
│   ├── db.ts
│   ├── redis.ts
│   ├── credit-ledger.ts
│   ├── honor-ledger.ts
│   └── providers/      # football-data.org
├── components/
├── middleware.ts       # approval gate
└── server.ts           # custom Next.js + Socket.io
```

## Conventions
- Component < 300 บรรทัด, function < 50 บรรทัด
- Server Component default, Client Component only when needed
- Zod validate API input ทุก route
- Test เฉพาะ ledger logic + payout calc (ไม่ต้อง 80% coverage)
- TypeScript strict
- ใช้ shadcn/ui + tailwind v4 (@theme block)

## Run commands
```bash
make up           # 1-command: postgres + redis + minio + migrate + seed + app
make docker-logs  # tail app log
make migrate      # prisma migrate dev
make seed         # seed DB
```

## ห้ามทำ (ย้ำ — เคยทำมาแล้วเสียเวลา)
- ❌ Email notification / nodemailer
- ❌ Web push notification / web-push
- ❌ OpenTelemetry / Prometheus / structured metrics
- ❌ SSRF allowlist / origin validation
- ❌ IP logging / anti-cheat sweep / suspicious activity table
- ❌ Achievement system, badge unlock
- ❌ Multi-competition flex schema (focus WC2026 ก่อน)
- ❌ PWA / service worker / offline mode
- ❌ Password auth (Google เท่านั้น)
- ❌ Comprehensive rate limiting (เพื่อนเล่นกัน)
- ❌ Loop spawn agent หลายตัว — เขียนตรงๆ แก้ตรงๆ

## ตัวอย่าง theme look and feel และ wireframe.
- docs/look_n_feel/...

