"""Regression test: Recommended-Actuator panel must surface every distinct
(model, pressure-label) position, not collapse same-model-across-pressures.

Screenshot valve (Ball) had 9 populated pneumatic columns but only 5 chips
rendered because dedup keyed on (target_type, model) alone, dropping the
3.5/4/5.5-bar repeats of the same model. Expected: all 9 distinct
(model,label) pneumatic chips survive; identical electric twins still collapse.

Run from repo root:  py tools/test_paired_dedup.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "app")
from catalog import load_all  # noqa: E402

PNEU_COLS = [100, 101, 102, 103, 104, 105, 106, 107, 108]


def main() -> int:
    cats = load_all(Path("data"))
    ball = cats["ball"]

    # Find the screenshot row: Double-Acting@3.5 == ACT-050D and
    # Fail-Open@3.5 == ACT-063SR05 (the exact combo from the bug report).
    target = None
    for row in ball.rows:
        if row.get("c100") == "ACT-050D" and row.get("c106") == "ACT-063SR05":
            target = row
            break
    assert target is not None, "screenshot row not found in Ball catalog"

    # Reconstruct the cascade picks that uniquely select this row.
    picks = {key: target.get(f"c{col}") for key, col, _ in ball.config.cascade}
    detail = ball.resolve(picks)
    assert detail is not None, "resolve() returned no match for screenshot picks"

    paired = detail.get("paired_actuators", [])
    pneumatic = [p for p in paired if p["target_type"] in ("pneumatic_rp", "pneumatic_sy")]

    # How many DISTINCT (model,label) pneumatic positions does the DB row carry?
    expected_distinct = len({
        (target.get(f"c{c}"),
         dict((pa.model_col, pa.label) for pa in ball.config.paired_actuators)[c])
        for c in PNEU_COLS
        if target.get(f"c{c}") not in (None, "", "0")
    })

    print(f"DB pneumatic columns populated (non-sentinel): "
          f"{sum(1 for c in PNEU_COLS if target.get(f'c{c}') not in (None, '', '0'))}")
    print(f"Distinct (model,label) pneumatic positions:    {expected_distinct}")
    print(f"Chips rendered by resolve():                   {len(pneumatic)}")
    for p in pneumatic:
        print(f"    {p['model']:<14} {p['label']}")

    if len(pneumatic) == expected_distinct:
        print(f"\nPASS — all {expected_distinct} distinct pneumatic positions surfaced.")
        return 0
    print(f"\nFAIL — expected {expected_distinct} chips, got {len(pneumatic)} "
          f"(same-model pressure variants are being dropped).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
