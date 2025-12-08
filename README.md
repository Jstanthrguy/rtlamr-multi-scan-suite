# rtlamr-multi-scan-suite
A modular sweep-and-analysis toolkit for rtlamr that performs full ISM band scans, derives core center frequencies, and enables focused multi-frequency monitoring and per-radio targeting.
# rtlamr Multi-Scan Suite

A modular sweep-and-analysis toolkit that extends rtlamr with full-band ISM (902–928 MHz) scanning, core center-frequency extraction, focused multi-frequency monitoring, and per-radio targeting. Designed as a layered workflow for RF operators who want structured, repeatable, laboratory-grade AMR spectrum exploration.

---

## Why This Exists

Most AMR meter deployments do not sit neatly on the seven “standard” rtlamr frequencies.  
Utilities scatter transmissions across the ISM band, and signal behavior varies widely by region.

This project was built to reveal that structure.

The Multi-Scan Suite provides the missing layers around rtlamr:

- wideband discovery,
- automated frequency intelligence,
- adaptive core-band selection,
- and a focused monitor loop.

It turns raw ISM activity into an actionable RF map — and gives operators the tools to explore meters in their native environment.

---

## Features

- **Full ISM Sweep (902–928 MHz)**  
  300 kHz stepping, operator-defined dwell time, structured logs.

- **Adaptive Core Frequency Analyzer**  
  Extracts the strongest N center frequencies from any sweep.

- **Focused Multi-Frequency Core Scan**  
  Efficient looping over only the most active channels.

- **Per-Radio Targeting**  
  Auto-suggested rtlamr commands for individual meters.

- **Flexible Band Window**  
  Customizable ISM min/max, adjustable step size.

- **Structured Logging**  
  Timestamped run directories with raw JSONL + summaries.

- **Dry-Run & Sanity Check Modes**  
  For safe testing before long sweeps.

---

## Usage (Basic Examples)

**Run a wideband ISM sweep:**

~/rtlamr/scripts/rtlamr_multi_scan.py
--ism-sweep
--ism-seconds-per-freq 40
--rtlamr ~/rtlamr/bin/rtlamr
--server 127.0.0.1:1234

markdown
Copy code

**Analyze sweep results:**

python3 rtlamr_scan_analyzer.py
--summary /path/to/summary.txt
--core-count 2

css
Copy code

**Run a focused core scan:**

~/rtlamr/scripts/rtlamr_multi_scan.py
--core-json /path/to/core_freqs.json
--seconds-per-freq 120
--rtlamr ~/rtlamr/bin/rtlamr

css
Copy code

**Track a specific meter:**

rtlamr -filterid=<ID> -format=json

yaml
Copy code

---

## Full Workflow

1. **ISM Sweep**  
   Discover all active ISM centers in your region.

2. **Analyzer Phase**  
   Reduce 87 stepped frequencies → the strongest core set.

3. **Core Multi-Scan**  
   Efficient monitoring of only the important channels.

4. **rtlamr Targeting**  
   Track individual radio IDs, types, or behaviors.

---

## Acknowledgments

This project builds on the excellent work of the original **rtlamr** developer, Ben Damman.  
Without that foundation, none of this layered system would exist.  
His work opened the door for exploration — this suite walks through it.

---

## Future Plans

- GUI dashboard (Python + FastAPI + Web front end)
- Real-time multi-radio grouping and clustering
- Cross-scan correlation tools
- Auto-detected drift windows
- Integration with rtl_power for hybrid RF intelligence
- Additional analysis modules (behavior timelines, burst density, etc.)

---

## License

Released under the MIT License. Contributions welcome.
