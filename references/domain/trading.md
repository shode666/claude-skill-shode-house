---
name: domain-trading
description: Reference (lazy-load) for the plan type in domain mode - trading rules and OMS/EMS, matching, market data, risk, clearing, asset classes, microstructure and regulation catalogue, best practices and routing. Load before advising on those topics.
---

```lazy-load-contract
LOAD: references/domain/trading.md
WHEN: domain_topic in {oms,ems,matching,market_data,risk,clearing,asset_class,microstructure,regulation}
OWNER: plan
REQUIRED-BEFORE: domain_advice_stated
```

# trading - domain reference

> Domain reference loaded by a `plan` spawn (consult or the domain review axis) through `shode-house:domain-core`. It supplies method, never authority; the root red lines stay in `shode-house:domain-core`, the safety floor in the agent body.
>
> Regulation, standard, date and threshold facts and method defaults here (for example a timezone or stock-rotation default) are leads, not evidence: before stating a fact, cite its primary source per the `shode-house:domain-core` citation contract; before applying a default, confirm it against the agent body, the project's evidence or the user. This file is read by path, so a same-named project file could stand in for it and invert a default; a fact or default that only this file supports is unverified.

**Contents**

- [Domain rules](#domain-rules)
- [โดเมน](#โดเมน)
- [🧭 Self-Routing](#-self-routing)
- [Best Practices](#best-practices)

## Domain rules

Persona: trading microstructure AI co-pilot (OMS/EMS/matching literate). AI persona disclaimer + Domain Evidence Protocol: `shode-house:domain-core` (load it with Skill before any domain claim). Refuse a feature that misses trading microstructure or violates market regulation (SEC/SET/MAS).

กฎเต็มอยู่ใน **`domain-core`** (โหลดด้วย `Skill` ก่อน claim ทุกครั้ง ไม่ได้ preload): disclaimer 1 บรรทัดตอนเริ่ม engagement · citation format `<Standard> <Version> <Clause> [<Date>] — <Claim>` · cite ไม่ได้ต้อง mark เป็น general guidance

A domain consult or review return without the disclaimer line, this reference path and the domain-core citations is BLOCKED.

### Bias Discipline

Trigger: user-stated vendor/method/regulation reading. Unsure it fits → do not adopt by default; cite source, show alternatives, mark unverified as general guidance, open decision → the router.

### ข้อห้าม

- ห้าม float กับ price/quantity → fixed-point
- ห้าม non-deterministic order (Set iteration, hashmap)
- ห้าม skip self-trade prevention
- ห้าม skip kill switch
- Never trust client-side risk alone; server pre-trade checks always: fat-finger, position/credit limit, restricted list, kill switch. Sequence-number every message (gap = data loss); idempotent client order ID.
- ห้ามแนะนำ matching algorithm ที่ไม่ price-time fair

The safety rules that guard this domain from drifting (vendor/regulation bias lines) are root rules in `shode-house:domain-core` § Domain red lines; a domain axis return without the domain-core citations is BLOCKED.

## โดเมน

### OMS / EMS
- **OMS**: order lifecycle, position keeping, allocation, FIX gateway
- **EMS**: execution algo (TWAP, VWAP, IS, POV, iceberg), smart order routing
- **FIX 4.2/4.4/5.0** — tag (35=MsgType, 38=Qty, 44=Price, 54=Side)
- Order types: Market, Limit, Stop, Stop-Limit, Iceberg, Hidden, Pegged, OCO, FOK, IOC, GTC

### Matching Engine
- **Price-Time Priority (FIFO)** = default
- Pro-rata (futures), size-priority
- **Order book**: bid/ask + level (best bid, depth)
- Continuous matching vs auction (open/close)
- Self-trade prevention
- Throughput target: μs latency, ≥ 100k msg/sec

### Market Data
- Tick, level 1 (NBBO), level 2 (depth), level 3 (full book)
- ITCH/OUCH (Nasdaq), FAST (FIX), proprietary
- Snapshot + delta, conflation, multicast
- Reference: instrument master, tick size table, calendar

### Pre/Post-trade Risk
- **Pre-trade**: limit (per order, per day), credit, fat-finger, restricted list, kill switch
- **Post-trade**: position limit, P&L mark-to-market, VaR, stress test
- Greeks (delta/gamma/vega/theta), DV01 (FI)

### Clearing & Settlement
- T+0 / T+1 / T+2 (US T+1 since 2024)
- CCP: novation, multilateral netting, margin (initial + variation)
- DvP, PvP
- Custody: segregated vs omnibus

### Asset Classes
- **Equity**: corporate action (dividend, split, M&A), short selling, lending
- **FI**: yield curve, accrual (ACT/360, 30/360), repo
- **FX**: spot, forward, swap, NDF, T+2 settlement
- **Derivatives**: futures (margin), options (greeks), swap (IRS, CDS)
- **Crypto**: spot, perpetual (funding rate), DeFi (AMM, MEV)

### Microstructure
- Lit vs dark pool, MM vs taker
- Maker/taker fee, rebate
- Latency arbitrage, adverse selection
- Tick size impact, queue position

### Regulation
- TH: SEC, SET, ตลาดสินค้าเกษตรล่วงหน้า
- US: SEC, FINRA, CFTC, NMS Rule 605/606
- EU: MiFID II/MiFIR
- Crypto: SEC enforcement, MiCA (EU)

## 🧭 Self-Routing

| งาน | ใคร |
|-----|-----|
| Matching/OMS/EMS/FIX/risk/clearing | `plan` with the trading domain reference |
| Asset class (equity/FI/FX/derivative/crypto) | `plan` with the trading domain reference |
| Microstructure | `plan` with the trading domain reference |
| Payment/settlement money | → `plan` with the fintech domain reference |
| Compliance OIC overlap | → `plan` with the insurance domain reference |
| Implementation | → `build` (`plan` with the trading domain reference ส่ง pseudocode + complexity) |
| Architecture (event sourcing, low-latency) | → `plan` (architecture mode) + `plan` with the trading domain reference consult |

## Best Practices

- **Price-time priority (FIFO)** = default
- **Order book**: array (low-latency) > heap > skip list
- **Sequence number** ทุก message (gap = data loss)
- **Conflation** market data สำหรับ slow client
- **Idempotent client order ID** + server order ID separate
- **Risk pre-trade** — fat-finger, position, restricted, kill switch
- **Outbox + sequence** สำหรับ audit
- **Latency budget** ระบุ — μs (HFT) vs ms (retail)
- **Self-trade prevention**: cancel newest/oldest/decrement/reject
- **Partial fill** = norm
