#!/usr/bin/env python3
"""
rtlamr_multi_scan.py

Multi-frequency scanner/aggregator around rtlamr.

Features
--------
- Core scan mode using a small set of known R900 center frequencies.
- ISM band sweep mode over 902–928 MHz in 300 kHz steps (configurable).
- Per-frequency dwell times (core and ISM can be different).
- Live, human-readable feedback in the terminal for each frequency:
    - Shows how many messages and how many radios were seen.
    - Shows which message types were decoded on that frequency.
- Logging to a run-specific directory:
    - Raw JSON lines from rtlamr.
    - A summary text file with:
        * Per-radio table like:
              Total  Freqs   ID         Type      CenterFreqs (MHz)
              -----  -----   ---------- --------  -----------------
                 49      7   1571038152 R900      911.500, 912.380, ...
        * Strongest center frequencies table.
        * Suggested rtlamr command for the strongest meter.
- Optional message-type selection via --msgtype:
    - Defaults to "all" (rtlamr -msgtype=all, no internal filter).
    - Accepts comma lists like "scm,idm,r900" and filters internally.
- Core frequency source selection:
    - Default core bandplan from default_core_freqs_mhz().
    - Optional --freqs overrides with a comma-separated MHz list.
    - Optional --core-json loads core freqs from core_freqs.json
      produced by rtlamr_scan_analyzer.py and overrides both.
- ISM sweep window selection:
    - Defaults: 902–928 MHz at 300 kHz steps.
    - Optional --ism-min-mhz / --ism-max-mhz to crop the window.
    - Optional --ism-step-khz to change stepping granularity.
"""

import argparse
import collections
import datetime
import json
import os
import subprocess
import sys
import threading
from typing import Dict, List, Optional, Tuple, Set

RadioStats = Dict[str, object]  # id, type, count, freqs (Counter[float -> int])


def default_core_freqs_mhz() -> List[float]:
    """Return the default 'core' R900 center frequencies in MHz."""
    return [
        910.200,
        911.500,
        912.380,
        914.000,
        915.500,
        916.600,
        918.000,
    ]


def build_ism_freqs_mhz(
    min_mhz: float = 902.0,
    max_mhz: float = 928.0,
    step_khz: float = 300.0,
) -> List[float]:
    """
    Build an ISM bandplan from min_mhz to max_mhz in 'step_khz' steps.

    Defaults correspond to the FCC 902–928 MHz ISM allocation at 300 kHz steps.
    """
    if step_khz <= 0:
        raise ValueError("step_khz must be > 0")

    step_mhz = step_khz / 1000.0
    freqs: List[float] = []
    f = min_mhz
    # Use a small epsilon to avoid rounding issues.
    while f <= max_mhz + 1e-9:
        freqs.append(round(f, 3))
        f += step_mhz
    return freqs


def ensure_log_dir(path: str) -> str:
    """Expand ~ and create log dir if needed, returning the absolute path."""
    path = os.path.expanduser(path)
    os.makedirs(path, exist_ok=True)
    return path


def compute_msgtype_config(raw_arg: str) -> Tuple[str, Optional[Set[str]]]:
    """
    Normalize the --msgtype argument for rtlamr and internal filtering.

    Returns:
        (msgtype_arg, accepted_msgtypes)

    msgtype_arg:
        String passed directly to rtlamr as -msgtype=...

    accepted_msgtypes:
        A set of allowed Type strings (e.g., {"SCM","IDM"}) for internal
        filtering, or None to accept all types.
    """
    if not raw_arg:
        return "all", None

    val = raw_arg.strip().lower()
    if val == "all":
        # Default behavior: rtlamr sees -msgtype=all; we do no extra filtering.
        return "all", None

    # Allow comma-separated lists, e.g. "scm,idm,r900"
    parts = [p.strip() for p in raw_arg.split(",") if p.strip()]
    if not parts:
        return "all", None

    # Internal comparison is case-insensitive; normalize to upper.
    accepted = {p.upper() for p in parts}
    # For rtlamr we pass through the tokens (minus whitespace).
    msgtype_arg = ",".join(parts)
    return msgtype_arg, accepted


