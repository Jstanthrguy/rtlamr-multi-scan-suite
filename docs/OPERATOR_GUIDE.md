# Operator Guide — rtlamr Multi-Scan Suite

This guide describes **common, effective operational workflows** for using the rtlamr Multi-Scan Suite in the field. It does **not** restrict entry mode or observation intent. Examples are illustrative, not mandatory.

---

## Scope and Audience

This document is for operators who want practical, step‑by‑step guidance to:

* discover AMR activity,
* monitor selected frequencies efficiently,
* and perform per‑radio observation.

Conceptual definitions live in **README.md** and **ARCHITECTURE.md**. This guide focuses on *how to operate* what those documents define.

---

## Prerequisites

* Linux system with Python 3.11+
* `rtlamr` binary available
* RTL‑SDR (or compatible backend) reachable via `rtl_tcp`
* Stable antenna and gain configuration

---

## Entry Modes (Overview)

The suite supports two frequency‑selection entry modes:

* **Enumerated (ISM‑derived):** frequencies are discovered from the environment via wideband ISM scanning and analysis.
* **Declared (Operator‑driven):** frequencies are provided directly by the operator (prior knowledge, reuse of results, or narrow probing).

Both modes feed the same observation tools. Choose based on intent and context.

---

## Start the SDR Backend

```bash
rtl_tcp -a 0.0.0.0 -p 1234 -s 2359296 -g 44.5
```

Verify connectivity before proceeding.

---

## ISM‑Derived Workflow (Enumerated Entry Mode)

Use this workflow when you want **environment‑driven discovery** without assumptions.

### 1. Run an ISM Sweep

```bash
./scripts/rtlamr_multi_scan.py \
  --ism-sweep \
  --ism-seconds-per-freq 40 \
  --rtlamr ~/rtlamr/bin/rtlamr \
  --server 127.0.0.1:1234
```

Outputs:

```text
logs/ism_sweeps/<timestamp>/
├── raw.jsonl
└── summary.txt
```

---

### 2. Analyze the Sweep

```bash
./scripts/rtlamr_scan_analyzer.py \
  --summary logs/ism_sweeps/<ts>/summary.txt \
  --core-count 2
```

Produces (co‑located with the sweep):

```text
core_freqs.json
radios.json
suggested_rtlamr_commands.txt
```

---

### 3. Run a Focused Core Scan

```bash
./scripts/rtlamr_multi_scan.py \
  --core-json core_freqs.json \
  --seconds-per-freq 120
```

Outputs:

```text
logs/core_scans/<timestamp>/
├── raw.jsonl
└── summary.txt
```

Use longer dwell times for stability and trend observation.

---

## Declared‑Frequency Workflow (Operator‑Driven Entry Mode)

Use this workflow when you already know which frequencies to observe or want rapid probing without a full ISM sweep.

### Run a Core Scan with Declared Frequencies

Provide a frequency set (for example, from prior results):

```bash
./scripts/rtlamr_multi_scan.py \
  --core-json <your_freq_set>.json \
  --seconds-per-freq 120
```

This produces the same core scan outputs as ISM‑derived core scans.

---

## Per‑Radio Tracking

For focused study of a specific radio:

```bash
rtlamr -filterid=<ID> -format=json
```

Useful for:

* burst interval analysis
* vendor behavior study
* drift and channel movement tracking

---

## Interpreting Outputs

* **raw.jsonl:** full decode stream for post‑processing
* **summary.txt:** human‑readable activity overview
* **core_freqs.json:** ranked center frequencies
* **radios.json:** observed radio identifiers and counts

Analyzer artifacts remain with their originating ISM sweep.

---

## Troubleshooting

* `rtl_tcp` unreachable: verify host/port and device presence
* Low decode rates: adjust gain or antenna placement
* High noise floor: reduce gain, improve grounding, relocate antenna
* Missing outputs: confirm correct paths and flags

---

## Example Workflow (Illustrative)

```text
Start rtl_tcp
→ ISM sweep (optional)
→ Analyze (optional)
→ Core scan (focused monitoring)
→ Per‑radio tracking
```

This is a **common** workflow, not a requirement. Entry modes and order may vary.

---

## Notes

AMR deployments vary widely by geography and vendor. Revisit sweeps periodically and adapt dwell times and frequency sets to local conditions.
