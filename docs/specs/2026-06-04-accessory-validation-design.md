# Design — Actuator-gated accessory validation

**Date:** 2026-06-04
**Status:** Approved (approach + shape). Two data slots pending (see §8).
**Area:** Product Code Finder — accessories picker.

---

## 1. Problem

Today the accessories picker lets the user select **any** family in **any** combination,
regardless of the chosen actuator (`app/accessories.py:1-21` documents this as
intentional). The user wants the selection **constrained by the resolved actuator's
class**: when a **Pneumatic** actuator is selected, only an allowlisted set of
accessory families may be chosen; the rest are locked out. The same applies to
**Electric** actuators with a different allowlist.

## 2. Decisions (clarified with the user, 2026-06-04)

- **Lockout style:** hard lock **+ auto-clear**. Blocked families are greyed out and
  unselectable. Any already-selected accessory whose family becomes blocked is
  **removed automatically**, with a small transient notice.
- **Gating:** rules apply **only when an actuator is resolved**. If the user has
  selected **only accessories** (no valve, no actuator), **no rules apply** — the
  picker stays wide open (current behavior).
- **Companion Flange (CFLG):** it is a *valve* accessory. Allowed only when a **valve
  is present** in the configuration; blocked in an **actuator-only** config.
- **SV ⇄ Positioner:** **mutually exclusive** (both directions). Selecting Solenoid
  Valve blocks the positioner family, and selecting the positioner blocks SV.
- **Scope:** Pneumatic **and** Electric rulesets. (Electric allowlist values pending —
  §8.)

### 2a. Positioner relabel (DEFERRED to user)

Investigation of the actual files established that the family currently labeled
**"PTR / Positioner Transmitter"** (`Positioner Data Sheet Structure_Final _R2.xlsx`,
`PS/PD` codes, "Electro-Pneumatic Positioner") is really the **Pneumatic Valve
Positioner** — there is **no genuine "Positioner Transmitter" dataset** anywhere
(neither a dedicated file nor a family in `Dashboard accessories.xlsx`). The other
file (`EVP Positioner Data Sheet…`, `ED` codes, "Electric Controller Card") is the
**Electronic Valve Positioner**. Source of the wrong label: `app/accessories.py:95`,
`("Positioner", "PTR", "T", "Positioner Transmitter")`, assigned during the
2026-06-03 split of the original 119-row positioner workbook.

**The user is separating PTR/PVP and renaming the files themselves.** This design
therefore leaves the **positioner families as a slot** (§5, §8) and does not perform
the rename. Intended end-state once the user's split lands:

- **Pneumatic actuator** → allow **Pneumatic Valve Positioner**, block Electronic.
- **Electric actuator** → allow **Electronic Valve Positioner (EVP)**, block Pneumatic.

## 3. Approach

**Approach A — frontend rule-config + enforcement in `AccessoryPicker`.**
Rules must react live to valve/actuator/accessory changes, all of which happen
client-side, so enforcement lives in the browser. The rule *data* lives in `app.js`
beside the picker to avoid a Python ↔ `catalog-engine.js` sync trap
(the deployed static engine is hand-maintained and diverges silently).

Rejected: **B** (backend serves allowlist) — forces every rule edit to be mirrored
into the static engine; **C** (pure backend filtering) — cannot react to live
SV⇄positioner toggles without round-trips.

## 4. Detection signals

- **Valve / actuator presence:** read the existing `category` field on the
  `valve-selector:resolved` / `:cleared` events (`"Valves"` vs `"Actuators"` —
  `app/static/app.js:374`, `app/catalog.py:647`). No new plumbing.
- **Actuator class (Pneumatic vs Electric):** **one new field** —
  add `actuatorClass: "Pneumatic" | "Electric"` to the resolved-event detail in
  `_emitResolvedEvent` (`app/static/app.js:370`), derived from the resolved
  actuator's `group` (`"Pneumatic"`, `app/catalog.py:649`) / `subgroup`
  (`"Electrical"`, `app/catalog.py:738`).

## 5. Components

### 5.1 Enriched resolved event
`_emitResolvedEvent` adds `actuatorClass` (null for valves; "Pneumatic"/"Electric"
for actuators).