def format_cmd_for_print(cmd: List[str]) -> str:
    """Short pretty-printer for a shell command line."""
    return " ".join(cmd)


def format_hms(total_seconds: float) -> str:
    """Format seconds as H:MM:SS."""
    total_seconds = int(total_seconds)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:d}:{m:02d}:{s:02d}"


def read_stderr(proc: subprocess.Popen, prefix: str = "[rtlamr stderr]") -> None:
    """
    Read stderr from rtlamr, but ONLY print real errors.
    Filters out normal startup noise such as decode.go:45 CenterFreq etc.
    """
    if proc.stderr is None:
        return

    ERROR_KEYWORDS = [
        "ERROR",
        "error",
        "failed",
        "panic",
        "fatal",
        "invalid",
        "could not",
        "overflow",
        "timeout",
        "unavailable",
    ]

    for line in proc.stderr:
        s = line.strip()
        if not s:
            continue

        # Check if this line contains an actual error keyword.
        low = s.lower()
        is_error = any(k in low for k in ERROR_KEYWORDS)

        if is_error:
            print(f"{prefix} {s}")
            sys.stdout.flush()


def run_rtlamr_for_freq(
    rtlamr_path: str,
    server: str,
    samplerate: int,
    center_freq_mhz: float,
    seconds: int,
    raw_log_fp,
    radios: Dict[int, RadioStats],
    center_totals: Dict[float, int],
    type_totals: Dict[str, int],
    msgtype_arg: str,
    accepted_msgtypes: Optional[Set[str]] = None,
    echo_hits: bool = False,
    print_cmd: bool = True,
) -> Tuple[int, int, Set[str]]:
    """
    Run rtlamr once for a single center frequency, aggregating stats.

    Returns:
        (num_messages, num_radios, types_seen)
    """
    center_hz = int(round(center_freq_mhz * 1e6))
    cmd = [
        rtlamr_path,
        f"-server={server}",
        f"-samplerate={samplerate}",
        f"-centerfreq={center_hz}",
        f"-msgtype={msgtype_arg}",
        "-format=json",
        "-unique=false",
        f"-duration={seconds}s",
    ]

    print(f"[*] Scanning {center_freq_mhz:.6f} MHz for {seconds} seconds...")
    # Command line print intentionally suppressed to avoid clutter:
    # if print_cmd:
    #     print("    " + format_cmd_for_print(cmd))

    # Start rtlamr process.
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    # Start background thread to echo stderr as it arrives.
    t_err = threading.Thread(target=read_stderr, args=(proc,), daemon=True)
    t_err.start()

    # Local per-frequency stats.
    num_messages = 0
    local_radios: Set[int] = set()
    types_seen: Set[str] = set()

    # Track length of last status line so we can overwrite cleanly.
    last_status_len = 0

    # JSON parse and aggregation loop.
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue

            # Mirror raw JSON to the log file.
            raw_log_fp.write(line + "\n")

            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                # Ignore non-JSON lines on stdout (should be rare).
                continue

            # rtlamr plaintext format can vary; we defensively extract fields.
            msg_type = str(msg.get("Type", "UNKNOWN")).upper()
            meter = msg.get("Message", msg)
            meter_id = meter.get("ID")

            if meter_id is None:
                continue

            # Apply internal filter if set.
            if accepted_msgtypes is not None and msg_type not in accepted_msgtypes:
                continue

            meter_id_int = int(meter_id)

            num_messages += 1
            local_radios.add(meter_id_int)
            types_seen.add(msg_type)

            # Global radio stats.
            if meter_id_int not in radios:
                radios[meter_id_int] = {
                    "id": meter_id_int,
                    "type": msg_type,
                    "count": 0,
                    "freqs": collections.Counter(),  # center_freq_mhz -> count
                }

            rstats = radios[meter_id_int]
            rstats["count"] = int(rstats["count"]) + 1
            rstats["type"] = msg_type
            rstats["freqs"][center_freq_mhz] += 1

            center_totals[center_freq_mhz] += 1
            type_totals[msg_type] += 1

            # Live status: single updating line instead of appending lines.
            if echo_hits:
                type_list = ", ".join(sorted(types_seen))
                status = (
                    f"    [{num_messages} msgs, {len(local_radios)} radios, "
                    f"types: {type_list}]"
                )
                # Pad with spaces if the new line is shorter than the previous,
                # so remnants don't linger.
                pad = ""
                if last_status_len > len(status):
                    pad = " " * (last_status_len - len(status))
                print("\r" + status + pad, end="", flush=True)
                last_status_len = len(status)

    except KeyboardInterrupt:
        print("\n[!] KeyboardInterrupt received; stopping current rtlamr instance...")
        proc.terminate()
        # Propagate the interrupt so the outer loop / main can exit
        raise
    finally:
        # Ensure the process exits.
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    # Finish the status line cleanly before printing the summary arrow.
    if echo_hits and num_messages > 0:
        print()  # move to next line

    # Live per-frequency summary line.
    if num_messages == 0:
        print("    -> no messages decoded on this frequency.")
    else:
        type_list = ", ".join(sorted(types_seen))
        print(
            f"    -> {num_messages} messages from {len(local_radios)} radios "
            f"(types: {type_list})"
        )

    sys.stdout.flush()
    return num_messages, len(local_radios), types_seen


