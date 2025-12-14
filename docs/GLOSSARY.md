# Glossary — rtlamr Multi-Scan Suite

This glossary defines shared terminology exactly as used by the suite. Definitions are precise and neutral, and do not prescribe workflow or intent.

---

**AMR** — Automated Meter Reading; RF-based systems used by utilities to transmit meter data.

**ISM Band** — The 902–928 MHz Industrial, Scientific, and Medical band used by many AMR systems in North America.

**SCM / SCM+** — Standard Consumption Message formats used by AMR meters for periodic consumption reporting.

**IDM** — Interval Data Message; AMR message format carrying interval-based usage data.

**R900** — A family of AMR protocols and devices operating in the 900 MHz ISM band.

**Burst** — A short-duration RF transmission emitted by an AMR device.

**Center Frequency** — A tuned observation frequency around which AMR activity is monitored; may be discovered from the environment or provided by the operator.

**Dwell Time** — The duration spent listening on a given center frequency during a scan.

**JSONL** — A file format where each line contains a single JSON object.

**Summary File** — A human-readable aggregation of observed activity for a scan session.

**rtl_tcp** — A network-accessible SDR backend used to stream IQ samples from an SDR device.

**Raw Scan** — Unfiltered `rtlamr` decode output recorded during a scan session.

**Core Frequency** — A center frequency selected for focused observation, either derived from analysis or declared by the ope
