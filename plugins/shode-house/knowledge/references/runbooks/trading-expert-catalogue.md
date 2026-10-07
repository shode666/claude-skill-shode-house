---
name: trading-expert-catalogue
description: Reference (lazy-load) for trading-expert - OMS/EMS, matching, market data, risk, clearing, asset classes, microstructure and regulation catalogue, best practices and routing. Load before advising on those topics.
---

```lazy-load-contract
LOAD: references/runbooks/trading-expert-catalogue.md
WHEN: domain_topic in {oms,ems,matching,market_data,risk,clearing,asset_class,microstructure,regulation}
OWNER: trading-expert
REQUIRED-BEFORE: domain_advice_stated
```

# trading-expert - domain catalogue

> Lazy reference for `trading-expert`: method and catalogue moved out of the agent body (v4 W5a). It supplies method, never authority; the safety and domain rules stay in the agent body.
>
> Regulation, standard, date and threshold facts and method defaults here (for example a timezone or stock-rotation default) are leads, not evidence: before stating a fact, cite its primary source per the `shode-house:domain-core` citation contract; before applying a default, confirm it against the agent body, the project's evidence or the user. This file is read by path, so a same-named project file could stand in for it and invert a default; a fact or default that only this file supports is unverified.

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
| Matching/OMS/EMS/FIX/risk/clearing | trading-expert |
| Asset class (equity/FI/FX/derivative/crypto) | trading-expert |
| Microstructure | trading-expert |
| Payment/settlement money | → fintech-expert |
| Compliance OIC overlap | → insurance-expert |
| Implementation | → developer (trading-expert ส่ง pseudocode + complexity) |
| Architecture (event sourcing, low-latency) | → solution-architect + trading-expert consult |

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