def write_summary_table(
    summary_path: str,
    radios: Dict[int, RadioStats],
    center_totals: Dict[float, int],
    type_totals: Dict[str, int],
) -> None:
    """Write a human-readable text summary table."""
    # Sort radios by descending total count.
    sorted_radios = sorted(
        radios.values(),
        key=lambda r: int(r.get("count", 0)),
        reverse=True,
    )

    # Sort center freqs by total messages.
    sorted_centers = sorted(
        center_totals.items(),
        key=lambda kv: kv[1],
        reverse=True,
    )

    # Determine "strongest" meter for suggested command.
    suggested_id = None
    if sorted_radios:
        strongest = sorted_radios[0]
        suggested_id = strongest["id"]

    with open(summary_path, "w") as f:
        f.write("=== Per-Radio Summary ===\n")
        f.write("Total   Freqs   ID         Type      CenterFreqs (MHz)\n")
        f.write("-----   -----   ---------- --------  ------------------\n")

        for r in sorted_radios:
            total = int(r.get("count", 0))
            freqs_counter = r.get("freqs", {})
            unique_freqs = len(freqs_counter)
            rid = r.get("id", 0)
            rtype = r.get("type", "UNKNOWN")

            # Format the frequency list nicely.
            freq_list = sorted(freqs_counter.keys())
            freq_str = ", ".join(f"{fq:.3f}" for fq in freq_list)

            f.write(
                f"{total:5d}   {unique_freqs:5d}   {rid:10d} {rtype:<8s}  {freq_str}\n"
            )

        f.write("\n=== Strongest Center Frequencies (by total messages) ===\n")
        f.write("Total   CenterFreq (MHz)\n")
        f.write("-----   ----------------\n")
        for cfreq, total in sorted_centers:
            f.write(f"{total:5d}   {cfreq:0.6f}\n")

        f.write("\n=== Message Types Totals ===\n")
        f.write("Type     Total\n")
        f.write("-------- -----\n")
        for t, total in sorted(type_totals.items(), key=lambda kv: kv[1], reverse=True):
            f.write(f"{t:<8s} {total:5d}\n")

        if suggested_id is not None:
            f.write("\n[*] Suggested rtlamr command to track strongest meter:\n\n")
            f.write(f"    rtlamr -filterid={suggested_id} -format=json\n")


