"""Generate the actuator-pairing data-gap report.

Reads the published catalog JSON (docs/data/*.json — the exact data the live
site serves) and reports every valve SKU that is missing one or more
recommended-actuator positions. A position is "empty" when its cell is blank,
the literal 0, or a broken-VLOOKUP Excel error (#N/A / #REF! / #VALUE!).

Outputs (under reports/):
  actuator_data_gaps.md          - human-readable report (all tables)
  actuator_data_gaps_by_sku.csv  - one row per SKU-with-gap (exact codes)
  actuator_data_gaps_by_series.csv - per series-prefix rollup

Run from repo root:  py tools/report_data_gaps.py
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "docs" / "data"
OUT = REPO / "reports"
CATALOGS = ["ball", "butterfly"]
ERRORS = {"#N/A", "#REF!", "#VALUE!"}


def empty_kind(v) -> str | None:
    """Classify a cell: 'blank' | 'zero' | 'error' | None (populated)."""
    s = "" if v is None else str(v).strip()
    if s == "":
        return "blank"
    if s == "0":
        return "zero"
    if s in ERRORS:
        return "error"
    return None


def strip_prefix(label: str) -> str:
    return re.sub(r"^(Pneumatic|Electric(?:al)?)\s*—\s*", "", label or "")


def series_prefix(series: str) -> str:
    m = re.match(r"(\d+[A-Za-z]+)", str(series))
    return m.group(1) if m else str(series)


def load(cat: str):
    d = json.loads((DATA / f"{cat}.json").read_text(encoding="utf-8"))
    idx = {c: i for i, c in enumerate(d["columns_used"])}
    # Map config -> columns
    positions = [(p["model_col"], strip_prefix(p["label"])) for p in d["paired_actuators"]]
    detail = {f["label"]: f["col"] for f in d["detail_columns"]}
    cascade = {c["key"]: c["col"] for c in d["cascade"]}
    bare_col = detail.get("Bare Valve Code") or detail.get("Code") or d.get("primary_col")
    return d, idx, positions, cascade, bare_col


def analyse(cat: str):
    d, idx, positions, cascade, bare_col = load(cat)
    rows = d["rows"]
    n = len(rows)

    def g(r, col):
        return r[idx[col]] if col in idx else None

    # Some positions share a stripped label (the two "Electrical" columns).
    # Give each a distinct display label so the per-position table counts and
    # shows them separately instead of colliding on the same key.
    label_counts = Counter(lab for _, lab in positions)
    seen_lab, disp_labels = {}, []
    for _, lab in positions:
        if label_counts[lab] > 1:
            seen_lab[lab] = seen_lab.get(lab, 0) + 1
            disp_labels.append(f"{lab} ({seen_lab[lab]})")
        else:
            disp_labels.append(lab)

    pos_counts = [Counter() for _ in positions]   # by position index
    pref_roll = defaultdict(lambda: {"pop": 0, "partial": 0, "full": 0, "skus": 0})
    sku_rows = []   # detailed per-SKU gap rows
    full_pop = 0

    series_col = cascade.get("series")
    size_col = cascade.get("size")
    end_col = cascade.get("end_connection")

    for r in rows:
        empties = []  # (display_label, kind)
        for i, (col, _lab) in enumerate(positions):
            k = empty_kind(g(r, col))
            if k:
                empties.append((disp_labels[i], k))
                pos_counts[i][k] += 1
        series = g(r, series_col) if series_col else ""
        pref = series_prefix(series)
        roll = pref_roll[pref]
        roll["skus"] += 1
        if not empties:
            full_pop += 1
            roll["pop"] += 1
        else:
            if len(empties) == len(positions):
                roll["full"] += 1
            else:
                roll["partial"] += 1
            sku_rows.append({
                "catalog": cat,
                "bare_valve_code": g(r, bare_col),
                "series": series,
                "size": g(r, size_col) if size_col else "",
                "end_connection": g(r, end_col) if end_col else "",
                "num_empty": len(empties),
                "all_empty": len(empties) == len(positions),
                "empty_positions": "; ".join(f"{lab} ({k})" for lab, k in empties),
            })

    return {
        "cat": cat, "n": n, "disp_labels": disp_labels, "pos_counts": pos_counts,
        "pref_roll": dict(pref_roll), "sku_rows": sku_rows, "full_pop": full_pop,
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    results = [analyse(c) for c in CATALOGS]

    # ---- CSV: per SKU ----
    by_sku = OUT / "actuator_data_gaps_by_sku.csv"
    with by_sku.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "catalog", "bare_valve_code", "series", "size", "end_connection",
            "num_empty", "all_empty", "empty_positions"])
        w.writeheader()
        for res in results:
            for row in sorted(res["sku_rows"], key=lambda x: (-x["num_empty"], str(x["series"]))):
                w.writerow(row)

    # ---- CSV: per series prefix ----
    by_series = OUT / "actuator_data_gaps_by_series.csv"
    with by_series.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["catalog", "series_prefix", "total_skus", "fully_populated",
                    "partially_empty", "fully_empty", "status"])
        for res in results:
            for pref, c in sorted(res["pref_roll"].items()):
                status = ("ALL EMPTY" if c["pop"] == 0 and c["skus"] else
                          "all populated" if c["partial"] == 0 and c["full"] == 0 else "mixed")
                w.writerow([res["cat"], pref, c["skus"], c["pop"],
                            c["partial"], c["full"], status])

    # ---- Markdown report ----
    md = []
    md.append("# AVCON Actuator-Pairing — Data Gap Report\n")
    md.append("_Generated: 2026-05-29_\n")
    md.append("**Source:** `docs/data/ball.json`, `docs/data/butterfly.json` "
              "(the same data the live site at codeslurp.github.io/avconproducts serves).\n")
    md.append("**\"Empty\" position** = a recommended-actuator cell that is blank, "
              "the literal `0`, or a broken-VLOOKUP Excel error (`#N/A` / `#REF!` / `#VALUE!`). "
              "Each valve has 11 positions: 9 pneumatic (Double-Acting / Fail-Close / "
              "Fail-Open, each at 3.5 / 4 / 5.5 bar) + 2 electric.\n")

    # Executive summary
    md.append("## 1. Executive summary\n")
    md.append("| Catalog | SKUs | Fully populated | Has >=1 empty | All 11 empty |")
    md.append("|---|--:|--:|--:|--:|")
    total_gap = 0
    for res in results:
        gaps = len(res["sku_rows"])
        allempty = sum(1 for r in res["sku_rows"] if r["all_empty"])
        total_gap += gaps
        md.append(f"| {res['cat'].title()} | {res['n']:,} | "
                  f"{res['full_pop']:,} ({100*res['full_pop']/res['n']:.1f}%) | "
                  f"{gaps:,} ({100*gaps/res['n']:.1f}%) | {allempty:,} |")
    md.append(f"\n**{total_gap:,} SKUs** across both catalogs have at least one missing "
              "actuator position.\n")

    # Per-series rollup (gaps only)
    for res in results:
        md.append(f"## 2.{results.index(res)+1} {res['cat'].title()} — by series family\n")
        md.append("| Series prefix | SKUs | Fully populated | Partially empty | All 11 empty | Status |")
        md.append("|---|--:|--:|--:|--:|---|")
        for pref, c in sorted(res["pref_roll"].items()):
            if c["partial"] == 0 and c["full"] == 0:
                status = "all populated"
            elif c["pop"] == 0:
                status = "**ALL EMPTY**"
            else:
                status = "mixed"
            md.append(f"| `{pref}` | {c['skus']:,} | {c['pop']:,} | "
                      f"{c['partial']:,} | {c['full']:,} | {status} |")
        md.append("")

    # Per-position breakdown
    for res in results:
        md.append(f"## 3.{results.index(res)+1} {res['cat'].title()} — by actuator position\n")
        md.append("| Position | Empty | % of SKUs | blank | zero | error |")
        md.append("|---|--:|--:|--:|--:|--:|")
        for i, lab in enumerate(res["disp_labels"]):
            cc = res["pos_counts"][i]
            tot = sum(cc.values())
            if tot:
                md.append(f"| {lab} | {tot:,} | {100*tot/res['n']:.1f}% | "
                          f"{cc['blank']:,} | {cc['zero']:,} | {cc['error']:,} |")
        md.append("")

    # Interpretation + priorities
    md.append("## 4. How to read blank vs zero vs error\n")
    md.append("- **blank** — cell never filled in. Most likely a *genuine gap* to fill.\n"
              "- **zero (`0`)** — usually a deliberate \"no actuator offered at this pressure\" "
              "(a real spec limit), often correct as-is.\n"
              "- **error (`#N/A`/`#REF!`/`#VALUE!`)** — the enrichment VLOOKUP found no match "
              "for that valve in the actuator-combination sheet (often a bad/missing series code).\n")

    md.append("## 5. Suggested priority\n")
    md.append("1. **Butterfly `…M` series** (`4020M`, `4022M`, `4023M`) — 21,600 SKUs with NO "
              "actuator data. Enrichment covers only the `…B` series. Either add combination "
              "data for the `M` variants or map them to their `…B` equivalents.\n")
    md.append("2. **Ball `2090F2005`** — 112 SKUs, every position `#N/A`. Likely a malformed "
              "series code (compare to normal `2090F155` / `2090F201`). Verify the code first.\n")
    md.append("3. **Ball Double-Acting @ 4 bar blanks** — the largest set of *blank* (not `0`) "
              "ball cells; most likely genuine fill-in gaps.\n")

    md.append("## 6. Exact codes\n")
    md.append("- `reports/actuator_data_gaps_by_sku.csv` — one row per SKU-with-gap: bare valve "
              "code, series, size, end connection, count + list of empty positions (with type).\n"
              "- `reports/actuator_data_gaps_by_series.csv` — per series-prefix rollup.\n")
    md.append("\n_Re-run `py tools/report_data_gaps.py` after rebuilding `docs/` to refresh._\n")

    (OUT / "actuator_data_gaps.md").write_text("\n".join(md), encoding="utf-8")

    # Console summary
    print("Wrote:")
    for p in ("actuator_data_gaps.md", "actuator_data_gaps_by_sku.csv",
              "actuator_data_gaps_by_series.csv"):
        fp = OUT / p
        print(f"  reports/{p}  ({fp.stat().st_size:,} bytes)")
    sku_total = sum(len(r["sku_rows"]) for r in results)
    print(f"Detailed CSV rows (SKUs with gaps): {sku_total:,}")


if __name__ == "__main__":
    main()
