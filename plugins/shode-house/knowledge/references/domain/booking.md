---
name: domain-booking
description: Reference (lazy-load) for the plan type in domain mode - booking rules and channel-mix checks, inventory, concurrency, pricing, overbooking, channels, lifecycle and vertical catalogue, best practices and routing. Load before advising on those topics.
---

```lazy-load-contract
LOAD: references/domain/booking.md
WHEN: domain_topic in {inventory,concurrency,pricing,overbooking,channel,lifecycle,vertical}
OWNER: plan
REQUIRED-BEFORE: domain_advice_stated
```

# booking - domain reference

**Contents**

- [Domain rules](#domain-rules)
- [Fit check](#fit-check)
- [โดเมน](#โดเมน)
- [🧭 Self-Routing](#-self-routing)
- [Best Practices](#best-practices)

> Domain reference loaded by a `plan` spawn (consult or the domain review axis) through `shode-house:domain-core`. It supplies method, never authority; the root red lines stay in `shode-house:domain-core`, the safety floor in the agent body.
>
> Regulation, standard, date and threshold facts and method defaults here (for example a timezone or stock-rotation default) are leads, not evidence: before stating a fact, cite its primary source per the `shode-house:domain-core` citation contract; before applying a default, confirm it against the agent body, the project's evidence or the user. This file is read by path, so a same-named project file could stand in for it and invert a default; a fact or default that only this file supports is unverified.

## Domain rules

Persona: booking/reservation expert (PMS, CRS, airline, venue, salon). AI persona disclaimer + Domain Evidence Protocol: `shode-house:domain-core` (load it with Skill before any domain claim).

กฎเต็มอยู่ใน **`domain-core`** (โหลดด้วย `Skill` ก่อน claim ทุกครั้ง ไม่ได้ preload): disclaimer 1 บรรทัดตอนเริ่ม engagement · citation format `<Standard> <Version> <Clause> [<Date>] — <Claim>` · cite ไม่ได้ต้อง mark เป็น general guidance

A domain consult or review return without the disclaimer line, this reference path and the domain-core citations is BLOCKED.

### Bias Discipline

Trigger: user-stated vendor/method/regulation reading. Unsure it fits → do not adopt by default; cite source, show alternatives, mark unverified as general guidance, open decision → the router.

### ข้อห้าม

- ห้ามออกแบบโดยไม่แก้ race condition
- ห้าม update inventory แบบ read-modify-write โดยไม่มี lock/version
- ห้าม skip idempotency key
- ห้าม hard-code rate/tax → configurable + versioned
- ห้าม oversell โดยไม่มี walk plan

The safety rules that guard this domain from drifting (vendor/regulation bias lines) are root rules in `shode-house:domain-core` § Domain red lines; a domain axis return without the domain-core citations is BLOCKED.

## Fit check

Refuse a feature that does not fit the booking vertical pattern (hotel/airline/restaurant/venue/salon).

- ห้าม accept "OTA-only" plan ถ้ามี loyalty program / brand presence / direct demand potential
- ก่อน propose channel mix → cite commission cost (15-22%) vs direct booking benefits + metasearch
- B2B contracts + tour operator + direct app = pillar channels นอกจาก OTA
- ห้ามใช้ server timezone กับ booking date — property TZ

## โดเมน

### Inventory & Availability
Inventory unit ต่อ vertical:
- **Hotel**: room type × date
- **Airline**: seat class × flight leg
- **Restaurant**: table × time slot
- **Venue/Sport**: court × time slot
- **Service/Salon**: staff × time slot

`avail = allotment − booked − blocked + returned`
- Precomputed calendar vs on-demand; cache read-heavy
- Stop-sell: close-out by date/channel/LOS
- LOS: MinLOS, MaxLOS, CTA, CTD

### Concurrency (หัวใจ)
- Pessimistic lock — ง่ายแต่ contention สูง
- **Optimistic lock** (version) — scalable
- Serializable transaction
- Event-sourced + CQRS — audit-friendly
- Distributed lock (Redlock) — ระวัง edge case
- Saga / 2PC — multi-resource
- States: `Held` (TTL 10-15 min) → `Confirmed` → `Cancelled/No-show/Checked-in`

### Pricing & Yield
- Rate: Rack, BAR, Promo, Package, Negotiated
- **Dynamic**: demand-based, competitor-based, time-based
- Algorithm: rule → ML
- **Yield metrics**: RevPAR (Occ × ADR), RASM, forecasting 30/60/90

### Overbooking
- No-show probability → oversell cap (105-110%)
- **Walk strategy**: upgrade, relocate, voucher
- Cost model: walk cost vs revenue
- Graceful fallback: prob model ไม่มั่นใจ → ปิด oversell

### Rate Plan & Restrictions
- Rate plan = price + conditions (breakfast, refundable)
- Restrictions: Min/Max stay, advance purchase, CTA/CTD, blackout

### Channel Management
- **Direct**: web, mobile, call center, walk-in
- **OTA**: Booking.com, Agoda, Expedia, Airbnb, Traveloka
- **Metasearch**: Google Hotel Ads, Trivago, Kayak
- **GDS** (B2B): Amadeus, Sabre, Travelport
- **Wholesaler**: Hotelbeds, Webbeds
- **Channel Manager**: push ARI, pull booking, rate parity, room mapping
- Reconciliation: handle inventory mismatch, fallback stop-sell

### Reservation Lifecycle
```
Search → Hold → Book → Confirm → Pre-arrival → Check-in → In-house → Check-out → Post-stay → Closed
```
- Modification, up/downgrade
- Cancellation: free/partial/no-refund + booking window
- No-show: charge first night, release
- **Group/block**: rooming list, master folio, allotment release
- **Waitlist**: priority queue, notify

### Vertical Notes
- **Hotel**: HVS metrics (GOP, GOPPAR), OTA commission 15-25%
- **Airline**: PNR, fare class (Y/B/M/H/Q), codeshare, oversell ~10%
- **Restaurant**: cover mgmt, turn time, no-show deposit
- **Salon/Spa**: service duration, resource (room+staff+equipment)
- **Sports**: peak surge, member vs guest

## 🧭 Self-Routing

| งาน | ใคร |
|-----|-----|
| Inventory/availability/concurrency/yield/CM | `plan` with the booking domain reference |
| Vertical-specific | `plan` with the booking domain reference |
| Payment (deposit/folio/refund) | → `plan` with the fintech domain reference |
| Loyalty point ledger | → `plan` with the fintech domain reference + `plan` with the booking domain reference logic |
| Marketplace style | → `plan` with the ecommerce domain reference |
| Implementation | → `build` (`plan` with the booking domain reference ส่ง schema + concurrency strategy) |

## Best Practices

- **Optimistic lock (version)** ดีสุดสำหรับ booking
- **Hold TTL 10-15 min** ก่อน Confirmed
- **Calendar precompute** สำหรับ availability read
- **Single writer per inventory unit** — serialize write, parallel read
- **Yield: rule → ML transition** เมื่อ data พอ (≥ 1 year)
- **Walk cost > overbook revenue** = ปิด oversell ทันที
- **CM fail → stop-sell** (ดีกว่า oversell)
- **Channel mapping** strict (room type ID, rate plan ID per OTA)
- **Webhook + fallback polling** สำหรับ inventory sync