def print_summary_to_stdout(summary_path: str) -> None:
    """Echo the human-readable summary file back to the terminal."""
    print("\n=== Summary for this cycle (screen copy) ===\n")
    try:
        with open(summary_path, "r") as f:
            for line in f:
                print(line.rstrip())
    except Exception as e:
        print(f"[!] Could not read summary file {summary_path}: {e}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-frequency rtlamr scanner with logging and ISM band sweep.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--rtlamr",
        required=True,
        help="Path to rtlamr binary.",
    )
    parser.add_argument(
        "--server",
        default="127.0.0.1:1234",
        help="rtl_tcp server (host:port).",
    )
    parser.add_argument(
        "--samplerate",
        type=int,
        default=2359296,
        help="rtlamr samplerate.",
    )

    # Core scan options.
    parser.add_argument(
        "--seconds-per-freq",
        type=int,
        default=120,
        help="Dwell time per core frequency (seconds).",
    )
    parser.add_argument(
        "--freqs",
        type=str,
        default="",
        help=(
            "Comma-separated list of core center freqs in MHz "
            "(overrides the default core bandplan when given)."
        ),
    )
    parser.add_argument(
        "--core-json",
        type=str,
        default="",
        help=(
            "Path to core_freqs.json produced by rtlamr_scan_analyzer.py. "
            "If provided, core frequencies will be loaded from this file and "
            "override both the default bandplan and --freqs."
        ),
    )

    # ISM sweep options.
    parser.add_argument(
        "--ism-sweep",
        action="store_true",
        help="Enable full ISM band sweep.",
    )
    parser.add_argument(
        "--ism-seconds-per-freq",
        type=int,
        default=30,
        help="Dwell time per ISM sweep frequency (seconds).",
    )
    parser.add_argument(
        "--ism-min-mhz",
        type=float,
        default=902.0,
        help="Lower edge of ISM sweep in MHz (default 902.0).",
    )
    parser.add_argument(
        "--ism-max-mhz",
        type=float,
        default=928.0,
        help="Upper edge of ISM sweep in MHz (default 928.0).",
    )
    parser.add_argument(
        "--ism-step-khz",
        type=float,
        default=300.0,
        help="ISM sweep step size in kHz (default 300.0).",
    )

    parser.add_argument(
        "--log-dir",
        default="~/rtlamr_logs",
        help="Directory for run logs.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run only a single cycle (core or ISM) then exit.",
    )

    parser.add_argument(
        "--sanity-check",
        action="store_true",
        help="Pause after showing configuration/ETA and ask for [Y/n] before running.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show configuration and ETA, then exit without running a scan.",
    )

    # msgtype option
    parser.add_argument(
        "--msgtype",
        default="all",
        help=(
            "Value for rtlamr -msgtype (e.g. all, scm, idm, net, r900, r900bcd, "
            "or a comma-separated list like 'scm,idm'). Defaults to 'all'."
        ),
    )

    return parser.parse_args(argv)


def parse_freq_list(freq_str: str) -> List[float]:
    """Parse a comma-separated list of MHz frequencies."""
    parts = [p.strip() for p in freq_str.split(",") if p.strip()]
    freqs: List[float] = []
    for p in parts:
        try:
            freqs.append(float(p))
        except ValueError:
            print(f"[!] Warning: could not parse freq '{p}', ignoring.")
    return freqs


