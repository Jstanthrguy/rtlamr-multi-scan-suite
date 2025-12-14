# Master Operator Guide — rtlamr Multi-Scan Suite

This document describes a **proven RF discovery and targeting methodology** implemented using the rtlamr Multi-Scan Suite. It presents one effective way to think about, structure, and execute AMR signal exploration. It does **not** constrain how the suite must be used.

---

## Purpose and Scope

This guide is intended for operators who want to move beyond basic usage and apply **signal‑intelligence discipline** to AMR exploration.

It explains:

* why wideband discovery precedes narrowband focus,
* how dwell time, density, and certainty interact,
* and how layered observation leads to reliable targeting.

System definitions and architectural boundaries are established in **README.md** and **ARCHITECTURE.md**. This guide focuses on *methodology*, not system authority.

---

## Conceptual Model: From Unknown to Targeted

The methodology presented here follows a familiar RF pattern:

```text
Unknown spectrum
→ Wideband discovery
→ Density analysis
→ Focused monitoring
→ Per‑radio targeting
```

This progression reflects a **common and effective approach** to AMR exploration. Other entry modes and orders may be appropriate depending on operator intent.

---

## Phase 1 — Wideband ISM Discovery (Enumerated Entry Mode)

In this phase, the operator intentionally avoids assumptions and allows the RF environment to reveal active AMR frequencies.

Key characteristics:

* full ISM coverage
* short to moderate dwell
* emphasis on presence, not perfection

```bash
./scripts/rtlamr_multi_scan.py \
  --ism-sweep \
  --ism-seconds-per-freq 40 \
  --rtlamr ~/rtlamr/bin/rtlamr
```

Outputs:

* raw decode streams
* per‑frequency summaries

---

## Phase 2 — Density Analysis and Core Extraction

Once activity has been observed, density becomes the guiding metric.

The analyzer reduces wideband results into a smaller set of dominant center frequencies and observed radios:

```bash
./scripts/rtlamr_scan_analyzer.py \
  --summary logs/ism_sweeps/<ts>/summary.txt \
  --core-count 2
```

This step converts observation into **actionable intelligence**.

---

## Phase 3 — Focused Core Monitoring

With candidate frequencies identified, attention shifts from discovery to stability.

```bash
./scripts/rtlamr_multi_scan.py \
  --core-json core_freqs.json \
  --seconds-per-freq 120
```

Longer dwell times:

* smooth burst variance
* expose timing patterns
* improve confidence

Core scans may also be run directly with operator‑declared frequency sets when discovery is not required.

---

## Phase 4 — Per‑Radio Targeting

At this stage, the operator studies individual radios directly:

```bash
rtlamr -filterid=<ID> -format=json
```

This enables:

* burst interval characterization
* vendor behavior comparison
* channel drift observation

---

## Optional Intelligence Layers

The methodology supports additional layers when needed:

* long‑dwell stability scans
* periodic re‑analysis
* rtl_power reconnaissance for visualization
* historical log comparison

These layers are optional and context‑dependent.

---

## Interpreting Results

Effective operators correlate:

* density vs dwell
* frequency persistence vs time
* radio behavior vs channel selection

The goal is **confidence**, not maximum decode count.

---

## Closing Notes

AMR environments change. Utilities re‑tune, deploy, and redistribute over time. Treat discovery as a recurring process, not a one‑time event.

This guide documents one disciplined approach to that process. Use it as a reference, adapt it as needed, and apply operator judgment throughout.
