# Architecture Overview — rtlamr Multi-Scan Suite

This document describes the architectural model of the rtlamr Multi-Scan Suite. It focuses on **structure and intent**, not usage mechanics.

The suite is organized around a shared scan engine, with clear separation between **frequency selection** and **observation intent**.

---

## 1. Entry Model

The Multi-Scan Suite operates with two explicit frequency-selection entry modes:

### Enumerated (ISM-derived)

Frequencies are discovered from the environment through wideband ISM scanning and analysis.

Flow:

```
ISM Sweep → Analyzer → Core frequency set
```

This mode is used when the operator wants to discover active AMR frequencies without prior assumptions.

---

### Declared (Operator-driven)

Frequencies are provided directly by the operator.

Sources may include:

* Prior knowledge
* Reuse of earlier results
* Narrow-band probing
* Manual experimentation

This mode does not require an ISM sweep.

---

Both entry modes feed the **same multi-frequency scan engine**. Once frequencies are selected, the system supports either:

* Broad observation across multiple channels
* Precise per-radio targeting

Frequency selection and observation intent are independent.

---

## 2. Sweep Engine

The sweep engine is responsible for wideband discovery across the ISM band.

Components:

* Frequency planner
* `rtlamr` process handler
* JSON decode parser
* Log writer

Outputs:

* Raw decode logs (`raw.jsonl`)
* Human-readable summaries (`summary.txt`)

Sweep sessions are timestamped and stored under `logs/ism_sweeps/`.

---

## 3. Analyzer

The analyzer processes completed ISM sweep sessions and derives actionable frequency intelligence.

Responsibilities:

* Parse sweep summaries
* Rank frequencies by message density
* Extract individual radio identifiers
* Generate suggested targeting commands

Outputs:

* `core_freqs.json`
* `radios.json`
* `suggested_rtlamr_commands.txt`

Analyzer products remain **co-located with the ISM sweep** that generated them.

---

## 4. Core Scan Engine

The core scan engine performs focused, repeated monitoring of selected frequencies.

Responsibilities:

* Iterate through provided frequency sets
* Invoke `rtlamr` on each frequency
* Record decode output

Core scans may be:

* Downstream products of ISM analysis
* Standalone scans using operator-declared frequencies

Results are stored as timestamped sessions under `logs/core_scans/`.

---

## 5. Logging Model

All runtime artifacts are written to timestamped session directories.

```
logs/
├── ism_sweeps/   # ISM discovery, analysis, and derived frequency artifacts
└── core_scans/   # Standalone or downstream multi-frequency scan results
```

Logging invariants:

* ISM-derived analyzer products remain with their originating sweep
* Core scans produce only their own raw logs and summaries
* No global or cross-session log directories are used

---

## 6. Philosophy

The suite is designed to be:

* **Deterministic** — explicit inputs produce repeatable results
* **Modular** — components are composable and reusable
* **Minimal** — few dependencies, transparent behavior

The architecture prioritizes clarity, operator control, and exploratory flexibility.
