# rtlamr-multi-scan-suite
A modular sweep-and-analysis toolkit for rtlamr that performs full ISM band scans, derives core center frequencies, and enables focused multi-frequency monitoring and per-radio targeting.
rtlamr Multi-Scan Suite

A layered sweep-and-analysis toolkit for AMR signal intelligence across the 902–928 MHz ISM band.

The Multi-Scan Suite extends rtlamr with a full-band ISM sweep engine, adaptive center-frequency extraction, a focused multi-channel scanning loop, and automated per-radio targeting tools.
It is designed for RF operators who want structured, repeatable, laboratory-grade AMR spectrum exploration.

Why This Exists

AMR deployments rarely sit on the “standard” rtlamr center frequencies.
Utilities spread devices across the ISM band, and burst patterns vary dramatically by geography, vendor, and meter type.

This suite exposes that structure.

It provides the missing layers around rtlamr:

Wideband discovery of all active AMR activity

Automated frequency intelligence extracted from real sweeps

Adaptive core-band selection based on message density

A focused monitor loop tuned to the strongest channels

Per-radio recommendations for direct rtlamr usage

The result is an actionable RF map: a repeatable, data-driven view into the AMR ecosystem where you live.

Features
1. Full ISM Sweep (902–928 MHz)

Stepped sweep (default 300 kHz)

Operator-defined dwell time

Consistent directory structure

Raw JSONL logs + text summaries

2. Adaptive Core Frequency Analyzer

Reduces 80–90 sweep frequencies → top N centers

Weighted selection by message density

Produces core_freqs.json, radios.json, and suggestions

3. Focused Multi-Frequency Core Scan

Cycles only through the important frequencies

Significantly lower CPU and noise load

Ideal for long-term observation and per-radio study

4. Per-Radio Targeting

Auto-suggested rtlamr commands for individual meters

Useful for studying behavior, burst timing, and drift

5. Flexible Band Window

Adjustable ISM min/max

Adjustable step size and dwell time

Supports “full sweep” or “narrow window” operation

6. Structured Logging

Timestamped run directories

Raw decode logs

Final summaries

Analyzer products (core frequencies, radio listings, suggestions)

7. Dry-Run & Operator Safety Modes

Allows validation before committing to long sweeps or multi-hour scans

Installation
Requirements

Linux (Debian recommended)

Python 3.11+

rtlamr binary (built locally or installed)

rtl_tcp server (RTL-SDR dongle), or any backend supported by rtlamr

A stable SDR gain configuration

Clone and prepare:

git clone https://github.com/<yourname>/rtlamr-multiscan.git
cd rtlamr-multiscan


Directory structure:

rtlamr/
├── scripts/
│   ├── rtlamr_multi_scan.py
│   └── rtlamr_scan_analyzer.py
├── config/
├── docs/
└── logs/   (ignored by git)

Usage Examples
1. Full ISM Sweep
~/rtlamr/scripts/rtlamr_multi_scan.py \
    --ism-sweep \
    --ism-seconds-per-freq 40 \
    --rtlamr ~/rtlamr/bin/rtlamr \
    --server 127.0.0.1:1234


This produces a timestamped directory under:

logs/ism_sweeps/<timestamp>/
    raw.jsonl
    summary.txt

2. Analyze Sweep Results
python3 ~/rtlamr/scripts/rtlamr_scan_analyzer.py \
    --summary /path/to/summary.txt \
    --core-count 2


Creates:

core_freqs.json
radios.json
suggested_rtlamr_commands.txt

3. Run a Focused Core Scan
~/rtlamr/scripts/rtlamr_multi_scan.py \
    --core-json ~/rtlamr/logs/ism_sweeps/<ts>/core_freqs.json \
    --seconds-per-freq 120 \
    --rtlamr ~/rtlamr/bin/rtlamr


Optimized for long-term monitoring.

4. Track a Specific Meter
rtlamr -filterid=<ID> -format=json


Ideal for:

analyzing burst intervals

understanding meter vendor IDs

tracking drift or channel movement

density estimation for deployment mapping

Workflow Overview
[1] ISM Sweep  →  Discover activity across 902–928 MHz
[2] Analyzer    →  Reduce full sweep → N strongest centers
[3] Core Scan   →  Monitor those centers efficiently
[4] Targeting   →  Study chosen radios using suggested commands


This tiered flow transforms raw RF activity into structured intelligence.

Directory Layout
rtlamr/
├── scripts/
│   ├── rtlamr_multi_scan.py
│   └── rtlamr_scan_analyzer.py
├── config/
├── docs/
├── logs/              (ignored)
│   ├── ism_sweeps/
│   ├── core_scans/
│   ├── raw/
│   └── summaries/
└── state/             (ignored)

Sample Output Structure

After a sweep:

logs/ism_sweeps/scan_20251207_155024/
│
├── raw.jsonl
├── summary.txt
├── core_freqs.json
├── radios.json
└── suggested_rtlamr_commands.txt


After a core scan:

logs/core_scans/scan_<timestamp>/
│
├── raw.jsonl
└── summary.txt

Notes on SDR Configuration

This project assumes:

stable RF gain settings

the operator understands noise floor effects

center-frequency selection may vary by location

rtlamr must be able to decode on the chosen hardware

All real-world AMR deployments behave differently.
This toolkit is built for exploration — not prediction.

Acknowledgments

This project builds on the excellent work of Ben Damman, the original author of rtlamr.
His decoder opened the ISM band to operators everywhere.
This suite extends that exploration with workflow structure and real-time intelligence.

Future Plans

GUI dashboard (FastAPI + Web front end)

Cluster analysis for multi-radio behavior

Burst timing histograms & drift detection

Correlation between sweeps and long-term stability

Hybrid integration with rtl_power waterfall intelligence

Optional Python package release

## License

Released under the MIT License.
Contributions welcome.
