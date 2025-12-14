# rtlamr Multi-Scan Suite

A modular sweep-and-analysis toolkit for **rtlamr** that enables full ISM-band discovery, adaptive frequency intelligence, and efficient multi-frequency monitoring across the 902–928 MHz ISM band.

The Multi-Scan Suite is designed for RF operators who want a **structured, repeatable, laboratory-grade workflow** for exploring AMR activity beyond default center frequencies.

---

## Why This Exists

AMR deployments rarely operate on a single “standard” center frequency.

Utilities distribute meters across the ISM band, and burst behavior varies significantly by geography, vendor, and meter type. A static tuning approach leaves activity undiscovered and patterns misunderstood.

This suite exposes that structure.

It adds missing layers around `rtlamr`:

* Wideband discovery of active AMR traffic
* Automated extraction of dominant center frequencies
* Focused, low-overhead multi-frequency monitoring
* Per-radio targeting guidance for deeper study

The result is an **actionable RF map**: a data-driven view of the AMR ecosystem where you operate.

---

## Operational Model

The suite separates **how frequencies are selected** from **how they are observed**.

ISM workflows enumerate frequencies from the environment through wideband discovery and analysis.
Direct scans use operator-declared frequencies without requiring a full ISM sweep.

Both approaches can be used for broad observation or precise per-radio targeting.

This design allows operators to move fluidly between discovery, monitoring, and focused study without changing tools or workflows.

---

## Features

### 1. Full ISM Sweep (902–928 MHz)

* Stepped sweep (default 300 kHz)
* Operator-defined dwell time
* Deterministic, timestamped session directories
* Raw JSONL logs with human-readable summaries

### 2. Adaptive Core Frequency Analyzer

* Reduces large sweep sets to the strongest centers
* Weighted by message density
* Produces `core_freqs.json`, `radios.json`, and targeting suggestions

### 3. Focused Multi-Frequency Core Scan

* Cycles only through selected center frequencies
* Significantly reduced CPU and noise load
* Suitable for long-term observation and per-radio analysis

### 4. Per-Radio Targeting

* Auto-generated `rtlamr` command suggestions
* Useful for studying burst timing, behavior, and drift

### 5. Flexible Band Window

* Adjustable ISM min/max range
* Adjustable step size and dwell time
* Supports both full-band and narrow-window operation

### 6. Structured Logging

* Timestamped run directories
* Raw decode logs and summaries
* Analyzer products co-located with their originating sweep

### 7. Dry-Run & Operator Safety Modes

* Validate parameters before committing to long scans
* Reduce risk during field experimentation

---

## Installation

### Requirements

* Linux (Debian recommended)
* Python 3.11+
* `rtlamr` binary (built locally or installed)
* `rtl_tcp` server (RTL-SDR dongle or compatible backend)
* Stable SDR gain configuration

### Clone and prepare

```bash
git clone https://github.com/<yourname>/rtlamr-multiscan.git
cd rtlamr-multiscan
```

---

## Directory Structure

```text
rtlamr/
├── scripts/
│   ├── rtlamr_multi_scan.py
│   └── rtlamr_scan_analyzer.py
├── config/
├── docs/
└── logs/              (ignored by git)
    ├── ism_sweeps/    # ISM discovery, analysis, and derived frequency artifacts
    └── core_scans/    # Standalone or downstream multi-frequency scan results
```

---

## Usage Examples

### 1. Full ISM Sweep

```bash
~/rtlamr/scripts/rtlamr_multi_scan.py \
    --ism-sweep \
    --ism-seconds-per-freq 40 \
    --rtlamr ~/rtlamr/bin/rtlamr \
    --server 127.0.0.1:1234
```

Produces:

```text
logs/ism_sweeps/<timestamp>/
├── raw.jsonl
└── summary.txt
```

---

### 2. Analyze Sweep Results

```bash
python3 ~/rtlamr/scripts/rtlamr_scan_analyzer.py \
    --summary /path/to/summary.txt \
    --core-count 2
```

Creates:

```text
core_freqs.json
radios.json
suggested_rtlamr_commands.txt
```

Analyzer artifacts remain co-located with the sweep that generated them.

---

### 3. Run a Focused Core Scan

```bash
~/rtlamr/scripts/rtlamr_multi_scan.py \
    --core-json ~/rtlamr/logs/ism_sweeps/<ts>/core_freqs.json \
    --seconds-per-freq 120 \
    --rtlamr ~/rtlamr/bin/rtlamr
```

Optimized for sustained monitoring with reduced overhead.

---

### 4. Track a Specific Meter

```bash
rtlamr -filterid=<ID> -format=json
```

Useful for:

* Burst interval analysis
* Vendor behavior study
* Drift and channel movement tracking
* Deployment density estimation

---

## Workflow Overview (ISM-Derived Example)

```text
[1] ISM Sweep   → Discover activity across 902–928 MHz
[2] Analyzer    → Reduce sweep to dominant centers
[3] Core Scan   → Monitor selected frequencies efficiently
[4] Targeting   → Study individual radios
```

This represents a common workflow, not a required one.

---

## Notes on SDR Configuration

This project assumes:

* Stable RF gain settings
* Operator awareness of noise-floor effects
* Environment-specific frequency behavior

AMR deployments vary widely.
This toolkit is built for **exploration**, not prediction.

---

## Acknowledgments

This project builds on the excellent work of **Ben Damman**, author of `rtlamr`.
His decoder opened the ISM band to operators everywhere.
This suite extends that work with structured workflows and frequency intelligence.

---

## Future Plans

* GUI dashboard (under active development; not yet released)
* Multi-radio behavior analysis
* Burst timing histograms and drift detection
* Long-term stability correlation
* Waterfall-based intelligence integration
* Optional Python package release

---

## License

Released under the **MIT License**.
Contributions welcome.
