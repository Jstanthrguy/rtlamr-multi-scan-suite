#!/usr/bin/env python3
"""rtlamr_scan_analyzer.py

Companion analyzer for rtlamr_multi_scan.py ISM sweeps.

It parses a summary.txt file produced by the scanner, derives:
  * Per-radio stats
  * Strongest center frequencies (core candidates)
and emits three helper files in the same directory:

  core_freqs.json
  radios.json
  suggested_rtlamr_commands.txt

Usage (typical):

  python3 rtlamr_scan_analyzer.py --summary /home/james/rtlamr_logs/2025....../summary.txt --core-count 2

If --summary is omitted, the script will look for the newest summary.txt
under --log-dir (default: ~/rtlamr_logs).
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def debug(msg: str) -> None:
    """Lightweight debug print; can be toggled off if needed."""
    # print(f"[DEBUG] {msg}")
    pass


class Radio:
    """Container for per-radio metrics parsed from summary.txt."""

    __slots__ = (
        "id",
        "type",
        "total_messages",
        "freqs_count",
        "center_freqs_mhz",
        "assigned_core_freq_mhz",
    )

    def __init__(
        self,
        id_: str,
        type_: str,
        total_messages: int,
        freqs_count: int,
        center_freqs_mhz: List[float],
    ) -> None:
        self.id: str = id_
        self.type: str = type_
        self.total_messages: int = total_messages
        self.freqs_count: int = freqs_count
        self.center_freqs_mhz: List[float] = center_freqs_mhz
        self.assigned_core_freq_mhz: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "total_messages": self.total_messages,
            "freqs_count": self.freqs_count,
            "center_freqs_mhz": self.center_freqs_mhz,
            "assigned_core_freq_mhz": self.assigned_core_freq_mhz,
        }


def parse_summary(summary_path: Path) -> Tuple[Dict[str, Radio], Dict[float, int]]:
    """Parse the summary.txt produced by rtlamr_multi_scan.py.

    Returns:
      radios: mapping from radio ID -> Radio
      freq_totals: mapping from center frequency (MHz) -> total message count
    """
    text = summary_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    radios: Dict[str, Radio] = {}
    freq_totals: Dict[float, int] = {}

    section: Optional[str] = None

    for raw_line in lines:
        line = raw_line.rstrip("\n")

        # Detect section boundaries
        if line.strip().startswith("=== Per-Radio Summary"):
            section = "per_radio"
            debug("Entering per_radio section")
            continue
        if line.strip().startswith("=== Strongest Center Frequencies"):
            section = "freq_totals"
            debug("Entering freq_totals section")
            continue
        if (
            line.startswith("===")
            and not line.strip().startswith("=== Per-Radio")
            and not line.strip().startswith("=== Strongest Center")
        ):
            # Any other === header ends our sections of interest
            section = None

        if not section:
            continue

        # Skip headers and separator lines
        if not line.strip():
            continue
        if line.strip().startswith("Total") or set(line.strip()) == {"-"}:
            continue

        if section == "per_radio":
            # Expected format (variable whitespace):
            # Total   Freqs   ID         Type      CenterFreqs (MHz)
            #   49       7   1571038152 R900      911.500, 912.380, ...
            parts = line.split()
            if len(parts) < 5:
                continue

            try:
                total_messages = int(parts[0])
                freqs_count = int(parts[1])
            except ValueError:
                # Not a data row; ignore
                continue

            radio_id = parts[2]
            radio_type = parts[3]
            # Everything after the 4th token is the CenterFreqs column
            freqs_str = " ".join(parts[4:])
            # freqs_str is typically a comma-separated list:
            # "911.500, 912.380, 915.500, 916.600, 918.000"
            center_freqs_mhz: List[float] = []
            for chunk in freqs_str.split(','):
                chunk = chunk.strip()
                if not chunk:
                    continue
                try:
                    center_freqs_mhz.append(float(chunk))
                except ValueError:
                    # Ignore anything that doesn't parse as float
                    continue

            radios[radio_id] = Radio(
                id_=radio_id,
                type_=radio_type,
                total_messages=total_messages,
                freqs_count=freqs_count,
                center_freqs_mhz=center_freqs_mhz,
            )

        elif section == "freq_totals":
            # Expected format:
            # Total   CenterFreq (MHz)
            #   32   916.600000
            parts = line.split()
            if len(parts) != 2:
                continue
            try:
                total = int(parts[0])
                freq = float(parts[1])
            except ValueError:
                continue
            freq_totals[freq] = total

    if not radios:
        raise RuntimeError(f"No per-radio data parsed from {summary_path}")
    if not freq_totals:
        raise RuntimeError(f"No center-frequency totals parsed from {summary_path}")

    return radios, freq_totals


def choose_core_frequencies(freq_totals: Dict[float, int], core_count: int) -> List[float]:
    """Pick the top-N strongest center frequencies by total message count.

    Frequencies are returned in descending order of total messages, with
    a secondary sort by ascending frequency for stability.
    """
    sorted_items = sorted(
        freq_totals.items(),
        key=lambda kv: (-kv[1], kv[0]),
    )
    core_freqs = [freq for freq, _ in sorted_items[:core_count]]
    return core_freqs


def assign_core_to_radios(
    radios: Dict[str, Radio],
    core_freqs: List[float],
    freq_totals: Dict[float, int],
) -> Dict[float, List[Radio]]:
    """Assign each radio to a single "core" center frequency.

    Strategy:
      1. If the radio's observed center frequencies intersect the core set,
         choose the intersecting frequency with the highest global message
         total (freq_totals).
      2. Otherwise, compute the mean of the radio's center freqs and assign
         to whichever core frequency is closest in MHz.

    Returns:
      mapping core_freq_mhz -> list of Radio objects assigned there
    """
    if not core_freqs:
        return {}

    by_core: Dict[float, List[Radio]] = {cf: [] for cf in core_freqs}

    for radio in radios.values():
        if not radio.center_freqs_mhz:
            # Fallback: stick it on the strongest core
            assigned = core_freqs[0]
        else:
            # Step 1: intersection
            intersect = []
            for f in radio.center_freqs_mhz:
                for cf in core_freqs:
                    if abs(f - cf) < 1e-6:
                        intersect.append(cf)
                        break

            if intersect:
                # Choose the intersecting core freq with highest global total
                assigned = max(
                    intersect,
                    key=lambda cf: (freq_totals.get(cf, 0), cf),
                )
            else:
                # Step 2: nearest to mean
                mean_f = sum(radio.center_freqs_mhz) / float(len(radio.center_freqs_mhz))
                assigned = min(core_freqs, key=lambda cf: abs(cf - mean_f))

        radio.assigned_core_freq_mhz = assigned
        by_core.setdefault(assigned, []).append(radio)

    # For each core, sort radios by total_messages descending
    for cf in by_core:
        by_core[cf].sort(key=lambda r: (-r.total_messages, r.id))

    return by_core


def write_core_freqs_json(
    out_path: Path,
    summary_path: Path,
    core_freqs: List[float],
    freq_totals: Dict[float, int],
    radios_by_core: Dict[float, List[Radio]],
) -> None:
    """Emit core_freqs.json."""
    core_entries = []
    for rank, cf in enumerate(core_freqs, start=1):
        core_entries.append(
            {
                "rank": rank,
                "freq_mhz": cf,
                "total_messages": int(freq_totals.get(cf, 0)),
                "radio_ids": [r.id for r in radios_by_core.get(cf, [])],
            }
        )

    payload = {
        "generated_by": "rtlamr_scan_analyzer",
        "version": 1,
        "summary_file": str(summary_path),
        "core_freqs": core_entries,
    }

    out_path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")


def write_radios_json(
    out_path: Path,
    summary_path: Path,
    radios: Dict[str, Radio],
    radios_by_core: Dict[float, List[Radio]],
) -> None:
    """Emit radios.json with per-radio assignments and within-core ranks."""
    # Build a lookup of rank within each core
    core_rank: Dict[Tuple[float, str], int] = {}
    for cf, rlist in radios_by_core.items():
        for idx, r in enumerate(rlist, start=1):
            core_rank[(cf, r.id)] = idx

    radios_list = []
    for r in sorted(radios.values(), key=lambda r: (-r.total_messages, r.id)):
        cf = r.assigned_core_freq_mhz
        rank_in_core = core_rank.get((cf, r.id)) if cf is not None else None
        rd = r.to_dict()
        rd["rank_within_core"] = rank_in_core
        radios_list.append(rd)

    payload = {
        "generated_by": "rtlamr_scan_analyzer",
        "version": 1,
        "summary_file": str(summary_path),
        "radios": radios_list,
    }

    out_path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")


def write_suggested_commands_txt(
    out_path: Path,
    core_freqs: List[float],
    freq_totals: Dict[float, int],
    radios_by_core: Dict[float, List[Radio]],
    top_n_per_core: int = 10,
) -> None:
    """Emit suggested_rtlamr_commands.txt.

    For each core frequency, we dump up to top_n_per_core radios, sorted
    by total message count, with one rtlamr command per radio.
    """
    lines: List[str] = []
    lines.append("# Suggested rtlamr commands per core center frequency\n")

    for rank, cf in enumerate(core_freqs, start=1):
        total = int(freq_totals.get(cf, 0))
        lines.append(
            f"# Core {rank}: {cf:.3f} MHz (total messages across all radios: {total})"
        )
        radios = radios_by_core.get(cf, [])
        if not radios:
            lines.append("#   (no radios assigned)\n")
            continue

        lines.append("#   Top radios at/near this center frequency:\n")
        for r in radios[:top_n_per_core]:
            freqs_str = ", ".join(f"{f:.3f}" for f in r.center_freqs_mhz)
            lines.append(
                f"rtlamr -filterid={r.id} -format=json    # total={r.total_messages}, type={r.type}, freqs=[{freqs_str}]\n"
            )

        lines.append("")  # blank line between cores

    out_path.write_text("\n".join(lines), encoding="utf-8")


def find_latest_summary(log_dir: Path) -> Path:
    """Find the newest summary.txt under log_dir (non-recursive)."""
    candidates = []
    for child in log_dir.iterdir():
        if not child.is_dir():
            continue
        candidate = child / "summary.txt"
        if candidate.is_file():
            candidates.append(candidate)

    if not candidates:
        raise FileNotFoundError(f"No summary.txt found under {log_dir}")

    # Newest by modification time
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze rtlamr_multi_scan ISM sweep logs and propose core freqs."
    )
    parser.add_argument(
        "--summary",
        type=str,
        default=None,
        help="Path to summary.txt. If omitted, the newest under --log-dir is used.",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=str(Path.home() / "rtlamr_logs"),
        help="Root log directory to search when --summary is not given (default: ~/rtlamr_logs).",
    )
    parser.add_argument(
        "--core-count",
        type=int,
        default=2,
        help="How many core center frequencies to select (default: 2).",
    )
    parser.add_argument(
        "--top-n-per-core",
        type=int,
        default=10,
        help="How many radios per core to list in suggested_rtlamr_commands.txt (default: 10).",
    )

    args = parser.parse_args()

    log_dir = Path(os.path.expanduser(args.log_dir))
    if args.summary:
        summary_path = Path(args.summary).expanduser().resolve()
    else:
        summary_path = find_latest_summary(log_dir)

    if not summary_path.is_file():
        raise FileNotFoundError(f"summary.txt not found at {summary_path}")

    print(f"[*] Using summary file: {summary_path}")
    print(f"[*] Parsing summary...", flush=True)
    radios, freq_totals = parse_summary(summary_path)

    print(f"[*] Parsed {len(radios)} radios and {len(freq_totals)} center frequencies.")

    core_count = max(1, int(args.core_count))
    core_freqs = choose_core_frequencies(freq_totals, core_count)
    print("[*] Selected core center frequencies:")
    for rank, cf in enumerate(core_freqs, start=1):
        print(f"    {rank}. {cf:.3f} MHz (total messages: {freq_totals.get(cf, 0)})")

    radios_by_core = assign_core_to_radios(radios, core_freqs, freq_totals)

    out_dir = summary_path.parent
    core_freqs_path = out_dir / "core_freqs.json"
    radios_path = out_dir / "radios.json"
    suggested_cmds_path = out_dir / "suggested_rtlamr_commands.txt"

    print(f"[*] Writing {core_freqs_path} ...")
    write_core_freqs_json(core_freqs_path, summary_path, core_freqs, freq_totals, radios_by_core)

    print(f"[*] Writing {radios_path} ...")
    write_radios_json(radios_path, summary_path, radios, radios_by_core)

    print(f"[*] Writing {suggested_cmds_path} ...")
    write_suggested_commands_txt(
        suggested_cmds_path,
        core_freqs,
        freq_totals,
        radios_by_core,
        top_n_per_core=int(args.top_n_per_core),
    )

    print("[*] Done.")


if __name__ == "__main__":
    main()
