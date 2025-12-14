# Quickstart — rtlamr Multi-Scan Suite

This Quickstart demonstrates a fast, reliable **ISM-derived entry mode** for the suite. It is an example workflow, not a requirement. Direct scans may skip steps 2–3.

---

## 1. Start rtl_tcp

```bash
rtl_tcp -a 0.0.0.0 -p 1234 -s 2359296 -g 44.5
```

---

## 2. Run an ISM Sweep (Enumerated Entry Mode)

```bash
./scripts/rtlamr_multi_scan.py \
  --ism-sweep \
  --ism-seconds-per-freq 30 \
  --rtlamr ~/rtlamr/bin/rtlamr
```

---

## 3. Analyze Results

```bash
./scripts/rtlamr_scan_analyzer.py \
  --summary logs/ism_sweeps/<ts>/summary.txt \
  --core-count 2
```

---

## 4. Run a Core Scan

```bash
./scripts/rtlamr_multi_scan.py \
  --core-json core_freqs.json \
  --seconds-per-freq 120
```

---

## 5. Track a Meter

```bash
rtlamr -filterid=<ID> -format=json
```
