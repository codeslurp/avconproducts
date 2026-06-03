# AVCON Actuator-Pairing — Data Gap Report

_Generated: 2026-05-29_

**Source:** `docs/data/ball.json`, `docs/data/butterfly.json` (the same data the live site at codeslurp.github.io/avconproducts serves).

**"Empty" position** = a recommended-actuator cell that is blank, the literal `0`, or a broken-VLOOKUP Excel error (`#N/A` / `#REF!` / `#VALUE!`). Each valve has 11 positions: 9 pneumatic (Double-Acting / Fail-Close / Fail-Open, each at 3.5 / 4 / 5.5 bar) + 2 electric.

## 1. Executive summary

| Catalog | SKUs | Fully populated | Has >=1 empty | All 11 empty |
|---|--:|--:|--:|--:|
| Ball | 3,892 | 2,688 (69.1%) | 1,204 (30.9%) | 112 |
| Butterfly | 43,200 | 21,600 (50.0%) | 21,600 (50.0%) | 21,600 |

**22,804 SKUs** across both catalogs have at least one missing actuator position.

## 2.1 Ball — by series family

| Series prefix | SKUs | Fully populated | Partially empty | All 11 empty | Status |
|---|--:|--:|--:|--:|---|
| `2030F` | 672 | 392 | 280 | 0 | mixed |
| `2038F` | 672 | 392 | 280 | 0 | mixed |
| `2060F` | 504 | 336 | 168 | 0 | mixed |
| `2070F` | 1,204 | 840 | 364 | 0 | mixed |
| `2090F` | 840 | 728 | 0 | 112 | mixed |

## 2.2 Butterfly — by series family

| Series prefix | SKUs | Fully populated | Partially empty | All 11 empty | Status |
|---|--:|--:|--:|--:|---|
| `4020B` | 7,200 | 7,200 | 0 | 0 | all populated |
| `4020M` | 7,200 | 0 | 0 | 7,200 | **ALL EMPTY** |
| `4022B` | 7,200 | 7,200 | 0 | 0 | all populated |
| `4022M` | 7,200 | 0 | 0 | 7,200 | **ALL EMPTY** |
| `4023B` | 7,200 | 7,200 | 0 | 0 | all populated |
| `4023M` | 7,200 | 0 | 0 | 7,200 | **ALL EMPTY** |

## 3.1 Ball — by actuator position

| Position | Empty | % of SKUs | blank | zero | error |
|---|--:|--:|--:|--:|--:|
| Double Acting @ 3.5 bar | 112 | 2.9% | 0 | 0 | 112 |
| Double Acting @ 4 bar | 616 | 15.8% | 504 | 0 | 112 |
| Double Acting @ 5.5 bar | 616 | 15.8% | 0 | 504 | 112 |
| Spring Return Fail-Close @ 3.5 bar | 112 | 2.9% | 0 | 0 | 112 |
| Spring Return Fail-Close @ 4 bar | 112 | 2.9% | 0 | 0 | 112 |
| Spring Return Fail-Close @ 5.5 bar | 112 | 2.9% | 0 | 0 | 112 |
| Spring Return Fail-Open @ 3.5 bar | 112 | 2.9% | 0 | 0 | 112 |
| Spring Return Fail-Open @ 4 bar | 112 | 2.9% | 0 | 0 | 112 |
| Spring Return Fail-Open @ 5.5 bar | 784 | 20.1% | 0 | 672 | 112 |
| Electrical (1) | 196 | 5.0% | 0 | 0 | 196 |
| Electrical (2) | 196 | 5.0% | 0 | 0 | 196 |

## 3.2 Butterfly — by actuator position

| Position | Empty | % of SKUs | blank | zero | error |
|---|--:|--:|--:|--:|--:|
| Double Acting | 21,600 | 50.0% | 21,600 | 0 | 0 |
| Double Acting (alt 1) | 21,600 | 50.0% | 21,600 | 0 | 0 |
| Double Acting (alt 2) | 21,600 | 50.0% | 21,600 | 0 | 0 |
| Spring Return Fail-Close | 21,600 | 50.0% | 21,600 | 0 | 0 |
| Spring Return Fail-Close (alt 1) | 21,600 | 50.0% | 21,600 | 0 | 0 |
| Spring Return Fail-Close (alt 2) | 21,600 | 50.0% | 21,600 | 0 | 0 |
| Spring Return Fail-Open | 21,600 | 50.0% | 21,600 | 0 | 0 |
| Spring Return Fail-Open (alt 1) | 21,600 | 50.0% | 21,600 | 0 | 0 |
| Spring Return Fail-Open (alt 2) | 21,600 | 50.0% | 21,600 | 0 | 0 |
| Electrical (1) | 21,600 | 50.0% | 21,600 | 0 | 0 |
| Electrical (2) | 21,600 | 50.0% | 21,600 | 0 | 0 |

## 4. How to read blank vs zero vs error

- **blank** — cell never filled in. Most likely a *genuine gap* to fill.
- **zero (`0`)** — usually a deliberate "no actuator offered at this pressure" (a real spec limit), often correct as-is.
- **error (`#N/A`/`#REF!`/`#VALUE!`)** — the enrichment VLOOKUP found no match for that valve in the actuator-combination sheet (often a bad/missing series code).

## 5. Suggested priority

1. **Butterfly `…M` series** (`4020M`, `4022M`, `4023M`) — 21,600 SKUs with NO actuator data. Enrichment covers only the `…B` series. Either add combination data for the `M` variants or map them to their `…B` equivalents.

2. **Ball `2090F2005`** — 112 SKUs, every position `#N/A`. Likely a malformed series code (compare to normal `2090F155` / `2090F201`). Verify the code first.

3. **Ball Double-Acting @ 4 bar blanks** — the largest set of *blank* (not `0`) ball cells; most likely genuine fill-in gaps.

## 6. Exact codes

- `reports/actuator_data_gaps_by_sku.csv` — one row per SKU-with-gap: bare valve code, series, size, end connection, count + list of empty positions (with type).
- `reports/actuator_data_gaps_by_series.csv` — per series-prefix rollup.


_Re-run `py tools/report_data_gaps.py` after rebuilding `docs/` to refresh._
