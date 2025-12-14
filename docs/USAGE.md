# rtlamr Multi-Scan Suite — Usage Guide

This document lists common, canonical command patterns and their expected outputs. Examples are grouped by **entry mode** and do not prescribe a required order.

---

## ISM-Derived Usage (Enumerated Entry Mode)

### Run an ISM Sweep

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

### Run the Analyzer

```bash
./scripts/rtlamr_scan_analyzer.py \
  --summary logs/ism_sweeps/<ts>/summary.txt \
  --core-count 2
```

Produces:

```text
core_freqs.json
radios.json
suggested_rtlamr_commands.txt
```

Analyzer artifacts remain co-located with the sweep that generated them.

---

## Core Scan Usage (Focused Observation)

Core scans may be run as downstream products of ISM analysis or as standalone scans using operator-declared frequency sets.

### Run a Core Scan

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

---

## Per-Radio Tracking

```bash
rtlamr -filterid=<ID> -format=json
```

Used for:

* Burst interval analysis
* Vendor behavior study
* Drift and channel movement tracking

---

## Troubleshooting

* `rtl_tcp` not running or unreachable
* Sample rate mismatch
* Gain set too low or too high
* RF noise or antenna placement issues

---

## Best Practices

* Use longer ISM sweeps for more accurate frequency ranking
* Re-run analysis periodically as RF environments change
* Inspect summaries and raw logs for recurring patterns