### 5.2 Pure evaluator (no DOM) — `evaluateFamilies(state)`
```
evaluateFamilies({ actuatorClass, valvePresent, selectedFamilies })
  -> { allowed: Set<familyKey>, reasons: Map<familyKey, string> }
```
Logic:
1. `actuatorClass == null` → **all families allowed** (accessory-only / no-actuator gate).
2. else → `allowed = new Set(RULESET[actuatorClass].allow)`, then apply conditionals:
   - `cflgNeedsValve`: if `!valvePresent`, remove `CFLG` (reason: "needs a valve").
   - `svExcludesPositioner`: if `SV ∈ selectedFamilies`, remove the positioner family;
     if positioner ∈ selectedFamilies, remove `SV`. (reason: "SV and positioner are
     mutually exclusive").
3. `reasons` carries a human string per blocked family for the UI.

This function is pure and side-effect free (testable — §7).

### 5.3 `AccessoryPicker` changes (`app/static/app.js`)
New state: `actuatorClass` (null), `valvePresent` (false). New listeners on
`document` for `valve-selector:resolved` / `:cleared` that update this state (keyed
on `detail.category`) and then call `_applyValidation()`.

`_applyValidation()`:
1. Call `evaluateFamilies(...)`.
2. **Family dropdown:** for each `<option>`, set `disabled` + a reason suffix when its
   family is not in `allowed`. If the currently-selected dropdown family is now
   disabled, reset the dropdown to "All families".
3. **Search/datalist:** `_fillDatalist` excludes blocked families; `_trySelectFromSearch`
   refuses a code whose family is blocked.
4. **Auto-clear:** delete any entry in `this.selected` whose family is now blocked;
   if any were removed, show a transient notice and re-render chips + `_broadcast()`
   (the combined code updates itself via `accessories:selected-changed`).

Re-run `_applyValidation()` also after each successful selection change (SV⇄positioner
is dynamic).

### 5.4 Ruleset config (the encoded rules)
```js
const ACCESSORY_RULESETS = {
  Pneumatic: {
    allow: ["SV", "LSB", "FRG", "CFLG", "Gland", "Silencer",
            "FCV", "ALR", "QEV", "BKT", "THW FOR MSD",
            /* + Pneumatic Valve Positioner — SLOT (§8) */],
    conditionals: ["cflgNeedsValve", "svExcludesPositioner"],
  },
  Electric: {
    allow: [ /* PENDING Electric allowlist (§8) */
             /* + Electronic Valve Positioner (EVP) */ ],
    conditionals: ["cflgNeedsValve", "svExcludesPositioner"],
  },
};
```
Family keys are the `data_key`s from `ACCESSORY_FAMILY_ORDER` (`app/accessories.py:91`).
`FRG`→shown as AFR, `THW FOR MSD`→shown as THW, etc.

## 6. Pneumatic truth table (for verification)

| Family (data_key) | Pneumatic | Note |
|---|---|---|
| SV | ✅ | mutually exclusive with positioner |
| LSB | ✅ | |
| Pneumatic Valve Positioner | ✅ (slot) | mutually exclusive with SV |
| FRG (AFR) | ✅ | |
| CFLG | ✅* | only if valve present |
| Gland | ✅ | |
| Silencer | ✅ | |
| FCV | ✅ | |
| ALR | ✅ | |
| QEV | ✅ | |
| BKT | ✅ | "Bracket & Adapter" |
| THW FOR MSD | ✅ | |
| EVP (Electronic Valve Positioner) | ❌ | electric-only |
| MOR | ❌ | |
| Plug | ❌ | (pending data anyway) |
| Volume Booster | ❌ | |
| Tube & Fittings (FITTING) | ❌ | |
| Direct Mount | ❌ | (pending data anyway) |

## 7. Testing

The evaluator is pure JS; the repo has **no JS test runner** (tests are Python).
Plan:
- **Manual test matrix** (documented in the implementation plan): no-actuator →
  all open; Pneumatic → table in §6; Pneumatic + valve vs actuator-only (CFLG);
  SV then positioner and vice-versa (auto-clear + lockout); switch Pneumatic→Electric
  with selections present (auto-clear).
- **Optional (not in scope unless requested):** a small Node script under `tools/`
  importing `evaluateFamilies` for automated assertions.

## 8. Open slots (pending user input)

1. **Electric allowlist** — which families are allowed under an Electric actuator
   (plus confirmation the two conditionals carry over). Until provided, the Electric
   ruleset is an empty slot and Electric actuators behave as "block everything except
   the slot" — so **do not ship Electric** until this is filled.
2. **Positioner family keys** — the user's PTR/PVP split + rename. Once done, fill the
   "Pneumatic Valve Positioner" slot in the Pneumatic ruleset, the "Electronic Valve
   Positioner (EVP)" entry in the Electric ruleset, and point `svExcludesPositioner`
   at the correct key per class.

## 9. Out of scope
- The positioner file rename/relabel (user-owned).
- Any change to valve/actuator resolution beyond adding `actuatorClass` to the event.
- Backend/static-engine rule duplication.
</content>
</invoke>