def load_core_freqs_from_json(path: str) -> List[float]:
    """
    Load core frequencies from a core_freqs.json file produced by
    rtlamr_scan_analyzer.py.

    Expected structure (simplified):

        {
          "core_freqs": [
            { "rank": 1, "freq_mhz": 911.6, ... },
            { "rank": 2, "freq_mhz": 912.2, ... }
          ],
          ...
        }
    """
    path_expanded = os.path.expanduser(path)
    try:
        with open(path_expanded, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[!] Failed to read core freqs JSON '{path_expanded}': {e}", file=sys.stderr)
        sys.exit(1)

    core_entries = data.get("core_freqs", [])
    freqs_mhz: List[float] = []
    for entry in core_entries:
        try:
            freqs_mhz.append(float(entry["freq_mhz"]))
        except Exception:
            continue

    if not freqs_mhz:
        print(f"[!] No usable core frequencies found in '{path_expanded}'.", file=sys.stderr)
        sys.exit(1)

    print("[*] Loaded core freqs from JSON:")
    for f_mhz in freqs_mhz:
        print(f"    - {f_mhz:.3f} MHz")
    return freqs_mhz


def resolve_core_freqs_mhz(args: argparse.Namespace) -> List[float]:
    """
    Decide which core frequencies to use, in this priority order:

        1) --core-json (core_freqs.json from analyzer)
        2) --freqs (manual comma-separated list)
        3) default_core_freqs_mhz()
    """
    # Highest priority: JSON from analyzer
    if args.core_json:
        return load_core_freqs_from_json(args.core_json)

    # Next: manual comma-separated list
    if args.freqs:
        freqs = parse_freq_list(args.freqs)
        if freqs:
            print("[*] Using custom core freqs from --freqs:")
            for f_mhz in freqs:
                print(f"    - {f_mhz:.3f} MHz")
            return freqs
        else:
            print("[!] No valid freqs parsed from --freqs; falling back to defaults.")

    # Fallback: built-in defaults
    core_freqs = default_core_freqs_mhz()
    print("[*] Using built-in default core freqs:")
    for f_mhz in core_freqs:
        print(f"    - {f_mhz:.3f} MHz")
    return core_freqs


def run_cycle(
    rtlamr_path: str,
    server: str,
    samplerate: int,
    core_freqs: List[float],
    core_seconds_per_freq: int,
    ism_sweep: bool,
    ism_seconds_per_freq: int,
    ism_min_mhz: float,
    ism_max_mhz: float,
    ism_step_khz: float,
    log_dir: str,
    msgtype_arg: str,
    accepted_msgtypes: Optional[Set[str]],
) -> None:
    """
    Run either a core scan or an ISM sweep once, with logging and live feedback.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(log_dir, f"scan_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    raw_path = os.path.join(run_dir, "raw.jsonl")
    summary_path = os.path.join(run_dir, "summary.txt")

    print(f"[*] Logging enabled; run directory: {run_dir}")
    print(f"[*] rtlamr msgtype argument: {msgtype_arg}")
    if accepted_msgtypes is None:
        print("[*] Internal message filter: ALL types")
    else:
        print(f"[*] Internal message filter set: {sorted(accepted_msgtypes)}")

    # Timing: cycle start
    cycle_start = datetime.datetime.now()

    radios: Dict[int, RadioStats] = {}
    center_totals: Dict[float, int] = collections.defaultdict(int)
    type_totals: Dict[str, int] = collections.defaultdict(int)

    with open(raw_path, "w") as raw_fp:
        if ism_sweep:
            ism_freqs = build_ism_freqs_mhz(
                min_mhz=ism_min_mhz,
                max_mhz=ism_max_mhz,
                step_khz=ism_step_khz,
            )
            print(
                f"[*] ISM sweep enabled: {len(ism_freqs)} freqs from "
                f"{ism_freqs[0]:.3f} to {ism_freqs[-1]:.3f} MHz "
                f"in {ism_step_khz:.1f} kHz steps."
            )
            print(f"[*] ISM sweep seconds per frequency: {ism_seconds_per_freq}")
            for idx, freq in enumerate(ism_freqs, start=1):
                print(f"\n=== [ISM] Frequency {idx}/{len(ism_freqs)}: {freq:.6f} MHz ===")

                # Time status for ISM sweep
                now = datetime.datetime.now()
                elapsed = (now - cycle_start).total_seconds()
                remaining_blocks = len(ism_freqs) - idx + 1
                remaining = remaining_blocks * ism_seconds_per_freq
                eta = now + datetime.timedelta(seconds=remaining)
                print(
                    f"[Time] Elapsed: {format_hms(elapsed)}  |  "
                    f"Remaining: {format_hms(remaining)}  |  "
                    f"ETA: {eta.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                run_rtlamr_for_freq(
                    rtlamr_path=rtlamr_path,
                    server=server,
                    samplerate=samplerate,
                    center_freq_mhz=freq,
                    seconds=ism_seconds_per_freq,
                    raw_log_fp=raw_fp,
                    radios=radios,
                    center_totals=center_totals,
                    type_totals=type_totals,
                    msgtype_arg=msgtype_arg,
                    accepted_msgtypes=accepted_msgtypes,
                    echo_hits=False,
                    print_cmd=(idx == 1),
                )
        else:
            print("[*] Core scan enabled.")
            print(
                f"[*] Core frequencies: "
                + ", ".join(f"{f:.6f} MHz" for f in core_freqs)
            )
            print(f"[*] Core seconds per frequency: {core_seconds_per_freq}")
            for idx, freq in enumerate(core_freqs, start=1):
                print(f"\n=== [CORE] Frequency {idx}/{len(core_freqs)}: {freq:.6f} MHz ===")

                # Time status for core scan
                now = datetime.datetime.now()
                elapsed = (now - cycle_start).total_seconds()
                remaining_blocks = len(core_freqs) - idx + 1
                remaining = remaining_blocks * core_seconds_per_freq
                eta = now + datetime.timedelta(seconds=remaining)
                print(
                    f"[Time] Elapsed: {format_hms(elapsed)}  |  "
                    f"Remaining: {format_hms(remaining)}  |  "
                    f"ETA: {eta.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                run_rtlamr_for_freq(
                    rtlamr_path=rtlamr_path,
                    server=server,
                    samplerate=samplerate,
                    center_freq_mhz=freq,
                    seconds=core_seconds_per_freq,
                    raw_log_fp=raw_fp,
                    radios=radios,
                    center_totals=center_totals,
                    type_totals=type_totals,
                    msgtype_arg=msgtype_arg,
                    accepted_msgtypes=accepted_msgtypes,
                    echo_hits=True,   # rolling counters, single updating line
                    print_cmd=(idx == 1),
                )

    # After the sweep, write summary.
    write_summary_table(
        summary_path=summary_path,
        radios=radios,
        center_totals=center_totals,
        type_totals=type_totals,
    )

    # For core scans, also show the full summary on screen (including suggestion).
    if not ism_sweep:
        print_summary_to_stdout(summary_path)

    print("\n[*] Cycle complete.")
    print(f"    Raw JSON log:     {raw_path}")
    print(f"    Summary text log: {summary_path}")


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    log_dir = ensure_log_dir(args.log_dir)

    # Determine which frequencies to use for core mode (JSON > freqs > default).
    core_freqs = resolve_core_freqs_mhz(args)

    # Clamp ISM dwell time into a reasonable window for exploration.
    if args.ism_seconds_per_freq < 5:
        print(
            f"[!] --ism-seconds-per-freq={args.ism_seconds_per_freq} too low; "
            f"clamping to 5s."
        )
        ism_seconds_per_freq = 5
    elif args.ism_seconds_per_freq > 120:
        print(
            f"[!] --ism-seconds-per-freq={args.ism_seconds_per_freq} too high; "
            f"clamping to 120s."
        )
        ism_seconds_per_freq = 120
    else:
        ism_seconds_per_freq = args.ism_seconds_per_freq

    # Interpret --msgtype into (rtlamr argument, internal filter set).
    msgtype_arg, accepted_msgtypes = compute_msgtype_config(args.msgtype)

    # ISM window sanity.
    ism_min_mhz = args.ism_min_mhz
    ism_max_mhz = args.ism_max_mhz
    ism_step_khz = args.ism_step_khz

    if ism_min_mhz >= ism_max_mhz:
        print(
            f"[!] Invalid ISM window: ism-min-mhz={ism_min_mhz} >= ism-max-mhz={ism_max_mhz}",
            file=sys.stderr,
        )
        sys.exit(1)

    if ism_step_khz <= 0:
        print(
            f"[!] Invalid --ism-step-khz={ism_step_khz}; resetting to 300.0 kHz.",
            file=sys.stderr,
        )
        ism_step_khz = 300.0

    print("[*] Starting rtlamr multi-frequency scanner.")
    print("[*] Ensure rtl_tcp is running on the server, e.g.:")
    print("    rtl_tcp -a 0.0.0.0 -g 7.7 -s 2359296")
    print(f"[*] Using remote rtl_tcp server: {args.server}")
    print(f"[*] rtlamr samplerate: {args.samplerate}")
    print(f"[*] Using rtlamr binary: {args.rtlamr}")
    print(f"[*] Logging directory: {log_dir}")
    print(f"[*] rtlamr msgtype: {msgtype_arg}")
    if args.ism_sweep:
        print("[*] ISM sweep enabled.")
        print(
            f"[*] ISM window: {ism_min_mhz:.3f}–{ism_max_mhz:.3f} MHz "
            f"@ {ism_step_khz:.1f} kHz steps"
        )
    else:
        print("[*] ISM sweep disabled; using core bandplan only.")

    # Pre-flight cycle duration / ETA estimate (best-effort)
    now = datetime.datetime.now()

    if args.ism_sweep:
        ism_freqs_preview = build_ism_freqs_mhz(
            min_mhz=ism_min_mhz,
            max_mhz=ism_max_mhz,
            step_khz=ism_step_khz,
        )
        total_secs = len(ism_freqs_preview) * ism_seconds_per_freq
        eta = now + datetime.timedelta(seconds=total_secs)
        print(
            f"[*] Estimated ISM cycle: {format_hms(total_secs)} "
            f"({len(ism_freqs_preview)} freqs × {ism_seconds_per_freq}s)"
        )
        print(f"[*] If started now, finish around: {eta.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        total_secs = len(core_freqs) * args.seconds_per_freq
        eta = now + datetime.timedelta(seconds=total_secs)
        print(
            f"[*] Estimated core cycle: {format_hms(total_secs)} "
            f"({len(core_freqs)} freqs × {args.seconds_per_freq}s)"
        )
        print(f"[*] If started now, finish around: {eta.strftime('%Y-%m-%d %H:%M:%S')}")

    # Dry-run: show config/ETA and exit without scanning
    if args.dry_run:
        print("[*] Dry run requested; no scan will be started.")
        return

    # Optional sanity-check / confirmation gate
    if args.sanity_check:
        try:
            resp = input("[?] Proceed with scan? [Y/n]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[!] Scan aborted before start.")
            return

        if resp and resp[0] in ("n", "N"):
            print("[*] Scan cancelled by user before start.")
            return

    try:
        while True:
            run_cycle(
                rtlamr_path=args.rtlamr,
                server=args.server,
                samplerate=args.samplerate,
                core_freqs=core_freqs,
                core_seconds_per_freq=args.seconds_per_freq,
                ism_sweep=args.ism_sweep,
                ism_seconds_per_freq=ism_seconds_per_freq,
                ism_min_mhz=ism_min_mhz,
                ism_max_mhz=ism_max_mhz,
                ism_step_khz=ism_step_khz,
                log_dir=log_dir,
                msgtype_arg=msgtype_arg,
                accepted_msgtypes=accepted_msgtypes,
            )
            if args.once:
                break
    except KeyboardInterrupt:
        print("\n[!] KeyboardInterrupt received; exiting.")


if __name__ == "__main__":
    main()
